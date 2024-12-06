from flask import Blueprint, request, redirect, url_for, render_template, session, flash, send_file
from datetime import datetime, timedelta
from .models import db, User, Product, Booking, Review, Notification
from .utils import generate_timeslots, create_ical


# Blueprint aanmaken
main = Blueprint('main', __name__)

# Hulpfuncties
def generate_timeslots(start_time, end_time, slot_duration):
    current_time = start_time
    slots = []
    while current_time < end_time:
        slot_start = current_time
        slot_end = current_time + slot_duration
        slots.append((slot_start, slot_end))
        current_time = slot_end
    return slots

def create_ical(timeslots, filename="timeslots.ics"):
    with open(filename, "w") as file:
        file.write("BEGIN:VCALENDAR\nVERSION:2.0\n")
        for i, (start, end) in enumerate(timeslots):
            file.write("BEGIN:VEVENT\n")
            file.write(f"UID:{i}@example.com\n")
            file.write(f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}\n")
            file.write(f"DTSTART:{start.strftime('%Y%m%dT%H%M%SZ')}\n")
            file.write(f"DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}\n")
            file.write(f"SUMMARY:Time Slot {i + 1}\n")
            file.write(f"DESCRIPTION:Time slot from {start} to {end}\n")
            file.write("END:VEVENT\n")
        file.write("END:VCALENDAR\n")

# Homepage Route
@main.route('/')
def home():
    return render_template('home.html')

# Dashboard Route
@main.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        products = Product.query.filter_by(providerID=user.userID).all()
        notifications = Notification.query.filter_by(receiverID=user.userID).all()
        return render_template('index.html', username=user.userName, listings=products, notifications=notifications)
    
    flash('You need to log in to view the dashboard.', 'warning')
    return redirect(url_for('main.login'))

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
            return redirect(url_for('main.dashboard'))
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
            return redirect(url_for('main.dashboard'))
        flash('Invalid credentials. Please try again.', 'danger')
    return render_template('login.html')

# Logout Route
@main.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('main.home'))

# Add Product Route
@main.route('/add-product', methods=['GET', 'POST'])
def add_product():
    if 'user_id' not in session:
        flash('You need to log in to add a product', 'warning')
        return redirect(url_for('main.login'))
    
    if request.method == 'POST':
        # Gegevens ophalen uit formulier
        name = request.form['listing_name']
        description = request.form['description']
        picture = request.form['picture']
        status = request.form['status']
        available_calendar = request.form['available_calendar']

        # Validatie van tijdgerelateerde invoer
        try:
            slot_duration = int(request.form['slot_duration'])  # Zorg dat het een int is
            start_time = datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid input format. Please check your time inputs.', 'danger')
            return redirect(url_for('main.add_product'))

        # Tijdslots genereren
        timeslots = generate_timeslots(start_time, end_time, timedelta(minutes=slot_duration))

        # iCalendar-bestand aanmaken
        filename = f"{name}_timeslots.ics"
        filepath = create_ical(timeslots, filename)

        # Controleer of een geldig pad is geretourneerd
        if filepath is None:
            raise ValueError("create_ical did not return a valid filepath")

        # Validatie van het bestandspad
        if not isinstance(filepath, str):
            raise TypeError(f"Expected a string for filepath, got {type(filepath)}")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Filepath does not exist: {filepath}")

        # Product opslaan in de database
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

        # Bestand verzenden
        flash('Successfully added a new product!', 'success')
        return send_file(filepath, as_attachment=True, download_name=filename, mimetype='text/calendar')

    return render_template('add_product.html')

# View All Listings Route
@main.route('/listings')
def listings():
    all_products = Product.query.all()
    return render_template('listings.html', listings=all_products)

# Book Product Route
@main.route('/book-product/<int:listingID>', methods=['GET', 'POST'])
def book_product(listingID):
    if 'user_id' not in session:
        flash('You need to log in to book a product', 'warning')
        return redirect(url_for('main.login'))
    
    product = Product.query.get_or_404(listingID)
    if request.method == 'POST':
        persons_booked = int(request.form['persons_booked'])
        time = request.form['time']
        commission_fee = float(request.form['commission_fee'])
        booked_calendar = request.form['booked_calendar']
        new_booking = Booking(
            listingID=listingID,
            buyerID=session['user_id'],
            personsBooked=persons_booked,
            time=time,
            commissionfee=commission_fee,
            booked_calendar=booked_calendar
        )
        db.session.add(new_booking)
        db.session.commit()
        flash('Booking successful', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('book_product.html', product=product)

# Product Details Route
@main.route('/product-details/<int:listingID>')
def product_details(listingID):
    product = Product.query.filter_by(listingID=listingID).first()
    if product:
        return render_template('product_details.html', product=product)
    flash('Product not found.', 'danger')
    return redirect(url_for('main.listings'))
