from flask import Blueprint, request, redirect, url_for, render_template, session, flash
from .models import db, User, Product, Booking, Review, Notification

main = Blueprint('main', __name__)

# Index Route: Dashboard
@main.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        products = Product.query.filter_by(providerID=user.userID).all()
        notifications = Notification.query.filter_by(receiverID=user.userID).all()
        return render_template('index.html', username=user.userName, listings=products, notifications=notifications)
    
    all_products = Product.query.all()
    return render_template('index.html', username=None, listings=all_products, notifications=[])

# View All Listings Route
@main.route('/listings')
def listings():
    all_products = Product.query.all()
    return render_template('listings.html', listings=all_products)

# Add Listing Route
@main.route('/add-listing', methods=['GET', 'POST'])
def add_listing():
    if 'user_id' not in session:
        flash('You need to log in to add a listing', 'warning')
        return redirect(url_for('main.login'))
    
    if request.method == 'POST':
        name = request.form['listing_name']
        description = request.form['description']
        picture = request.form['picture']
        status = request.form['status']
        available_calendar = request.form['available_calendar']
        new_product = Product(
            name=name,
            description=description,
            picture=picture,
            status=status,
            available_calendar=available_calendar,
            providerID=session['user_id']
        )
        db.session.add(new_product)
        db.session.commit()
        flash('Listing added successfully', 'success')
        return redirect(url_for('main.index'))
    return render_template('add_listing.html')

# Register Route
@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        auth_id = request.form['auth_id']
        if User.query.filter_by(userName=username).first() is None:
            new_user = User(userName=username, email=email, authID=auth_id)
            db.session.add(new_user)
            db.session.commit()
            session['user_id'] = new_user.userID
            flash('Registration successful', 'success')
            return redirect(url_for('main.index'))
        flash('Username or email already registered', 'danger')
    return render_template('register.html')

# Login Route
@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        auth_id = request.form['auth_id']
        user = User.query.filter_by(userName=username, email=email, authID=auth_id).first()
        if user:
            session['user_id'] = user.userID
            flash('Login successful', 'success')
            return redirect(url_for('main.index'))
        flash('Invalid credentials. Please try again.', 'danger')
    return render_template('login.html')

# Logout Route
@main.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return redirect(url_for('main.index'))

# Book Product Route
@main.route('/book-product/<int:product_id>', methods=['GET', 'POST'])
def book_product(product_id):
    if 'user_id' not in session:
        flash('You need to log in to book a product', 'warning')
        return redirect(url_for('main.login'))
    
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        persons_booked = int(request.form['persons_booked'])
        time = request.form['time']
        commission_fee = float(request.form['commission_fee'])
        booked_calendar = request.form['booked_calendar']
        new_booking = Booking(
            listingID=product_id,
            buyerID=session['user_id'],
            personsBooked=persons_booked,
            time=time,
            commissionfee=commission_fee,
            booked_calendar=booked_calendar
        )
        db.session.add(new_booking)
        db.session.commit()
        flash('Booking successful', 'success')
        return redirect(url_for('main.index'))
    return render_template('book_product.html', product=product)

# Add Review Route
@main.route('/add-review/<int:booking_id>', methods=['GET', 'POST'])
def add_review(booking_id):
    if 'user_id' not in session:
        flash('You need to log in to leave a review', 'warning')
        return redirect(url_for('main.login'))
    
    booking = Booking.query.get_or_404(booking_id)
    if request.method == 'POST':
        score = int(request.form['score'])
        new_review = Review(
            score=score,
            buyerID=session['user_id'],
            BookingID=booking_id
        )
        db.session.add(new_review)
        db.session.commit()
        flash('Review added successfully', 'success')
        return redirect(url_for('main.index'))
    return render_template('add_review.html', booking=booking)

# View Notifications Route
@main.route('/notifications')
def notifications():
    if 'user_id' not in session:
        flash('You need to log in to view notifications', 'warning')
        return redirect(url_for('main.login'))
    
    user_notifications = Notification.query.filter_by(receiverID=session['user_id']).all()
    return render_template('notifications.html', notifications=user_notifications)

# Success Route
@main.route('/success')
def success():
    message = request.args.get('message', 'Your action was successful!')
    return render_template('success.html', message=message)

@main.route('/current-bookings')
def current_bookings():
    if 'user_id' not in session:
        flash('You need to log in to view your bookings.', 'warning')
        return redirect(url_for('main.login'))
    
    user_bookings = Booking.query.filter_by(buyerID=session['user_id']).all()
    return render_template('current_booking.html', bookings=user_bookings)

@main.route('/home')
def home():
    return render_template('home.html')

@main.route('/reservation-success')
def reservation_success():
    return render_template('reservation_success.html')