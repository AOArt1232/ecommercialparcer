import sqlite3

connection = sqlite3.connect("products.db")
cursor = connection.cursor()

print("Tables:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
print(cursor.fetchall())

print("\nProducts table structure:")
cursor.execute("PRAGMA table_info(products)")
print(cursor.fetchall())

print("\nProducts:")
cursor.execute("SELECT * FROM products")
print(cursor.fetchall())

connection.close()