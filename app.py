from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, send_from_directory, session
from flask_mail import Mail, Message
import sqlite3
import os

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "marketplace.db")
app.secret_key = "aftf-secret-key"

# ==========================================
# EMAIL CONFIGURATION (GMAIL)
# ==========================================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'kennethchisom57@gmail.com' # <-- Your Email
app.config['MAIL_PASSWORD'] = 'tpdzzrhgsifhikem'      # <-- YOUR 16-LETTER APP PASSWORD (NO SPACES)
app.config['MAIL_DEFAULT_SENDER'] = 'kennethchisom57@gmail.com'

mail = Mail(app)
# ==========================================

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ==============
# DATABASE
# ============
def create_database():
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT, product_name TEXT NOT NULL, price REAL NOT NULL,
            category TEXT NOT NULL, description TEXT NOT NULL, location TEXT NOT NULL, image TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL, phone TEXT NOT NULL,
            address TEXT NOT NULL, city TEXT NOT NULL, total REAL NOT NULL, status TEXT DEFAULT 'Pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    connection.commit()
    connection.close()

# HOME PAGE
@app.route("/")
def home():
    category = request.args.get("category")
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    if category:
        cursor.execute("SELECT * FROM products WHERE category = ? ORDER BY id DESC", (category,))
    else:
        cursor.execute("SELECT * FROM products ORDER BY id DESC")
    products = cursor.fetchall()

    wishlist_ids = []
    if session.get("user_id"):
        cursor.execute("SELECT product_id FROM wishlist WHERE user_id = ?", (session["user_id"],))
        wishlist_ids = [row[0] for row in cursor.fetchall()]
    connection.close()
    return render_template("index.html", products=products, selected_category=category, wishlist_ids=wishlist_ids)

@app.route("/wishlist")
def wishlist():
    if not session.get("user_id"): return redirect("/login")
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("""
        SELECT p.id, p.product_name, p.price, p.category, p.description, p.location, p.image
        FROM wishlist w JOIN products p ON p.id = w.product_id WHERE w.user_id = ? ORDER BY w.id DESC
    """, (session["user_id"],))
    wishlist_items = cursor.fetchall()
    connection.close()
    return render_template("wishlist.html", wishlist_items=wishlist_items)

@app.route("/sell")
def sell(): return render_template("sell.html")

@app.route("/contact")
def contact(): return render_template("contact.html")

@app.route("/post", methods=["POST"])
def post_product():
    product_name = request.form["product_name"]
    price = request.form["price"]
    category = request.form["category"]
    description = request.form["description"]
    location = request.form["location"]
    image = request.files["product_image"]
    image_filename = image.filename
    image.save(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))

    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO products (product_name, price, category, description, location, image) VALUES (?, ?, ?, ?, ?, ?)
    """, (product_name, price, category, description, location, image_filename))
    connection.commit()
    connection.close()
    return redirect("/")

@app.route("/delete-product/<int:product_id>")
def delete_product(product_id):
    if not session.get("is_admin"): return "Not allowed", 403
    next_url = request.args.get("next", "/")
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("SELECT image FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    if row:
        image_filename = row[0]
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        connection.commit()
        try:
            if image_filename and not image_filename.startswith("http"):
                image_path = os.path.join(app.config["UPLOAD_FOLDER"], image_filename)
                if os.path.exists(image_path): os.remove(image_path)
        except Exception: pass
    connection.close()
    return redirect(next_url)

@app.route("/product/<int:product_id>")
def product_details(product_id):
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    connection.close()
    if product is None: return "Product not found", 404

    viewed = session.get("recently_viewed", [])
    if product_id in viewed: viewed.remove(product_id)
    viewed.insert(0, product_id)
    viewed = viewed[:10]
    session["recently_viewed"] = viewed
    return render_template("product.html", product=product)

@app.route("/add-to-cart/<int:product_id>")
def add_to_cart(product_id):
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("SELECT stock, product_name FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    connection.close()
    if not row: return redirect("/")
    stock = row[0] if row[0] is not None else 0
    product_name = row[1]
    if stock <= 0: return redirect(request.referrer or "/")

    cart = session.get("cart", {})
    if isinstance(cart, list):
        new_cart = {}
        for old_product_id in cart:
            old_product_id = str(old_product_id)
            new_cart[old_product_id] = new_cart.get(old_product_id, 0) + 1
        cart = new_cart
    product_id = str(product_id)
    cart[product_id] = cart.get(product_id, 0) + 1
    session["cart"] = cart
    session["last_added_product"] = product_name

    next_url = request.referrer or "/product/" + product_id
    separator = "&" if "?" in next_url else "?"
    return redirect(f"{next_url}{separator}added=1")

@app.route("/cart")
def cart():
    cart = session.get("cart", {})
    products = []
    total = 0
    cart_count = 0
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()

    for product_id, quantity in cart.items():
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        if product:
            products.append((product, quantity))
            total += float(product[2]) * quantity
            cart_count += quantity

    viewed_ids = session.get("recently_viewed", [])
    cart_product_ids = [str(pid) for pid in cart.keys()]
    viewed_ids = [pid for pid in viewed_ids if str(pid) not in cart_product_ids]
    recently_viewed = []
    if viewed_ids:
        placeholders = ",".join("?" for _ in viewed_ids)
        cursor.execute(f"SELECT * FROM products WHERE id IN ({placeholders})", viewed_ids)
        rows = {row[0]: row for row in cursor.fetchall()}
        recently_viewed = [rows[pid] for pid in viewed_ids if pid in rows]

    connection.close()
    return render_template("cart.html", products=products, total=total, cart_count=cart_count, recently_viewed=recently_viewed)

@app.route("/increase-cart/<int:product_id>")
def increase_cart(product_id):
    cart = session.get("cart", {})
    product_id = str(product_id)
    if product_id in cart: cart[product_id] += 1
    else: cart[product_id] = 1
    session["cart"] = cart
    return redirect("/cart")

@app.route("/decrease-cart/<int:product_id>")
def decrease_cart(product_id):
    cart = session.get("cart", {})
    product_id = str(product_id)
    if product_id in cart:
        cart[product_id] -= 1
        if cart[product_id] <= 0: del cart[product_id]
    session["cart"] = cart
    return redirect("/cart")

@app.route("/remove-from-cart/<int:product_id>")
def remove_from_cart(product_id):
    cart = session.get("cart", {})
    product_id = str(product_id)
    if isinstance(cart, list):
        new_cart = {}
        for item in cart:
            item = str(item)
            new_cart[item] = new_cart.get(item, 0) + 1
        cart = new_cart
    if product_id in cart: del cart[product_id]
    session["cart"] = cart
    return redirect("/cart")

@app.route("/checkout")
def checkout():
    cart = session.get("cart", {})
    products = []
    total = 0
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    for product_id, quantity in cart.items():
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        if product:
            products.append((product, quantity))
            total += float(product[2]) * quantity
    connection.close()
    return render_template("checkout.html", products=products, total=total)

@app.route("/place-order", methods=["POST"])
def place_order():
    full_name = request.form["full_name"]
    phone = request.form["phone"]
    delivery_type = request.form.get("delivery_type", "pickup")
    DELIVERY_FEE = 500
    if delivery_type == "delivery":
        address = request.form.get("address", "On Campus")
        city = request.form.get("city", "LASU Campus")
        delivery_fee = DELIVERY_FEE
    else:
        address = "Pickup at LASU ICT Centre"
        city = "LASU ICT Centre"
        delivery_fee = 0

    cart = session.get("cart", {})
    subtotal = 0
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()

    for product_id, quantity in cart.items():
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        if product:
            stock = product[7] if len(product) > 7 and product[7] is not None else 0
            if stock < quantity:
                connection.close()
                return f"Not enough stock for '{product[1]}'. Only {stock} left.", 400
            subtotal += float(product[2]) * quantity

    connection.close()
    total = subtotal + delivery_fee

    session["checkout_details"] = {"full_name": full_name, "phone": phone, "address": address, "city": city, "delivery_type": delivery_type, "total": total}
    return redirect("/payment")

@app.route("/payment")
def payment():
    if not session.get("checkout_details"): return redirect("/cart")
    total = session["checkout_details"]["total"]
    return render_template("payment.html", total=total)

@app.route("/process-payment", methods=["POST"])
def process_payment():
    if not session.get("checkout_details"): return redirect("/cart")

    details = session["checkout_details"]
    cart = session.get("cart", {})
    payment_method = request.form.get("payment_method", "card")
    final_total = details["total"]
    if payment_method == "transfer": final_total += 50 

    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()

    items_bought = []
    for product_id, quantity in cart.items():
        cursor.execute("SELECT product_name, image FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        if product: items_bought.append(f"{product[0]}•{product[1]}•{quantity}")
    items_string = ", ".join(items_bought)

    cursor.execute("""
        INSERT INTO orders (full_name, phone, address, city, total, status, created_at, items_summary)
        VALUES (?, ?, ?, ?, ?, 'Paid', CURRENT_TIMESTAMP, ?)
    """, (details["full_name"], details["phone"], details["address"], details["city"], final_total, items_string))
    order_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO messages (user_phone, title, message) VALUES (?, 'Your order has been received!', ?)
    """, (details["phone"], f"Thank you for choosing LASU CampusMart! We have received your order #{order_id}."))

    for product_id, quantity in cart.items():
        cursor.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, product_id))

    connection.commit()

    # --- SEND EMAILS ---
    
    # 1. User Receipt
    try:
        user_email = session.get("user_email") 
        if user_email:
            msg = Message(f"Order Confirmed #{order_id} - LASU CampusMart", recipients=[user_email])
            msg.html = f"<h3>Hi {details['full_name']},</h3><p>We received your payment of ₦{final_total}. Your order is being processed.</p>"
            mail.send(msg)
            print(f"✅ User email sent to {user_email}")
    except Exception as e: print(f"❌ User email failed: {e}")

    # 2. Vendor Sale Alert
    try:
        first_product_id = list(cart.keys())[0]
        cursor.execute("SELECT category FROM products WHERE id = ?", (first_product_id,))
        category_row = cursor.fetchone()
        if category_row:
            product_category = category_row[0]
            cursor.execute("SELECT email, business_name FROM vendors WHERE category = ? AND status = 'Approved' LIMIT 1", (product_category,))
            vendor_info = cursor.fetchone()
            if vendor_info:
                msg = Message(f"New Sale! Order #{order_id}", recipients=[vendor_info[0]])
                msg.html = f"<h3>Hi {vendor_info[1]},</h3><p>You made a sale! Order #{order_id} has been paid.</p>"
                mail.send(msg)
                print(f"✅ Vendor email sent to {vendor_info[0]}")
    except Exception as e: print(f"❌ Vendor email failed: {e}")

    # 3. Admin Alert
    try:
        admin_email = app.config['MAIL_USERNAME'] 
        msg = Message(f"Admin Alert: New Order #{order_id}", recipients=[admin_email])
        msg.html = f"<h3>New Order Placed</h3><p>Order #{order_id} by {details['full_name']} for ₦{final_total}.</p>"
        mail.send(msg)
        print(f"✅ Admin email sent to {admin_email}")
    except Exception as e: print(f"❌ Admin email failed: {e}")

    connection.close()
    session.pop("cart", None)
    session.pop("checkout_details", None)
    return render_template("Order_success.html", total=final_total, order_id=order_id)

@app.route("/carousel")
def carousel(): return render_template("index.html")

@app.route("/search")
def search():
    query = request.args.get("query", "").strip()
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    if query:
        words = query.split()
        conditions = []
        params = []
        for word in words:
            conditions.append("(product_name LIKE ? OR description LIKE ? OR category LIKE ?)")
            params.extend([f"%{word}%"] * 3)
        sql = "SELECT * FROM products WHERE " + " OR ".join(conditions) + " ORDER BY id DESC"
        cursor.execute(sql, params)
    else:
        cursor.execute("SELECT * FROM products ORDER BY id DESC")
    products = cursor.fetchall()
    wishlist_ids = []
    if session.get("user_id"):
        cursor.execute("SELECT product_id FROM wishlist WHERE user_id = ?", (session["user_id"],))
        wishlist_ids = [row[0] for row in cursor.fetchall()]
    connection.close()
    return render_template("search_results.html", products=products, query=query, wishlist_ids=wishlist_ids)

# =========================
# ADMIN
# =========================
ADMIN_PASSWORD = "janney27"

@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if session.get("is_admin"): return redirect("/admin")
    if request.method == "POST":
        if request.form.get("password", "") == ADMIN_PASSWORD:
            session["is_admin"] = True
            session.permanent = True
            return redirect("/admin")
        return render_template("admin_login.html", error="Wrong password. Try again.")
    return render_template("admin_login.html")

@app.route("/admin-logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect("/admin-login")

@app.route("/admin")
def admin_dashboard():
    if not session.get("is_admin"): return redirect("/admin-login")
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("SELECT SUM(total) FROM orders")
    total_revenue = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(DISTINCT phone) FROM orders")
    total_customers = cursor.fetchone()[0] or 0
    cursor.execute("SELECT id, full_name, phone, city, total FROM orders ORDER BY id DESC LIMIT 5")
    recent_orders = cursor.fetchall()
    cursor.execute("SELECT product_name, price, category FROM products ORDER BY id DESC LIMIT 5")
    top_products = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM products WHERE stock <= 5")
    low_stock_count = cursor.fetchone()[0] or 0
    cursor.execute("SELECT id, product_name, stock FROM products WHERE stock <= 5 ORDER BY stock ASC LIMIT 3")
    low_stock_items = cursor.fetchall()
    connection.close()
    return render_template("admin_dashboard.html", total_revenue=total_revenue, total_orders=total_orders, total_products=total_products, total_customers=total_customers, recent_orders=recent_orders, top_products=top_products, low_stock_count=low_stock_count, low_stock_items=low_stock_items)

@app.route("/admin/products")
def admin_products():
    if not session.get("is_admin"): return redirect("/admin-login")
    search = request.args.get("search", "").strip()
    stock_filter = request.args.get("stock", "").strip()
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    query = "SELECT * FROM products"
    conditions = []
    params = []
    if search:
        conditions.append("product_name LIKE ?")
        params.append(f"%{search}%")
    if stock_filter == "in": conditions.append("stock > 5")
    elif stock_filter == "low": conditions.append("stock BETWEEN 1 AND 5")
    elif stock_filter == "out": conditions.append("stock <= 0")
    if conditions: query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    products = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM products")
    total_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM products WHERE stock > 5")
    in_stock_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM products WHERE stock BETWEEN 1 AND 5")
    low_stock_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM products WHERE stock <= 0")
    out_stock_count = cursor.fetchone()[0]
    connection.close()
    return render_template("admin_products.html", products=products, search=search, stock_filter=stock_filter, total_count=total_count, in_stock_count=in_stock_count, low_stock_count=low_stock_count, out_stock_count=out_stock_count)

@app.route("/admin/products/update-stock/<int:product_id>", methods=["POST"])
def admin_update_stock(product_id):
    if not session.get("is_admin"): return "Not allowed", 403
    new_stock = request.form.get("stock", "0")
    try: new_stock = int(new_stock)
    except ValueError: new_stock = 0
    if new_stock < 0: new_stock = 0
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, product_id))
    connection.commit()
    connection.close()
    return redirect("/admin/products")

@app.route("/admin/orders")
def admin_orders():
    if not session.get("is_admin"): return redirect("/admin-login")
    status_filter = request.args.get("status", "").strip()
    search = request.args.get("search", "").strip()
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    query = "SELECT id, full_name, phone, address, city, total, status, created_at FROM orders"
    conditions = []
    params = []
    if status_filter:
        conditions.append("status = ?")
        params.append(status_filter)
    if search:
        conditions.append("(full_name LIKE ? OR phone LIKE ? OR id LIKE ?)")
        params.extend([f"%{search}%"] * 3)
    if conditions: query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    orders = cursor.fetchall()
    cursor.execute("SELECT status, COUNT(*) FROM orders GROUP BY status")
    status_counts = dict(cursor.fetchall())
    connection.close()
    return render_template("admin_orders.html", orders=orders, status_filter=status_filter, search=search, status_counts=status_counts)

@app.route("/admin/orders/update/<int:order_id>", methods=["POST"])
def admin_update_order_status(order_id):
    if not session.get("is_admin"): return "Not allowed", 403
    new_status = request.form.get("status", "Pending")
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
    cursor.execute("SELECT phone, total FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    if order and new_status in ['Vendor Confirmed', 'Shipped', 'Delivered']:
        phone = order[0]
        title = f"Order {new_status}"
        msg = f"Your order #{order_id} status has been updated to: {new_status}."
        cursor.execute("INSERT INTO messages (user_phone, title, message) VALUES (?, ?, ?)", (phone, title, msg))
    connection.commit()
    connection.close()
    return redirect("/admin/orders")

@app.route("/admin/vendors")
def admin_vendors():
    if not session.get("is_admin"): return redirect("/admin-login")
    status_filter = request.args.get("status", "").strip()
    search = request.args.get("search", "").strip()
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    query = "SELECT id, full_name, business_name, email, phone, category, status, created_at, tax_status FROM vendors"
    conditions = []
    params = []
    if status_filter:
        conditions.append("status = ?")
        params.append(status_filter)
    if search:
        conditions.append("(business_name LIKE ? OR full_name LIKE ? OR email LIKE ? OR phone LIKE ?)")
        params.extend([f"%{search}%"] * 4)
    if conditions: query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    vendors = cursor.fetchall()
    cursor.execute("SELECT status, COUNT(*) FROM vendors GROUP BY status")
    status_counts = dict(cursor.fetchall())
    connection.close()
    return render_template("admin_vendors.html", vendors=vendors, status_filter=status_filter, search=search, status_counts=status_counts)

@app.route("/admin/vendors/update/<int:vendor_id>", methods=["POST"])
def admin_update_vendor_status(vendor_id):
    if not session.get("is_admin"): return "Not allowed", 403
    new_status = request.form.get("status", "Pending")
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("SELECT email, business_name FROM vendors WHERE id = ?", (vendor_id,))
    vendor = cursor.fetchone()
    cursor.execute("UPDATE vendors SET status = ? WHERE id = ?", (new_status, vendor_id))
    connection.commit()
    connection.close()

    if new_status == 'Approved' and vendor and vendor[0]:
        try:
            msg = Message("Your Vendor Account is Approved!", recipients=[vendor[0]])
            msg.html = f"<h3>Congratulations {vendor[1]}!</h3><p>Your vendor application has been approved.</p>"
            mail.send(msg)
            print(f"✅ SUCCESS! Email sent to {vendor[0]}")
        except Exception as e: print(f"❌ FAILED to send to {vendor[0]}. Error: {e}")
    return redirect("/admin/vendors")

@app.route("/admin/confirm-tax/<int:vendor_id>", methods=["POST"])
def admin_confirm_tax(vendor_id):
    if not session.get("is_admin"): return redirect("/admin-login")
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("UPDATE vendors SET tax_status = 'Paid', tax_paid_at = CURRENT_TIMESTAMP WHERE id = ?", (vendor_id,))
    connection.commit()
    connection.close()
    return redirect("/admin/vendors")

# =========================
# REGISTER / LOGIN / PROFILE
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"): return redirect("/")
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        matric_or_staff_id = request.form.get("matric_or_staff_id", "").strip()
        role = request.form.get("role", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        phone = request.form.get("phone", "").strip()
        errors = []
        if not (full_name and email and matric_or_staff_id and role and password): errors.append("All fields are required.")
        if len(password) < 6: errors.append("Password must be at least 6 characters.")
        if password != confirm_password: errors.append("Passwords do not match.")
        if role not in ["student", "lecturer", "staff"]: errors.append("Invalid role selected.")
        
        if not errors:
            connection = sqlite3.connect("marketplace.db")
            cursor = connection.cursor()
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone(): errors.append("An account with this email already exists.")
            connection.close()

        if errors:
            return render_template("register.html", errors=errors, form_data={"full_name": full_name, "email": email, "matric_or_staff_id": matric_or_staff_id, "role": role, "phone": phone})

        password_hash = generate_password_hash(password)
        connection = sqlite3.connect("marketplace.db")
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO users (full_name, email, matric_or_staff_id, role, password_hash, phone) VALUES (?, ?, ?, ?, ?, ?)
        """, (full_name, email, matric_or_staff_id, role, password_hash, phone))
        connection.commit()
        connection.close()

        # Registration Email
        try:
            msg = Message("Welcome to LASU CampusMart!", recipients=[email])
            msg.html = f"<h3>Hi {full_name},</h3><p>Your account has been created successfully. You can now start shopping!</p>"
            mail.send(msg)
            print(f"✅ Registration email sent to {email}")
        except Exception as e: print(f"❌ Registration email failed: {e}")

        return redirect("/login?registered=1")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"): return redirect("/profile")
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        errors = []
        if not email or not password: errors.append("Please enter both email and password.")
        if not errors:
            connection = sqlite3.connect("marketplace.db")
            cursor = connection.cursor()
            cursor.execute("SELECT id, full_name, email, role, password_hash FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            connection.close()
            if user and check_password_hash(user[4], password):
                session.clear() 
                session["user_id"] = user[0]
                session["user_name"] = user[1]
                session["user_email"] = user[2]
                session["user_role"] = user[3]
                return redirect("/profile")
            else: errors.append("Invalid email or password.")
        return render_template("login.html", errors=errors, email=email)
    registered = request.args.get("registered") == "1"
    reset = request.args.get("reset") == "1"
    return render_template("login.html", registered=registered, reset=reset)

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        connection = sqlite3.connect("marketplace.db")
        cursor = connection.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        connection.close()
        if user: return redirect(f"/reset-password?email={email}")
        else: return render_template("forgot_password.html", error="No account found with that email.")
    return render_template("forgot_password.html")

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    email = request.args.get("email", "")
    if not email: return redirect("/forgot-password")
    if request.method == "POST":
        new_password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        if len(new_password) < 6: return render_template("reset_password.html", email=email, error="Password must be at least 6 characters.")
        if new_password != confirm_password: return render_template("reset_password.html", email=email, error="Passwords do not match.")
        password_hash = generate_password_hash(new_password)
        connection = sqlite3.connect("marketplace.db")
        cursor = connection.cursor()
        cursor.execute("UPDATE users SET password_hash = ? WHERE email = ?", (password_hash, email))
        connection.commit()
        connection.close()
        return redirect("/login?reset=1")
    return render_template("reset_password.html", email=email)

@app.route("/settings")
def settings():
    if not session.get("user_id"): return redirect("/login")
    return render_template("settings.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/wishlist/toggle/<int:product_id>")
def wishlist_toggle(product_id):
    if not session.get("user_id"): return redirect("/login")
    user_id = session["user_id"]
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("SELECT product_name FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    product_name = row[0] if row else "Product"
    cursor.execute("SELECT id FROM wishlist WHERE user_id = ? AND product_id = ?", (user_id, product_id))
    existing = cursor.fetchone()
    action = "added"
    if existing:
        cursor.execute("DELETE FROM wishlist WHERE id = ?", (existing[0],))
        action = "removed"
    else: cursor.execute("INSERT INTO wishlist (user_id, product_id) VALUES (?, ?)", (user_id, product_id))
    connection.commit()
    connection.close()
    session["wishlist_toast_name"] = product_name
    session["wishlist_toast_action"] = action
    next_url = request.referrer or "/"
    separator = "&" if "?" in next_url else "?"
    return redirect(f"{next_url}{separator}wishlist={action}")

@app.route("/admin/inventory")
def admin_inventory():
    if not session.get("is_admin"): return redirect("/admin-login")
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("SELECT id, product_name, price, category, stock, image, location FROM products WHERE stock <= 0 ORDER BY product_name ASC")
    out_of_stock = cursor.fetchall()
    cursor.execute("SELECT id, product_name, price, category, stock, image, location FROM products WHERE stock BETWEEN 1 AND 5 ORDER BY stock ASC")
    low_stock = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM products")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM products WHERE stock > 5")
    healthy = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM products WHERE stock <= 0")
    out_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM products WHERE stock BETWEEN 1 AND 5")
    low_count = cursor.fetchone()[0]
    connection.close()
    return render_template("admin_inventory.html", out_of_stock=out_of_stock, low_stock=low_stock, total=total, healthy=healthy, out_count=out_count, low_count=low_count)

@app.route("/admin/reports")
def admin_reports():
    if not session.get("is_admin"): return redirect("/admin-login")
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("SELECT SUM(total) FROM orders")
    total_revenue = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0] or 0
    avg_order = (total_revenue / total_orders) if total_orders > 0 else 0
    cursor.execute("SELECT DATE(created_at) as day, SUM(total) FROM orders WHERE created_at IS NOT NULL GROUP BY DATE(created_at) ORDER BY day DESC LIMIT 7")
    raw_daily = cursor.fetchall()
    daily_revenue = list(reversed(raw_daily))
    cursor.execute("SELECT p.category, SUM(o.total) FROM orders o JOIN products p ON p.id = o.id GROUP BY p.category ORDER BY SUM(o.total) DESC")
    category_revenue = cursor.fetchall()
    cursor.execute("SELECT o.id, o.full_name, o.total, o.city, o.created_at FROM orders o ORDER BY o.total DESC LIMIT 5")
    top_orders = cursor.fetchall()
    best_day = "—"
    if daily_revenue: best_day = max(daily_revenue, key=lambda x: x[1] or 0)[0] or "—"
    connection.close()
    return render_template("admin_reports.html", total_revenue=total_revenue, total_orders=total_orders, avg_order=avg_order, daily_revenue=daily_revenue, category_revenue=category_revenue, top_orders=top_orders, best_day=best_day)

@app.route("/my-orders")
def my_orders():
    if not session.get("user_id"): return redirect("/login")
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("SELECT phone FROM users WHERE id = ?", (session["user_id"],))
    user = cursor.fetchone()
    user_phone = user[0] if user and user[0] else ""
    orders = []
    if user_phone:
        cursor.execute("""
            SELECT id, total, status, created_at, city, items_summary FROM orders WHERE phone = ? ORDER BY id DESC
        """, (user_phone,))
        orders = cursor.fetchall()
    connection.close()
    return render_template("my_orders.html", orders=orders)

@app.route("/cancel-order/<int:order_id>")
def cancel_order(order_id):
    if not session.get("user_id"): return redirect("/login")
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE orders SET status = 'Cancelled' WHERE id = ? AND status IN ('Pending', 'Paid', 'Pending Vendor')
    """, (order_id,))
    connection.commit()
    connection.close()
    return redirect("/my-orders")

@app.route("/profile")
def profile():
    if not session.get("user_id"): return redirect("/login")
    session["is_vendor"] = False
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("SELECT full_name, email, phone FROM users WHERE id = ?", (session["user_id"],))
    user = cursor.fetchone()
    if not user: return redirect("/logout")
    order_count = 0
    if user[2]: 
        cursor.execute("SELECT COUNT(*) FROM orders WHERE phone = ?", (user[2],))
        order_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM wishlist WHERE user_id = ?", (session["user_id"],))
    wishlist_count = cursor.fetchone()[0]
    connection.close()
    return render_template("profile.html", user=user, order_count=order_count, wishlist_count=wishlist_count)

@app.route("/vendor-signup", methods=["GET", "POST"])
def vendor_signup():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        business_name = request.form.get("business_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        if not (full_name and business_name and email and phone and category):
            return render_template("vendor_signup.html", error="Please fill in all required fields.")
        connection = sqlite3.connect("marketplace.db")
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO vendors (full_name, business_name, email, phone, category, description) VALUES (?, ?, ?, ?, ?, ?)
        """, (full_name, business_name, email, phone, category, description))
        connection.commit()
        connection.close()
        return redirect(f"/vendor-signup?success=1&email={email}")

    success = request.args.get("success") == "1"
    is_approved_vendor = False
    email_to_check = request.args.get("email", "").strip().lower()
    if not email_to_check and session.get("user_id"):
        connection = sqlite3.connect("marketplace.db")
        cursor = connection.cursor()
        cursor.execute("SELECT email FROM users WHERE id = ?", (session["user_id"],))
        user_record = cursor.fetchone()
        if user_record: email_to_check = user_record[0]
        connection.close()
    if email_to_check:
        connection = sqlite3.connect("marketplace.db")
        cursor = connection.cursor()
        cursor.execute("SELECT status FROM vendors WHERE email = ?", (email_to_check,))
        vendor = cursor.fetchone()
        connection.close()
        if vendor and vendor[0] == 'Approved': is_approved_vendor = True
    return render_template("vendor_signup.html", success=success, is_approved_vendor=is_approved_vendor)

@app.route("/vendor-portal")
def vendor_portal():
    if session.get("user_id"): return redirect("/vendor-dashboard")
    return render_template("vendor_login.html")

@app.route("/vendor-login-action", methods=["POST"])
def vendor_login_action():
    email = request.form.get("email", "").strip().lower()
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("SELECT id, status FROM vendors WHERE email = ?", (email,))
    vendor = cursor.fetchone()
    if not vendor:
        connection.close()
        return render_template("vendor_login.html", error="Email not found. Please register as a vendor first.")
    if vendor[1] != 'Approved':
        connection.close()
        return render_template("vendor_login.html", pending_message=f"Your application is currently '{vendor[1]}'. Please wait for the Admin to approve your account.")
    cursor.execute("SELECT id, full_name FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    connection.close()
    if user:
        session["user_id"] = user[0]
        session["user_name"] = user[1]
        session["user_email"] = email
        session["is_vendor"] = True
        return redirect("/vendor-dashboard")
    else: return render_template("vendor_login.html", error="User account error. Please contact support.")

@app.route("/vendor-tax-payment")
def vendor_tax_payment():
    if not session.get("user_id"): return redirect("/login")
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("SELECT tax_status, tax_paid_at FROM vendors WHERE email = ?", (session.get("user_email"),))
    vendor = cursor.fetchone()
    connection.close()
    return render_template("vendor_tax.html", tax_status=vendor[0] if vendor else 'Unpaid', tax_paid_at=vendor[1])

@app.route("/vendor-pay-tax", methods=["POST"])
def vendor_pay_tax():
    if not session.get("user_id"): return redirect("/login")
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("UPDATE vendors SET tax_status = 'Pending' WHERE email = ?", (session.get("user_email"),))
    connection.commit()
    connection.close()
    return redirect("/vendor-tax-payment")

@app.route("/vendor-dashboard")
def vendor_dashboard():
    if not session.get("user_id"): return redirect("/login")
    session["is_vendor"] = True
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("SELECT email FROM users WHERE id = ?", (session["user_id"],))
    user = cursor.fetchone()
    vendor_app = None
    vendor_orders = []
    if user:
        cursor.execute("SELECT business_name, category, status, created_at, tax_paid_at, tax_status FROM vendors WHERE email = ?", (user[0],))
        vendor_app = cursor.fetchone()
        cursor.execute("SELECT id, full_name, total, status, created_at FROM orders WHERE status IN ('Pending Vendor', 'Vendor Confirmed') ORDER BY id DESC")
        vendor_orders = cursor.fetchall()
    connection.close()
    return render_template("vendor_dashboard.html", vendor=vendor_app, orders=vendor_orders)

@app.route("/vendor-order/<int:order_id>")
def vendor_order_details(order_id):
    if not session.get("user_id") or not session.get("is_vendor"): return redirect("/login")
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    connection.close()
    return render_template("vendor_order_details.html", order=order)

@app.route("/vendor-confirm-payment/<int:order_id>", methods=["POST"])
def vendor_confirm_payment(order_id):
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("UPDATE orders SET status = 'Vendor Confirmed', vendor_confirmed = 1 WHERE id = ?", (order_id,))
    connection.commit()
    connection.close()
    return redirect(f"/vendor-order/{order_id}")

@app.route("/vendor-deliver-order/<int:order_id>", methods=["POST"])
def vendor_deliver_order(order_id):
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("UPDATE orders SET status = 'Delivered' WHERE id = ?", (order_id,))
    connection.commit()
    connection.close()
    return redirect(f"/vendor-order/{order_id}?delivered=1")

@app.route("/vendor-confirmed-payments")
def vendor_confirmed_payments():
    if not session.get("user_id") or not session.get("is_vendor"): return redirect("/login")
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("SELECT email FROM users WHERE id = ?", (session["user_id"],))
    user = cursor.fetchone()
    payments = []
    if user:
        cursor.execute("SELECT id, full_name, total, status, created_at FROM orders WHERE status IN ('Vendor Confirmed', 'Ready for Delivery', 'Delivered') ORDER BY id DESC")
        payments = cursor.fetchall()
    connection.close()
    return render_template("vendor_payment_records.html", payments=payments)

@app.route("/inbox")
def inbox():
    if not session.get("user_id"): return redirect("/login")
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("SELECT phone FROM users WHERE id = ?", (session["user_id"],))
    user = cursor.fetchone()
    user_phone = user[0] if user and user[0] else ""
    messages = []
    if user_phone:
        cursor.execute("SELECT title, message, created_at FROM messages WHERE user_phone = ? ORDER BY id DESC", (user_phone,))
        messages = cursor.fetchall()
    connection.close()
    return render_template("inbox.html", messages=messages)

@app.route("/account-redirect")
def account_redirect():
    if not session.get("user_id"): return redirect("/login")
    connection = sqlite3.connect("marketplace.db")
    cursor = connection.cursor()
    cursor.execute("SELECT email FROM users WHERE id = ?", (session["user_id"],))
    user = cursor.fetchone()
    if not user:
        connection.close()
        session.clear()
        return redirect("/login")
    user_email = user[0]
    cursor.execute("SELECT status FROM vendors WHERE email = ?", (user_email,))
    vendor = cursor.fetchone()
    connection.close()
    if vendor and vendor[0] == 'Approved':
        session["is_vendor"] = True
        if session.get("view_mode") == "buyer": return redirect("/profile")
        else: return redirect("/vendor-dashboard")
    else:
        session["is_vendor"] = False
        return redirect("/profile")

@app.route("/switch-to-buyer")
def switch_to_buyer():
    session["view_mode"] = "buyer"
    return redirect("/profile")

@app.route("/switch-to-vendor")
def switch_to_vendor():
    session["view_mode"] = "vendor"
    return redirect("/vendor-dashboard")

@app.route("/send-message/<int:product_id>", methods=["POST"])
def send_message(product_id):
    if not session.get("user_id"): return redirect("/login")
    message_text = request.form.get("message", "").strip()
    if message_text:
        connection = sqlite3.connect("marketplace.db")
        cursor = connection.cursor()
        cursor.execute("SELECT email FROM users WHERE id = ?", (session["user_id"],))
        sender_email = cursor.fetchone()[0]
        receiver_email = "admin@lasucampusmart.com" 
        cursor.execute("INSERT INTO chats (product_id, sender_email, receiver_email, message) VALUES (?, ?, ?, ?)", (product_id, sender_email, receiver_email, message_text))
        connection.commit()
        connection.close()
        return redirect(f"/product/{product_id}?message_sent=1")
    return redirect(f"/product/{product_id}")

if __name__ == "__main__":
    create_database()
    app.run(debug=True)