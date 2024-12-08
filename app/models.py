from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'User'  # Adjusted to match the image
    userID = db.Column(db.Integer, primary_key=True)
    userName = db.Column(db.String(100), nullable=False)
    authID = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)


class Notification(db.Model):
    __tablename__ = 'Notification'  # Adjusted to match the image
    notificationID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type = db.Column(db.String(50), nullable=False)
    viewed = db.Column(db.Boolean, default=False, nullable=False)

    # Foreign Key
    receiverID = db.Column(db.Integer, db.ForeignKey('User.userID'), nullable=False)


class Product(db.Model):
    __tablename__ = 'Product'  # Adjusted to match the image
    listingID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    picture = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(50), nullable=False)

    # Foreign Key
    providerID = db.Column(db.Integer, db.ForeignKey('User.userID'), nullable=False)

    # Additional Field
    available_calendar = db.Column(db.Text, nullable=False)


class Booking(db.Model):
    __tablename__ = 'Booking'  # Adjusted to match the image
    BookingID = db.Column(db.Integer, primary_key=True)
    personsBooked = db.Column(db.Integer, nullable=True)
    time = db.Column(db.DateTime, nullable=False)
    commissionfee = db.Column(db.Float, nullable=False)

    # Foreign Keys
    listingID = db.Column(db.Integer, db.ForeignKey('Product.listingID'), nullable=False)
    buyerID = db.Column(db.Integer, db.ForeignKey('User.userID'), nullable=False)

    # Additional Field
    booked_calendar = db.Column(db.Text, nullable=False)


class Review(db.Model):
    __tablename__ = 'Review'  # Adjusted to match the image
    reviewID = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, nullable=False)

    # Foreign Keys
    buyerID = db.Column(db.Integer, db.ForeignKey('User.userID'), nullable=False)
    BookingID = db.Column(db.Integer, db.ForeignKey('Booking.BookingID'), nullable=False)

    buyer = db.relationship('User', backref='reviews', lazy=True)