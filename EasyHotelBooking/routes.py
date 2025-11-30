import json
from datetime import datetime, timedelta, time, date
from flask import render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from app import app
from extensions import db, login_manager
from models import User, Room, Amenity, Booking, BookingAmenity, Rating, Notification, Attendance, LeaveRequest, Payroll
import re
import random
import smtplib
from email.mime.text import MIMEText
from flask_dance.contrib.google import make_google_blueprint, google
import os
from werkzeug.utils import secure_filename
from flask_mail import Message
import secrets
from flask_mail import Mail

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'hoteleasy244@gmail.com'
app.config['MAIL_PASSWORD'] = 'jler dwhq hzms pzom'
mail = Mail(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    rooms = Room.query.all()
    # Print all room image paths for debugging
    for room in rooms:
        print(f"Room: {room.name}, Image URL: {room.image_url}")
    return render_template('index.html', rooms=rooms)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        elif current_user.is_staff:
            return redirect(url_for('staff_dashboard'))
        else:
            return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        # Prevent admin from logging in via user login
        if user and user.is_admin:
            flash('Admin accounts must log in through the admin login page.', 'danger')
            return render_template('login.html')
        
        if user and user.check_password(password):
            login_user(user)
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            elif user.is_staff:
                return redirect(url_for('staff_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')
            
    return render_template('login.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password) and user.is_admin:
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials', 'danger')
            
    return render_template('admin_login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        verification_code = request.form.get('verification_code')
        phone_number = request.form.get('phone_number')
        
        # If we're verifying the code
        if verification_code:
            if verification_code == session.get('email_verification'):
                user_data = session.pop('pending_user')
                new_user = User(username=user_data['username'], email=user_data['email'], phone_number=user_data['phone_number'])
                new_user.set_password(user_data['password'])
                db.session.add(new_user)
                db.session.commit()
                session.pop('email_verification', None)
                session.pop('email_verification_email', None)
                login_user(new_user)  # Automatically log in the user
                flash('Registration successful! Welcome to Easy Hotel.', 'success')
                if new_user.is_admin:
                    return redirect(url_for('user_list'))
                else:
                    return redirect(url_for('dashboard'))
            else:
                flash('Invalid verification code. Please try again.', 'danger')
                return render_template('register.html', require_code=True, email=email)
        
        # Initial registration form submission
        # Username validation
        if not re.match(r'^[A-Za-z]{5,}$', username or ''):
            flash('Username must be at least 5 letters and contain only letters.', 'danger')
            return render_template('register.html')
        
        # Password validation
        if not re.match(r'^(?=.*\d).{8,}$', password or ''):
            flash('Password must be at least 8 characters and include a number.', 'danger')
            return render_template('register.html')
        
        # Email validation
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email or ''):
            flash('Invalid email address.', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
        
        # Phone number validation
        if not phone_number or not phone_number.isdigit() or len(phone_number) != 11:
            flash('Phone number must be exactly 11 digits and contain only numbers.', 'danger')
            return render_template('register.html')
        
        # Check if user already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or email already exists', 'danger')
            return render_template('register.html')
        
        # Generate and send verification code
        code = str(random.randint(100000, 999999))
        session['email_verification'] = code
        session['email_verification_email'] = email
        session['pending_user'] = {
            'username': username,
            'email': email,
            'password': password,
            'phone_number': phone_number
        }
        
        # Send verification email
        try:
            msg = MIMEText(f'''
            Welcome to Easy Hotel!
            
            Your verification code is: {code}
            
            Please enter this code to complete your registration.
            
            If you did not request this registration, please ignore this email.
            
            Best regards,
            Easy Hotel Team
            ''')
            msg['Subject'] = 'Easy Hotel - Email Verification'
            msg['From'] = 'no-reply@easyhotel.com'
            msg['To'] = email
            
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login('hoteleasy244@gmail.com', 'jler dwhq hzms pzom')
                server.sendmail('no-reply@easyhotel.com', [email], msg.as_string())
            
            flash('Verification code has been sent to your email. Please check your inbox.', 'info')
            return render_template('register.html', require_code=True, email=email)
            
        except Exception as e:
            print(f"Email error: {str(e)}")  # For debugging
            flash('Failed to send verification email. Please try again later.', 'danger')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        return update_profile()
    return render_template('profile.html', current_user=current_user)

@app.route('/bookings')
@login_required
def bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).all()
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    return render_template('bookings.html', bookings=bookings, notifications=notifications, datetime=datetime)

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    elif current_user.is_staff:
        return redirect(url_for('staff_dashboard'))
    else:
        return redirect(url_for('bookings'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
        
    pending_bookings = Booking.query.filter_by(status='pending').all()
    confirmed_bookings = Booking.query.filter_by(status='confirmed').all()
    cancelled_bookings = Booking.query.filter_by(status='cancelled').all()
    recent_ratings = Rating.query.order_by(Rating.created_at.desc()).limit(10).all()
    
    # Calculate total revenue from confirmed bookings
    total_revenue = db.session.query(db.func.sum(Booking.total_price)).filter_by(status='confirmed').scalar() or 0
    
    return render_template('admin_dashboard.html', 
                          pending_bookings=pending_bookings,
                          confirmed_bookings=confirmed_bookings,
                          cancelled_bookings=cancelled_bookings,
                          recent_ratings=recent_ratings,
                          total_revenue=total_revenue)

@app.route('/booking', methods=['GET', 'POST'])
@login_required
def booking():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
        
    rooms = Room.query.all()
    amenities = Amenity.query.all()
    
    if request.method == 'POST':
        room_id = request.form.get('room_id')
        check_in_date = datetime.strptime(request.form.get('check_in_date'), '%Y-%m-%d').date()
        check_out_date = datetime.strptime(request.form.get('check_out_date'), '%Y-%m-%d').date()
        adults = int(request.form.get('adults', 1))
        children = int(request.form.get('children', 0))
        total_guests = adults + children
        
        room = Room.query.get(room_id)
        
        # Check if room is available for the selected dates
        existing_bookings = Booking.query.filter_by(room_id=room_id).filter(
            ((Booking.check_in_date <= check_in_date) & (Booking.check_out_date >= check_in_date)) |
            ((Booking.check_in_date <= check_out_date) & (Booking.check_out_date >= check_out_date)) |
            ((Booking.check_in_date >= check_in_date) & (Booking.check_out_date <= check_out_date))
        ).filter(Booking.status != 'cancelled').count()
        
        if existing_bookings > 0:
            flash('Room is not available for the selected dates', 'danger')
            return redirect(url_for('booking'))
            
        if total_guests > room.capacity:
            flash(f'This room can only accommodate up to {room.capacity} guests', 'danger')
            return redirect(url_for('booking'))
            
        # Calculate total price
        days = (check_out_date - check_in_date).days
        total_price = room.price_per_night * days
        
        # Get selected amenities
        selected_amenities = []
        amenities_cost = 0
        
        for amenity in amenities:
            quantity = request.form.get(f'amenity_{amenity.id}')
            if quantity and int(quantity) > 0:
                selected_amenities.append({
                    'id': amenity.id,
                    'quantity': int(quantity)
                })
                amenities_cost += amenity.price * int(quantity)
                
        total_price += amenities_cost
        
        # Store booking details in session for checkout
        session['booking'] = {
            'room_id': room_id,
            'check_in_date': check_in_date.strftime('%Y-%m-%d'),
            'check_out_date': check_out_date.strftime('%Y-%m-%d'),
            'adults': adults,
            'children': children,
            'total_guests': total_guests,
            'total_price': total_price,
            'amenities': selected_amenities
        }
        
        return redirect(url_for('checkout'))
        
    return render_template('booking.html', rooms=rooms, amenities=amenities)

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if current_user.is_admin or 'booking' not in session:
        return redirect(url_for('booking'))
        
    booking_data = session['booking']
    room = Room.query.get(booking_data['room_id'])
    
    amenities_details = []
    for amenity_data in booking_data['amenities']:
        amenity = Amenity.query.get(amenity_data['id'])
        amenities_details.append({
            'id': amenity.id,
            'name': amenity.name,
            'price': amenity.price,
            'quantity': amenity_data['quantity'],
            'total': amenity.price * amenity_data['quantity']
        })
    
    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        
        # Create booking
        new_booking = Booking(
            user_id=current_user.id,
            room_id=booking_data['room_id'],
            check_in_date=datetime.strptime(booking_data['check_in_date'], '%Y-%m-%d').date(),
            check_out_date=datetime.strptime(booking_data['check_out_date'], '%Y-%m-%d').date(),
            guests=booking_data['total_guests'],
            total_price=booking_data['total_price'],
            status='pending'
        )
        
        db.session.add(new_booking)
        db.session.flush()  # Get the booking ID
        
        # Add booking amenities
        for amenity_data in booking_data['amenities']:
            booking_amenity = BookingAmenity(
                booking_id=new_booking.id,
                amenity_id=amenity_data['id'],
                quantity=amenity_data['quantity']
            )
            db.session.add(booking_amenity)
            
        # Create notification
        notification = Notification(
            user_id=current_user.id,
            title="Booking Confirmation",
            message=f"Your booking at Easy Hotel has been received and is pending confirmation. Booking ID: {new_booking.id}"
        )
        db.session.add(notification)
        
        db.session.commit()
        
        # Clear booking data from session
        session.pop('booking', None)
        
        flash('Booking completed successfully! Awaiting admin confirmation.', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('checkout.html', room=room, booking=booking_data, amenities=amenities_details)

@app.route('/rating/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def rating(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    # Check if booking belongs to current user
    if booking.user_id != current_user.id and not current_user.is_admin:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
        
    # Check if booking is completed and confirmed
    if booking.status != 'confirmed' or booking.check_out_date > datetime.now().date():
        flash('You can only rate confirmed and completed stays', 'warning')
        return redirect(url_for('dashboard'))
        
    # Check if already rated
    existing_rating = Rating.query.filter_by(booking_id=booking_id).first()
    
    if request.method == 'POST' and not existing_rating:
        overall_rating = int(request.form.get('overall_rating'))
        room_rating = int(request.form.get('room_rating'))
        amenities_rating = int(request.form.get('amenities_rating'))
        service_rating = int(request.form.get('service_rating'))
        comment = request.form.get('comment')
        
        # Validate ratings
        if not all(1 <= rating <= 5 for rating in [overall_rating, room_rating, amenities_rating, service_rating]):
            flash('All ratings must be between 1 and 5 stars', 'danger')
            return redirect(url_for('rating', booking_id=booking_id))
            
        new_rating = Rating(
            user_id=current_user.id,
            booking_id=booking_id,
            overall_rating=overall_rating,
            room_rating=room_rating,
            amenities_rating=amenities_rating,
            service_rating=service_rating,
            comment=comment
        )
        
        db.session.add(new_rating)
        
        # Create notification for admin
        notification = Notification(
            user_id=current_user.id,
            title="New Rating Submitted",
            message=f"A new rating has been submitted for booking #{booking_id}. Overall rating: {overall_rating}/5"
        )
        db.session.add(notification)
        
        db.session.commit()
        
        flash('Thank you for your rating!', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('rating.html', booking=booking, existing_rating=existing_rating)

@app.route('/notifications')
@login_required
def notifications():
    user_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    
    # Mark all as read
    for notification in user_notifications:
        notification.is_read = True
    
    db.session.commit()
    
    return render_template('notifications.html', notifications=user_notifications)

# Admin Routes
@app.route('/booking/<int:booking_id>/cancel', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    # Check if booking belongs to current user
    if booking.user_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if booking can be cancelled (not already cancelled and not past check-in)
    if booking.status == 'cancelled':
        flash('This booking is already cancelled', 'warning')
        return redirect(url_for('dashboard'))
    
    if booking.check_in_date <= datetime.now().date():
        flash('Cannot cancel a booking that has already started', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get cancellation reason
    reason = request.form.get('reason')
    if not reason:
        flash('Please provide a reason for cancellation', 'danger')
        return redirect(url_for('dashboard'))
    
    # Update booking status
    booking.status = 'cancelled'
    booking.cancellation_reason = reason
    booking.cancelled_by = 'user'
    
    # Create notification
    notification = Notification(
        user_id=current_user.id,
        title="Booking Cancelled",
        message=f"Your booking (ID: {booking.id}) has been cancelled. Reason: {reason}"
    )
    db.session.add(notification)
    
    db.session.commit()
    
    flash('Booking cancelled successfully', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/booking/<int:booking_id>/verify', methods=['POST'])
@login_required
def verify_booking(booking_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    booking = Booking.query.get_or_404(booking_id)
    action = request.form.get('action')
    
    if action == 'confirm':
        booking.status = 'confirmed'
        notification_message = f"Your booking (ID: {booking.id}) has been confirmed. We look forward to welcoming you to Easy Hotel!"
    elif action == 'cancel':
        reason = request.form.get('reason')
        booking.status = 'cancelled'
        booking.cancellation_reason = reason
        booking.cancelled_by = 'admin'
        notification_message = f"Your booking (ID: {booking.id}) has been cancelled by the administrator. Reason: {reason}"
    else:
        return jsonify({'success': False, 'message': 'Invalid action'}), 400
        
    # Create notification for the user
    notification = Notification(
        user_id=booking.user_id,
        title=f"Booking {booking.status.capitalize()}",
        message=notification_message
    )
    
    db.session.add(notification)
    db.session.commit()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/rating/<int:rating_id>/reply', methods=['POST'])
@login_required
def reply_to_rating(rating_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    rating = Rating.query.get_or_404(rating_id)
    reply = request.form.get('reply')
    
    rating.admin_reply = reply
    
    # Create notification for the user
    notification = Notification(
        user_id=rating.user_id,
        title="Response to Your Rating",
        message=f"Admin has responded to your rating: {reply}"
    )
    
    db.session.add(notification)
    db.session.commit()
    
    return redirect(url_for('admin_dashboard'))

# API Routes for AJAX
@app.route('/api/rooms')
def api_rooms():
    rooms = Room.query.all()
    room_list = []
    
    for room in rooms:
        # Debug information about the room
        print(f"Processing room for API: {room.name}, Image URL: {room.image_url}")
        room_list.append({
            'id': room.id,
            'name': room.name,
            'description': room.description,
            'price_per_night': room.price_per_night,
            'capacity': room.capacity,
            'image_url': room.image_url
        })
    
    return jsonify(room_list)

@app.route('/debug/images')
def debug_images():
    return render_template('debug_images.html')
    
@app.route('/debug/api/rooms')
def debug_api_rooms():
    rooms = Room.query.all()
    room_data = []
    
    for room in rooms:
        room_data.append({
            'id': room.id,
            'name': room.name,
            'image_url': room.image_url,
            'description': room.description
        })
    
    return render_template('debug_room_api.html', rooms=room_data)

@app.route('/api/amenities')
def api_amenities():
    amenities = Amenity.query.all()
    amenity_list = []
    
    for amenity in amenities:
        amenity_list.append({
            'id': amenity.id,
            'name': amenity.name,
            'description': amenity.description,
            'price': amenity.price
        })
    
    return jsonify(amenity_list)

@app.route('/api/check_availability')
def check_availability():
    room_id = request.args.get('room_id')
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    
    if not all([room_id, check_in, check_out]):
        return jsonify({'available': False, 'message': 'Missing parameters'})
    
    try:
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'available': False, 'message': 'Invalid date format'})
    
    # Check if room is available for the selected dates
    existing_bookings = Booking.query.filter_by(room_id=room_id).filter(
        ((Booking.check_in_date <= check_in_date) & (Booking.check_out_date >= check_in_date)) |
        ((Booking.check_in_date <= check_out_date) & (Booking.check_out_date >= check_out_date)) |
        ((Booking.check_in_date >= check_in_date) & (Booking.check_out_date <= check_out_date))
    ).filter(Booking.status != 'cancelled').count()
    
    return jsonify({
        'available': existing_bookings == 0,
        'message': 'Room available' if existing_bookings == 0 else 'Room not available for selected dates'
    })

@app.route('/api/calculate_price')
def calculate_price():
    room_id = request.args.get('room_id')
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    adults = int(request.args.get('adults', 1))
    children = int(request.args.get('children', 0))
    amenities = request.args.get('amenities', '[]')
    
    if not all([room_id, check_in, check_out]):
        return jsonify({'success': False, 'message': 'Missing parameters'})
    
    try:
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        amenities_data = json.loads(amenities)
    except (ValueError, json.JSONDecodeError):
        return jsonify({'success': False, 'message': 'Invalid parameters'})
    
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'success': False, 'message': 'Room not found'})
    
    # Calculate number of days
    days = (check_out_date - check_in_date).days
    if days <= 0:
        return jsonify({'success': False, 'message': 'Check-out date must be after check-in date'})
    
    # Check if total guests exceed room capacity
    total_guests = adults + children
    if total_guests > room.capacity:
        return jsonify({'success': False, 'message': f'Room can only accommodate up to {room.capacity} guests'})
    
    # Calculate room cost
    room_cost = room.price_per_night * days
    
    # Calculate amenities cost
    amenities_cost = 0
    for amenity_data in amenities_data:
        amenity = Amenity.query.get(amenity_data.get('id'))
        if amenity:
            amenities_cost += amenity.price * amenity_data.get('quantity', 0)
    
    total_cost = room_cost + amenities_cost
    
    return jsonify({
        'success': True,
        'room_cost': room_cost,
        'amenities_cost': amenities_cost,
        'total_cost': total_cost,
        'days': days
    })

@app.route('/api/notifications/count')
@login_required
def notification_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})

@app.route('/api/notifications')
@login_required
def get_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return jsonify({
        'notifications': [{
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat()
        } for n in notifications]
    })

@app.route('/api/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    for notification in notifications:
        notification.is_read = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/revenue/weekly')
@login_required
def get_weekly_revenue():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
        
    # Get the last 8 weeks of data
    end_date = datetime.now()
    start_date = end_date - timedelta(weeks=8)
    
    # Query confirmed bookings within the date range
    bookings = Booking.query.filter(
        Booking.status == 'confirmed',
        Booking.created_at >= start_date,
        Booking.created_at <= end_date
    ).all()
    
    # Group bookings by week
    weekly_data = {}
    for booking in bookings:
        week_start = booking.created_at - timedelta(days=booking.created_at.weekday())
        week_key = week_start.strftime('%Y-%m-%d')
        if week_key not in weekly_data:
            weekly_data[week_key] = 0
        weekly_data[week_key] += booking.total_price
    
    # Format data for chart
    labels = []
    data = []
    for week_start in sorted(weekly_data.keys()):
        labels.append(datetime.strptime(week_start, '%Y-%m-%d').strftime('%b %d'))
        data.append(weekly_data[week_start])
    
    return jsonify({
        'labels': labels,
        'data': data
    })

@app.route('/api/revenue/monthly')
@login_required
def get_monthly_revenue():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
        
    # Get the last 12 months of data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    # Query confirmed bookings within the date range
    bookings = Booking.query.filter(
        Booking.status == 'confirmed',
        Booking.created_at >= start_date,
        Booking.created_at <= end_date
    ).all()
    
    # Group bookings by month
    monthly_data = {}
    for booking in bookings:
        month_key = booking.created_at.strftime('%Y-%m')
        if month_key not in monthly_data:
            monthly_data[month_key] = 0
        monthly_data[month_key] += booking.total_price
    
    # Format data for chart
    labels = []
    data = []
    for month_key in sorted(monthly_data.keys()):
        labels.append(datetime.strptime(month_key, '%Y-%m').strftime('%b %Y'))
        data.append(monthly_data[month_key])
    
    return jsonify({
        'labels': labels,
        'data': data
    })

@app.route('/api/revenue/yearly')
@login_required
def get_yearly_revenue():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
        
    # Get all years of data
    bookings = Booking.query.filter_by(status='confirmed').all()
    
    # Group bookings by year
    yearly_data = {}
    for booking in bookings:
        year_key = booking.created_at.strftime('%Y')
        if year_key not in yearly_data:
            yearly_data[year_key] = 0
        yearly_data[year_key] += booking.total_price
    
    # Format data for chart
    labels = []
    data = []
    for year_key in sorted(yearly_data.keys()):
        labels.append(year_key)
        data.append(yearly_data[year_key])
    
    return jsonify({
        'labels': labels,
        'data': data
    })

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    username = request.form.get('username')
    email = request.form.get('email')
    phone_number = request.form.get('phone_number')
    # Phone number validation
    if not phone_number or not phone_number.isdigit() or len(phone_number) != 11:
        flash('Phone number must be exactly 11 digits and contain only numbers.', 'danger')
        return redirect(url_for('dashboard'))
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_new_password = request.form.get('confirm_new_password')

    # Check for email or username conflicts
    if User.query.filter(User.email == email, User.id != current_user.id).first():
        flash('Email already in use by another account.', 'danger')
        return redirect(url_for('dashboard'))
    if User.query.filter(User.username == username, User.id != current_user.id).first():
        flash('Username already in use by another account.', 'danger')
        return redirect(url_for('dashboard'))

    # Password change logic
    if new_password or confirm_new_password:
        if not current_password or not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('dashboard'))
        if new_password != confirm_new_password:
            flash('New password and confirmation do not match.', 'danger')
            return redirect(url_for('dashboard'))
        if len(new_password) < 8 or not any(char.isdigit() for char in new_password):
            flash('New password must be at least 8 characters and include a number.', 'danger')
            return redirect(url_for('dashboard'))
        current_user.set_password(new_password)

    current_user.username = username
    current_user.email = email
    current_user.phone_number = phone_number
    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/receipt/<int:booking_id>')
@login_required
def receipt(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id and not current_user.is_admin:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    room = Room.query.get(booking.room_id)
    amenities = BookingAmenity.query.filter_by(booking_id=booking.id).all()
    amenities_details = [{
        'name': a.amenity.name,
        'quantity': a.quantity,
        'price': a.amenity.price,
        'total': a.amenity.price * a.quantity
    } for a in amenities]
    return render_template('receipt.html', booking=booking, room=room, amenities=amenities_details)

@app.route('/admin/add_room', methods=['GET', 'POST'])
@login_required
def admin_add_room():
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price_per_night = float(request.form.get('price_per_night'))
        capacity = int(request.form.get('capacity'))
        image_file = request.files.get('image_file')
        image_url = None
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            image_folder = os.path.join('static', 'images', 'rooms')
            os.makedirs(image_folder, exist_ok=True)
            image_path = os.path.join(image_folder, filename)
            image_file.save(image_path)
            image_url = f'/static/images/rooms/{filename}'
        else:
            flash('Image upload failed.', 'danger')
            return redirect(url_for('admin_add_room'))
        new_room = Room(name=name, description=description, price_per_night=price_per_night, capacity=capacity, image_url=image_url)
        db.session.add(new_room)
        db.session.commit()
        flash('Room added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_add_room.html')

@app.route('/admin/add_amenity', methods=['GET', 'POST'])
@login_required
def admin_add_amenity():
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        new_amenity = Amenity(name=name, description=description, price=price)
        db.session.add(new_amenity)
        db.session.commit()
        flash('Amenity added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_add_amenity.html')

@app.route('/admin/staff')
@login_required
def staff_list():
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('dashboard'))
    staff = User.query.filter_by(is_staff=True).all()
    return render_template('staff_list.html', staff=staff)

@app.route('/admin/staff/add', methods=['GET', 'POST'])
@login_required
def add_staff():
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        verification_code = request.form.get('verification_code')
        email = request.form.get('email')
        if verification_code:
            if verification_code == session.get('staff_email_verification'):
                staff_data = session.pop('pending_staff')
                staff_user = User(
                    username=staff_data['username'],
                    email=staff_data['email'],
                    is_staff=True,
                    staff_role=staff_data['staff_role'],
                    staff_status=staff_data['staff_status'],
                    staff_shift=staff_data['staff_shift'],
                    phone_number=staff_data['phone_number']
                )
                staff_user.set_password(staff_data['password'])
                db.session.add(staff_user)
                db.session.commit()
                session.pop('staff_email_verification', None)
                session.pop('staff_email_verification_email', None)
                flash('Staff member added successfully.', 'success')
                return redirect(url_for('staff_list'))
            else:
                flash('Invalid verification code. Please try again.', 'danger')
                return render_template('add_staff.html', require_code=True, email=email)
        # Initial staff form submission
        full_name = request.form.get('full_name')
        username = request.form.get('username')
        password = request.form.get('password') or secrets.token_urlsafe(8)
        staff_role = request.form.get('staff_role')
        phone_number = request.form.get('phone_number')
        staff_shift = request.form.get('staff_shift')
        staff_status = request.form.get('staff_status', 'active')
        # Validation
        if not all([full_name, username, email, password, staff_role]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('add_staff'))
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or email already exists.', 'danger')
            return redirect(url_for('add_staff'))
        if staff_role not in ['Front Desk', 'Bell Boy', 'Housekeeping']:
            flash('Invalid staff role.', 'danger')
            return redirect(url_for('add_staff'))
        if len(password) < 8 or not any(c.isdigit() for c in password):
            flash('Password must be at least 8 characters and include a number.', 'danger')
            return redirect(url_for('add_staff'))
        if not phone_number or not phone_number.isdigit() or len(phone_number) != 11:
            flash('Phone number must be exactly 11 digits and contain only numbers.', 'danger')
            return redirect(url_for('add_staff'))
        # Generate and send verification code
        code = str(random.randint(100000, 999999))
        session['staff_email_verification'] = code
        session['staff_email_verification_email'] = email
        session['pending_staff'] = {
            'username': username,
            'email': email,
            'password': password,
            'staff_role': staff_role,
            'staff_status': staff_status,
            'staff_shift': staff_shift,
            'phone_number': phone_number
        }
        # Send verification email
        try:
            msg = Message('Easy Hotel - Staff Email Verification',
                          sender='no-reply@easyhotel.com',
                          recipients=[email])
            msg.body = f'''
            Welcome to Easy Hotel Staff!

            Your verification code is: {code}

            Please enter this code to complete your staff registration.

            If you did not request this, please ignore this email.

            Best regards,
            Easy Hotel Team
            '''
            mail.send(msg)
        except Exception as e:
            print(f"Email error: {str(e)}")
            flash('Failed to send verification email. Please try again later.', 'danger')
            return render_template('add_staff.html')
        flash('Verification code has been sent to the staff email. Please check the inbox.', 'info')
        return render_template('add_staff.html', require_code=True, email=email)
    return render_template('add_staff.html')

@app.route('/staff/payroll')
@login_required
def staff_payroll():
    if not current_user.is_staff or current_user.is_admin:
        return redirect(url_for('dashboard'))
    from datetime import datetime
    # Get the most recent payroll issued
    last_payroll = Payroll.query.filter_by(staff_id=current_user.id).order_by(Payroll.period_end.desc()).first()
    # Get the next payroll (pending or not yet issued)
    next_payroll = Payroll.query.filter_by(staff_id=current_user.id, status='pending').order_by(Payroll.period_end.asc()).first()
    # Get all payrolls for history
    payroll_history = Payroll.query.filter_by(staff_id=current_user.id).order_by(Payroll.period_end.desc()).all()
    return render_template('staff_payroll.html', last_payroll=last_payroll, next_payroll=next_payroll, payroll_history=payroll_history)

@app.route('/staff/payroll/delete/<int:payroll_id>', methods=['POST'])
@login_required
def delete_staff_payroll(payroll_id):
    if not current_user.is_staff or current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('staff_payroll'))
    payroll = Payroll.query.get_or_404(payroll_id)
    if payroll.staff_id != current_user.id:
        flash('You can only delete your own payroll.', 'danger')
        return redirect(url_for('staff_payroll'))
    if payroll.status != 'pending':
        flash('Only pending payrolls can be deleted.', 'danger')
        return redirect(url_for('staff_payroll'))
    db.session.delete(payroll)
    db.session.commit()
    flash('Payroll deleted.', 'success')
    return redirect(url_for('staff_payroll'))

@app.route('/staff/dashboard', methods=['GET', 'POST'])
@login_required
def staff_dashboard():
    if not current_user.is_staff or current_user.is_admin:
        return redirect(url_for('dashboard'))
    from datetime import datetime
    # Get the next payroll for the staff
    next_payroll = Payroll.query.filter_by(staff_id=current_user.id, status='pending').order_by(Payroll.period_end.asc()).first()
    # Render different dashboard for each staff role
    if current_user.staff_role == 'Front Desk':
        return render_template('frontdesk_dashboard.html', bookings=Booking.query.order_by(Booking.check_in_date.desc()).all(), message_sent=False, next_payroll=next_payroll)
    elif current_user.staff_role == 'Bell Boy':
        return render_template('bellboy_dashboard.html', bookings=Booking.query.order_by(Booking.check_in_date.desc()).all(), message_sent=False, next_payroll=next_payroll)
    elif current_user.staff_role == 'Housekeeping':
        return render_template('housekeeping_dashboard.html', bookings=Booking.query.order_by(Booking.check_in_date.desc()).all(), message_sent=False, next_payroll=next_payroll)
    else:
        return render_template('staff_dashboard.html', bookings=Booking.query.order_by(Booking.check_in_date.desc()).all(), message_sent=False, next_payroll=next_payroll)

@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance():
    if not current_user.is_staff:
        return redirect(url_for('dashboard'))
    from datetime import date, datetime as dt
    import os
    today = date.today()
    attendance_record = Attendance.query.filter_by(user_id=current_user.id, date=today).first()
    leave_requests = LeaveRequest.query.filter_by(user_id=current_user.id).order_by(LeaveRequest.start_date.desc()).all()
    message = None
    if request.method == 'POST':
        action = request.form.get('action')
        if action in ['clock_in', 'clock_out']:
            verify_id = request.form.get('verify_id')
            id_image_file = request.files.get('id_image')
            id_image_path = None
            if id_image_file and id_image_file.filename:
                filename = secure_filename(f"{current_user.username}_{today}_{action}_id.jpg")
                image_folder = os.path.join('static', 'uploads', 'attendance_ids')
                os.makedirs(image_folder, exist_ok=True)
                image_path = os.path.join(image_folder, filename)
                id_image_file.save(image_path)
                id_image_path = f'/static/uploads/attendance_ids/{filename}'
            if verify_id != current_user.username:
                message = 'ID verification failed.'
            else:
                now = dt.now().time()
                if action == 'clock_in':
                    if attendance_record and attendance_record.clock_in:
                        message = 'Already clocked in today.'
                    else:
                        if not attendance_record:
                            attendance_record = Attendance(user_id=current_user.id, date=today)
                            db.session.add(attendance_record)
                        attendance_record.clock_in = now
                        attendance_record.verified_by_id = verify_id
                        if id_image_path:
                            attendance_record.id_image = id_image_path
                        attendance_record.approved = False
                        db.session.commit()
                        message = 'Clocked in successfully. Awaiting admin approval.'
                elif action == 'clock_out':
                    if not attendance_record or not attendance_record.clock_in:
                        message = 'You must clock in first.'
                    elif attendance_record.clock_out:
                        message = 'Already clocked out today.'
                    else:
                        attendance_record.clock_out = now
                        attendance_record.verified_by_id = verify_id
                        if id_image_path:
                            attendance_record.id_image = id_image_path
                        attendance_record.approved = False
                        db.session.commit()
                        message = 'Clocked out successfully. Awaiting admin approval.'
        elif action == 'request_leave':
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            reason = request.form.get('reason')
            from datetime import datetime
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            except Exception:
                message = 'Invalid date format.'
                attendance_logs = Attendance.query.filter_by(user_id=current_user.id).order_by(Attendance.date.desc()).all()
                return render_template('attendance.html', attendance_record=attendance_record, attendance_logs=attendance_logs, leave_requests=leave_requests, message=message)
            if start_date and end_date and reason:
                leave = LeaveRequest(user_id=current_user.id, start_date=start_date_obj, end_date=end_date_obj, reason=reason)
                db.session.add(leave)
                db.session.commit()
                message = 'Leave request submitted.'
            else:
                message = 'Please fill all leave request fields.'
    attendance_logs = Attendance.query.filter_by(user_id=current_user.id).order_by(Attendance.date.desc()).all()
    return render_template('attendance.html', attendance_record=attendance_record, attendance_logs=attendance_logs, leave_requests=leave_requests, message=message)

@app.route('/admin/attendance', methods=['GET', 'POST'])
@login_required
def admin_attendance():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    all_attendance = Attendance.query.order_by(Attendance.date.desc()).all()
    leave_requests = LeaveRequest.query.order_by(LeaveRequest.start_date.desc()).all()
    message = None
    if request.method == 'POST':
        action = request.form.get('action')
        leave_id = request.form.get('leave_id')
        attendance_id = request.form.get('attendance_id')
        if action in ['approve', 'reject'] and leave_id:
            leave = LeaveRequest.query.get(leave_id)
            if leave:
                leave.status = 'approved' if action == 'approve' else 'rejected'
                leave.admin_comment = request.form.get('admin_comment', '')
                db.session.commit()
                message = f'Leave request {action}d.'
        if action in ['approve_attendance', 'reject_attendance'] and attendance_id:
            attendance = Attendance.query.get(attendance_id)
            if attendance:
                attendance.approved = (action == 'approve_attendance')
                db.session.commit()
                message = f'Attendance {"approved" if attendance.approved else "rejected"}.'
    return render_template('admin_attendance.html', all_attendance=all_attendance, leave_requests=leave_requests, message=message)

@app.route('/admin/payroll/<int:payroll_id>/archive', methods=['POST'])
@login_required
def archive_payroll(payroll_id):
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('payroll_management'))
    payroll = Payroll.query.get_or_404(payroll_id)
    payroll.archived = True
    db.session.commit()
    flash('Payroll archived.', 'success')
    return redirect(url_for('payroll_management'))

@app.route('/admin/payroll/<int:payroll_id>/unarchive', methods=['POST'])
@login_required
def unarchive_payroll(payroll_id):
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('payroll_management'))
    payroll = Payroll.query.get_or_404(payroll_id)
    payroll.archived = False
    db.session.commit()
    flash('Payroll unarchived.', 'success')
    return redirect(url_for('payroll_management'))

@app.route('/admin/payroll/<int:payroll_id>/edit', methods=['POST'])
@login_required
def edit_payroll(payroll_id):
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('payroll_management'))
    payroll = Payroll.query.get_or_404(payroll_id)
    try:
        bonuses = float(request.form.get('bonuses', 0) or 0)
        deductions = float(request.form.get('deductions', 0) or 0)
    except ValueError:
        flash('Invalid bonus or deduction amount.', 'danger')
        return redirect(url_for('payroll_management'))
    payroll.bonuses = bonuses
    payroll.deductions = deductions
    payroll.net_pay = payroll.gross_pay + bonuses - deductions
    db.session.commit()
    flash('Payroll updated.', 'success')
    return redirect(url_for('payroll_management'))

@app.route('/admin/payroll/<int:payroll_id>/pay', methods=['POST'])
@login_required
def pay_payroll(payroll_id):
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('payroll_management'))
    payroll = Payroll.query.get_or_404(payroll_id)
    payroll.status = 'paid'
    db.session.commit()
    flash('Payroll marked as paid.', 'success')
    return redirect(url_for('payroll_management'))

@app.route('/admin/payroll', methods=['GET', 'POST'])
@login_required
def payroll_management():
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    show_archived = request.args.get('show_archived', '0') == '1'
    if show_archived:
        payrolls = Payroll.query.order_by(Payroll.date_issued.desc()).filter_by(archived=True).all()
    else:
        payrolls = Payroll.query.order_by(Payroll.date_issued.desc()).filter_by(archived=False).all()
    if request.method == 'POST':
        # Get period from form
        period_start = request.form.get('period_start')
        period_end = request.form.get('period_end')
        if not period_start or not period_end:
            flash('Please select a valid pay period.', 'danger')
            return render_template('payroll_management.html', payrolls=payrolls, show_archived=show_archived)
        period_start = datetime.strptime(period_start, '%Y-%m-%d').date()
        period_end = datetime.strptime(period_end, '%Y-%m-%d').date()
        staff_list = User.query.filter_by(is_staff=True, staff_status='active').all()
        for staff in staff_list:
            # Set hourly and overtime rates based on staff_role
            if staff.staff_role == 'Front Desk':
                hourly_rate = 100.0
                overtime_rate = 100.0 * 1.25
            elif staff.staff_role == 'Bell Boy':
                hourly_rate = 90.0
                overtime_rate = 90.0 * 1.25
            elif staff.staff_role == 'Housekeeping':
                hourly_rate = 89.375
                overtime_rate = 89.375 * 1.25
            else:
                hourly_rate = staff.hourly_rate or 0.0
                overtime_rate = staff.overtime_rate or hourly_rate
            # Prevent duplicate payrolls
            existing = Payroll.query.filter_by(
                staff_id=staff.id,
                period_start=period_start,
                period_end=period_end
            ).first()
            if existing:
                continue
            # Get attendance for this staff in the period
            attendances = Attendance.query.filter_by(user_id=staff.id, approved=True).filter(
                Attendance.date >= period_start, Attendance.date <= period_end
            ).all()
            total_hours = 0.0
            overtime_hours = 0.0
            for att in attendances:
                if att.clock_in and att.clock_out:
                    in_dt = datetime.combine(att.date, att.clock_in)
                    out_dt = datetime.combine(att.date, att.clock_out)
                    hours = (out_dt - in_dt).total_seconds() / 3600.0
                    # Overtime: hours above 8 per day
                    overtime = max(0, hours - 8)
                    overtime_hours += overtime
                    total_hours += hours
            # Calculate pay
            if staff.salary_type == 'fixed':
                gross_pay = staff.base_salary
            else:
                base_hours = total_hours - overtime_hours
                gross_pay = (base_hours * hourly_rate) + (overtime_hours * overtime_rate)
            # Deductions/Bonuses (manual for now)
            deductions = 0.0
            bonuses = 0.0
            net_pay = gross_pay + bonuses - deductions
            # Create payroll record
            payroll = Payroll(
                staff_id=staff.id,
                period_start=period_start,
                period_end=period_end,
                total_hours=total_hours,
                overtime_hours=overtime_hours,
                gross_pay=gross_pay,
                deductions=deductions,
                bonuses=bonuses,
                net_pay=net_pay,
                date_issued=datetime.utcnow(),
                status='pending'
            )
            db.session.add(payroll)
        db.session.commit()
        flash('Payroll generated for all staff for the selected period.', 'success')
        return redirect(url_for('payroll_management'))
    return render_template('payroll_management.html', payrolls=payrolls, show_archived=show_archived)

@app.route('/admin/fix_staff_salary_type')
@login_required
def fix_staff_salary_type():
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    updated = 0
    for staff in User.query.filter_by(is_staff=True).all():
        staff.salary_type = 'hourly'
        updated += 1
    db.session.commit()
    flash(f'Set salary_type="hourly" for {updated} staff.', 'success')
    return redirect(url_for('payroll_management'))

@app.route('/admin/fix_staff_roles_and_salary', methods=['POST', 'GET'])
@login_required
def fix_staff_roles_and_salary():
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    updated = 0
    valid_roles = ['Front Desk', 'Bell Boy', 'Housekeeping']
    for staff in User.query.filter_by(is_staff=True).all():
        staff.salary_type = 'hourly'
        if staff.staff_role not in valid_roles:
            staff.staff_role = 'Front Desk'  # Default/fallback role
        updated += 1
    db.session.commit()
    flash(f'Set salary_type="hourly" and fixed staff_role for {updated} staff.', 'success')
    return redirect(url_for('payroll_management'))

@app.route('/admin/rooms', methods=['GET', 'POST'])
@login_required
def admin_rooms():
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('admin_dashboard'))
    rooms = Room.query.all()
    if request.method == 'POST':
        room_id = request.form.get('room_id')
        room = Room.query.get(room_id)
        if room:
            room.name = request.form.get('name')
            room.description = request.form.get('description')
            room.price_per_night = float(request.form.get('price_per_night'))
            room.capacity = int(request.form.get('capacity'))
            # Optionally handle image update here
            db.session.commit()
            flash('Room updated successfully!', 'success')
        return redirect(url_for('admin_rooms'))
    return render_template('admin_rooms.html', rooms=rooms)

@app.route('/admin/amenities', methods=['GET', 'POST'])
@login_required
def admin_amenities():
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('admin_dashboard'))
    amenities = Amenity.query.all()
    if request.method == 'POST':
        amenity_id = request.form.get('amenity_id')
        amenity = Amenity.query.get(amenity_id)
        if amenity:
            amenity.name = request.form.get('name')
            amenity.description = request.form.get('description')
            amenity.price = float(request.form.get('price'))
            db.session.commit()
            flash('Amenity updated successfully!', 'success')
        return redirect(url_for('admin_amenities'))
    return render_template('admin_amenities.html', amenities=amenities)

@app.route('/admin/users')
@login_required
def user_list():
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('dashboard'))
    users = User.query.filter_by(is_admin=False, is_staff=False).all()
    return render_template('user_list.html', users=users)

@app.route('/walkin_booking', methods=['GET', 'POST'])
@login_required
# You may want to add a role check for front desk staff here
def walkin_booking():
    from datetime import datetime, date
    import os
    import secrets
    import smtplib
    from email.mime.text import MIMEText
    rooms = Room.query.all()
    available_rooms = []
    guest = None
    receipt = None
    error = None
    if request.method == 'POST':
        # Get form data
        check_in = request.form.get('check_in')
        check_out = request.form.get('check_out')
        room_id = request.form.get('room_id')
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        id_proof_file = request.files.get('id_proof')
        id_proof_path = None
        if id_proof_file and id_proof_file.filename:
            filename = f"{name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{id_proof_file.filename}"
            upload_folder = os.path.join('static', 'uploads', 'ids')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, filename)
            id_proof_file.save(file_path)
            id_proof_path = f'/static/uploads/ids/{filename}'
        # Validate dates and room
        if not (check_in and check_out and room_id and name and phone and email and id_proof_path):
            error = 'All fields are required.'
        else:
            # Check room availability
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
            room = Room.query.get(room_id)
            if not room:
                error = 'Room not found.'
            else:
                # Check for overlapping bookings
                overlapping = Booking.query.filter(
                    Booking.room_id == room_id,
                    Booking.status != 'cancelled',
                    Booking.check_out_date > check_in_date,
                    Booking.check_in_date < check_out_date
                ).first()
                if overlapping:
                    error = 'Room is not available for the selected dates.'
                else:
                    # Create guest (if not exists)
                    guest = User.query.filter_by(email=email).first()
                    if not guest:
                        # Generate a unique username
                        base_username = name.replace(' ', '').lower() if name else "temp"
                        username = base_username
                        counter = 1
                        username_exists = User.query.filter_by(username=username).first()
                        if username_exists:
                            flash('Username has already exist', 'danger')
                            return render_template('walkin_booking.html', rooms=rooms, available_rooms=available_rooms, error='Username has already exist', now=date.today())
                        guest = User(username=username, email=email, phone_number=phone)
                        random_password = secrets.token_urlsafe(10)
                        verification_code = str(random.randint(100000, 999999))
                        guest.set_password(random_password)
                        db.session.add(guest)
                        db.session.commit()
                        # Send email with password and verification code
                        try:
                            msg = MIMEText(f'''
Welcome to Easy Hotel!

Your walk-in account has been created.

Login Email: {email}
Password: {random_password}

Please use these credentials to log in and verify your account.

Best regards,\nEasy Hotel Team
''')
                            msg['Subject'] = 'Easy Hotel - Walk-in Account Details'
                            msg['From'] = 'no-reply@easyhotel.com'
                            msg['To'] = email
                            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                                server.starttls()
                                server.login('hoteleasy244@gmail.com', 'jler dwhq hzms pzom')
                                server.sendmail('no-reply@easyhotel.com', [email], msg.as_string())
                        except Exception as e:
                            print(f"Email error: {str(e)}")
                    # Create booking
                    booking = Booking(
                        user_id=guest.id,
                        room_id=room_id,
                        check_in_date=check_in_date,
                        check_out_date=check_out_date,
                        guests=1,
                        status='confirmed',
                        total_price=room.price_per_night * (check_out_date - check_in_date).days
                    )
                    db.session.add(booking)
                    # Set room status to Occupied
                    room.status = 'Occupied'
                    db.session.commit()
                    return redirect(url_for('walkin_receipt', booking_id=booking.id))
    # For GET or error, show available rooms for selected dates
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    if check_in and check_out:
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        for room in rooms:
            overlapping = Booking.query.filter(
                Booking.room_id == room.id,
                Booking.status != 'cancelled',
                Booking.check_out_date > check_in_date,
                Booking.check_in_date < check_out_date
            ).first()
            if not overlapping:
                available_rooms.append(room)
    return render_template('walkin_booking.html', rooms=rooms, available_rooms=available_rooms, error=error, now=date.today())

@app.route('/walkin_receipt/<int:booking_id>')
@login_required
def walkin_receipt(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    return render_template('walkin_receipt.html', booking=booking)

@app.route('/api/available_rooms')
def api_available_rooms():
    from datetime import datetime
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    if not check_in or not check_out:
        return jsonify({'success': False, 'rooms': []})
    check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
    check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
    rooms = Room.query.all()
    available_rooms = []
    for room in rooms:
        overlapping = Booking.query.filter(
            Booking.room_id == room.id,
            Booking.status != 'cancelled',
            Booking.check_out_date > check_in_date,
            Booking.check_in_date < check_out_date
        ).first()
        if not overlapping:
            available_rooms.append({
                'id': room.id,
                'name': room.name,
                'price_per_night': room.price_per_night
            })
    return jsonify({'success': True, 'rooms': available_rooms})

@app.route('/admin/pos', methods=['GET', 'POST'])
@login_required
def admin_pos():
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    from datetime import datetime, date
    from sqlalchemy import extract
    today = date.today()
    month = today.month
    year = today.year
    monthly_bookings = Booking.query.filter(
        extract('month', Booking.created_at) == month,
        extract('year', Booking.created_at) == year,
        Booking.status == 'confirmed'
    ).all()
    total_monthly_income = sum(b.total_price for b in monthly_bookings)
    sales_per_day = {}
    for booking in monthly_bookings:
        day = booking.created_at.strftime('%Y-%m-%d')
        sales_per_day.setdefault(day, 0)
        sales_per_day[day] += booking.total_price
    bills = 0
    salary_distribution = 0
    sales_result = None
    selected_day = None
    day_sales = 0
    if request.method == 'POST':
        try:
            bills = float(request.form.get('bills', 0))
            salary_distribution = float(request.form.get('salary_distribution', 0))
            selected_day = request.form.get('selected_day')
            day_sales = sales_per_day.get(selected_day, 0)
            sales_result = day_sales - bills - salary_distribution
        except Exception as e:
            flash('Invalid input for POS calculation.', 'danger')
    return render_template('admin_pos.html',
        total_monthly_income=total_monthly_income,
        sales_per_day=sales_per_day,
        bills=bills,
        salary_distribution=salary_distribution,
        sales_result=sales_result,
        selected_day=selected_day,
        day_sales=day_sales
    )
