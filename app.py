from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import db
from models.user import User
from models.product import Product
from models.cart import Cart
from models.order import Order, OrderItem
from functools import wraps

app = Flask(__name__)
app.secret_key = "shopeasy-development-secret-key"

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "mysql+pymysql://root:Shraddha1010%40@localhost/ecommerce_db"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):

        user = User.query.get(session["user_id"])

        if not user or user.role != "admin":
            return "Access Denied: Admins only!", 403

        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            return "Email already registered!"

        hashed_password = generate_password_hash(password)

        new_user = User(
            name=name,
            email=email,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        return "Registration Successful!"

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):

            session["user_id"] = user.id
            session["user_name"] = user.name

            return redirect(url_for("dashboard"))

        else:
            return "Invalid email or password!"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return "You have been logged out successfully!"

@app.route("/dashboard")
@login_required

def dashboard():

    return render_template(
        "dashboard.html",
        user_name=session["user_name"]
    )


@app.route("/add-product", methods=["GET", "POST"])
@login_required
def add_product():

    if request.method == "POST":

        name = request.form["name"]
        description = request.form["description"]
        price = request.form["price"]
        stock = request.form["stock"]
        category = request.form["category"]

        new_product = Product(
            name=name,
            description=description,
            price=price,
            stock=stock,
            category=category
        )

        db.session.add(new_product)
        db.session.commit()

        return "Product Added Successfully!"

    return render_template("add_product.html")



@app.route("/products")
def products():

    all_products = Product.query.all()

    return render_template(
        "products.html",
        products=all_products
    )


@app.route("/edit-product/<int:product_id>", methods=["GET", "POST"])
@login_required
def edit_product(product_id):

    product = Product.query.get_or_404(product_id)

    if request.method == "POST":

        product.name = request.form["name"]
        product.description = request.form["description"]
        product.price = request.form["price"]
        product.stock = request.form["stock"]
        product.category = request.form["category"]

        db.session.commit()

        return "Product Updated Successfully!"

    return render_template(
        "edit_product.html",
        product=product
    )


@app.route("/delete-product/<int:product_id>", methods=["POST"])
@login_required
def delete_product(product_id):

    product = Product.query.get_or_404(product_id)

    db.session.delete(product)
    db.session.commit()

    return redirect(url_for("products"))



@app.route("/add-to-cart/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id):

    product = Product.query.get_or_404(product_id)

    cart_item = Cart.query.filter_by(
        user_id=session["user_id"],
        product_id=product_id
    ).first()

    if cart_item:
        cart_item.quantity += 1
    else:
        new_item = Cart(
            user_id=session["user_id"],
            product_id=product.id,
            quantity=1
        )

        db.session.add(new_item)

    db.session.commit()

    return "Product Added to Cart Successfully!"




@app.route("/cart")
@login_required
def view_cart():

    cart_items = Cart.query.filter_by(
        user_id=session["user_id"]
    ).all()

    total_amount = sum(
        item.product.price * item.quantity
        for item in cart_items
    )

    return render_template(
        "cart.html",
        cart_items=cart_items,
        total_amount=total_amount
    )


@app.route("/update-cart/<int:cart_id>", methods=["POST"])
@login_required
def update_cart(cart_id):

    cart_item = Cart.query.filter_by(
        id=cart_id,
        user_id=session["user_id"]
    ).first_or_404()

    quantity = int(request.form["quantity"])

    if quantity < 1:
        return "Quantity must be at least 1!"

    if quantity > cart_item.product.stock:
        return "Requested quantity exceeds available stock!"

    cart_item.quantity = quantity

    db.session.commit()

    return redirect(url_for("view_cart"))


@app.route("/remove-from-cart/<int:cart_id>", methods=["POST"])
@login_required
def remove_from_cart(cart_id):

    cart_item = Cart.query.filter_by(
        id=cart_id,
        user_id=session["user_id"]
    ).first_or_404()

    db.session.delete(cart_item)
    db.session.commit()

    return redirect(url_for("view_cart"))


@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():

    cart_items = Cart.query.filter_by(
        user_id=session["user_id"]
    ).all()

    if not cart_items:
        return "Your cart is empty!"

    total = sum(
        item.product.price * item.quantity
        for item in cart_items
    )

    if request.method == "POST":

        address = request.form["address"].strip()

        if not address:
            return "Please enter your delivery address."

        for item in cart_items:
            if item.quantity > item.product.stock:
                return f"Insufficient stock for {item.product.name}"

        new_order = Order(
            user_id=session["user_id"],
            total_amount=total,
            address=address
        )

        db.session.add(new_order)
        db.session.flush()

        for item in cart_items:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.product.price
            )

            item.product.stock -= item.quantity
            db.session.add(order_item)
            db.session.delete(item)

        db.session.commit()

        return redirect(url_for("order_history"))

    return render_template(
        "checkout.html",
        cart_items=cart_items,
        total_amount=total
    )


@app.route("/order-history")
@login_required
def order_history():

    orders = Order.query.filter_by(
        user_id=session["user_id"]
    ).order_by(Order.order_date.desc()).all()

    return render_template("order_history.html", orders=orders)


@app.route("/admin")
@admin_required
def admin_dashboard():

    total_products = Product.query.count()
    total_orders = Order.query.count()
    total_users = User.query.count()

    orders = Order.query.order_by(
        Order.order_date.desc()
    ).all()

    return render_template(
        "admin_dashboard.html",
        total_products=total_products,
        total_orders=total_orders,
        total_users=total_users,
        orders=orders
    )


@app.route("/update-order/<int:order_id>", methods=["POST"])
@admin_required
def update_order(order_id):

    order = Order.query.get_or_404(order_id)

    status = request.form["status"]

    allowed_statuses = ["Pending", "Confirmed", "Shipped", "Delivered", "Cancelled"]

    if status not in allowed_statuses:
        return "Invalid order status!", 400

    order.status = status
    db.session.commit()

    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":

    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully!")
        except Exception as e:
            print("Database Error:", e)

    app.run(debug=True)
