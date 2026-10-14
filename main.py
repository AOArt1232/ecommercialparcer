

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from playwright.sync_api import sync_playwright
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError



AMAZON_URL = "https://www.amazon.com/Best-Sellers/zgbs"

import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsProactorEventLoopPolicy()
    )

from fastapi import FastAPI

app = FastAPI()


def get_products():
    url = "https://www.amazon.com/Best-Sellers/zgbs"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        page = browser.new_page()

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        # Give Amazon a moment to render the products
        page.wait_for_timeout(5000)

        # Amazon products have data-asin
        products = page.locator("[data-asin]")

        result = []

        for i in range(products.count()):
            product = products.nth(i)

            asin = product.get_attribute("data-asin")

            if not asin:
                continue

            # Find the product container
            container = product.locator(
                "xpath=ancestor::*[@id='gridItemRoot'][1]"
            )

            if container.count() == 0:
                container = product

            # Title
            image = container.locator("img").first
            title = image.get_attribute("alt") or "N/A"

            # Price
            price_locator = container.locator(
                ".p13n-sc-price, .a-size-base.a-color-price"
            )

            price = "N/A"

            if price_locator.count() > 0:
                price = price_locator.first.inner_text().strip()

            # Rating
            rating_locator = container.locator(".a-icon-alt")

            rating = "N/A"

            if rating_locator.count() > 0:
                rating = rating_locator.first.inner_text().strip()

            # Product link
            link = f"https://www.amazon.com/dp/{asin}"

            # Image
            image_url = image.get_attribute("src")

            if not image_url:
                image_url = image.get_attribute("data-src")

            result.append({
                "title": title.strip(),
                "price": price,
                "rating": rating,
                "link": link,
                "image": image_url
            })

            # We only need 3
            if len(result) == 3:
                break

        browser.close()

        print()
        return result

@app.get("/products")
def products_api():
    return get_products()


@app.get("/", response_class=HTMLResponse)
def home():
    products = get_products()

    html = """
    <html>
    <head>
        <title>Amazon Best Sellers</title>
        <style>
            body {
                font-family: Arial;
                background: #f5f5f5;
                padding: 40px;
            }

            .products {
                display: flex;
                gap: 30px;
                justify-content: center;
            }

            .product {
                background: white;
                width: 280px;
                padding: 20px;
                border-radius: 10px;
            }

            .product img {
                width: 100%;
                height: 250px;
                object-fit: contain;
            }

            .title {
                font-weight: bold;
                margin-top: 15px;
            }

            .price {
                font-size: 20px;
                color: #B12704;
                margin-top: 10px;
            }

            .rating {
                margin-top: 10px;
            }

            a {
                display: block;
                background: #ff9900;
                color: black;
                text-align: center;
                padding: 10px;
                margin-top: 15px;
                text-decoration: none;
            }
        </style>
    </head>

    <body>
        <h1>Amazon Best Sellers</h1>
        <div class="products">
    """

    for product in products:
        html += f"""
            <div class="product">
                <img src="{product['image'] or ''}">

                <div class="title">
                    {product['title']}
                </div>

                <div class="price">
                    {product['price']}
                </div>

                <div class="rating">
                    ⭐ {product['rating']}
                </div>

                <a href="{product['link']}" target="_blank">
                    View on Amazon
                </a>
            </div>
        """

    html += """
        </div>
    </body>
    </html>
    """

    return html


def get_categories():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto(
            "https://www.amazon.com/Best-Sellers/zgbs",
            wait_until="domcontentloaded",
            timeout=60000
        )

        page.wait_for_timeout(5000)

        links = page.locator("a")

        categories = []

        for i in range(links.count()):
            link = links.nth(i)

            href = link.get_attribute("href")
            text = link.inner_text().strip()

            if (
                href
                and "/Best-Sellers-" in href
                and text
            ):
                if href.startswith("/"):
                    href = "https://www.amazon.com" + href

                categories.append({
                    "name": text,
                    "link": href
                })

        browser.close()

        return categories




class Subcategory(BaseModel):
    name: str
    link: str


async def get_subcategories(category: str) -> List[dict]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            )
        )

        page = await context.new_page()

        try:
            # Search Amazon for the requested category.
            search_url = (
                "https://www.amazon.com/s"
                f"?k={category.replace(' ', '+')}"
            )

            await page.goto(
                search_url,
                wait_until="domcontentloaded",
                timeout=30_000,
            )

            # Amazon may display a CAPTCHA or other bot-protection page.
            if "captcha" in page.url.lower():
                raise HTTPException(
                    status_code=503,
                    detail="Amazon presented a CAPTCHA."
                )

            # Wait for the search results/category navigation to load.
            await page.wait_for_load_state("networkidle", timeout=15_000)

            subcategories = []

            # Amazon's category/navigation links vary between pages,
            # so inspect links that point to Amazon category nodes.
            links = await page.locator("a").all()

            for link in links:
                text = (await link.inner_text()).strip()
                href = await link.get_attribute("href")

                if not text or not href:
                    continue

                # Category links commonly contain /b/ or /gp/browse.
                if "/b/" not in href and "/gp/browse" not in href:
                    continue

                if href.startswith("/"):
                    href = "https://www.amazon.com" + href

                # Remove tracking/query parameters where possible.
                href = href.split("?")[0]

                item = {
                    "name": text,
                    "link": href,
                }

                # Avoid duplicates.
                if item not in subcategories:
                    subcategories.append(item)

            return subcategories

        except PlaywrightTimeoutError:
            raise HTTPException(
                status_code=504,
                detail="Amazon took too long to respond."
            )

        finally:
            await browser.close()


@app.get("/subcategories", response_model=List[Subcategory])
async def subcategories(category: str):
    if not category.strip():
        raise HTTPException(
            status_code=400,
            detail="The category parameter cannot be empty."
        )

    return await get_subcategories(category.strip())



@app.get("/categories")
def categories_api():
    return get_categories()

# from playwright.sync_api import sync_playwright
#
# with sync_playwright() as p:
#     browser = p.chromium.launch(headless=False)
#     page = browser.new_page()
#
#     page.goto(
#         "https://www.amazon.com",
#         wait_until="domcontentloaded",
#         timeout=60000
#     )
#
#     print(page.title())
#     print(page.url)
#
#     page.wait_for_timeout(10000)
#
#     browser.close()

# if __name__ == "__main__":
#     get_products()
#     get_categories()