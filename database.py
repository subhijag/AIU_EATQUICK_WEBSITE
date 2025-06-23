import sqlite3 as sql
from werkzeug.security import generate_password_hash, check_password_hash

class Database:
    def __init__(self):
        self.conn = sql.connect("foodSystem.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.setup_tables()

    def setup_tables(self):
        self.CreateTableAdmin()
        self.CreateTableCustomer()
        self.CreateTablePayment()
        self.CreateTableFood()
        self.CreateTableORDERED()
        self.CreateTableReviews()
        self.CreateTablePreferences()
        self.create_admin_user()

    def create_admin_user(self):
        self.cursor.execute("SELECT COUNT(*) FROM Admin")
        if self.cursor.fetchone()[0] == 0:
            try:
                hashed_password = generate_password_hash('admin123')
                self.cursor.execute(
                    "INSERT INTO Admin (admin_id, admin_email, admin_password) VALUES (?, ?, ?)",
                    (1, "admin@gmail.com", hashed_password)
                )
                self.conn.commit()
            except sql.Error:
                self.conn.rollback()

    def CreateTableAdmin(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS Admin(
            admin_id       INTEGER PRIMARY KEY,
            admin_email    VARCHAR(30) UNIQUE,
            admin_password VARCHAR(100)
        )''')
        self.conn.commit()

    def CreateTableCustomer(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS Customers(
            customer_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name     VARCHAR(30),
            last_name      VARCHAR(30),
            user_name      VARCHAR(30),
            email          VARCHAR(50) UNIQUE,
            password       VARCHAR(100),
            phone_no       VARCHAR(25),
            admin_id       INTEGER DEFAULT 1,
            FOREIGN KEY (admin_id) REFERENCES Admin(admin_id)
        )''')
        self.conn.commit()

    def CreateTablePayment(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS Payment(
            pay_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            pay_number VARCHAR(30),
            pay_amount FLOAT,
            customer_id INTEGER,
            FOREIGN KEY (customer_id) REFERENCES Customers(customer_id)
        )''')
        self.conn.commit()

    def CreateTableFood(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS Food(
            food_no      INTEGER PRIMARY KEY AUTOINCREMENT,
            food_image   VARCHAR(100),
            food_price   FLOAT,
            food_title   VARCHAR(30),
            food_desc    TEXT,
            availability INTEGER DEFAULT 1
        )''')
        self.conn.commit()

    def CreateTableORDERED(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS ORDERED(
            order_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            food_no       INTEGER,
            quantity      INTEGER,
            pay_amount    FLOAT,
            ordered_date  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            pay_id        INTEGER,
            customer_id   INTEGER,
            order_status  VARCHAR(20) DEFAULT 'Pending',
            FOREIGN KEY (food_no) REFERENCES Food(food_no),
            FOREIGN KEY (pay_id) REFERENCES Payment(pay_id),
            FOREIGN KEY (customer_id) REFERENCES Customers(customer_id)
        )''')
        self.conn.commit()

    def CreateTableReviews(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS Reviews(
            review_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            review_rate INTEGER,
            review_desc TEXT,
            order_id    INTEGER UNIQUE,
            FOREIGN KEY (order_id) REFERENCES ORDERED(order_id)
        )''')
        self.conn.commit()

    def CreateTablePreferences(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS Preferences(
            preference_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id      INTEGER UNIQUE,
            favorite_cuisine VARCHAR(30),
            dietary_needs    TEXT,
            delivery_address TEXT,
            payment_method   VARCHAR(50),
            FOREIGN KEY (customer_id) REFERENCES Customers(customer_id)
        )''')
        self.conn.commit()

    def insertIntoCustomer(self, first_name, last_name, username, email, password, phone):
        try:
            hashed_password = generate_password_hash(password)
            self.cursor.execute('''
            INSERT INTO Customers (first_name, last_name, user_name, email, password, phone_no)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (first_name, last_name, username, email, hashed_password, phone))
            self.conn.commit()
            return self.cursor.lastrowid
        except sql.Error:
            return None

    def checkIfCustomerAlreadyExist(self, email):
        self.cursor.execute("SELECT * FROM Customers WHERE email = ? COLLATE NOCASE", (email,))
        return self.cursor.fetchone() is not None

    def returnCustomerAccordingToEmail(self, email):
        self.cursor.execute("SELECT * FROM Customers WHERE email = ? COLLATE NOCASE", (email,))
        return self.cursor.fetchone()

    def getCustomerById(self, customer_id):
        self.cursor.execute("SELECT * FROM Customers WHERE customer_id = ?", (customer_id,))
        return self.cursor.fetchone()

    def updateCustomerPreferences(self, customer_id, favorite_cuisine, dietary_needs, delivery_address, payment_method):
        try:
            self.cursor.execute("SELECT * FROM Preferences WHERE customer_id = ?", (customer_id,))
            if self.cursor.fetchone():
                self.cursor.execute('''
                UPDATE Preferences 
                SET favorite_cuisine = ?, dietary_needs = ?, delivery_address = ?, payment_method = ?
                WHERE customer_id = ?
                ''', (favorite_cuisine, dietary_needs, delivery_address, payment_method, customer_id))
            else:
                self.cursor.execute('''
                INSERT INTO Preferences (customer_id, favorite_cuisine, dietary_needs, delivery_address, payment_method)
                VALUES (?, ?, ?, ?, ?)
                ''', (customer_id, favorite_cuisine, dietary_needs, delivery_address, payment_method))
            self.conn.commit()
            return True
        except sql.Error:
            self.conn.rollback()
            return False

    def getCustomerPreferences(self, customer_id):
        self.cursor.execute("SELECT * FROM Preferences WHERE customer_id = ?", (customer_id,))
        return self.cursor.fetchone()

    def getCustomerOrderCount(self, customer_id):
        self.cursor.execute("SELECT COUNT(*) FROM ORDERED WHERE customer_id = ?", (customer_id,))
        return self.cursor.fetchone()[0] or 0

    def getCustomerAverageRating(self, customer_id):
        self.cursor.execute('''
        SELECT AVG(Reviews.review_rate)
        FROM Reviews
        JOIN ORDERED ON Reviews.order_id = ORDERED.order_id
        WHERE ORDERED.customer_id = ?
        ''', (customer_id,))
        result = self.cursor.fetchone()[0]
        return round(result, 1) if result else 0.0

    def getCustomerActiveOrders(self, customer_id):
        self.cursor.execute("SELECT COUNT(*) FROM ORDERED WHERE customer_id = ? AND order_status = 'Pending'", (customer_id,))
        return self.cursor.fetchone()[0] or 0

    def getAdminByEmail(self, email):
        self.cursor.execute("SELECT * FROM Admin WHERE admin_email = ? COLLATE NOCASE", (email,))
        return self.cursor.fetchone()

    def InsertIntoFood(self, image, price, title, desc, availability=1):
        try:
            self.cursor.execute('''
            INSERT INTO Food (food_image, food_price, food_title, food_desc, availability)
            VALUES (?, ?, ?, ?, ?)
            ''', (image, price, title, desc, availability))
            self.conn.commit()
            return True
        except sql.Error:
            self.conn.rollback()
            return False

    def returnFoods(self):
        self.cursor.execute("SELECT * FROM Food")
        return self.cursor.fetchall()

    def foodIdExists(self, food_id):
        self.cursor.execute("SELECT COUNT(*) FROM Food WHERE food_no = ?", (food_id,))
        return self.cursor.fetchone()[0] > 0

    def returnFoodById(self, food_id):
        self.cursor.execute("SELECT * FROM Food WHERE food_no = ?", (food_id,))
        return self.cursor.fetchone()

    def updateFood(self, food_id, title, price, desc, image):
        try:
            self.cursor.execute('''
            UPDATE Food 
            SET food_title = ?, food_price = ?, food_desc = ?, food_image = ?
            WHERE food_no = ?
            ''', (title, price, desc, image, food_id))
            self.conn.commit()
            return True
        except sql.Error:
            self.conn.rollback()
            return False

    def deleteFood(self, food_id):
        try:
            self.cursor.execute("DELETE FROM Food WHERE food_no = ?", (food_id,))
            self.conn.commit()
            return True
        except sql.Error:
            self.conn.rollback()
            return False

    def createOrder(self, pay_number, customer_id, food_id, quantity, pay_amount):
        try:
            self.cursor.execute('''
            INSERT INTO Payment (pay_number, pay_amount, customer_id)
            VALUES (?, ?, ?)
            ''', (pay_number, pay_amount, customer_id))
            pay_id = self.cursor.lastrowid

            self.cursor.execute('''
            INSERT INTO ORDERED (food_no, quantity, pay_amount, pay_id, customer_id)
            VALUES (?, ?, ?, ?, ?)
            ''', (food_id, quantity, pay_amount, pay_id, customer_id))
            self.conn.commit()
            return True
        except sql.Error:
            self.conn.rollback()
            return False

    def getCustomerOrders(self, customer_id):
        self.cursor.execute('''
        SELECT ORDERED.order_id, Food.food_title, Food.food_price, Food.food_image, 
               ORDERED.ordered_date, ORDERED.quantity, ORDERED.pay_amount, 
               Payment.pay_number, ORDERED.order_status
        FROM ORDERED
        JOIN Food ON ORDERED.food_no = Food.food_no
        JOIN Payment ON ORDERED.pay_id = Payment.pay_id
        WHERE ORDERED.customer_id = ?
        ORDER BY ORDERED.order_id DESC
        ''', (customer_id,))
        return self.cursor.fetchall()

    def userOwnsOrder(self, user_id, order_id):
        self.cursor.execute('''
        SELECT COUNT(*) 
        FROM ORDERED 
        WHERE order_id = ? AND customer_id = ?
        ''', (order_id, user_id))
        return self.cursor.fetchone()[0] > 0

    def createReview(self, rate, desc, order_id):
        try:
            self.cursor.execute('''
            INSERT INTO Reviews (review_rate, review_desc, order_id)
            VALUES (?, ?, ?)
            ''', (rate, desc, order_id))
            self.conn.commit()
            return True
        except sql.Error:
            self.conn.rollback()
            return False

    def returnCustomers(self):
        self.cursor.execute("SELECT * FROM Customers")
        return self.cursor.fetchall()

    def customerIdExists(self, customer_id):
        self.cursor.execute("SELECT COUNT(*) FROM Customers WHERE customer_id = ?", (customer_id,))
        return self.cursor.fetchone()[0] > 0

    def deleteCustomer(self, customer_id):
        try:
            self.cursor.execute("DELETE FROM Customers WHERE customer_id = ?", (customer_id,))
            self.conn.commit()
            return True
        except sql.Error:
            self.conn.rollback()
            return False

    def returnAllOrderDetailsOfCustomerWithJoins(self):
        self.cursor.execute('''
        SELECT ORDERED.order_id, Customers.first_name, Customers.last_name, 
               Food.food_title, ORDERED.quantity, ORDERED.pay_amount, 
               ORDERED.ordered_date, ORDERED.order_status
        FROM ORDERED
        JOIN Customers ON ORDERED.customer_id = Customers.customer_id
        JOIN Food ON ORDERED.food_no = Food.food_no
        ORDER BY ORDERED.order_id DESC
        ''')
        return self.cursor.fetchall()

    def updateOrderStatusToDelivered(self, order_id):
        try:
            self.cursor.execute('''
            UPDATE ORDERED SET order_status = 'Delivered' WHERE order_id = ?
            ''', (order_id,))
            self.conn.commit()
            return True
        except sql.Error:
            self.conn.rollback()
            return False

    def deleteOrderWithOrderId(self, order_id):
        try:
            self.cursor.execute("DELETE FROM ORDERED WHERE order_id = ?", (order_id,))
            self.conn.commit()
            return True
        except sql.Error:
            self.conn.rollback()
            return False

    def returnAllReviewsOfFood_noWithJoins(self, food_no):
        self.cursor.execute('''
        SELECT Reviews.review_rate, Reviews.review_desc, Customers.first_name, Customers.last_name
        FROM Reviews
        JOIN ORDERED ON Reviews.order_id = ORDERED.order_id
        JOIN Customers ON ORDERED.customer_id = Customers.customer_id
        WHERE ORDERED.food_no = ?
        ''', (food_no,))
        return self.cursor.fetchall()

    def returnReviewsOfFood_noWithJoins(self, food_no):
        self.cursor.execute('''
        SELECT AVG(Reviews.review_rate), COUNT(Reviews.review_id)
        FROM Reviews
        JOIN ORDERED ON Reviews.order_id = ORDERED.order_id
        WHERE ORDERED.food_no = ?
        ''', (food_no,))
        return self.cursor.fetchone()

    def returnAllReviewsRatesAndFood_nos(self):
        self.cursor.execute('''
        SELECT ORDERED.food_no, AVG(Reviews.review_rate)
        FROM Reviews
        JOIN ORDERED ON Reviews.order_id = ORDERED.order_id
        GROUP BY ORDERED.food_no
        ''')
        return self.cursor.fetchall()

    def FoodsFilterBy(self, column):
        self.cursor.execute(f"SELECT * FROM Food ORDER BY {column}")
        return self.cursor.fetchall()

    def FoodsFilterByOrderRatings(self):
        self.cursor.execute('''
        SELECT Food.* 
        FROM Food
        LEFT JOIN (
            SELECT ORDERED.food_no, AVG(Reviews.review_rate) as avg_rating
            FROM Reviews
            JOIN ORDERED ON Reviews.order_id = ORDERED.order_id
            GROUP BY ORDERED.food_no
        ) AS FoodRatings ON Food.food_no = FoodRatings.food_no
        ORDER BY FoodRatings.avg_rating DESC
        ''')
        return self.cursor.fetchall()

    def __del__(self):
        self.conn.close()

db = Database()
