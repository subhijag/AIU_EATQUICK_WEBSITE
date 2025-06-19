from flask import Flask, render_template, redirect, request, url_for, session, abort
import os
from werkzeug.utils import secure_filename
from database import Database
db = Database()


def checkAppropriateFile(file):
    ALLOWED_EXTENSIONS = ['png', 'jpg', 'jpeg']
    for f in ALLOWED_EXTENSIONS:
        if file.endswith(f):
            return True
    return False


# db.CreateTableAdmin()
# db.insertIntoAdmin(1, 'admin@gmail.com', 'aiu1234')
# db.CreateTablePayment()
# db.CreateTableCustomer()
# db.CreateTableFood()
# db.CreateTableORDERED()
# db.CreateTableReviews()


app = Flask(__name__)
app.secret_key = 'aiu123'

@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if "Useremail" and "Userpassword" not in session:
        if request.method == 'POST':
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            username = request.form['username']
            Useremail = request.form['Useremail']
            Userpassword = request.form['Userpassword']
            phone = request.form['phone']
            address = request.form['address']

            session['first_name'] = first_name
            session['last_name'] = last_name
            session['username'] = username
            session['Useremail'] = Useremail
            session['Userpassword'] = Userpassword
            session['phone'] = phone
            session['address'] = address

            check = db.checkIfCustomerAlreadyExistForSignUp(Useremail, Userpassword)
            if not check:
                db.insertIntoCustomer(
                    first_name, last_name, username, Useremail, Userpassword, phone, address)
                return redirect(url_for('home'))
            else:
                session.pop('Useremail', None)
                session.pop('Userpassword', None)
                return render_template('loginsss.html', flag=True)
        else:
            return render_template('loginsss.html')
    return redirect(url_for('home'))


@app.route('/login', methods=['POST', 'GET'])
def login():
    if "Useremail" and "Userpassword" not in session:
        if request.method == 'POST':
            Useremail = request.form['Useremail']
            Userpassword = request.form['Userpassword']
            session["Useremail"] = Useremail
            session["Userpassword"] = Userpassword
            # we can not pass values withouot confirming that user is in the session so
            # return render_template("admin.html", email=email, password=password)
            check = db.checkIfCustomerAlreadyExistForLogin(Useremail, Userpassword)
            if (check == True):
                return redirect(url_for('home'))
            else:
                session.pop("Useremail", None)
                session.pop("Userpassword", None)
                return render_template("loginsss.html", flag=True)
        else:
            return render_template("loginsss.html")
    else:
        return redirect(url_for('home'))


@app.route('/')
def frontPage():
    return render_template('frontPage.html')


@app.route('/home')
def home():
    if "Useremail" and "Userpassword" in session:
        return render_template('home.html')
    return redirect(url_for('login'))


@app.route('/menu')
def menu():
    if "Useremail" and "Userpassword" in session:
        foods = db.returnFoods()
        foods = foods.fetchall()

        foodnosAndRates = db.returnAllReviewsRatesAndFood_nos()
        foodnosAndRates = foodnosAndRates.fetchall()

        return render_template("menu.html", foods=foods, foodnosAndRates=foodnosAndRates)
    return redirect(url_for('login'))


@app.route('/account')
def account():
    if "Useremail" and "Userpassword" in session:
        useremail = session["Useremail"]
        userpassword = session["Userpassword"]
        customer = db.returnCustomerAccordingToSession(useremail, userpassword)
        customer = customer.fetchone()
        return render_template('accounts.html', customer=customer)
    return redirect(url_for('login'))


@app.route('/menu/<filter>')
def filter(filter):
    if "Useremail" and "Userpassword" in session:
        if filter == 'filterByPrice':
            foods = db.FoodsFilterBy("food_price")
            foods = foods.fetchall()
            foodnosAndRates = db.returnAllReviewsRatesAndFood_nos()
            foodnosAndRates = foodnosAndRates.fetchall()        
            return render_template('menu.html', foods=foods, foodnosAndRates=foodnosAndRates)

        elif filter == 'filterByRating':
            foods = db.FoodsFilterByOrderRatings()
            foods = foods.fetchall()
            foodnosAndRates = db.returnAllReviewsRatesAndFood_nos()
            foodnosAndRates = foodnosAndRates.fetchall()
            return render_template('menu.html', foods=foods, foodnosAndRates=foodnosAndRates)
        return redirect(url_for('menu'))
    return redirect(url_for('login'))

@app.route('/update_orderMarked/<int:or_id>')
def markAsDone(or_id):
    if "email" and "password" in session:
        db.updateOrderStatusToDelivered(or_id)
        return redirect(url_for('allOrders'))
    return redirect(url_for('adminLogin'))

@app.route('/remove_order/<int:or_id>')
def removeOrder(or_id):
    if "email" and "password" in session:
        db.deleteOrderWithOrderId(or_id)
        return redirect(url_for('allOrders'))
    return redirect(url_for('adminLogin'))

@app.route('/menu/customer_orders')
def orderDetails(flag=None):
    if "Useremail" and "Userpassword" in session:
        useremail = session["Useremail"]
        userpassword = session["Userpassword"]
        customer = db.returnCustomerAccordingToSession(useremail, userpassword)
        customer = customer.fetchone()
        customerId = customer[0]
        orderDetails = db.returnOrderDetailsOfCustomerWithJoins(customerId)
        orderDetails = orderDetails.fetchall()
        getFlag = flag
        return render_template('adminreceived.html', orderDetails=orderDetails, getFlag=getFlag)
    return redirect(url_for('login'))

@app.route('/allcustomer_orders')
def allOrders():
    if "email" and "password" in session:
        orderDetails = db.returnAllOrderDetailsOfCustomerWithJoins()
        orderDetails = orderDetails.fetchall()
        return render_template('pages.html', orderDetails=orderDetails)
    return redirect(url_for('adminLogin'))

@app.route('/menu/<int:food_id>', methods=['POST', 'GET'])
def product(food_id):
    if "Useremail" and "Userpassword" in session:
        if request.method == 'POST':
            quantity = request.form['quantity']
            pay_number = request.form['pay_number']
            pay_amount = request.form['pay_amount']
            useremail = session["Useremail"]
            userpassword = session["Userpassword"]
            customer = db.returnCustomerAccordingToSession(useremail, userpassword)
            customer = customer.fetchone()
            customerId = customer[0]

            already, pay_id = db.insertIntoPaymentThenOrders(pay_number,customerId, food_id, quantity, pay_amount)

            if already == None:
                return redirect(url_for('orderDetails', flag=False))
            elif already[0] == 'addfoods' and pay_id == None:
                return render_template('addfoods.html')
            # we can cancel order here so we have to delete those things
            #db.updateCustomerWithPayId(customerId, payId)
        else:
            if db.foodIdExists(food_id):
                food = db.returnFoodById(food_id)
                food = food.fetchone()
                reviewsAndCount = db.returnReviewsOfFood_noWithJoins(food_id)
                reviewsAndCount = reviewsAndCount.fetchone()

                allRevs = db.returnAllReviewsOfFood_noWithJoins(food_id).fetchall()
                return render_template("pages.html", food=food, reviewsAndCount=reviewsAndCount, allRevs=allRevs)
            else:
                abort(404)
    return redirect(url_for('login'))

@app.route('/admin/login', methods=['POST', 'GET'])
def adminLogin():
    if "email" and "password" not in session:
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            session["email"] = email
            session["password"] = password
            # we can not pass values withouot confirming that user is in the session so
            # return render_template("admin.html", email=email, password=password)
            check = db.checkInAdmin(email, password)
            if (check == True):
                return redirect(url_for('admin'))
            else:
                session.pop("email", None)
                session.pop("password", None)
                return render_template("loginsss.html", flag=True)
        else:
            return render_template("loginsss.html")
    else:
        return redirect(url_for('admin'))


@app.route('/admin/home')
def admin():
    if "email" and "password" in session:
        foods = db.returnFoods()
        foods = foods.fetchall()
        foodnosAndRates = db.returnAllReviewsRatesAndFood_nos()
        foodnosAndRates = foodnosAndRates.fetchall()
        return render_template('admin.html', foods=foods, foodnosAndRates=foodnosAndRates)
    return redirect(url_for('adminLogin'))


@app.route('/addfood', methods=['POST', 'GET'])
def addFood():
    if "email" and "password" in session:
        if request.method == 'POST':
            foodTitle = request.form['foodTitle']
            foodPrice = request.form['foodPrice']
            foodDesc = request.form['food_desc']
            imageFile = request.files['imageFile']

            if imageFile.filename == '':
                return redirect(request.url)
            if imageFile and checkAppropriateFile(imageFile.filename):
                Securefilename = secure_filename(imageFile.filename)
                imageFile.save(os.path.join(
                    app.config['UPLOAD_FOLDER'], Securefilename))
                db.InsertIntoFood(Securefilename,
                                  foodPrice, foodTitle, foodDesc, 1)
            return redirect(url_for('admin'))
        else:
            return render_template('addfoods.html')
    return redirect(url_for("adminLogin"))


@app.route('/delete/<int:id>')
def delFood(id):
    if "email" and "password" in session:
        if db.foodIdExists(id):
            db.deleteFood(id)
            return redirect(url_for('admin'))
        else:
            abort(404)
    return redirect(url_for("adminLogin"))

@app.route('/edit/<int:id>', methods=['POST', 'GET'])
def editFood(id):
    if "email" and "password" in session:
        if db.foodIdExists(id):
            if request.method == 'POST':
                foodTitle = request.form['foodTitle']
                foodPrice = request.form['foodPrice']
                foodDesc = request.form['food_desc']
                imageFile = request.files['imageFile']
                if imageFile.filename == '':
                    return redirect(request.url)
                if imageFile and checkAppropriateFile(imageFile.filename):
                    Securefilename = secure_filename(imageFile.filename)
                    imageFile.save(os.path.join(
                        app.config['UPLOAD_FOLDER'], Securefilename))
                db.updateFood(id, foodTitle, foodPrice, foodDesc, Securefilename)
                return redirect(url_for('admin'))

            food = db.returnFoodById(id)
            food = food.fetchone()
            return render_template('addfoods.html', food=food)
        else:
            abort(404)
    return redirect(url_for("adminLogin"))

@app.route('/deleteall')
def deleteAll():
    if "email" and "password" in session:
        db.deleteAllFoods()
        return redirect(url_for('admin'))
    return redirect(url_for("adminLogin"))

@app.route('/allCustomers')
def allCustomers():
    if "email" and "password" in session:
        customers = db.returnCustomers()
        customers = customers.fetchall()
        return render_template('pages.html', customers=customers)
    return redirect(url_for("adminLogin"))


@app.route('/delCustomer/<int:id>')
def delCustomer(id):
    if "email" and "password" in session:
        if db.customerIdExists(id):
            db.deleteCustomer(id)
            return redirect(url_for('allCustomers'))
        else:
            abort(404)
    return redirect(url_for("adminLogin"))

@app.route('/review/<int:order_id>', methods=['POST', 'GET'])
def Review(order_id):
    if "Useremail" and "Userpassword" in session:
        if db.OrderIdExists(order_id):
            if request.method == 'POST':
                review_rate = request.form['review_rate']
                review_desc = request.form['review_desc']

                uflag = db.InsertIntoReviews(review_rate, review_desc, order_id)
                if(uflag==True):
                    return redirect(url_for('orderDetails'))
                else:
                    return render_template('pages.html', order_id = order_id, flag= True)
            else:
                return render_template('pages.html', order_id = order_id)
        else:
            abort(404)
    return redirect(url_for("login"))

@app.route('/menufor_review')
def reviewMenu():
    if "email" and "password" in session:
        foods = db.returnFoods()
        foods = foods.fetchall()
        return render_template('pages.html', foods=foods)
    return redirect(url_for("adminLogin"))

@app.route('/allreviews/<int:food_no>')
def allReviews(food_no):
    if "email" and "password" in session:
        allreviews = db.returnAllReviewsOfFood_noWithJoins(food_no)
        allreviews = allreviews.fetchall()
        reviewsAndCount = db.returnReviewsOfFood_noWithJoins(food_no)
        reviewsAndCount = reviewsAndCount.fetchone()
        return render_template('pages.html', allreviews=allreviews, reviewsAndCount=reviewsAndCount)
    return redirect(url_for("adminLogin"))

@app.route('/logout')
def userLogout():
    if "Useremail" and "Userpassword" in session:
        session.pop('Useremail', None)
        session.pop('Userpassword', None)
        return redirect(url_for('login'))
    return redirect(url_for("login"))

@app.route('/admin/logout')
def adminLogout():
    if "email" and "password" in session:
        session.pop('email', None)
        session.pop('password', None)
        return redirect(url_for('adminLogin'))
    return redirect(url_for("adminLogin"))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


if __name__ == "__main__":
    app.run(debug=False)
