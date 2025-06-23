from functools import wraps
from flask import Flask, render_template, redirect, request, url_for, session, abort
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from database import Database

# app and database
db = Database()
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'strong_secret_key_123!')
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
app.config['SESSION_TYPE'] = 'filesystem'

# upload directory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("is_admin"):
            return f(*args, **kwargs)
        return redirect(url_for('adminLogin'))
    return decorated

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" in session:
            return f(*args, **kwargs)
        return redirect(url_for('login'))
    return decorated

@app.route('/')
def frontPage():
    return render_template('frontPage.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        form = request.form
        fields = [form.get(f) for f in ['first_name', 'last_name', 'username', 'email', 'password', 'phone']]
        if not all(fields):
            return render_template('signup.html', error="All fields are required")

        if db.checkIfCustomerAlreadyExist(fields[3]):
            return render_template('signup.html', flag=True)

        user_id = db.insertIntoCustomer(*fields)
        if user_id:
            session.update({'user_id': user_id, 'user_email': fields[3], 'is_admin': False})
            return redirect(url_for('home'))

        return render_template('signup.html', error="Registration failed")
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, password = request.form.get('email'), request.form.get('password')
        role = request.form.get('role', 'customer')

        if role == 'admin':
            admin = db.getAdminByEmail(email)
            if admin and check_password_hash(admin[2], password):
                session.update({'is_admin': True, 'admin_id': admin[0]})
                return redirect(url_for('admin'))
            return render_template('login.html', flag=True, role='admin')

        customer = db.returnCustomerAccordingToEmail(email)
        if customer and check_password_hash(customer[5], password):
            session.update({'user_id': customer[0], 'user_email': email, 'is_admin': False})
            return redirect(url_for('home'))
        return render_template('login.html', flag=True)

    return render_template('login.html')

@app.route('/logout')
def userLogout():
    session.clear()
    return redirect(url_for('frontPage'))

@app.route('/home')
@login_required
def home():
    return render_template('home.html')

@app.route('/menu')
@login_required
def menu():
    foods = db.returnFoods()
    ratings = db.returnAllReviewsRatesAndFood_nos()
    orders = db.getCustomerOrders(session['user_id']) 
    has_ready_orders = any(order[8] == "Ready" for order in orders) 

    return render_template("menu.html", foods=foods, foodnosAndRates=ratings, has_ready_orders=has_ready_orders)

@app.route('/account')
@login_required
def account():
    customer = db.getCustomerById(session['user_id'])
    if not customer:
        return redirect(url_for('logout'))

    prefs = db.getCustomerPreferences(session['user_id'])
    preferences = {
        'favorite_cuisine': prefs[2] if prefs else 'Not set',
        'dietary_needs': prefs[3] if prefs else 'Not set',
        'delivery_address': prefs[4] if prefs else 'Not set',
        'payment_method': prefs[5] if prefs else 'Not set',
    }

    return render_template('accounts.html', customer=customer, preferences=preferences,
                           order_count=db.getCustomerOrderCount(session['user_id']),
                           avg_rating=db.getCustomerAverageRating(session['user_id']),
                           active_orders=db.getCustomerActiveOrders(session['user_id']))

@app.route('/update_preferences', methods=['POST'])
@login_required
def update_preferences():
    try:
        db.updateCustomerPreferences(
            session['user_id'],
            request.form.get('favorite_cuisine'),
            request.form.get('dietary_needs'),
            request.form.get('delivery_address'),
            request.form.get('payment_method')
        )
        return redirect(url_for('account'))
    except Exception as e:
        return redirect(url_for('account', error=str(e)))

@app.route('/menu/<filter>')
@login_required
def filter_menu(filter):
    if filter == 'filterByPrice':
        foods = db.FoodsFilterBy("food_price")
    elif filter == 'filterByRating':
        foods = db.FoodsFilterByOrderRatings()
    else:
        return redirect(url_for('menu'))

    ratings = db.returnAllReviewsRatesAndFood_nos()
    return render_template('menu.html', foods=foods, foodnosAndRates=ratings)

@app.route('/menu/<int:food_id>', methods=['GET', 'POST'])
@login_required
def product(food_id):
    if not db.foodIdExists(food_id):
        abort(404)

    food = db.returnFoodById(food_id)
    reviews = db.returnReviewsOfFood_noWithJoins(food_id)
    all_reviews = db.returnAllReviewsOfFood_noWithJoins(food_id)

    if request.method == 'POST':
        quantity = int(request.form.get('quantity', 0))
        pay_number = request.form.get('pay_number', '')
        pay_amount = float(request.form.get('pay_amount', 0))

        if quantity <= 0:
            return render_template("customerproduct.html", food=food, reviewsAndCount=reviews, allRevs=all_reviews, error="Invalid quantity")

        if db.createOrder(pay_number, session['user_id'], food_id, quantity, pay_amount):
            success = "Order placed successfully!"
            return render_template("customerproduct.html", food=food, reviewsAndCount=reviews, allRevs=all_reviews, success=success)

        return render_template("customerproduct.html", food=food, reviewsAndCount=reviews, allRevs=all_reviews, error="Order failed")

    return render_template("customerproduct.html", food=food, reviewsAndCount=reviews, allRevs=all_reviews)

@app.route('/menu/customer_orders')
@login_required
def orderDetails():
    orders = db.getCustomerOrders(session['user_id'])

    # Check if any order is marked "Ready"
    has_ready_orders = any(order[8] == "Ready" for order in orders)

    return render_template('orders.html', orderDetails=orders, has_ready_orders=has_ready_orders)

@app.route('/review/<int:order_id>', methods=['GET', 'POST'])
@login_required
def Review(order_id):
    if not db.userOwnsOrder(session['user_id'], order_id):
        abort(403)

    if request.method == 'POST':
        rate = int(request.form.get('review_rate', 0))
        desc = request.form.get('review_desc', '')

        if 1 <= rate <= 5:
            if db.createReview(rate, desc, order_id):
                return redirect(url_for('orderDetails'))
        return render_template('pages.html', order_id=order_id, error="Review failed")

    return render_template('pages.html', order_id=order_id)

@app.route('/admin/login', methods=['GET', 'POST'])
def adminLogin():
    if request.method == 'POST':
        email, password = request.form.get('email'), request.form.get('password')
        admin = db.getAdminByEmail(email)
        if admin and check_password_hash(admin[2], password):
            session.update({'is_admin': True, 'admin_id': admin[0]})
            return redirect(url_for('admin'))
        return render_template("login.html", flag=True, role='admin')
    return render_template("login.html", role='admin')

@app.route('/admin/logout')
@admin_required
def adminLogout():
    session.pop('is_admin', None)
    session.pop('admin_id', None)
    return redirect(url_for('frontPage'))

@app.route('/admin/home')
@admin_required
def admin():
    foods = db.returnFoods()
    ratings = db.returnAllReviewsRatesAndFood_nos()
    return render_template('admin.html', foods=foods, foodnosAndRates=ratings)

@app.route('/addfood', methods=['GET', 'POST'])
@admin_required
def addFood():
    if request.method == 'POST':
        title, price, desc = request.form.get('foodTitle'), request.form.get('foodPrice'), request.form.get('food_desc')
        imageFile = request.files.get('imageFile')

        if not all([title, price, desc]):
            return render_template('addfoods.html', error="All fields required")

        try:
            price = float(price)
        except ValueError:
            return render_template('addfoods.html', error="Invalid price")

        if imageFile and allowed_file(imageFile.filename):
            filename = secure_filename(imageFile.filename)
            imageFile.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            return render_template('addfoods.html', error="Invalid file type")

        if db.InsertIntoFood(filename, price, title, desc, 1):
            return redirect(url_for('admin'))
        return render_template('addfoods.html', error="Failed to add food")

    return render_template('addfoods.html')

@app.route('/delete/<int:id>')
@admin_required
def delFood(id):
    if db.foodIdExists(id):
        db.deleteFood(id)
    return redirect(url_for('admin'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def editFood(id):
    if not db.foodIdExists(id):
        abort(404)

    food = db.returnFoodById(id)

    if request.method == 'POST':
        filename = food[1]
        new_file = request.files.get('imageFile')
        if new_file and new_file.filename:
            if allowed_file(new_file.filename):
                filename = secure_filename(new_file.filename)
                new_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            else:
                return render_template('addfoods.html', food=food, error="Invalid file type")

        if db.updateFood(id, request.form.get('foodTitle'), request.form.get('foodPrice'), request.form.get('food_desc'), filename):
            return redirect(url_for('admin'))
        return render_template('addfoods.html', food=food, error="Update failed")

    return render_template('addfoods.html', food=food)

@app.route('/deleteAll')
@admin_required
def deleteAll():
    db.cursor.execute("DELETE FROM Food")
    db.conn.commit()
    return redirect(url_for('admin'))

@app.route('/allCustomers')
@admin_required
def allCustomers():
    return render_template('pages.html', customers=db.returnCustomers())

@app.route('/delCustomer/<int:id>')
@admin_required
def delCustomer(id):
    if db.customerIdExists(id):
        db.deleteCustomer(id)
    return redirect(url_for('allCustomers'))

@app.route('/allcustomer_orders')
@admin_required
def allOrders():
    return render_template('pages.html', orderDetails=db.returnAllOrderDetailsOfCustomerWithJoins())

@app.route('/update_orderMarked/<int:or_id>')
@admin_required
def markAsDone(or_id):
    db.updateOrderStatusToDelivered(or_id)
    session.pop("popup_shown", None)
    return redirect(url_for('adminReceived'))

@app.route('/admin/received')
@admin_required
def adminReceived():
    orders = db.returnAllOrderDetailsOfCustomerWithJoins()
    return render_template('adminreceived.html', orderDetails=orders)

@app.route('/remove_order/<int:or_id>')
@admin_required
def removeOrder(or_id):
    db.deleteOrderWithOrderId(or_id)
    return redirect(url_for('allOrders'))

@app.route('/menufor_review')
@admin_required
def reviewMenu():
    return render_template('pages.html', foods=db.returnFoods())

@app.route('/allreviews/<int:food_no>')
@admin_required
def allReviews(food_no):
    allreviews = db.returnAllReviewsOfFood_noWithJoins(food_no)
    reviewsAndCount = db.returnReviewsOfFood_noWithJoins(food_no)
    return render_template('pages.html', allreviews=allreviews, reviewsAndCount=reviewsAndCount)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
