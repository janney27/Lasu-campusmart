import sqlite3

conn = sqlite3.connect("marketplace.db")
cur = conn.cursor()

# =========================================
# EDIT BELOW: match the product by its CURRENT name on your site,
# =========================================

updates = [
    {
        "current_name": "White Laboratory Coat",
        "new_name": "White Laboratory Coat",
        "new_image": "https://plus.unsplash.com/premium_photo-1673953886001-d866feca057f?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTIwfHxsYWJvcmF0b3J5JTIwY29hdHxlbnwwfHwwfHx8MA%3D%3D",
        "new_price": 7000
    },

    {
    "current_name": "LASU-Branded Water Bottle In Packs",
    "new_name": "LASU-Branded Water Bottle In Packs",
    "new_image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQZ7XBPlIyTZhU3Dbp7Q_l5lp4n92ML4ekRCyTxrkXjCg&s=10",
    "new_price": 2000
},

    {
        "current_name":"A4 Document Printing Service",
        "new_name": "A4 Document Printing Service",
        "new_image": "https://d2k7xl8xl93d43.cloudfront.net/images/opt/products_gallery_images/Hot-Lamination-Documents-1_1767750461660.png?v=1896",
        "new_price": 100
    },

    {
        "current_name": "Document Spiral Binding Service",
        "new_name": "Document Spiral Binding Service",
        "new_image": "https://static.vecteezy.com/system/resources/thumbnails/071/881/615/small/open-spiral-notebook-with-blank-white-page-photo.jpg",
        "new_price": 500
    },

    {
        "current_name":"Universal ID Card Holder & Lanyard",
        "new_name":"Universal ID Card Holder & Lanyard",
        "new_image":"https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSXxODD_CSsUN5Taq_QWAkg4ilUif43C_PcLzU-mPpM-Q&s=10",
        "new_price": 1500
    },

    {
        "current_name": "Foldable Student Umbrella",
        "new_name": "PORTABLE UNISEX FOLDABLE UMBRELLA HIGH QUALITY FOR STUDENT",
        "new_image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQqw13ugowUHFoFb4e5m_Gpn9fYpc5FAqITmAj6LD_72w&s=10",
        "new_price": 8000
    },


    {
        "current_name": "A4 Document Lamination Service",
        "new_name": "A4 Document Lamination Service",
        "new_image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRij6THT5BskZldluT8efbRUAORmRF5bMi98lK5Phd_NA&s=10",
        "new_price": 500
    },


    {
        "current_name": "Anker 20W USB-C Phone Charger",
        "new_name": "Samsung Samsung CHARGER 45W SUPER FAST CHARGER ADAPTIVE CHARGING FOR NOTE 20 Ultra S20 S21 S22 S23 S24 S25 S26 Ultra Type-C To Type C",
        "new_image": "https://ng.jumia.is/unsafe/fit-in/500x500/filters:fill(white)/product/07/8976272/1.jpg?1518",
        "new_price": 6000
    },


    {
        "current_name": "Engineering Scientific Calculator",
        "new_name": "CASIO FX-9750GLL-WE White",
        "new_image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSz2Q2k9sHoHp-LXSb-Id64UsFbmTcdUwVegljzdGTyQL0SaAcBRJIR97E&s=10",
        "new_price": 15000
    },

    {
        "current_name": "Scientific Laboratory Notebook",
        "new_name": "Scientific Laboratory Notebook",
        "new_image": "https://m.media-amazon.com/images/I/71hnxsHo5aL._AC_UF894,1000_QL80_.jpg",
        "new_price": 3000
    },

    {
        "current_name": "Law Student Case File Folder",
        "new_name": "Law Student Case File Folder",
        "new_image": "https://m.media-amazon.com/images/I/518rUDqO+fL._AC_UF350,350_QL80_.jpg",
        "new_price": 4000
    },

    {
            "current_name": "Engineering Technical Drawing Set",
            "new_name": "Engineering Technical Drawing Set",
            "new_image": "https://img.kwcdn.com/product/fancy/61343abc-488c-4916-b95e-cedd557088de.jpg?imageMogr2/auto-orient%7CimageView2/2/w/800/q/70/format/webp",
            "new_price": 5000
    },


        {
                "current_name": "Bic Cristal Ballpoint Pen",
                "new_name": "Vista Titan Ballpoint Pen - 50pcs",
                "new_image": "https://www-konga-com-res.cloudinary.com/image/upload/f_auto,q_auto,w_640,c_limit/media/catalog/product/E/K/62214_1793379415.jpg",
                "new_price": 6500
     },

     {
             "current_name": "Ugreen USB-C to USB-C Cable",
             "new_name": "SupDevice 3 in 1 USB Charging Cable for iPhone/Type-C/Micro USB Charger Cable for iPhone 14 13 12 Pro Max Xs Max Charger Cable for Redmi, OnePlus, SamSung USB C Mobile Phones,",
             "new_image": "https://ng.jumia.is/unsafe/fit-in/680x680/filters:fill(white)/product/65/8050024/2.jpg?3067",
             "new_price": 1200
    },


    {
            "current_name": "LASU-Branded Polo Shirt",
            "new_name": "TOUPHY T-Shirts +Shorts 100% Cotton Men's Short Sleeve Set-White",
            "new_image": "https://ng.jumia.is/unsafe/fit-in/680x680/filters:fill(white)/product/64/986649/1.jpg?6662",
            "new_price": 9000
    },


    {
            "current_name": "LASU-Branded T-Shirt",
            "new_name": "Corporate Quality Office Long Sleeve Shirt",
            "new_image": "https://ng.jumia.is/unsafe/fit-in/680x680/filters:fill(white)/product/69/7419914/1.jpg?5563",
            "new_price": 34000
    },


    {
            "current_name": "LASU-Branded Face Cap",
            "new_name": "LADIES STAR-PRINTED LONG SLEEVE TOP AND TROUSER",
            "new_image": "https://ng.jumia.is/unsafe/fit-in/680x680/filters:fill(white)/product/76/2426814/1.jpg?6078",
            "new_price": 12550
   },

   {
               "current_name": "HP Laptop Stand",
               "new_name": "GUEETON Plastic Foldable Adjustable Stand Holder For Laptop White",
               "new_image": "https://ng.jumia.is/unsafe/fit-in/680x680/filters:fill(white)/product/00/8161622/3.jpg?5646",
               "new_price": 2534
    },

      {
                  "current_name": "LASU-Branded Backpack",
                  "new_name": "Men Sling Bag Pack With Lock Waterproof Anti-Theft Chest Bag",
                  "new_image": "https://ng.jumia.is/unsafe/fit-in/680x680/filters:fill(white)/product/25/5206943/1.jpg?3867",
                  "new_price": 1234
    },

         {
                     "current_name": "Name on site now",
                     "new_name": "New name",
                     "new_image": "Image URL",
                     "new_price": 1234
   },
]

# =========================================
# DO NOT EDIT BELOW
# =========================================

for u in updates:
    cur.execute("SELECT id, product_name FROM products WHERE product_name = ?", (u["current_name"],))
    row = cur.fetchone()

    if not row:
        print(f"❌ NOT FOUND: '{u['current_name']}'")
        continue

    cur.execute(
        "UPDATE products SET product_name = ?, image = ?, price = ? WHERE id = ?",
        (u["new_name"], u["new_image"], u["new_price"], row[0])
    )
    print(f"✅ Changed '{u['current_name']}' → '{u['new_name']}'")

conn.commit()
conn.close()
print("\nDone. Refresh your site with Ctrl + Shift + R")