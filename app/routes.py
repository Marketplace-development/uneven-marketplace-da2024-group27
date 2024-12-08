from flask import Blueprint, request, redirect, url_for, render_template, session, flash, send_file
from datetime import datetime, timedelta
from .models import db, User, Product, Booking, Review, Notification
from .utils import generate_timeslots, create_ical
import os 

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
    return os.getcwd() + "/" + filename

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
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        available_calendar = [start_time, end_time]

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
        return redirect(url_for('main.dashboard'))
    return render_template('add_product.html')

# View All Listings Route
@main.route('/listings')
def listings():
    all_products = Product.query.all()
    return render_template('listings.html', listings=all_products)

# Book Product Route
from datetime import datetime

@main.route('/book-product/<int:listingID>', methods=['GET', 'POST'])
def book_product(listingID):
    # Controleer of de gebruiker is ingelogd
    if 'user_id' not in session:
        flash('You need to log in to book a product', 'warning')
        return redirect(url_for('main.login'))

    product = Product.query.get_or_404(listingID)

    # Parse de beschikbare kalender (start en einddatum)
    available_calendar = []
    if product.available_calendar:
        available_calendar = product.available_calendar.split(",")  # Splits op basis van komma
    
    if request.method == 'POST':
        try:
            # Haal gegevens op uit het formulier
            start_time = datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')
            commission_fee = 0.25  # Vast bedrag voor commissie

            # Controleer of de geboekte tijden binnen de beschikbare periode vallen
            available_start = datetime.strptime(available_calendar[0], '%Y-%m-%dT%H:%M')
            available_end = datetime.strptime(available_calendar[1], '%Y-%m-%dT%H:%M')
            if not (available_start <= start_time < end_time <= available_end):
                flash('Selected time is not within the available period.', 'danger')
                return redirect(url_for('main.book_product', listingID=listingID))

            # Voeg nieuwe booking toe
            booked_calendar = f"{start_time} - {end_time}"
            new_booking = Booking(
                listingID=listingID,
                buyerID=session['user_id'],
                time=start_time,
                commissionfee=commission_fee,
                booked_calendar=booked_calendar
            )
            db.session.add(new_booking)

            # Voeg notificatie toe
            notification_message = f"Booking confirmed for {product.name} from {start_time} to {end_time}."
            new_notification = Notification(
                message=notification_message,
                receiverID=session['user_id']
            )
            db.session.add(new_notification)
            db.session.commit()

            flash(f"{product.name} was successfully booked!", "success")
            return redirect(url_for('main.dashboard'))

        except ValueError as e:
            flash(f"Invalid input: {str(e)}", 'danger')
            return redirect(url_for('main.book_product', listingID=listingID))

    return render_template(
        'book_product.html',
        product=product,
        available_calendar=available_calendar
    )

# Product Details Route
@main.route('/product-details/<int:listingID>')
def product_details(listingID):
    product = Product.query.filter_by(listingID=listingID).first_or_404()

    # Haal alle boekingen op
    bookings = Booking.query.filter_by(listingID=listingID).all()

    # Haal alle reviews op en controleer op geldige buyers
    reviews = Review.query.join(Booking).filter(Booking.listingID == listingID).all()
    valid_reviews = [review for review in reviews if review.buyer]

    # Bereken de gemiddelde score
    average_score = (
        db.session.query(db.func.avg(Review.score))
        .join(Booking)
        .filter(Booking.listingID == listingID)
        .scalar()
    )

    return render_template(
        'product_details.html',
        product=product,
        reviews=valid_reviews,
        average_score=round(average_score, 2) if average_score else None
    )

# Edit Product Route
@main.route('/edit-product/<int:listingID>', methods=['GET', 'POST'])
def edit_product(listingID):
    if 'user_id' not in session:
        flash('You need to log in to edit a product', 'warning')
        return redirect(url_for('main.login'))
    
    product = Product.query.filter_by(listingID=listingID, providerID=session['user_id']).first()
    if not product:
        flash('Product not found or you do not have permission to edit this product.', 'danger')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        # Update de basisgegevens van het product
        product.name = request.form['listing_name']
        product.description = request.form['description']
        product.picture = request.form['picture']
        product.status = request.form['status']
        product.available_calendar = request.form['available_calendar']

        # Kalenderinformatie ophalen en valideren
        try:
            start_time = request.form['start_time']
            end_time = request.form['end_time']
            slot_duration = int(request.form['slot_duration'])

            # Valideer tijd
            start_time_dt = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
            end_time_dt = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
            if start_time_dt >= end_time_dt:
                flash('Start time must be before end time.', 'danger')
                return redirect(url_for('main.edit_product', listingID=listingID))

            # Genereer tijdslots
            timeslots = generate_timeslots(start_time_dt, end_time_dt, timedelta(minutes=slot_duration))

            # Optioneel: Maak een iCalendar-bestand
            filename = f"{product.name}_timeslots.ics"
            create_ical(timeslots, filename)

            # Sla nieuwe kalenderinformatie op
            product.available_calendar = [start_time, end_time]
        except ValueError:
            flash('Invalid input format. Please check your time inputs.', 'danger')
            return redirect(url_for('main.edit_product', listingID=listingID))

        # Opslaan in de database
        db.session.commit()
        flash('Product updated successfully, including calendar!', 'success')
        return redirect(url_for('main.dashboard'))
    
    # Render de bewerkingspagina
    return render_template('edit_product.html', product=product)

@main.route('/delete-product/<int:listingID>', methods=['POST'])
def delete_product(listingID):
    if 'user_id' not in session:
        flash('You need to log in to delete a product', 'warning')
        return redirect(url_for('main.login'))

    product = Product.query.filter_by(listingID=listingID, providerID=session['user_id']).first()
    if not product:
        flash('Product not found or you do not have permission to delete this product.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Verwijder gekoppelde reviews
    bookings = Booking.query.filter_by(listingID=listingID).all()
    for booking in bookings:
        Review.query.filter_by(BookingID=booking.BookingID).delete()

    # Verwijder gekoppelde bookings
    Booking.query.filter_by(listingID=listingID).delete()

    # Verwijder het product
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('main.dashboard'))

@main.route('/booking/<int:BookingID>/add_review', methods=['GET', 'POST'])
def add_review(BookingID):
    # Controleer of de boeking bestaat
    booking = Booking.query.get_or_404(BookingID)

    # Controleer of de gebruiker de eigenaar van de boeking is
    if booking.buyerID != session.get('user_id'):
        flash("You are not authorized to review this booking.", "danger")
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        score = request.form.get('score')

        # Validatie
        if not score or int(score) < 1 or int(score) > 5:
            flash("Please provide a valid score between 1 and 5.", "danger")
            return redirect(url_for('main.add_review', BookingID=BookingID))

        # Voeg de review toe
        review = Review(
            score=int(score),
            buyerID=session.get('user_id'),
            BookingID=booking.BookingID
        )
        db.session.add(review)
        db.session.commit()
        flash("Review added successfully!", "success")
        return redirect(url_for('main.dashboard'))

    return render_template('add_review.html', booking=Booking.query.get_or_404(BookingID))
