from fastapi import FastAPI
from playwright.sync_api import sync_playwright

app = FastAPI()


def parse_product(product):
    title = product.locator("div._cDEzb_p13n-sc-css-line-clamp-3_g3dy1").inner_text()
    price = product.locator(".p13n-sc-price").inner_text()
    rating = product.locator(".a-icon-alt").first.inner_text()

    link = product.locator("a").first.get_attribute("href")
    picture = product.locator("img").first.get_attribute("src")

    if link and link.startswith("/"):
        link = "https://www.amazon.com" + link

    return {
        "title": title,
        "price": price,
        "rating": rating,
        "link": link,
        "picture": picture,
    }


@app.get("/products")
def get_products():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(
            "https://www.amazon.com/Best-Sellers/zgbs",
            wait_until="domcontentloaded"
        )

        products = page.locator("div.zg-grid-general-faceout")
        products.first.wait_for()

        result = [
            parse_product(products.nth(i))
            for i in range(min(3, products.count()))
        ]

        browser.close()

        return result

