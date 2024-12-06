from flask import Blueprint, request, redirect, url_for, render_template, session, flash, send_file
from datetime import datetime, timedelta
from .models import db, User, Product, Booking, Review, Notification

# Blueprint aanmaken
main = Blueprint('main', __name__)

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
    # Controleer of de gebruiker is ingelogd
    if 'user_id' not in session:
        flash('You need to log in to add a product', 'warning')
        return redirect(url_for('main.login'))
    
    if request.method == 'POST':
        # Haal gegevens op uit het formulier
        name = request.form['listing_name']
        description = request.form['description']
        picture = request.form['picture']
        status = request.form['status']
        available_calendar = request.form['available_calendar']

        # Maak een nieuw product aan en sla op in de database
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

        flash('Successfully added a new product!', 'success')
        return redirect(url_for('main.dashboard'))
    
    # Als het een GET-verzoek is, toon het formulier
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
    product = Product.query.filter_by(listingID=listingID).first_or_404()

    # Haal alle boekingen op die bij dit product horen
    bookings = Booking.query.filter_by(listingID=listingID).all()

    # Verzamel alle reviews die bij deze boekingen horen
    reviews = Review.query.join(Booking).filter(Booking.listingID == listingID).all()

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
        reviews=reviews,
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
        # Update de gegevens van het product
        product.name = request.form['listing_name']
        product.description = request.form['description']
        product.picture = request.form['picture']
        product.status = request.form['status']
        product.available_calendar = request.form['available_calendar']
        
        # Opslaan in de database
        db.session.commit()
        flash('Product updated successfully!', 'success')
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

@main.route('/booking/<int:bookingID>/add-review', methods=['GET', 'POST'])
def add_review(bookingID):
    # Controleer of de boeking bestaat
    booking = Booking.query.get_or_404(bookingID)

    # Controleer of de gebruiker de eigenaar van de boeking is
    if booking.buyerID != session.get('user_id'):
        flash("You are not authorized to review this booking.", "danger")
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        score = request.form.get('score')

        # Validatie
        if not score or int(score) < 1 or int(score) > 5:
            flash("Please provide a valid score between 1 and 5.", "danger")
            return redirect(url_for('main.add_review', bookingID=bookingID))

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

    return render_template('add_review.html', booking=booking)
