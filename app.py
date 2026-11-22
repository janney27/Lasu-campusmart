import os
import secrets
from pathlib import Path
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import DictCursor
import requests

import requests
from flask import Flask, render_template, request, redirect, send_from_directory, session, abort
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


# ------------------------------------------------------------
# APP CONFIGURATION
# ------------------------------------------------------------
app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# Set SECRET_KEY in Render Environment Variables.
# The fallback is suitable only for local school-project testing.
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config.update(
    UPLOAD_FOLDER=str(UPLOAD_FOLDER),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 7,
)

# Gmail settings are optional. Add these environment variables if you use Gmail:
# MAIL_USERNAME, MAIL_PASSWORD
mail_username = os.environ.get("MAIL_USERNAME", "")
mail_password = os.environ.get("MAIL_PASSWORD", "")
app.config.update(
    MAIL_SERVER="smtp.gmail.com",
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=mail_username,
    MAIL_PASSWORD=mail_password,
    MAIL_DEFAULT_SENDER=mail_username or None,
)
mail = Mail(app)


def send_welcome_email(to_email, full_name):
    """Send a welcome email through Resend when RESEND_API_KEY is configured."""
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print("Welcome email skipped: RESEND_API_KEY is not set.")
        return

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": "LASU CampusMart <onboarding@resend.dev>",
                "to": [to_email],
                "subject": "Welcome to LASU CampusMart!",
                "html": (
                    f"<h3>Hi {full_name},</h3>"
                    "<p>Your account has been created successfully. "
                    "You can now start shopping!</p>"
                ),
            },
            timeout=10,
        )
        print(f"Resend status: {response.status_code} {response.text}")
    except requests.RequestException as exc:
        print(f"Welcome email failed: {exc}")


def send_mail_message(subject, recipients, html):
    """Do not let an email-provider problem break an order or account action."""
    if not app.config.get("MAIL_USERNAME") or not app.config.get("MAIL_PASSWORD"):
        print("Email skipped: MAIL_USERNAME / MAIL_PASSWORD not configured.")
        return
    try:
        message = Message(subject, recipients=recipients)
        message.html = html
        mail.send(message)
    except Exception as exc:
        print(f"Email failed: {exc}")


    # ------------------------------------------------------------
# POSTGRESQL DATABASE
# ------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing. Add it in Render Environment.")

class DatabaseConnection:
    """Small compatibility layer for the existing connection.execute() code."""

    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, params=()):
        cursor = self.connection.cursor()
        sql = sql.replace("?", "%s")
        cursor.execute(sql, params)
        return cursor

    def executescript(self, script):
        cursor = self.connection.cursor()
        for statement in script.split(";"):
            if statement.strip():
                cursor.execute(statement)
        return cursor


@contextmanager
def get_db_connection():
    connection = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=DictCursor,
        connect_timeout=15,
    )
    db = DatabaseConnection(connection)

    try:
        yield db
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def add_column_if_missing(connection, table_name, column_name, column_definition):
    result = connection.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = ?
          AND column_name = ?
        """,
        (table_name, column_name),
    ).fetchone()

    if not result:
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )


def create_database():
    """Create all application tables in PostgreSQL."""

    with get_db_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                matric_or_staff_id TEXT NOT NULL,
                role TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS products (
                id BIGSERIAL PRIMARY KEY,
                product_name TEXT NOT NULL,
                price DOUBLE PRECISION NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                image TEXT NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS orders (
                id BIGSERIAL PRIMARY KEY,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                city TEXT NOT NULL,
                total DOUBLE PRECISION NOT NULL,
                status TEXT DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                items_summary TEXT DEFAULT '',
                vendor_confirmed INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS wishlist (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, product_id)
            );

            CREATE TABLE IF NOT EXISTS vendors (
                id BIGSERIAL PRIMARY KEY,
                full_name TEXT NOT NULL,
                business_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'Pending',
                tax_status TEXT DEFAULT 'Unpaid',
                tax_paid_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS messages (
                id BIGSERIAL PRIMARY KEY,
                user_phone TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chats (
                id BIGSERIAL PRIMARY KEY,
                product_id BIGINT,
                sender_email TEXT NOT NULL,
                receiver_email TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        add_column_if_missing(
            connection, "products", "stock", "INTEGER NOT NULL DEFAULT 0"
        )
        add_column_if_missing(
            connection, "orders", "items_summary", "TEXT DEFAULT ''"
        )
        add_column_if_missing(
            connection, "orders", "vendor_confirmed", "INTEGER DEFAULT 0"
        )

        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_orders_phone ON orders(phone)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_phone ON messages(user_phone)"
        )


       

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# ------------------------------------------------------------
# HOME, PRODUCTS, SEARCH, WISHLIST
# ------------------------------------------------------------
@app.route("/")
def home():
    category = request.args.get("category")
    with get_db_connection() as connection:
        if category:
            products = connection.execute(
                "SELECT * FROM products WHERE category = ? ORDER BY id DESC",
                (category,),
            ).fetchall()
        else:
            products = connection.execute(
                "SELECT * FROM products ORDER BY id DESC"
            ).fetchall()

        wishlist_ids = []
        if session.get("user_id"):
            wishlist_ids = [
                row["product_id"]
                for row in connection.execute(
                    "SELECT product_id FROM wishlist WHERE user_id = ?",
                    (session["user_id"],),
                ).fetchall()
            ]

    return render_template(
        "index.html",
        products=products,
        selected_category=category,
        wishlist_ids=wishlist_ids,
    )


@app.route("/wishlist")
def wishlist():
    if not session.get("user_id"):
        return redirect("/login")

    with get_db_connection() as connection:
        wishlist_items = connection.execute(
            """
            SELECT p.id, p.product_name, p.price, p.category,
                   p.description, p.location, p.image
            FROM wishlist w
            JOIN products p ON p.id = w.product_id
            WHERE w.user_id = ?
            ORDER BY w.id DESC
            """,
            (session["user_id"],),
        ).fetchall()

    return render_template("wishlist.html", wishlist_items=wishlist_items)


@app.route("/sell")
def sell():
    return render_template("sell.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/post", methods=["POST"])
def post_product():
    product_name = request.form.get("product_name", "").strip()
    price = request.form.get("price", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()
    location = request.form.get("location", "").strip()
    image = request.files.get("product_image")

    if not all([product_name, price, category, description, location]) or not image or not image.filename:
        return "Please complete all product fields and choose an image.", 400

    try:
        price = float(price)
        if price < 0:
            raise ValueError
    except ValueError:
        return "Enter a valid product price.", 400

    image_filename = secure_filename(image.filename)
    if not image_filename:
        return "Invalid image filename.", 400

    # Avoid overwriting another upload with the same filename.
    stem, extension = os.path.splitext(image_filename)
    image_filename = f"{stem}_{secrets.token_hex(4)}{extension}"
    image.save(UPLOAD_FOLDER / image_filename)

    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO products
            (product_name, price, category, description, location, image, stock)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_name,
                price,
                category,
                description,
                location,
                image_filename,
                max(0, int(request.form.get("stock", 0) or 0)),
            ),
        )

    return redirect("/")


@app.route("/delete-product/<int:product_id>", methods=["POST", "GET"])
def delete_product(product_id):
    if not session.get("is_admin"):
        return "Not allowed", 403

    next_url = request.args.get("next", "/")
    with get_db_connection() as connection:
        row = connection.execute(
            "SELECT image FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if row:
            connection.execute("DELETE FROM products WHERE id = ?", (product_id,))
            image_filename = row["image"]
        else:
            image_filename = None

    if image_filename and not image_filename.startswith(("http://", "https://")):
        image_path = UPLOAD_FOLDER / os.path.basename(image_filename)
        if image_path.is_file():
            try:
                image_path.unlink()
            except OSError:
                pass

    return redirect(next_url if next_url.startswith("/") and not next_url.startswith("//") else "/")


@app.route("/product/<int:product_id>")
def product_details(product_id):
    with get_db_connection() as connection:
        product = connection.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()

    if product is None:
        return "Product not found", 404

    viewed = session.get("recently_viewed", [])
    if product_id in viewed:
        viewed.remove(product_id)
    viewed.insert(0, product_id)
    session["recently_viewed"] = viewed[:10]
    return render_template("product.html", product=product)


@app.route("/add-to-cart/<int:product_id>")
def add_to_cart(product_id):
    with get_db_connection() as connection:
        product = connection.execute(
            "SELECT stock, product_name FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()

    if not product:
        return redirect("/")
    if (product["stock"] or 0) <= 0:
        return redirect(request.referrer or "/")

    cart_data = session.get("cart", {})
    if isinstance(cart_data, list):
        converted = {}
        for old_id in cart_data:
            old_id = str(old_id)
            converted[old_id] = converted.get(old_id, 0) + 1
        cart_data = converted

    key = str(product_id)
    cart_data[key] = int(cart_data.get(key, 0)) + 1
    session["cart"] = cart_data
    session["last_added_product"] = product["product_name"]

    next_url = request.referrer or f"/product/{product_id}"
    separator = "&" if "?" in next_url else "?"
    return redirect(f"{next_url}{separator}added=1")


@app.route("/cart")
def cart():
    cart_data = session.get("cart", {})
    if isinstance(cart_data, list):
        converted = {}
        for item in cart_data:
            item = str(item)
            converted[item] = converted.get(item, 0) + 1
        cart_data = converted
        session["cart"] = cart_data

    products = []
    total = 0
    cart_count = 0

    with get_db_connection() as connection:
        for product_id, quantity in cart_data.items():
            product = connection.execute(
                "SELECT * FROM products WHERE id = ?", (product_id,)
            ).fetchone()
            if product:
                quantity = max(1, int(quantity))
                products.append((product, quantity))
                total += float(product["price"]) * quantity
                cart_count += quantity

        cart_product_ids = set(cart_data.keys())
        viewed_ids = [
            int(pid)
            for pid in session.get("recently_viewed", [])
            if str(pid) not in cart_product_ids
        ]
        recently_viewed = []
        if viewed_ids:
            placeholders = ",".join("?" for _ in viewed_ids)
            rows = connection.execute(
                f"SELECT * FROM products WHERE id IN ({placeholders})",
                viewed_ids,
            ).fetchall()
            row_map = {row["id"]: row for row in rows}
            recently_viewed = [row_map[pid] for pid in viewed_ids if pid in row_map]

    return render_template(
        "cart.html",
        products=products,
        total=total,
        cart_count=cart_count,
        recently_viewed=recently_viewed,
    )


@app.route("/increase-cart/<int:product_id>")
def increase_cart(product_id):
    cart_data = session.get("cart", {})
    if isinstance(cart_data, list):
        converted = {}
        for item in cart_data:
            item = str(item)
            converted[item] = converted.get(item, 0) + 1
        cart_data = converted

    key = str(product_id)
    with get_db_connection() as connection:
        product = connection.execute(
            "SELECT stock FROM products WHERE id = ?", (product_id,)
        ).fetchone()

    if product:
        current = int(cart_data.get(key, 0))
        if current < int(product["stock"] or 0):
            cart_data[key] = current + 1
    session["cart"] = cart_data
    return redirect("/cart")


@app.route("/decrease-cart/<int:product_id>")
def decrease_cart(product_id):
    cart_data = session.get("cart", {})
    key = str(product_id)
    if key in cart_data:
        cart_data[key] -= 1
        if cart_data[key] <= 0:
            del cart_data[key]
    session["cart"] = cart_data
    return redirect("/cart")


@app.route("/remove-from-cart/<int:product_id>")
def remove_from_cart(product_id):
    cart_data = session.get("cart", {})
    if isinstance(cart_data, list):
        converted = {}
        for item in cart_data:
            item = str(item)
            converted[item] = converted.get(item, 0) + 1
        cart_data = converted
    cart_data.pop(str(product_id), None)
    session["cart"] = cart_data
    return redirect("/cart")


@app.route("/checkout")
def checkout():
    cart_data = session.get("cart", {})
    products = []
    total = 0

    with get_db_connection() as connection:
        for product_id, quantity in cart_data.items():
            product = connection.execute(
                "SELECT * FROM products WHERE id = ?", (product_id,)
            ).fetchone()
            if product:
                products.append((product, quantity))
                total += float(product["price"]) * int(quantity)

    return render_template("checkout.html", products=products, total=total)


@app.route("/place-order", methods=["POST"])
def place_order():
    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    if not full_name or not phone:
        return "Please provide your name and phone number.", 400

    delivery_type = request.form.get("delivery_type", "pickup")
    delivery_fee = 500 if delivery_type == "delivery" else 0
    if delivery_type == "delivery":
        address = request.form.get("address", "On Campus").strip()
        city = request.form.get("city", "LASU Campus").strip()
    else:
        address = "Pickup at LASU ICT Centre"
        city = "LASU ICT Centre"

    cart_data = session.get("cart", {})
    if not cart_data:
        return redirect("/cart")

    subtotal = 0
    with get_db_connection() as connection:
        for product_id, quantity in cart_data.items():
            product = connection.execute(
                "SELECT product_name, price, stock FROM products WHERE id = ?",
                (product_id,),
            ).fetchone()
            if not product:
                return f"Product {product_id} is no longer available.", 400
            quantity = int(quantity)
            stock = int(product["stock"] or 0)
            if quantity < 1 or stock < quantity:
                return f"Not enough stock for '{product['product_name']}'. Only {stock} left.", 400
            subtotal += float(product["price"]) * quantity

    session["checkout_details"] = {
        "full_name": full_name,
        "phone": phone,
        "address": address,
        "city": city,
        "delivery_type": delivery_type,
        "total": subtotal + delivery_fee,
    }
    return redirect("/payment")


@app.route("/payment")
def payment():
    if not session.get("checkout_details"):
        return redirect("/cart")
    return render_template("payment.html", total=session["checkout_details"]["total"])


@app.route("/process-payment", methods=["POST"])
def process_payment():
    details = session.get("checkout_details")
    cart_data = session.get("cart", {})
    if not details or not cart_data:
        return redirect("/cart")

    payment_method = request.form.get("payment_method", "card")
    final_total = float(details["total"])
    if payment_method == "transfer":
        final_total += 50

    try:
        with get_db_connection() as connection:
            items_bought = []
            for product_id, quantity in cart_data.items():
                product = connection.execute(
                    "SELECT product_name, image, stock, price FROM products WHERE id = ?",
                    (product_id,),
                ).fetchone()
                if not product:
                    return f"Product {product_id} is no longer available.", 400
                quantity = int(quantity)
                if int(product["stock"] or 0) < quantity:
                    return f"Not enough stock for '{product['product_name']}'.", 400
                items_bought.append(
                    f"{product['product_name']}•{product['image']}•{quantity}"
                )

            cursor = connection.execute(
                """
                INSERT INTO orders
                (full_name, phone, address, city, total, status, created_at, items_summary)
                VALUES (?, ?, ?, ?, ?, 'Paid', CURRENT_TIMESTAMP, ?)
                RETURNING id """
                (
                    details["full_name"],
                    details["phone"],
                    details["address"],
                    details["city"],
                    final_total,
                    ", ".join(items_bought),
                ),
            )
            order_id = cursor.fetchone()["id"]

            connection.execute(
                """
                INSERT INTO messages (user_phone, title, message)
                VALUES (?, ?, ?)
                """,
                (
                    details["phone"],
                    "Your order has been received!",
                    f"Thank you for choosing LASU CampusMart! We have received your order #{order_id}.",
                ),
            )

            for product_id, quantity in cart_data.items():
                connection.execute(
                    "UPDATE products SET stock = stock - ? WHERE id = ?",
                    (int(quantity), product_id),
                )

            first_product_id = next(iter(cart_data))
            first_product = connection.execute(
                "SELECT category FROM products WHERE id = ?",
                (first_product_id,),
            ).fetchone()
            vendor_info = None
            if first_product:
                vendor_info = connection.execute(
                    """
                    SELECT email, business_name FROM vendors
                    WHERE category = ? AND status = 'Approved'
                    LIMIT 1
                    """,
                    (first_product["category"],),
                ).fetchone()

        # Emails are sent after the database transaction succeeds.
        user_email = session.get("user_email")
        if user_email:
            send_mail_message(
                f"Order Confirmed #{order_id} - LASU CampusMart",
                [user_email],
                f"<h3>Hi {details['full_name']},</h3>"
                f"<p>We received your payment of ₦{final_total:,.2f}. "
                "Your order is being processed.</p>",
            )

        if vendor_info:
            send_mail_message(
                f"New Sale! Order #{order_id}",
                [vendor_info["email"]],
                f"<h3>Hi {vendor_info['business_name']},</h3>"
                f"<p>You made a sale! Order #{order_id} has been paid.</p>",
            )

        admin_email = app.config.get("MAIL_USERNAME")
        if admin_email:
            send_mail_message(
                f"Admin Alert: New Order #{order_id}",
                [admin_email],
                f"<h3>New Order Placed</h3>"
                f"<p>Order #{order_id} by {details['full_name']} "
                f"for ₦{final_total:,.2f}.</p>",
            )

    except psycopg2.Error as exc:
        app.logger.exception("Could not process order")
        return "There was a database problem processing your order. Please try again.", 500

    session.pop("cart", None)
    session.pop("checkout_details", None)
    return render_template("Order_success.html", total=final_total, order_id=order_id)


@app.route("/carousel")
def carousel():
    return render_template("index.html")


@app.route("/search")
def search():
    query = request.args.get("query", "").strip()
    with get_db_connection() as connection:
        if query:
            words = query.split()
            conditions = []
            params = []
            for word in words:
                conditions.append(
                    "(product_name LIKE ? OR description LIKE ? OR category LIKE ?)"
                )
                params.extend([f"%{word}%"] * 3)
            sql = (
                "SELECT * FROM products WHERE "
                + " OR ".join(conditions)
                + " ORDER BY id DESC"
            )
            products = connection.execute(sql, params).fetchall()
        else:
            products = connection.execute(
                "SELECT * FROM products ORDER BY id DESC"
            ).fetchall()

        wishlist_ids = []
        if session.get("user_id"):
            wishlist_ids = [
                row["product_id"]
                for row in connection.execute(
                    "SELECT product_id FROM wishlist WHERE user_id = ?",
                    (session["user_id"],),
                ).fetchall()
            ]

    return render_template(
        "search_results.html",
        products=products,
        query=query,
        wishlist_ids=wishlist_ids,
    )


# ------------------------------------------------------------
# ADMIN
# ------------------------------------------------------------
def admin_required():
    return bool(session.get("is_admin"))


@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if admin_required():
        return redirect("/admin")
    if request.method == "POST":
        supplied_password = request.form.get("password", "")
        configured_password = os.environ.get("JANNEY27", "")
        if configured_password and secrets.compare_digest(
            supplied_password, configured_password
        ):
            session.clear()
            session["is_admin"] = True
            session.permanent = True
            return redirect("/admin")
        return render_template(
            "admin_login.html",
            error="Wrong password. Check the configured admin password.",
        )
    return render_template("admin_login.html")


@app.route("/admin-logout")
def admin_logout():
    session.clear()
    return redirect("/admin-login")


@app.route("/admin")
def admin_dashboard():
    if not admin_required():
        return redirect("/admin-login")
    with get_db_connection() as connection:
        total_revenue = connection.execute(
            "SELECT SUM(total) FROM orders"
        ).fetchone()[0] or 0
        total_orders = connection.execute(
            "SELECT COUNT(*) FROM orders"
        ).fetchone()[0]
        total_products = connection.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()[0]
        total_customers = connection.execute(
            "SELECT COUNT(DISTINCT phone) FROM orders"
        ).fetchone()[0]
        recent_orders = connection.execute(
            "SELECT id, full_name, phone, city, total FROM orders ORDER BY id DESC LIMIT 5"
        ).fetchall()
        top_products = connection.execute(
            "SELECT product_name, price, category FROM products ORDER BY id DESC LIMIT 5"
        ).fetchall()
        low_stock_count = connection.execute(
            "SELECT COUNT(*) FROM products WHERE stock <= 5"
        ).fetchone()[0]
        low_stock_items = connection.execute(
            "SELECT id, product_name, stock FROM products WHERE stock <= 5 ORDER BY stock ASC LIMIT 3"
        ).fetchall()

    return render_template(
        "admin_dashboard.html",
        total_revenue=total_revenue,
        total_orders=total_orders,
        total_products=total_products,
        total_customers=total_customers,
        recent_orders=recent_orders,
        top_products=top_products,
        low_stock_count=low_stock_count,
        low_stock_items=low_stock_items,
    )


@app.route("/admin/products")
def admin_products():
    if not admin_required():
        return redirect("/admin-login")
    search_term = request.args.get("search", "").strip()
    stock_filter = request.args.get("stock", "").strip()
    query = "SELECT * FROM products"
    conditions = []
    params = []

    if search_term:
        conditions.append("product_name LIKE ?")
        params.append(f"%{search_term}%")
    if stock_filter == "in":
        conditions.append("stock > 5")
    elif stock_filter == "low":
        conditions.append("stock BETWEEN 1 AND 5")
    elif stock_filter == "out":
        conditions.append("stock <= 0")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC"

    with get_db_connection() as connection:
        products = connection.execute(query, params).fetchall()
        total_count = connection.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()[0]
        in_stock_count = connection.execute(
            "SELECT COUNT(*) FROM products WHERE stock > 5"
        ).fetchone()[0]
        low_stock_count = connection.execute(
            "SELECT COUNT(*) FROM products WHERE stock BETWEEN 1 AND 5"
        ).fetchone()[0]
        out_stock_count = connection.execute(
            "SELECT COUNT(*) FROM products WHERE stock <= 0"
        ).fetchone()[0]

    return render_template(
        "admin_products.html",
        products=products,
        search=search_term,
        stock_filter=stock_filter,
        total_count=total_count,
        in_stock_count=in_stock_count,
        low_stock_count=low_stock_count,
        out_stock_count=out_stock_count,
    )


@app.route("/admin/products/update-stock/<int:product_id>", methods=["POST"])
def admin_update_stock(product_id):
    if not admin_required():
        return "Not allowed", 403
    try:
        new_stock = max(0, int(request.form.get("stock", "0")))
    except ValueError:
        new_stock = 0
    with get_db_connection() as connection:
        connection.execute(
            "UPDATE products SET stock = ? WHERE id = ?",
            (new_stock, product_id),
        )
    return redirect("/admin/products")


@app.route("/admin/orders")
def admin_orders():
    if not admin_required():
        return redirect("/admin-login")
    status_filter = request.args.get("status", "").strip()
    search_term = request.args.get("search", "").strip()
    query = """
        SELECT id, full_name, phone, address, city, total, status, created_at
        FROM orders
    """
    conditions = []
    params = []
    if status_filter:
        conditions.append("status = ?")
        params.append(status_filter)
    if search_term:
        conditions.append("(full_name LIKE ? OR phone LIKE ? OR CAST(id AS TEXT) LIKE ?)")
        params.extend([f"%{search_term}%"] * 3)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC"

    with get_db_connection() as connection:
        orders = connection.execute(query, params).fetchall()
        status_counts = dict(
            connection.execute(
                "SELECT status, COUNT(*) FROM orders GROUP BY status"
            ).fetchall()
        )

    return render_template(
        "admin_orders.html",
        orders=orders,
        status_filter=status_filter,
        search=search_term,
        status_counts=status_counts,
    )


@app.route("/admin/orders/update/<int:order_id>", methods=["POST"])
def admin_update_order_status(order_id):
    if not admin_required():
        return "Not allowed", 403
    new_status = request.form.get("status", "Pending")
    with get_db_connection() as connection:
        order = connection.execute(
            "SELECT phone FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
        connection.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (new_status, order_id),
        )
        if order and new_status in ("Vendor Confirmed", "Shipped", "Delivered"):
            connection.execute(
                "INSERT INTO messages (user_phone, title, message) VALUES (?, ?, ?)",
                (
                    order["phone"],
                    f"Order {new_status}",
                    f"Your order #{order_id} status has been updated to: {new_status}.",
                ),
            )
    return redirect("/admin/orders")


@app.route("/admin/vendors")
def admin_vendors():
    if not admin_required():
        return redirect("/admin-login")
    status_filter = request.args.get("status", "").strip()
    search_term = request.args.get("search", "").strip()
    query = """
        SELECT id, full_name, business_name, email, phone, category,
               status, created_at, tax_status
        FROM vendors
    """
    conditions = []
    params = []
    if status_filter:
        conditions.append("status = ?")
        params.append(status_filter)
    if search_term:
        conditions.append(
            "(business_name LIKE ? OR full_name LIKE ? OR email LIKE ? OR phone LIKE ?)"
        )
        params.extend([f"%{search_term}%"] * 4)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC"

    with get_db_connection() as connection:
        vendors = connection.execute(query, params).fetchall()
        status_counts = dict(
            connection.execute(
                "SELECT status, COUNT(*) FROM vendors GROUP BY status"
            ).fetchall()
        )

    return render_template(
        "admin_vendors.html",
        vendors=vendors,
        status_filter=status_filter,
        search=search_term,
        status_counts=status_counts,
    )


@app.route("/admin/vendors/update/<int:vendor_id>", methods=["POST"])
def admin_update_vendor_status(vendor_id):
    if not admin_required():
        return "Not allowed", 403
    new_status = request.form.get("status", "Pending")
    with get_db_connection() as connection:
        vendor = connection.execute(
            "SELECT email, business_name FROM vendors WHERE id = ?",
            (vendor_id,),
        ).fetchone()
        connection.execute(
            "UPDATE vendors SET status = ? WHERE id = ?",
            (new_status, vendor_id),
        )

    if new_status == "Approved" and vendor and vendor["email"]:
        send_mail_message(
            "Your Vendor Account is Approved!",
            [vendor["email"]],
            f"<h3>Congratulations {vendor['business_name']}!</h3>"
            "<p>Your vendor application has been approved.</p>",
        )
    return redirect("/admin/vendors")


@app.route("/admin/confirm-tax/<int:vendor_id>", methods=["POST"])
def admin_confirm_tax(vendor_id):
    if not admin_required():
        return redirect("/admin-login")
    with get_db_connection() as connection:
        connection.execute(
            """
            UPDATE vendors
            SET tax_status = 'Paid', tax_paid_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (vendor_id,),
        )
    return redirect("/admin/vendors")


# ------------------------------------------------------------
# REGISTER, LOGIN, PASSWORD RESET, PROFILE
# ------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect("/")

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        matric_or_staff_id = request.form.get("matric_or_staff_id", "").strip()
        role = request.form.get("role", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        phone = request.form.get("phone", "").strip()

        errors = []
        if not all([full_name, email, matric_or_staff_id, role, password]):
            errors.append("All fields are required.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm_password:
            errors.append("Passwords do not match.")
        if role not in ("student", "lecturer", "staff"):
            errors.append("Invalid role selected.")

        form_data = {
            "full_name": full_name,
            "email": email,
            "matric_or_staff_id": matric_or_staff_id,
            "role": role,
            "phone": phone,
        }

        if not errors:
            try:
                with get_db_connection() as connection:
                    existing = connection.execute(
                        "SELECT id FROM users WHERE email = ?", (email,)
                    ).fetchone()
                    if existing:
                        errors.append("An account with this email already exists.")
                    else:
                        connection.execute(
                            """
                            INSERT INTO users
                            (full_name, email, matric_or_staff_id, role, password_hash, phone)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                full_name,
                                email,
                                matric_or_staff_id,
                                role,
                                generate_password_hash(password),
                                phone,
                            ),
                        )
            except psycopg2.IntegrityError:
                errors.append("An account with this email already exists.")
            except psycopg2.Error:
                app.logger.exception("Registration database error")
                errors.append("Something went wrong while creating your account. Please try again.")

        if errors:
            return render_template(
                "register.html", errors=errors, form_data=form_data
            )

        send_welcome_email(email, full_name)
        return redirect("/login?registered=1")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect("/profile")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        errors = []

        if not email or not password:
            errors.append("Please enter both email and password.")

        if not errors:
            with get_db_connection() as connection:
                user = connection.execute(
                    """
                    SELECT id, full_name, email, role, password_hash
                    FROM users WHERE email = ?
                    """,
                    (email,),
                ).fetchone()

            if user and check_password_hash(user["password_hash"], password):
                # Remove any previous user's/admin/vendor session values.
                session.clear()
                session["user_id"] = user["id"]
                session["user_name"] = user["full_name"]
                session["user_email"] = user["email"]
                session["user_role"] = user["role"]
                session["is_vendor"] = False
                session.permanent = True
                return redirect("/profile")

            errors.append("Invalid email or password.")

        return render_template("login.html", errors=errors, email=email)

    return render_template(
        "login.html",
        registered=request.args.get("registered") == "1",
        reset=request.args.get("reset") == "1",
    )


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        with get_db_connection() as connection:
            user = connection.execute(
                "SELECT id FROM users WHERE email = ?", (email,)
            ).fetchone()

        if user:
            # School-project flow retained. A real deployment should use a
            # time-limited, single-use reset token delivered by email.
            return redirect(f"/reset-password?email={email}")
        return render_template(
            "forgot_password.html",
            error="No account found with that email.",
        )
    return render_template("forgot_password.html")


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    email = request.args.get("email", "").strip().lower()
    if not email:
        return redirect("/forgot-password")

    if request.method == "POST":
        new_password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        if len(new_password) < 6:
            return render_template(
                "reset_password.html",
                email=email,
                error="Password must be at least 6 characters.",
            )
        if new_password != confirm_password:
            return render_template(
                "reset_password.html",
                email=email,
                error="Passwords do not match.",
            )

        with get_db_connection() as connection:
            cursor = connection.execute(
                "UPDATE users SET password_hash = ? WHERE email = ?",
                (generate_password_hash(new_password), email),
            )
            if cursor.rowcount == 0:
                return render_template(
                    "reset_password.html",
                    email=email,
                    error="No account found with that email.",
                )
        return redirect("/login?reset=1")

    return render_template("reset_password.html", email=email)


@app.route("/settings")
def settings():
    if not session.get("user_id"):
        return redirect("/login")
    return render_template("settings.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/wishlist/toggle/<int:product_id>")
def wishlist_toggle(product_id):
    if not session.get("user_id"):
        return redirect("/login")

    user_id = session["user_id"]
    with get_db_connection() as connection:
        product = connection.execute(
            "SELECT product_name FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        product_name = product["product_name"] if product else "Product"
        existing = connection.execute(
            "SELECT id FROM wishlist WHERE user_id = ? AND product_id = ?",
            (user_id, product_id),
        ).fetchone()

        if existing:
            connection.execute(
                "DELETE FROM wishlist WHERE id = ?", (existing["id"],)
            )
            action = "removed"
        else:
            if product:
                connection.execute(
                 "INSERT INTO wishlist (user_id, product_id) VALUES (?, ?) ON CONFLICT (user_id, product_id) DO NOTHING",
                    (user_id, product_id),
                )
            action = "added"

    session["wishlist_toast_name"] = product_name
    session["wishlist_toast_action"] = action
    next_url = request.referrer or "/"
    separator = "&" if "?" in next_url else "?"
    return redirect(f"{next_url}{separator}wishlist={action}")


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    with get_db_connection() as connection:
        user = connection.execute(
            "SELECT full_name, email, phone FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not user:
            session.clear()
            return redirect("/login")

        order_count = 0
        if user["phone"]:
            order_count = connection.execute(
                "SELECT COUNT(*) FROM orders WHERE phone = ?",
                (user["phone"],),
            ).fetchone()[0]
        wishlist_count = connection.execute(
            "SELECT COUNT(*) FROM wishlist WHERE user_id = ?", (user_id,)
        ).fetchone()[0]

    return render_template(
        "profile.html",
        user=user,
        order_count=order_count,
        wishlist_count=wishlist_count,
    )


# ------------------------------------------------------------
# ORDERS, INBOX, INVENTORY, REPORTS
# ------------------------------------------------------------
@app.route("/admin/inventory")
def admin_inventory():
    if not admin_required():
        return redirect("/admin-login")
    with get_db_connection() as connection:
        out_of_stock = connection.execute(
            """
            SELECT id, product_name, price, category, stock, image, location
            FROM products WHERE stock <= 0 ORDER BY product_name ASC
            """
        ).fetchall()
        low_stock = connection.execute(
            """
            SELECT id, product_name, price, category, stock, image, location
            FROM products WHERE stock BETWEEN 1 AND 5 ORDER BY stock ASC
            """
        ).fetchall()
        total = connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        healthy = connection.execute(
            "SELECT COUNT(*) FROM products WHERE stock > 5"
        ).fetchone()[0]
        out_count = connection.execute(
            "SELECT COUNT(*) FROM products WHERE stock <= 0"
        ).fetchone()[0]
        low_count = connection.execute(
            "SELECT COUNT(*) FROM products WHERE stock BETWEEN 1 AND 5"
        ).fetchone()[0]

    return render_template(
        "admin_inventory.html",
        out_of_stock=out_of_stock,
        low_stock=low_stock,
        total=total,
        healthy=healthy,
        out_count=out_count,
        low_count=low_count,
    )


@app.route("/admin/reports")
def admin_reports():
    if not admin_required():
        return redirect("/admin-login")
    with get_db_connection() as connection:
        total_revenue = connection.execute(
            "SELECT SUM(total) FROM orders"
        ).fetchone()[0] or 0
        total_orders = connection.execute(
            "SELECT COUNT(*) FROM orders"
        ).fetchone()[0]
        avg_order = total_revenue / total_orders if total_orders else 0
        raw_daily = connection.execute(
            """
            SELECT DATE(created_at) AS day, SUM(total)
            FROM orders
            WHERE created_at IS NOT NULL
            GROUP BY DATE(created_at)
            ORDER BY day DESC LIMIT 7
            """
        ).fetchall()
        daily_revenue = list(reversed(raw_daily))
        top_orders = connection.execute(
            """
            SELECT id, full_name, total, city, created_at
            FROM orders ORDER BY total DESC LIMIT 5
            """
        ).fetchall()
        # The original join used orders.id = products.id, which does not
        # represent the products in an order. Leave this chart empty rather
        # than displaying misleading category totals.
        category_revenue = []

    best_day = "—"
    if daily_revenue:
        best_day = max(
            daily_revenue, key=lambda row: row["sum(total)"] or 0
        )["day"] or "—"

    return render_template(
        "admin_reports.html",
        total_revenue=total_revenue,
        total_orders=total_orders,
        avg_order=avg_order,
        daily_revenue=daily_revenue,
        category_revenue=category_revenue,
        top_orders=top_orders,
        best_day=best_day,
    )


@app.route("/my-orders")
def my_orders():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")
    with get_db_connection() as connection:
        user = connection.execute(
            "SELECT phone FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        user_phone = user["phone"] if user and user["phone"] else ""
        orders = []
        if user_phone:
            orders = connection.execute(
                """
                SELECT id, total, status, created_at, city, items_summary
                FROM orders WHERE phone = ? ORDER BY id DESC
                """,
                (user_phone,),
            ).fetchall()

    return render_template("my_orders.html", orders=orders)


@app.route("/cancel-order/<int:order_id>", methods=["POST", "GET"])
def cancel_order(order_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    with get_db_connection() as connection:
        user = connection.execute(
            "SELECT phone FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not user or not user["phone"]:
            return redirect("/my-orders")

        # A user can cancel only an order associated with their own phone.
        connection.execute(
            """
            UPDATE orders
            SET status = 'Cancelled'
            WHERE id = ? AND phone = ?
              AND status IN ('Pending', 'Paid', 'Pending Vendor')
            """,
            (order_id, user["phone"]),
        )

    return redirect("/my-orders")


@app.route("/inbox")
def inbox():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    with get_db_connection() as connection:
        user = connection.execute(
            "SELECT phone FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        user_phone = user["phone"] if user and user["phone"] else ""
        messages = []
        if user_phone:
            messages = connection.execute(
                """
                SELECT title, message, created_at
                FROM messages WHERE user_phone = ? ORDER BY id DESC
                """,
                (user_phone,),
            ).fetchall()

    return render_template("inbox.html", messages=messages)


# ------------------------------------------------------------
# VENDOR FEATURES
# ------------------------------------------------------------
@app.route("/vendor-signup", methods=["GET", "POST"])
def vendor_signup():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        business_name = request.form.get("business_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()

        if not all([full_name, business_name, email, phone, category]):
            return render_template(
                "vendor_signup.html",
                error="Please fill in all required fields.",
            )

        try:
            with get_db_connection() as connection:
                connection.execute(
                    """
                    INSERT INTO vendors
                    (full_name, business_name, email, phone, category, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (full_name, business_name, email, phone, category, description),
                )
            return redirect(f"/vendor-signup?success=1&email={email}")
        except Exception as e:
            print("VENDOR ERROR:", e) 
            return f"Database Error: {e}", 500
    
    success = request.args.get("success") == "1"
    email_to_check = request.args.get("email", "").strip().lower()
    if not email_to_check and session.get("user_id"):
        with get_db_connection() as connection:
            user_record = connection.execute(
                "SELECT email FROM users WHERE id = ?",
                (session["user_id"],),
            ).fetchone()
        if user_record:
            email_to_check = user_record["email"]

    is_approved_vendor = False
    if email_to_check:
        with get_db_connection() as connection:
            vendor = connection.execute(
                "SELECT status FROM vendors WHERE email = ? ORDER BY id DESC LIMIT 1",
                (email_to_check,),
            ).fetchone()
        is_approved_vendor = bool(vendor and vendor["status"] == "Approved")

    return render_template(
        "vendor_signup.html",
        success=success,
        is_approved_vendor=is_approved_vendor,
    )


@app.route("/vendor-portal")
def vendor_portal():
    if session.get("user_id") and session.get("is_vendor"):
        return redirect("/vendor-dashboard")
    return render_template("vendor_login.html")


@app.route("/vendor-login-action", methods=["POST"])
def vendor_login_action():
    email = request.form.get("email", "").strip().lower()
    with get_db_connection() as connection:
        vendor = connection.execute(
            """
            SELECT id, status FROM vendors
            WHERE email = ? ORDER BY id DESC LIMIT 1
            """,
            (email,),
        ).fetchone()
        if not vendor:
            return render_template(
                "vendor_login.html",
                error="Email not found. Please register as a vendor first.",
            )
        if vendor["status"] != "Approved":
            return render_template(
                "vendor_login.html",
                pending_message=(
                    f"Your application is currently '{vendor['status']}'. "
                    "Please wait for the Admin to approve your account."
                ),
            )
        user = connection.execute(
            "SELECT id, full_name, email, role FROM users WHERE email = ?",
            (email,),
        ).fetchone()

    if not user:
        return render_template(
            "vendor_login.html",
            error="User account error. Please contact support.",
        )

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["full_name"]
    session["user_email"] = user["email"]
    session["user_role"] = user["role"]
    session["is_vendor"] = True
    session["view_mode"] = "vendor"
    session.permanent = True
    return redirect("/vendor-dashboard")


@app.route("/vendor-tax-payment")
def vendor_tax_payment():
    if not session.get("user_id") or not session.get("is_vendor"):
        return redirect("/login")
    with get_db_connection() as connection:
        vendor = connection.execute(
            """
            SELECT tax_status, tax_paid_at FROM vendors
            WHERE email = ? ORDER BY id DESC LIMIT 1
            """,
            (session.get("user_email"),),
        ).fetchone()
    return render_template(
        "vendor_tax.html",
        tax_status=vendor["tax_status"] if vendor else "Unpaid",
        tax_paid_at=vendor["tax_paid_at"] if vendor else None,
    )


@app.route("/vendor-pay-tax", methods=["POST"])
def vendor_pay_tax():
    if not session.get("user_id") or not session.get("is_vendor"):
        return redirect("/login")
    with get_db_connection() as connection:
        connection.execute(
            "UPDATE vendors SET tax_status = 'Pending' WHERE email = ?",
            (session.get("user_email"),),
        )
    return redirect("/vendor-tax-payment")


@app.route("/vendor-dashboard")
def vendor_dashboard():
    if not session.get("user_id") or not session.get("is_vendor"):
        return redirect("/login")

    with get_db_connection() as connection:
        user = connection.execute(
            "SELECT email FROM users WHERE id = ?",
            (session["user_id"],),
        ).fetchone()
        vendor_app = None
        vendor_orders = []
        if user:
            vendor_app = connection.execute(
                """
                SELECT business_name, category, status, created_at,
                       tax_paid_at, tax_status
                FROM vendors WHERE email = ? ORDER BY id DESC LIMIT 1
                """,
                (user["email"],),
            ).fetchone()
            vendor_orders = connection.execute(
                """
                SELECT id, full_name, total, status, created_at
                FROM orders
                WHERE status IN ('Pending Vendor', 'Vendor Confirmed')
                ORDER BY id DESC
                """
            ).fetchall()

    return render_template(
        "vendor_dashboard.html",
        vendor=vendor_app,
        orders=vendor_orders,
    )


@app.route("/vendor-order/<int:order_id>")
def vendor_order_details(order_id):
    if not session.get("user_id") or not session.get("is_vendor"):
        return redirect("/login")
    with get_db_connection() as connection:
        order = connection.execute(
            "SELECT * FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
    if not order:
        return "Order not found", 404
    return render_template("vendor_order_details.html", order=order)


@app.route("/vendor-confirm-payment/<int:order_id>", methods=["POST"])
def vendor_confirm_payment(order_id):
    if not session.get("user_id") or not session.get("is_vendor"):
        return "Not allowed", 403
    with get_db_connection() as connection:
        connection.execute(
            """
            UPDATE orders
            SET status = 'Vendor Confirmed', vendor_confirmed = 1
            WHERE id = ?
            """,
            (order_id,),
        )
    return redirect(f"/vendor-order/{order_id}")


@app.route("/vendor-deliver-order/<int:order_id>", methods=["POST"])
def vendor_deliver_order(order_id):
    if not session.get("user_id") or not session.get("is_vendor"):
        return "Not allowed", 403
    with get_db_connection() as connection:
        connection.execute(
            "UPDATE orders SET status = 'Delivered' WHERE id = ?",
            (order_id,),
        )
    return redirect(f"/vendor-order/{order_id}?delivered=1")


@app.route("/vendor-confirmed-payments")
def vendor_confirmed_payments():
    if not session.get("user_id") or not session.get("is_vendor"):
        return redirect("/login")
    with get_db_connection() as connection:
        payments = connection.execute(
            """
            SELECT id, full_name, total, status, created_at
            FROM orders
            WHERE status IN ('Vendor Confirmed', 'Ready for Delivery', 'Delivered')
            ORDER BY id DESC
            """
        ).fetchall()
    return render_template("vendor_payment_records.html", payments=payments)


@app.route("/account-redirect")
def account_redirect():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    with get_db_connection() as connection:
        user = connection.execute(
            "SELECT email FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not user:
            session.clear()
            return redirect("/login")
        vendor = connection.execute(
            """
            SELECT status FROM vendors
            WHERE email = ? ORDER BY id DESC LIMIT 1
            """,
            (user["email"],),
        ).fetchone()

    if vendor and vendor["status"] == "Approved":
        session["is_vendor"] = True
        if session.get("view_mode") == "buyer":
            return redirect("/profile")
        return redirect("/vendor-dashboard")

    session["is_vendor"] = False
    return redirect("/profile")


@app.route("/switch-to-buyer")
def switch_to_buyer():
    if not session.get("user_id"):
        return redirect("/login")
    session["view_mode"] = "buyer"
    session["is_vendor"] = False
    return redirect("/profile")


@app.route("/switch-to-vendor")
def switch_to_vendor():
    if not session.get("user_id"):
        return redirect("/login")
    session["view_mode"] = "vendor"
    session["is_vendor"] = True
    return redirect("/vendor-dashboard")


@app.route("/send-message/<int:product_id>", methods=["POST"])
def send_message(product_id):
    if not session.get("user_id"):
        return redirect("/login")
    message_text = request.form.get("message", "").strip()
    if not message_text:
        return redirect(f"/product/{product_id}")

    with get_db_connection() as connection:
        sender = connection.execute(
            "SELECT email FROM users WHERE id = ?",
            (session["user_id"],),
        ).fetchone()
        if not sender:
            session.clear()
            return redirect("/login")
        product = connection.execute(
            "SELECT id FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if not product:
            return "Product not found", 404
        connection.execute(
            """
            INSERT INTO chats (product_id, sender_email, receiver_email, message)
            VALUES (?, ?, ?, ?)
            """,
            (
                product_id,
                sender["email"],
                "admin@lasucampusmart.com",
                message_text,
            ),
        )
    return redirect(f"/product/{product_id}?message_sent=1")


@app.route("/close-account", methods=["POST"])
def close_account():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    try:
        with get_db_connection() as connection:
            connection.execute("DELETE FROM wishlist WHERE user_id = ?", (user_id,))
            connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
    except psycopg2.Error:
        app.logger.exception("Account deletion failed")
        return "Could not close the account. Please try again.", 500

    session.clear()
    return redirect("/register")


# Initialize/migrate the database when the app starts.
create_database()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")