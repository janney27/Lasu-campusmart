import sqlite3

# =========================================
# PRODUCT CATALOG — LASU CampusMart
# =========================================

PRODUCTS = [
    # ===== 📚 Academic Materials (1-5) =====
    {
        "name": "A4 200-Page Spiral Notebook",
        "price": 1500,
        "category": "academic",
        "description": "High-quality A4 spiral notebook with 200 pages. Perfect for lectures and notes.",
        "location": "LASU Bookshop",
        "image": "https://picsum.photos/seed/notebook/600/600"
    },
    {
        "name": "Bic Cristal Ballpoint Pen",
        "price": 200,
        "category": "academic",
        "description": "Classic Bic Cristal ballpoint pen. Smooth writing, long-lasting ink.",
        "location": "LASU Bookshop",
        "image": "https://picsum.photos/seed/pen/600/600"
    },
    {
        "name": "A4 Document File Folder",
        "price": 800,
        "category": "academic",
        "description": "Durable A4 file folder for organizing important documents and assignments.",
        "location": "LASU Bookshop",
        "image": "https://picsum.photos/seed/folder/600/600"
    },
    {
        "name": "Casio FX-991ES Plus Scientific Calculator",
        "price": 12500,
        "category": "academic",
        "description": "Genuine Casio FX-991ES Plus. Ideal for engineering, science, and mathematics students.",
        "location": "Faculty of Science",
        "image": "https://picsum.photos/seed/calculator/600/600"
    },
    {
        "name": "STABILO Boss Original Highlighter",
        "price": 1200,
        "category": "academic",
        "description": "Premium STABILO highlighter with vibrant colors. Perfect for studying.",
        "location": "LASU Bookshop",
        "image": "https://picsum.photos/seed/highlighter/600/600"
    },

    # ===== 💻 Phone & Computer Accessories (6-12) =====
    {
        "name": "SanDisk 64GB USB Flash Drive",
        "price": 6500,
        "category": "tech",
        "description": "Genuine SanDisk 64GB USB drive. Fast transfer speeds, reliable storage.",
        "location": "Student Union Building",
        "image": "https://picsum.photos/seed/usb/600/600"
    },
    {
        "name": "Logitech M185 Wireless Mouse",
        "price": 9500,
        "category": "tech",
        "description": "Reliable Logitech wireless mouse with long battery life. USB nano receiver included.",
        "location": "ICT Centre",
        "image": "https://picsum.photos/seed/mouse/600/600"
    },
    {
        "name": "Anker 20W USB-C Phone Charger",
        "price": 8500,
        "category": "tech",
        "description": "Fast-charging Anker 20W USB-C adapter. Compact and travel-friendly.",
        "location": "ICT Centre",
        "image": "https://picsum.photos/seed/charger/600/600"
    },
    {
        "name": "Oraimo 10,000mAh Power Bank",
        "price": 15000,
        "category": "tech",
        "description": "Oraimo power bank with 10,000mAh capacity. Charge your phone multiple times.",
        "location": "Student Union Building",
        "image": "https://picsum.photos/seed/powerbank/600/600"
    },
    {
        "name": "Ugreen USB-C to USB-C Cable",
        "price": 3500,
        "category": "tech",
        "description": "Durable Ugreen Type-C cable. Fast charging and data transfer.",
        "location": "ICT Centre",
        "image": "https://picsum.photos/seed/cable/600/600"
    },
    {
        "name": "HP Wireless Keyboard",
        "price": 18500,
        "category": "tech",
        "description": "HP wireless keyboard with comfortable typing. Ideal for study and work.",
        "location": "ICT Centre",
        "image": "https://picsum.photos/seed/keyboard/600/600"
    },
    {
        "name": "HP Laptop Stand",
        "price": 12000,
        "category": "tech",
        "description": "Ergonomic HP laptop stand. Improves posture and cooling.",
        "location": "ICT Centre",
        "image": "https://picsum.photos/seed/laptopstand/600/600"
    },

    # ===== 🎒 Student Essentials (13-17) =====
    {
        "name": "Waterproof Student Backpack",
        "price": 14500,
        "category": "essentials",
        "description": "Spacious waterproof backpack with laptop compartment. Perfect for campus.",
        "location": "Student Union Building",
        "image": "https://picsum.photos/seed/backpack/600/600"
    },
    {
        "name": "Stainless Steel 750ml Water Bottle",
        "price": 4500,
        "category": "essentials",
        "description": "Insulated stainless steel bottle. Keeps drinks cold for 12 hours.",
        "location": "Student Union Building",
        "image": "https://picsum.photos/seed/bottle/600/600"
    },
    {
        "name": "Foldable Student Umbrella",
        "price": 3500,
        "category": "essentials",
        "description": "Compact foldable umbrella. Windproof and lightweight.",
        "location": "Student Union Building",
        "image": "https://picsum.photos/seed/umbrella/600/600"
    },
    {
        "name": "Universal ID Card Holder & Lanyard",
        "price": 1500,
        "category": "essentials",
        "description": "Durable ID card holder with LASU-themed lanyard.",
        "location": "Student Union Building",
        "image": "https://picsum.photos/seed/idcard/600/600"
    },
    {
        "name": "Rechargeable LED Reading Lamp",
        "price": 7500,
        "category": "essentials",
        "description": "Rechargeable LED reading lamp. Perfect for late-night study sessions.",
        "location": "Student Union Building",
        "image": "https://picsum.photos/seed/lamp/600/600"
    },

    # ===== 👕 University Merchandise (18-22) =====
    {
        "name": "LASU-Branded Polo Shirt",
        "price": 9500,
        "category": "merch",
        "description": "Official LASU-branded polo shirt. Comfortable cotton fabric.",
        "location": "LASU Merchandise Store",
        "image": "https://picsum.photos/seed/polo/600/600"
    },
    {
        "name": "LASU-Branded T-Shirt",
        "price": 6500,
        "category": "merch",
        "description": "Official LASU-branded T-shirt. Available in multiple sizes.",
        "location": "LASU Merchandise Store",
        "image": "https://picsum.photos/seed/tshirt/600/600"
    },
    {
        "name": "LASU-Branded Face Cap",
        "price": 4500,
        "category": "merch",
        "description": "Official LASU face cap. Adjustable strap.",
        "location": "LASU Merchandise Store",
        "image": "https://picsum.photos/seed/cap/600/600"
    },
    {
        "name": "LASU-Branded Backpack",
        "price": 18500,
        "category": "merch",
        "description": "Official LASU branded backpack. Premium quality.",
        "location": "LASU Merchandise Store",
        "image": "https://picsum.photos/seed/lasubag/600/600"
    },
    {
        "name": "LASU-Branded Water Bottle",
        "price": 5000,
        "category": "merch",
        "description": "Official LASU-branded water bottle. Insulated and durable.",
        "location": "LASU Merchandise Store",
        "image": "https://picsum.photos/seed/lasubottle/600/600"
    },

    # ===== 🧪 Faculty-Specific Items (23-27) =====
    {
        "name": "Engineering Technical Drawing Set",
        "price": 8500,
        "category": "faculty",
        "description": "Complete technical drawing set for engineering students.",
        "location": "Faculty of Engineering",
        "image": "https://picsum.photos/seed/drawingset/600/600"
    },
    {
        "name": "White Laboratory Coat",
        "price": 7000,
        "category": "faculty",
        "description": "Standard white lab coat. Required for science and medical students.",
        "location": "Faculty of Science",
        "image": ""
    },
    {
        "name": "Scientific Laboratory Notebook",
        "price": 2500,
        "category": "faculty",
        "description": "Hardcover lab notebook for recording experiments.",
        "location": "Faculty of Science",
        "image": "https://picsum.photos/seed/labnotebook/600/600"
    },
    {
        "name": "Law Student Case File Folder",
        "price": 3500,
        "category": "faculty",
        "description": "Premium case file folder for law students.",
        "location": "Faculty of Law",
        "image": "https://picsum.photos/seed/casefile/600/600"
    },
    {
        "name": "Engineering Scientific Calculator",
        "price": 15500,
        "category": "faculty",
        "description": "Advanced scientific calculator for engineering students.",
        "location": "Faculty of Engineering",
        "image": "https://picsum.photos/seed/engcalc/600/600"
    },

    # ===== 🖨️ Campus Services (28-30) =====
    {
        "name": "A4 Document Printing Service",
        "price": 50,
        "category": "services",
        "description": "Black & white A4 printing service. Per page.",
        "location": "LASU ICT Centre",
        "image": "https://picsum.photos/seed/printing/600/600"
    },
    {
        "name": "Document Spiral Binding Service",
        "price": 800,
        "category": "services",
        "description": "Professional spiral binding for projects and reports.",
        "location": "LASU ICT Centre",
        "image": "https://picsum.photos/seed/binding/600/600"
    },
    {
        "name": "A4 Document Lamination Service",
        "price": 500,
        "category": "services",
        "description": "Durable A4 lamination. Protects important documents.",
        "location": "LASU ICT Centre",
        "image": "https://picsum.photos/seed/lamination/600/600"
    },
]


# =========================================
# INSERT INTO DATABASE
# =========================================

def insert_products():
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()

    added = 0
    skipped = 0

    for p in PRODUCTS:
        # Skip if a product with same name already exists
        cursor.execute(
            "SELECT id FROM products WHERE product_name = ?",
            (p["name"],)
        )
        if cursor.fetchone():
            skipped += 1
            continue

        cursor.execute("""
            INSERT INTO products
            (product_name, price, category, description, location, image)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            p["name"],
            p["price"],
            p["category"],
            p["description"],
            p["location"],
            p["image"]
        ))
        added += 1

    connection.commit()
    connection.close()

    print(f"✅ Added {added} products")
    print(f"⏭️  Skipped {skipped} (already existed)")


if __name__ == "__main__":
    insert_products()