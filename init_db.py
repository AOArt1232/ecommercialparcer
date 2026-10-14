import sqlite3


connection = sqlite3.connect("products.db")

cursor = connection.cursor()

cursor.execute("""
    DROP TABLE IF EXISTS products
""")

cursor.execute("""
    CREATE TABLE products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        price TEXT,
        rating TEXT,
        link TEXT,
        picture TEXT
    )
""")

connection.commit()
connection.close()

print("Database initialized.")