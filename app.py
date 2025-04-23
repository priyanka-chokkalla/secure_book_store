from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
import random
import string
import os
import re
from werkzeug.security import generate_password_hash, check_password_hash  # For password hashing

app = Flask(__name__)
app.secret_key = 'srujanadeviiahdhbtxfvskzkhg'  # Our secure key

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookstore.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Email Configuration for OTP
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'd.srujana2024@gmail.com'
app.config['MAIL_PASSWORD'] = 'qeul pckw vxop amhs '
mail = Mail(app)

# Database Models   #
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)  # Use hashed passwords in production
    otp = db.Column(db.String(6))
    is_verified = db.Column(db.Boolean, default=False)

    def validate_password(self, password):
        # Password must be at least 8 characters long and only letters
        if len(password) < 8:
            return False
        if not password.isalpha():
            return False
        return True

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(500))
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    pdf_file = db.Column(db.String(200), nullable=False)  # Store the file path for the PDF

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, default=1)

# Routes            #

@app.route('/')
def home():
    products = Product.query.all()  # Fetch all products from the database
    return render_template('home.html', products=products)  # Render home.html with products

@app.route('/index')
def index():
    return render_template('index.html')  # Render index.html after successful login and OTP verification

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        print(f"Attempting to register user with email: {email}") 
        
        # Password validation
        if len(password) < 8 or not password.isalpha():
            flash("Password must be at least 8 characters long and contain only letters.", "danger")
            print("Password validation failed.") 
            return redirect(url_for('register'))
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            flash("Email already exists.", "danger")
            print("Email already exists.") 
        else:
            hashed_password = generate_password_hash(password)  # Hash the password before storing
            new_user = User(email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful. Please login.", "success")
            print("User registered successfully.") 
            return redirect(url_for('login'))
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        print(f"Attempting to login with email: {email}") 
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):  # Verify hashed password
            session['user_id'] = user.id
            otp = ''.join(random.choices(string.digits, k=6))
            user.otp = otp
            db.session.commit()
            try:
                msg = Message("Your OTP Code", sender=app.config['MAIL_USERNAME'], recipients=[user.email])
                msg.body = f"Your OTP code is: {otp}"
                mail.send(msg)
                flash("OTP sent to your email. Please verify.", "info")
                print(f"OTP sent to {user.email}") 
            except Exception as e:
                flash("Failed to send OTP email.", "danger")
                print(f"Error sending OTP: {e}") 
            return redirect(url_for('verify_otp'))
        else:
            flash("Invalid credentials.", "danger")
            print("Invalid credentials attempt.") 
    return render_template('login.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        otp_entered = request.form['otp']
        print(f"Entered OTP: {otp_entered}") 
        if user.otp == otp_entered:
            user.is_verified = True  # Mark the user as verified
            user.otp = None  # Clear OTP after verification
            db.session.commit()
            flash("OTP verified. Login successful!", "success")
            print(f"OTP verified for user {user.email}") 
            return redirect(url_for('index'))
        else:
            flash("Invalid OTP. Try again.", "danger")
            print("Invalid OTP entered.") 
    return render_template('verify_otp.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Logged out successfully.", "info")
    return render_template('logout.html')
from flask import request

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))

    quantity = int(request.form.get('quantity', 1))
    cart_item = Cart(user_id=session['user_id'], product_id=product_id, quantity=quantity)
    db.session.add(cart_item)
    db.session.commit()
    flash("Added to cart.", "success")

    # send them right back to the page they clicked “Add to Cart” on:
    return redirect(request.referrer or url_for('index'))

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        flash("Login required.", "warning")
        return redirect(url_for('login'))
    user_id = session['user_id']
    items = (
        db.session.query(Cart, Product)
        .join(Product, Cart.product_id == Product.id)
        .filter(Cart.user_id == user_id)
        .all()
    )
    total = sum(p.price * c.quantity for c, p in items)
    return render_template('cart.html', cart_items=items, total=total)

@app.route('/delete_from_cart/<int:cart_id>', methods=['POST'])
def delete_from_cart(cart_id):
    cart_item = Cart.query.get(cart_id)
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
        flash("Item removed.", "success")
    return redirect(url_for('cart'))

@app.route('/payment_success')
def payment_success():
    if 'user_id' in session:
        Cart.query.filter_by(user_id=session['user_id']).delete()
        db.session.commit()
        flash('Payment successful!', 'success')
    return redirect(url_for('home'))

@app.route('/payment_cancelled')
def payment_cancelled():
    flash('Payment cancelled.', 'info')
    return redirect(url_for('cart'))

@app.route('/pdfs/<filename>')
def serve_pdf(filename):
    # This serves the PDF from the templates/PDF directory
    return send_from_directory(os.path.join(app.root_path, 'templates/PDF'), filename)

if __name__ == '__main__':
    with app.app_context():
        # If the database doesn't exist, create it and add sample books
        if not os.path.exists('bookstore.db'):
            db.create_all()
            # Add all sample books and tutorials to the database
            sample_books = [
                Product(
                    title="Introduction to Algorithms",
                    description="A comprehensive textbook on algorithms covering a wide range of topics in computer science.",
                    price=59.99,
                    stock=10,
                    pdf_file="templates/PDF/pdf1.pdf"
                ),
                Product(
                    title="Clean Code: A Handbook of Agile Software Craftsmanship",
                    description="A guide to writing clean and maintainable code by Robert C. Martin.",
                    price=29.99,
                    stock=15,
                    pdf_file="templates/PDF/pdf2.pdf"
                ),
                Product(
                    title="The Pragmatic Programmer",
                    description="Offers practical advice on software development and coding practices.",
                    price=25.50,
                    stock=12,
                    pdf_file="templates/PDF/pdf3.pdf"
                ),
                Product(
                    title="Design Patterns: Elements of Reusable Object-Oriented Software",
                    description="A classic work describing common design patterns in software engineering.",
                    price=35.00,
                    stock=8,
                    pdf_file="templates/PDF/pdf4.pdf"
                ),
                Product(
                    title="Tutorial 1: Algorithms",
                    description="Learn the fundamentals of algorithms.",
                    price=19.99,
                    stock=10,
                    pdf_file="templates/PDF/tutorial1.pdf"
                ),
                Product(
                    title="Tutorial 2: Clean Code",
                    description="Best practices for writing clean and maintainable code.",
                    price=19.99,
                    stock=10,
                    pdf_file="templates/PDF/tutorial2.pdf"
                ),
                Product(
                    title="Tutorial 3: Design Patterns",
                    description="Understanding common design patterns in software engineering.",
                    price=19.99,
                    stock=10,
                    pdf_file="templates/PDF/tutorial3.pdf"
                ),
                Product(
                    title="Tutorial 4: Data Structures",
                    description="An introduction to common data structures.",
                    price=19.99,
                    stock=10,
                    pdf_file="templates/PDF/tutorial4.pdf"
                ),
                Product(
                    title="Tutorial 5: Software Engineering",
                    description="A guide to software engineering principles.",
                    price=19.99,
                    stock=10,
                    pdf_file="templates/PDF/tutorial5.pdf"
                ),
                Product(
                    title="Tutorial 6: Database Design",
                    description="Learn about relational databases and design patterns.",
                    price=19.99,
                    stock=10,
                    pdf_file="templates/PDF/tutorial6.pdf"
                )
            ]
            for book in sample_books:
                db.session.add(book)
            db.session.commit()

    # Add the port number (5000+)
    app.run(debug=True, port=5000)
