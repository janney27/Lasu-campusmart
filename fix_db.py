import sqlite3

connection = sqlite3.connect("marketplace.db")
cursor = connection.cursor()

# ---- Orders columns ----
cursor.execute("PRAGMA table_info(orders)")
columns = [row[1] for row in cursor.fetchall()]
print("Existing columns:", columns)

if "status" not in columns:
    cursor.execute("ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'Pending'")
    print("✅ Added 'status' column")
else:
    print("⏭️  'status' column already exists")

if "created_at" not in columns:
    cursor.execute("ALTER TABLE orders ADD COLUMN created_at TIMESTAMP")
    print("✅ Added 'created_at' column")
else:
    print("⏭️  'created_at' column already exists")


# ---- Create vendors table if missing ----
cursor.execute("""
    CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        business_name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'Pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
print("✅ Vendors table ready")

 # ---- Create users table if missing ----
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        matric_or_staff_id TEXT NOT NULL,
        role TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
print("✅ Users table ready")


cursor.execute("""
    CREATE TABLE IF NOT EXISTS wishlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, product_id)
    )
""")
print("✅ Wishlist table ready")

# ---- Add 'stock' column to products if missing ----

cursor.execute("PRAGMA table_info(products)")
product_columns = [row[1] for row in cursor.fetchall()]

if "stock" not in product_columns:
    cursor.execute("ALTER TABLE products ADD COLUMN stock INTEGER DEFAULT 10")
    print("✅ Added 'stock' column to products (default: 10)")

    # Set existing products to have stock of 10
    cursor.execute("UPDATE products SET stock = 10 WHERE stock IS NULL")
    print("✅ Set stock = 10 for existing products")
else:
    print("⏭️  'stock' column already exists")

cursor.execute("PRAGMA table_info(users)")
user_columns = [row[1] for row in cursor.fetchall()]


if "phone" not in user_columns:
    cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    print("✅ Added 'phone' column to users table")
else:
    print("⏭️  'phone' column already exists")
    
# ---- Close connection (LAST) ----
connection.commit()
connection.close()
print("Done.")