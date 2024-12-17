from flask import Blueprint, request, redirect, url_for, render_template, session, flash, send_file
from datetime import datetime, timedelta
from .models import db, User, Product, Booking, Review, Notification
from .utils import generate_timeslots, create_ical
from sqlalchemy.sql import func
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
        price = request.form['price']  # Haal de prijs per dag op
        # Nieuwe waarde voor timeslot toevoegen
        timeslot = request.form['timeslot']  # Haal het handmatig ingevoerde tijdslot op

        # Product opslaan in de database, inclusief het handmatig ingevoerde timeslot
        new_product = Product(
            name=name,
            description=description,
            picture=picture,
            status=status,
            price=price,  # Voeg de prijs per dag toe
            timeslot=timeslot,  # Opslaan van het handmatig ingevoerde tijdslot
            providerID=session['user_id']
        )
        db.session.add(new_product)
        db.session.commit()

        # Bestand verzenden
        flash('Successfully added a new product!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('add_product.html')



# View All Listings Route
from sqlalchemy import func

@main.route('/listings', methods=['GET'])
def listings():
    # Verkrijg zoekterm en sorteermogelijkheid van de URL-parameters
    search_query = request.args.get('search', '').strip()  # De zoekterm, standaard leeg
    sort_option = request.args.get('sort', 'name_asc')  # De sorteeroptie, standaard op naam sorteren (A-Z)
    status_filter = request.args.get('status', 'all')  # De statusfilter, standaard op 'all' (toon alles)
    # Begin de basisquery voor producten
    query = Product.query

    # Als er een zoekterm is, filter dan op naam of beschrijving
    if search_query:
        query = query.filter(
            (Product.name.ilike(f'%{search_query}%')) |  # Zoeken in de naam van het product
            (Product.description.ilike(f'%{search_query}%'))  # Zoeken in de beschrijving van het product
        )
    if status_filter != 'all':
        # Filteren op basis van de geselecteerde status
        query = query.filter(Product.status == status_filter)
    # Als de statusfilter 'all' is, geen extra filter toepassen
    else:
        # Je hoeft geen filter toe te passen als 'all' is geselecteerd
        # De query zal gewoon alle producten tonen, zonder statusbeperkingen
        pass

    # Sorteren op basis van de geselecteerde optie
    if sort_option == 'name_asc':
        query = query.order_by(Product.name.asc())
    elif sort_option == 'name_desc':
        query = query.order_by(Product.name.desc())
    elif sort_option == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort_option == 'price_desc':
        query = query.order_by(Product.price.desc())

    # Haal de producten op na filteren en sorteren
    all_products = query.all()

    # Render de template met de gefilterde producten en de zoekterm
    return render_template('listings.html', listings=all_products, sort_option=sort_option, search_query=search_query, status_filter=status_filter)


@main.route('/book-product/<int:listingID>', methods=['GET', 'POST'])
def book_product(listingID):
    # Haal het product op
    product = Product.query.get_or_404(listingID)

    # Controleer of het product beschikbaar is
    if product.status.lower() == 'unavailable':
        flash('This product is already unavailable.', 'warning')
        return redirect(url_for('main.product_details', listingID=listingID))

    # Controleer of de gebruiker is ingelogd
    if 'user_id' not in session:
        flash('You need to log in to book a product.', 'warning')
        return redirect(url_for('auth.login'))  

    # Maak een nieuwe booking aan en update de productstatus
    new_booking = Booking(
        listingID=listingID,
        buyerID=session['user_id']
    )
    product.status = 'Unavailable'

    # Sla alles op in de database
    db.session.add(new_booking)
    db.session.commit()

    # Redirect naar succespagina
    session['product_name'] = product.name  # Sla tijdelijk op in session
    return redirect(url_for('main.booking_success'))


@main.route('/booking-success')
def booking_success():
    product_name = request.args.get('product_name', 'Product')
    return render_template('booking_success.html', product_name=product_name)

# Product Details Route

@main.route('/product-details/<int:listingID>')
def product_details(listingID):
    # Haal het product op, of retourneer 404 als het niet bestaat
    product = Product.query.get_or_404(listingID)

    # Haal alle boekingen op die bij dit product horen
    bookings = Booking.query.filter_by(listingID=listingID).all()

    # Haal reviews op die gerelateerd zijn aan dit product via boekingen
    reviews = (
        Review.query
        .join(Booking, Review.BookingID == Booking.BookingID)
        .filter(Booking.listingID == listingID)
        .all()
    )

    # Bereken de gemiddelde score van de reviews (indien beschikbaar)
    average_score = (
        db.session.query(func.avg(Review.score))
        .join(Booking, Review.BookingID == Booking.BookingID)
        .filter(Booking.listingID == listingID)
        .scalar()
    )

    # Haal de eigenaar van het product op via providerID
    owner = User.query.get_or_404(product.providerID)

    timeslot = product.timeslot
    # Render de 'product_details.html' template met de relevante gegevens
    return render_template(
        'product_details.html',
        product=product,
        bookings=bookings,
        reviews=reviews,
        average_score=round(average_score, 2) if average_score else None,
        owner=owner,  # Voeg de eigenaar toe aan de template
        timeslot=timeslot  # Voeg de timeslot toe aan de template
    )

# Edit Product Route
@main.route('/edit-product/<int:listingID>', methods=['GET', 'POST'])
def edit_product(listingID):
    if 'user_id' not in session:
        flash('You need to log in to edit a product', 'warning')
        return redirect(url_for('main.login'))
    
    # Zoek het product van de gebruiker
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

        # **Prijs update**: Haal de prijs op uit het formulier
        try:
            product.price = float(request.form['price'])  # Zet de prijs om naar een float
        except ValueError:
            flash('Invalid price format. Please enter a valid number.', 'danger')
            return redirect(url_for('main.edit_product', listingID=listingID))


        # Opslaan in de database
        db.session.commit()
        flash('Product updated successfully, including calendar, price, and timeslot!', 'success')
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
        # Probeer het ophalen en valideren van de score
        try:
            # Haal de score op uit het formulier
            score = int(request.form.get('score'))

            # Score validatie (moet tussen 1 en 5 zijn)
            if not (1 <= score <= 5):
                raise ValueError("Score must be between 1 and 5.")

            # Controleer of er al een review bestaat voor deze boeking
            existing_review = Review.query.filter_by(BookingID=booking.BookingID).first()
            if existing_review:
                flash("A review already exists for this booking.", "warning")
                return redirect(url_for('main.product_details', listingID=booking.listingID))

            # Voeg de review toe aan de database
            review = Review(
                score=score,
                buyerID=session.get('user_id'),
                BookingID=booking.BookingID
            )
            db.session.add(review)
            db.session.commit()

            # Succesbericht en redirect
            flash("Review added successfully!", "success")
            return redirect(url_for('main.product_details', listingID=booking.listingID))
        except ValueError as e:
            # Foutmelding bij ongeldige invoer
            flash(str(e), "danger")
            return render_template('add_review.html', booking=booking)
        except Exception as e:
            # Algemene foutafhandeling
            flash("An unexpected error occurred. Please try again.", "danger")
            return render_template('add_review.html', booking=booking)

    # Render de `add_review.html` template voor GET-verzoeken
    return render_template('add_review.html', booking=booking)


@main.route('/bookings')
def bookings():
    if 'user_id' not in session:
        flash('You need to log in to view bookings', 'warning')
        return redirect(url_for('main.login'))

    user_id = session['user_id']

    # My Bookings: Haal boekingen op die door de gebruiker zijn gemaakt
    my_bookings = db.session.query(Booking, Product).join(Product, Product.listingID == Booking.listingID).filter(Booking.buyerID == user_id).all()

    # Booked By Others: Haal boekingen op van producten die door de gebruiker worden aangeboden
    booked_by_others = db.session.query(Booking, Product, User).join(Product, Product.listingID == Booking.listingID).join(User, User.userID == Booking.buyerID).filter(Product.providerID == user_id).all()

    return render_template('bookings.html', my_bookings=my_bookings, booked_by_others=booked_by_others)
@main.route('/booking/<int:BookingID>/delete', methods=['POST'])
def delete_booking(BookingID):
    if 'user_id' not in session:
        flash('You need to log in to perform this action', 'warning')
        return redirect(url_for('main.login'))

    user_id = session['user_id']

    # Haal de boeking op
    booking = Booking.query.get_or_404(BookingID)

    # Controleer of de gebruiker eigenaar is van de boeking
    if booking.buyerID != user_id:
        flash('You are not authorized to delete this booking.', 'danger')
        return redirect(url_for('main.bookings'))

    try:
        # Haal het product op gekoppeld aan de boeking
        product = Product.query.get(booking.listingID)

        # Verwijder eerst gerelateerde reviews
        Review.query.filter_by(BookingID=BookingID).delete()

        # Verwijder de boeking
        db.session.delete(booking)

        # Update de productstatus naar 'unavailable' als het product bestaat
        if product:
            product.status = 'Available'

        # Sla alles op in de database
        db.session.commit()

        flash('Booking successfully deleted, and product status updated to unavailable.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {e}', 'danger')

    return redirect(url_for('main.bookings'))
