from flask import Flask, json, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
import urllib
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<Product {self.name}>'


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(255), nullable=False)
    customer_email = db.Column(db.String(255), nullable=False)
    # Menambahkan kolom nomor telepon
    customer_phone = db.Column(db.String(20), nullable=True)
    # Menambahkan kolom alamat
    customer_address = db.Column(db.String(512), nullable=True)
    total_price = db.Column(db.Float, nullable=False)
    # Order status: pending, completed, etc.
    status = db.Column(db.String(50), default='pending')

    # To store the items in the order (can also be a separate table if more complex relationships needed)
    order_items = db.relationship('OrderItem', backref='order', lazy=True)


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey(
        'orders.id'), nullable=False)


with app.app_context():
    db.create_all()


@app.route('/e-commerce')
def index():
    page = request.args.get('page', 1, type=int)
    products = Product.query.paginate(page=page, per_page=6)
    return render_template('ecommerce/index.html', products=products)


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        # Mengambil data yang dikirim dengan form
        customer_name = request.form.get('customer_name')
        customer_email = request.form.get('customer_email')
        customer_phone = request.form.get(
            'customer_phone')  # Ambil nomor telepon
        customer_address = request.form.get('customer_address')  # Ambil alamat
        # Cart data yang diambil dari hidden field
        cart_data = request.form.get('cart_data')

        if not cart_data:
            return "Cart data missing", 400

        try:
            # Mengkonversi cart_data (string JSON) menjadi objek Python
            cart = json.loads(cart_data)
        except json.JSONDecodeError as e:
            return f"Error decoding JSON data: {e}", 400

        # Menghitung total harga
        total_price = sum(item['price'] * item['quantity'] for item in cart)

        # Menyimpan order ke dalam database
        order = Order(customer_name=customer_name,
                      customer_email=customer_email,
                      customer_phone=customer_phone,  # Menyimpan nomor telepon
                      customer_address=customer_address,  # Menyimpan alamat,
                      total_price=total_price)
        db.session.add(order)
        db.session.commit()  # Commit untuk mendapatkan ID order

        # Menyimpan order items
        for item in cart:
            order_item = OrderItem(
                product_name=item['name'],
                quantity=item['quantity'],
                price=item['price'],
                order_id=order.id  # Menghubungkan order dengan item yang baru saja disimpan
            )
            db.session.add(order_item)

        # Commit perubahan ke database
        db.session.commit()

        # Redirect ke halaman order success
        return redirect(url_for('order_success', order_id=order.id))

    # Untuk method GET, menampilkan halaman checkout
    # Cart data dari URL (misal jika Anda menginginkan URL query string)
    cart_data = request.args.get('cart_data')
    print(f"Cart data: {cart_data}", flush=True)
    if cart_data:
        decoded_cart_data = urllib.parse.unquote(cart_data)
        # Jika ada cart_data, decode dan load ke dalam cart
        cart = json.loads(decoded_cart_data)
        print(f"Cart: {cart}", flush=True)
    else:
        cart = []

    # Hitung total harga jika ada cart
    total_price = sum(item['price'] * item['quantity'] for item in cart)

    return render_template('ecommerce/checkout.html', cart=cart, total_price=total_price)


@app.route('/order-success/<int:order_id>')
def order_success(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('ecommerce/order_success.html', order=order)


@app.route('/admin')
def admin_dashboard():
    return render_template('ecommerce/admin/dashboard.html')


@app.route('/admin/orders')
def list_orders():
    orders = Order.query.all()  # Mengambil semua order
    return render_template('ecommerce/admin/list_orders.html', orders=orders)


@app.route('/admin/orders/<int:order_id>')
def order_details(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('ecommerce/admin/order_details.html', order=order)


@app.route('/admin/products')
def list_products():
    products = Product.query.all()
    return render_template('ecommerce/admin/list_products.html', products=products)


@app.route('/admin/products/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        image_url = request.form['image_url']

        product = Product(name=name, price=price, image_url=image_url)
        db.session.add(product)
        db.session.commit()

        return redirect(url_for('list_products'))

    return render_template('ecommerce/admin/add_product.html')


@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        product.name = request.form['name']
        product.price = request.form['price']
        product.image_url = request.form['image_url']

        db.session.commit()
        return redirect(url_for('list_products'))

    return render_template('ecommerce/admin/edit_product.html', product=product)


@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('list_products'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
