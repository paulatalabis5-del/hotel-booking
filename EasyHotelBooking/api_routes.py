from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
import jwt
from datetime import datetime, timedelta
from models import (User, Room, Booking, Amenity, BookingAmenity, Rating, Notification, Payment,
                   CheckInOut, RoomStatus, CleaningTask, SecurityPatrol, SecurityIncident, 
                   WorkOrder, Equipment, EquipmentMaintenance, DailyReport, StaffPerformance, Attendance)
from extensions import db
import smtplib
from email.mime.text import MIMEText
import random
import os
from payment_service import gcash_service

# Create API blueprint
api_bp = Blueprint('unique_api_blueprint_xyz789', __name__, url_prefix='/api')

# JWT Secret Key (should be in environment variables in production)
JWT_SECRET_KEY = 'your-secret-key-here'
JWT_ALGORITHM = 'HS256'

# Email configuration
EMAIL_SERVER = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USERNAME = 'hoteleasy244@gmail.com'
EMAIL_PASSWORD = 'jler dwhq hzms pzom'
EMAIL_FROM = 'no-reply@easyhotel.com'

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            current_user_id = data['user_id']
        except:
            return jsonify({'message': 'Token is invalid'}), 401
        
        return f(current_user_id, *args, **kwargs)
    return decorated

def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def send_verification_email(email, verification_code):
    """Send verification email to user"""
    try:
        print(f"📧 Attempting to send verification email to: {email}")
        print(f"📧 Using SMTP server: {EMAIL_SERVER}:{EMAIL_PORT}")
        print(f"📧 Verification code: {verification_code}")
        
        msg = MIMEText(f'''
        Welcome to Easy Hotel!
        
        Your verification code is: {verification_code}
        
        Please enter this code to complete your registration.
        
        If you did not request this registration, please ignore this email.
        
        Best regards,
        Easy Hotel Team
        ''')
        msg['Subject'] = 'Easy Hotel - Email Verification'
        msg['From'] = EMAIL_FROM
        msg['To'] = email
        
        with smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT) as server:
            server.starttls()
            print(f"📧 TLS started successfully")
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            print(f"📧 Login successful")
            server.sendmail(EMAIL_FROM, [email], msg.as_string())
            print(f"✅ Email sent successfully to {email}")
        
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ SMTP Authentication Error: {str(e)}")
        print(f"❌ Check if 2FA is enabled and App Password is correct")
        return False
    except smtplib.SMTPException as e:
        print(f"❌ SMTP Error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Email error: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        return False

# Authentication Routes
@api_bp.route('/auth/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required'}), 400
    
    user = User.query.filter_by(email=email).first()
    
    if user and user.check_password(password):
        token = generate_token(user.id)
        return jsonify({
            'success': True,
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin,
                'is_staff': user.is_staff,
                'staff_role': user.staff_role
            }
        })
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@api_bp.route('/auth/register', methods=['POST'])
def api_register():
    data = request.get_json()
    
    # Validation
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    phone_number = data.get('phone_number')
    verification_code = data.get('verification_code')
    
    if not all([username, email, password, confirm_password, phone_number]):
        return jsonify({'success': False, 'message': 'All fields are required'}), 400
    
    if password != confirm_password:
        return jsonify({'success': False, 'message': 'Passwords do not match'}), 400
    
    # If verification code is provided, verify it
    if verification_code:
        # Check if verification code is valid
        pending_user = User.query.filter_by(email=email, is_verified=False).first()
        if not pending_user or pending_user.verification_code != verification_code:
            return jsonify({'success': False, 'message': 'Invalid verification code'}), 400
        
        # Verify the user
        pending_user.is_verified = True
        pending_user.verification_code = None
        db.session.commit()
        
        # Generate token and return success
        token = generate_token(pending_user.id)
        return jsonify({
            'success': True, 
            'message': 'Registration successful',
            'token': token,
            'user': {
                'id': pending_user.id,
                'username': pending_user.username,
                'email': pending_user.email,
                'is_admin': pending_user.is_admin,
                'is_staff': pending_user.is_staff,
                'staff_role': pending_user.staff_role
            }
        })
    
    # Check if user already exists (only for new registrations)
    if User.query.filter((User.email == email) | (User.username == username)).first():
        return jsonify({'success': False, 'message': 'User already exists'}), 400
    
    # Generate verification code
    verification_code = str(random.randint(100000, 999999))
    
    # Create user with verification pending
    new_user = User(
        username=username,
        email=email,
        phone_number=phone_number,
        is_verified=False,
        verification_code=verification_code
    )
    new_user.set_password(password)
    
    db.session.add(new_user)
    db.session.commit()
    
    # Send verification email
    email_sent = send_verification_email(email, verification_code)
    
    if email_sent:
        return jsonify({
            'success': True, 
            'message': 'Verification code sent to your email. Please check your inbox.',
            'requires_verification': True
        })
    else:
        # If email fails, delete the user and return error
        # This ensures proper verification is enforced
        db.session.delete(new_user)
        db.session.commit()
        
        return jsonify({
            'success': False, 
            'message': 'Failed to send verification email. Please try again or contact support.',
        }), 500

@api_bp.route('/auth/forgot-password', methods=['POST'])
def api_forgot_password():
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'success': False, 'message': 'Email is required'}), 400
    
    # Check if user exists
    user = User.query.filter_by(email=email).first()
    if not user:
        # Don't reveal if email exists or not for security
        return jsonify({
            'success': True, 
            'message': 'If an account with this email exists, password reset instructions have been sent.'
        })
    
    # Generate reset code
    reset_code = str(random.randint(100000, 999999))
    
    # Store reset code (in a real app, you'd want to store this with expiration)
    user.verification_code = reset_code
    db.session.commit()
    
    # Send reset email
    if send_password_reset_email(email, reset_code):
        return jsonify({
            'success': True, 
            'message': 'If an account with this email exists, password reset instructions have been sent.'
        })
    else:
        return jsonify({'success': False, 'message': 'Failed to send reset email. Please try again.'}), 500

def send_password_reset_email(email, reset_code):
    """Send password reset email to user"""
    try:
        msg = MIMEText(f'''
        Easy Hotel - Password Reset
        
        You have requested to reset your password.
        
        Your password reset code is: {reset_code}
        
        Please use this code to reset your password. This code will expire in 1 hour.
        
        If you did not request this password reset, please ignore this email and your password will remain unchanged.
        
        Best regards,
        Easy Hotel Team
        ''')
        msg['Subject'] = 'Easy Hotel - Password Reset'
        msg['From'] = EMAIL_FROM
        msg['To'] = email
        
        with smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, [email], msg.as_string())
        
        return True
    except Exception as e:
        print(f"Email error: {str(e)}")
        return False

def send_staff_verification_email(email, username, verification_code, password):
    """Send verification email to new staff member"""
    try:
        msg = MIMEText(f'''
        Welcome to Easy Hotel Staff Team!
        
        Dear {username},
        
        Your staff account has been created successfully. To complete your registration, please verify your email address.
        
        Your verification code is: {verification_code}
        
        Please provide this code to your administrator to activate your account.
        
        Your login credentials (after verification):
        Email: {email}
        Password: {password}
        
        Please keep this information secure and do not share it with anyone.
        
        If you have any questions, please contact your administrator.
        
        Best regards,
        Easy Hotel Management Team
        ''')
        msg['Subject'] = 'Easy Hotel - Staff Account Verification'
        msg['From'] = EMAIL_FROM
        msg['To'] = email
        
        with smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, [email], msg.as_string())
        
        return True
    except Exception as e:
        print(f"Email error: {str(e)}")
        return False

@api_bp.route('/auth/reset-password', methods=['POST'])
def api_reset_password():
    data = request.get_json()
    email = data.get('email')
    reset_code = data.get('reset_code')
    new_password = data.get('new_password')
    
    if not all([email, reset_code, new_password]):
        return jsonify({'success': False, 'message': 'All fields are required'}), 400
    
    # Find user with matching email and reset code
    user = User.query.filter_by(email=email, verification_code=reset_code).first()
    if not user:
        return jsonify({'success': False, 'message': 'Invalid reset code or email'}), 400
    
    # Update password and clear reset code
    user.set_password(new_password)
    user.verification_code = None
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': 'Password reset successfully'
    })

# User Routes
@api_bp.route('/user/profile', methods=['GET'])
@token_required
def get_user_profile(current_user_id):
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    return jsonify({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'phone_number': user.phone_number,
            'is_admin': user.is_admin,
            'is_staff': user.is_staff,
            'staff_role': user.staff_role,
            'staff_status': user.staff_status,
            'staff_shift': user.staff_shift,
            'created_at': user.created_at.isoformat()
        }
    })

@api_bp.route('/user/profile', methods=['PUT'])
@token_required
def update_user_profile(current_user_id):
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    data = request.get_json()
    
    # Update fields
    if 'username' in data:
        user.username = data['username']
    if 'email' in data:
        user.email = data['email']
    if 'phone_number' in data:
        user.phone_number = data['phone_number']
    
    # Handle password change
    if 'new_password' in data and 'current_password' in data:
        if user.check_password(data['current_password']):
            user.set_password(data['new_password'])
        else:
            return jsonify({'message': 'Current password is incorrect'}), 400
    
    db.session.commit()
    
    return jsonify({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'phone_number': user.phone_number,
            'is_admin': user.is_admin,
            'is_staff': user.is_staff,
            'staff_role': user.staff_role,
            'staff_status': user.staff_status,
            'staff_shift': user.staff_shift,
            'created_at': user.created_at.isoformat()
        }
    })

# Room Routes
@api_bp.route('/rooms', methods=['GET'])
def get_rooms():
    from models import RoomSize, FloorPlan
    
    rooms = Room.query.all()
    rooms_data = []
    
    for room in rooms:
        # Get related data
        room_size = RoomSize.query.get(room.room_size_id) if room.room_size_id else None
        floor_plan = FloorPlan.query.get(room.floor_id) if room.floor_id else None
        
        room_dict = {
            'id': room.id,
            'room_number': room.room_number,
            'room_type_id': room.room_size_id,
            'room_type_name': room_size.room_type_name if room_size else 'Unknown',
            'floor_plan_id': room.floor_id,
            'floor_name': floor_plan.floor_name if floor_plan else 'Unknown',
            'price_per_night': room.price_per_night,
            'max_adults': room_size.max_adults if room_size else 0,
            'max_children': room_size.max_children if room_size else 0,
            'status': room.status,
            'image_url': room.image_url or ''
        }
        rooms_data.append(room_dict)
    
    return jsonify(rooms_data)

@api_bp.route('/admin/rooms', methods=['POST'])
@token_required
def create_room(current_user_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    # Get JSON data from request
    data = request.get_json()
    
    # Extract required fields
    room_number = data.get('room_number')
    room_type_id = data.get('room_type_id') or data.get('room_size_id')
    floor_plan_id = data.get('floor_plan_id') or data.get('floor_id')
    price_per_night = data.get('price_per_night')
    status = data.get('status', 'available')
    image_url = data.get('image_url', '')
    
    # Validate required fields
    if not all([room_number, room_type_id, floor_plan_id, price_per_night]):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    
    # Check if room number already exists
    existing_room = Room.query.filter_by(room_number=room_number).first()
    if existing_room:
        return jsonify({'success': False, 'message': f'Room number {room_number} already exists'}), 400
    
    try:
        price_per_night = float(price_per_night)
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid price format'}), 400
    
    # Create room with new schema
    new_room = Room(
        room_number=room_number,
        room_size_id=room_type_id,
        floor_id=floor_plan_id,
        price_per_night=price_per_night,
        status=status,
        image_url=image_url
    )
    
    db.session.add(new_room)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Room created successfully',
        'room': {
            'id': new_room.id,
            'room_number': new_room.room_number,
            'price_per_night': new_room.price_per_night,
            'status': new_room.status
        }
    })

@api_bp.route('/admin/rooms/<int:room_id>', methods=['PUT'])
@token_required
def update_room(current_user_id, room_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'success': False, 'message': 'Room not found'}), 404
    
    # Get JSON data from request
    data = request.get_json()
    
    # Update fields if provided
    if 'room_number' in data:
        # Check if new room number already exists (excluding current room)
        existing_room = Room.query.filter_by(room_number=data['room_number']).filter(Room.id != room_id).first()
        if existing_room:
            return jsonify({'success': False, 'message': f'Room number {data["room_number"]} already exists'}), 400
        room.room_number = data['room_number']
    
    if 'room_type_id' in data or 'room_size_id' in data:
        room.room_size_id = data.get('room_type_id') or data.get('room_size_id')
    
    if 'floor_plan_id' in data or 'floor_id' in data:
        room.floor_id = data.get('floor_plan_id') or data.get('floor_id')
    
    if 'price_per_night' in data:
        try:
            room.price_per_night = float(data['price_per_night'])
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid price format'}), 400
    
    if 'status' in data:
        room.status = data['status']
    
    if 'image_url' in data:
        room.image_url = data['image_url']
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Room updated successfully',
        'room': {
            'id': room.id,
            'room_number': room.room_number,
            'price_per_night': room.price_per_night,
            'status': room.status
        }
    })

@api_bp.route('/admin/rooms/<int:room_id>', methods=['DELETE'])
@token_required
def delete_room(current_user_id, room_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'success': False, 'message': 'Room not found'}), 404
    
    # Check if room has active bookings
    active_bookings = Booking.query.filter_by(room_id=room_id).filter(
        Booking.status.in_(['pending', 'confirmed'])
    ).count()
    
    if active_bookings > 0:
        return jsonify({'success': False, 'message': 'Cannot delete room with active bookings'}), 400
    
    db.session.delete(room)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Room deleted successfully'
    })

@api_bp.route('/check_availability', methods=['GET'])
def check_availability():
    room_id = request.args.get('room_id')
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    
    if not all([room_id, check_in, check_out]):
        return jsonify({'available': False, 'message': 'Missing parameters'}), 400
    
    try:
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'available': False, 'message': 'Invalid date format'}), 400
    
    # Check for overlapping bookings
    existing_bookings = Booking.query.filter_by(room_id=room_id).filter(
        ((Booking.check_in_date <= check_in_date) & (Booking.check_out_date >= check_in_date)) |
        ((Booking.check_in_date <= check_out_date) & (Booking.check_out_date >= check_out_date)) |
        ((Booking.check_in_date >= check_in_date) & (Booking.check_out_date <= check_out_date))
    ).filter(Booking.status != 'cancelled').count()
    
    return jsonify({
        'available': existing_bookings == 0,
        'message': 'Room available' if existing_bookings == 0 else 'Room not available'
    })

# Booking Routes
@api_bp.route('/bookings', methods=['GET'])
@token_required
def get_bookings(current_user_id):
    bookings = Booking.query.filter_by(user_id=current_user_id).all()
    return jsonify({
        'bookings': [booking.to_dict() for booking in bookings]
    })

@api_bp.route('/bookings', methods=['POST'])
@token_required
def create_booking(current_user_id):
    data = request.get_json()
    
    room_id = data.get('room_id')
    check_in_date = datetime.strptime(data.get('check_in_date'), '%Y-%m-%d').date()
    check_out_date = datetime.strptime(data.get('check_out_date'), '%Y-%m-%d').date()
    guests = data.get('guests')
    amenities = data.get('amenities', [])
    
    # Get room
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'message': 'Room not found'}), 404
    
    # Check availability
    existing_bookings = Booking.query.filter_by(room_id=room_id).filter(
        ((Booking.check_in_date <= check_in_date) & (Booking.check_out_date >= check_in_date)) |
        ((Booking.check_in_date <= check_out_date) & (Booking.check_out_date >= check_out_date)) |
        ((Booking.check_in_date >= check_in_date) & (Booking.check_out_date <= check_out_date))
    ).filter(Booking.status != 'cancelled').count()
    
    if existing_bookings > 0:
        return jsonify({'message': 'Room not available for selected dates'}), 400
    
    # Calculate total price
    days = (check_out_date - check_in_date).days
    total_price = room.price_per_night * days
    
    # Add amenities cost
    for amenity_data in amenities:
        amenity = Amenity.query.get(amenity_data['id'])
        if amenity:
            total_price += amenity.price * amenity_data['quantity']
    
    # Create booking
    booking = Booking(
        user_id=current_user_id,
        room_id=room_id,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        guests=guests,
        total_price=total_price,
        status='pending'
    )
    
    db.session.add(booking)
    db.session.flush()
    
    # Add amenities
    for amenity_data in amenities:
        booking_amenity = BookingAmenity(
            booking_id=booking.id,
            amenity_id=amenity_data['id'],
            quantity=amenity_data['quantity']
        )
        db.session.add(booking_amenity)
    
    db.session.commit()
    
    return jsonify({
        'booking': booking.to_dict(),
        'message': 'Booking created successfully'
    })

@api_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@token_required
def cancel_booking(current_user_id, booking_id):
    booking = Booking.query.get(booking_id)
    if not booking or booking.user_id != current_user_id:
        return jsonify({'message': 'Booking not found'}), 404
    
    data = request.get_json()
    reason = data.get('reason')
    
    if not reason:
        return jsonify({'message': 'Cancellation reason is required'}), 400
    
    booking.status = 'cancelled'
    booking.cancellation_reason = reason
    booking.cancelled_by = 'user'
    
    db.session.commit()
    
    return jsonify({
        'booking': booking.to_dict(),
        'message': 'Booking cancelled successfully'
    })

# Admin Routes
@api_bp.route('/admin/bookings/pending', methods=['GET'])
@token_required
def get_pending_bookings(current_user_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    bookings = Booking.query.filter_by(status='pending').all()
    return jsonify({
        'bookings': [booking.to_dict() for booking in bookings]
    })

@api_bp.route('/admin/bookings/<int:booking_id>/verify', methods=['POST'])
@token_required
def verify_booking(current_user_id, booking_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'message': 'Booking not found'}), 404
    
    data = request.get_json()
    action = data.get('action')
    reason = data.get('reason')
    
    if action == 'confirm':
        booking.status = 'confirmed'
    elif action == 'cancel':
        booking.status = 'cancelled'
        booking.cancellation_reason = reason
        booking.cancelled_by = 'admin'
    else:
        return jsonify({'message': 'Invalid action'}), 400
    
    db.session.commit()
    
    return jsonify({
        'booking': booking.to_dict(),
        'message': f'Booking {action}ed successfully'
    })

# Staff Routes
@api_bp.route('/staff/attendance', methods=['POST'])
@token_required
def staff_attendance(current_user_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_staff:
        return jsonify({'message': 'Unauthorized'}), 403
    
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            verify_id = data.get('verify_id')
            action = data.get('action')
        else:
            verify_id = request.form.get('verify_id')
            action = request.form.get('action')
        
        if not verify_id or not action:
            return jsonify({'success': False, 'message': 'Missing verify_id or action'}), 400
        
        # Simple verification - in real app, you'd verify the ID
        if verify_id != str(user.id):
            return jsonify({'success': False, 'message': 'Invalid verification ID'}), 400
        
        from datetime import datetime, date
        from models import Attendance
        
        today = date.today()
        
        # Get or create attendance record for today
        attendance = Attendance.query.filter_by(
            user_id=current_user_id,
            date=today
        ).first()
        
        if not attendance:
            attendance = Attendance(
                user_id=current_user_id,
                date=today
            )
            db.session.add(attendance)
        
        if action == 'clock_in':
            if attendance.clock_in:
                return jsonify({'success': False, 'message': 'Already clocked in today'}), 400
            
            attendance.clock_in = datetime.now().time()
            message = 'Clocked in successfully'
            
        elif action == 'clock_out':
            if not attendance.clock_in:
                return jsonify({'success': False, 'message': 'Must clock in first'}), 400
            
            if attendance.clock_out:
                return jsonify({'success': False, 'message': 'Already clocked out today'}), 400
            
            attendance.clock_out = datetime.now().time()
            message = 'Clocked out successfully'
        
        else:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400
        
        # Handle image upload if present
        if 'id_image' in request.files:
            image_file = request.files['id_image']
            if image_file and image_file.filename:
                import os
                from werkzeug.utils import secure_filename
                
                filename = secure_filename(image_file.filename)
                timestamp = str(int(datetime.now().timestamp()))
                filename = f"{timestamp}_{filename}"
                
                upload_folder = os.path.join('static', 'uploads', 'attendance_ids')
                os.makedirs(upload_folder, exist_ok=True)
                
                file_path = os.path.join(upload_folder, filename)
                image_file.save(file_path)
                
                attendance.id_image = f"/static/uploads/attendance_ids/{filename}"
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message,
            'attendance': {
                'date': attendance.date.isoformat(),
                'clock_in': attendance.clock_in.isoformat() if attendance.clock_in else None,
                'clock_out': attendance.clock_out.isoformat() if attendance.clock_out else None,
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

# Admin Staff Management Routes
@api_bp.route('/admin/staff', methods=['GET'])
@token_required
def get_all_staff(current_user_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    staff_members = User.query.filter_by(is_staff=True).all()
    return jsonify({
        'staff': [staff.to_dict() for staff in staff_members]
    })

@api_bp.route('/admin/staff', methods=['POST'])
@token_required
def create_staff(current_user_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    # Validation
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    phone_number = data.get('phone_number')
    staff_role = data.get('staff_role')
    staff_shift = data.get('staff_shift')
    
    if not all([username, email, password, phone_number, staff_role]):
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Check if user already exists
    if User.query.filter((User.email == email) | (User.username == username)).first():
        return jsonify({'message': 'User already exists'}), 400
    
    # Generate verification code
    verification_code = str(random.randint(100000, 999999))
    
    # Create staff member with verification pending
    new_staff = User(
        username=username,
        email=email,
        phone_number=phone_number,
        is_staff=True,
        staff_role=staff_role,
        staff_shift=staff_shift,
        staff_status='active',
        is_verified=False,
        verification_code=verification_code
    )
    new_staff.set_password(password)
    
    db.session.add(new_staff)
    db.session.commit()
    
    # Send verification email
    if send_staff_verification_email(email, username, verification_code, password):
        return jsonify({
            'staff': new_staff.to_dict(),
            'message': 'Staff member created successfully. Verification email sent.',
            'requires_verification': True,
            'verification_code': verification_code  # For testing purposes
        })
    else:
        # If email fails, delete the staff and return error
        db.session.delete(new_staff)
        db.session.commit()
        return jsonify({'message': 'Failed to send verification email. Please try again.'}), 500

@api_bp.route('/admin/staff/<int:staff_id>', methods=['PUT'])
@token_required
def update_staff(current_user_id, staff_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    staff_member = User.query.get(staff_id)
    if not staff_member or not staff_member.is_staff:
        return jsonify({'message': 'Staff member not found'}), 404
    
    data = request.get_json()
    
    # Update fields
    if 'username' in data:
        staff_member.username = data['username']
    if 'email' in data:
        staff_member.email = data['email']
    if 'phone_number' in data:
        staff_member.phone_number = data['phone_number']
    if 'staff_role' in data:
        staff_member.staff_role = data['staff_role']
    if 'staff_shift' in data:
        staff_member.staff_shift = data['staff_shift']
    if 'staff_status' in data:
        staff_member.staff_status = data['staff_status']
    
    db.session.commit()
    
    return jsonify({
        'staff': staff_member.to_dict(),
        'message': 'Staff member updated successfully'
    })

@api_bp.route('/admin/staff/<int:staff_id>', methods=['DELETE'])
@token_required
def delete_staff(current_user_id, staff_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    staff_member = User.query.get(staff_id)
    if not staff_member or not staff_member.is_staff:
        return jsonify({'message': 'Staff member not found'}), 404
    
    db.session.delete(staff_member)
    db.session.commit()
    
    return jsonify({
        'message': 'Staff member deleted successfully'
    })

# Admin Attendance Management Routes
@api_bp.route('/admin/attendance', methods=['GET'])
@token_required
def get_all_attendance(current_user_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    try:
        from models import Attendance
        from datetime import datetime, timedelta
        
        # Get date range from query params
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        staff_id = request.args.get('staff_id')
        
        query = Attendance.query
        
        if staff_id:
            query = query.filter_by(user_id=staff_id)
        
        if start_date:
            query = query.filter(Attendance.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        
        if end_date:
            query = query.filter(Attendance.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
        else:
            # Default to last 30 days
            thirty_days_ago = datetime.now().date() - timedelta(days=30)
            query = query.filter(Attendance.date >= thirty_days_ago)
        
        attendance_records = query.order_by(Attendance.date.desc()).all()
        
        result = []
        for record in attendance_records:
            staff_user = User.query.get(record.user_id)
            result.append({
                'id': record.id,
                'staff_id': record.user_id,
                'staff_name': staff_user.username if staff_user else 'Unknown',
                'staff_role': staff_user.staff_role if staff_user else 'Unknown',
                'date': record.date.isoformat(),
                'clock_in': record.clock_in.isoformat() if record.clock_in else None,
                'clock_out': record.clock_out.isoformat() if record.clock_out else None,
                'hours_worked': _calculate_hours_worked(record.clock_in, record.clock_out),
                'approved': record.approved,
                'id_image': record.id_image
            })
        
        return jsonify({
            'attendance': result,
            'total_records': len(result)
        })
        
    except Exception as e:
        return jsonify({'message': f'Error fetching attendance: {str(e)}'}), 500

@api_bp.route('/admin/attendance/<int:attendance_id>/approve', methods=['POST'])
@token_required
def approve_attendance(current_user_id, attendance_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    try:
        from models import Attendance
        
        attendance = Attendance.query.get(attendance_id)
        if not attendance:
            return jsonify({'message': 'Attendance record not found'}), 404
        
        data = request.get_json()
        approved = data.get('approved', True)
        
        attendance.approved = approved
        attendance.verified_by_id = str(current_user_id)
        
        db.session.commit()
        
        return jsonify({
            'message': f'Attendance {"approved" if approved else "rejected"} successfully',
            'attendance': {
                'id': attendance.id,
                'approved': attendance.approved,
                'verified_by_id': attendance.verified_by_id
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error updating attendance: {str(e)}'}), 500

def _calculate_hours_worked(clock_in, clock_out):
    if not clock_in or not clock_out:
        return 0.0
    
    from datetime import datetime, timedelta
    
    # Convert time objects to datetime for calculation
    today = datetime.now().date()
    clock_in_dt = datetime.combine(today, clock_in)
    clock_out_dt = datetime.combine(today, clock_out)
    
    # Handle overnight shifts
    if clock_out_dt < clock_in_dt:
        clock_out_dt += timedelta(days=1)
    
    duration = clock_out_dt - clock_in_dt
    hours = duration.total_seconds() / 3600
    
    return round(hours, 2)

@api_bp.route('/admin/staff/<int:staff_id>/verify', methods=['POST'])
@token_required
def verify_staff(current_user_id, staff_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    verification_code = data.get('verification_code')
    
    if not verification_code:
        return jsonify({'message': 'Verification code is required'}), 400
    
    staff_member = User.query.get(staff_id)
    if not staff_member or not staff_member.is_staff:
        return jsonify({'message': 'Staff member not found'}), 404
    
    if staff_member.verification_code != verification_code:
        return jsonify({'message': 'Invalid verification code'}), 400
    
    # Verify the staff member
    staff_member.is_verified = True
    staff_member.verification_code = None
    db.session.commit()
    
    return jsonify({
        'staff': staff_member.to_dict(),
        'message': 'Staff member verified successfully'
    })

# Reports and Analytics Routes
@api_bp.route('/admin/reports/dashboard', methods=['GET'])
@token_required
def get_dashboard_reports(current_user_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    try:
        # Get date range (default to last 30 days)
        from datetime import datetime, timedelta
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        # Total bookings
        total_bookings = Booking.query.count()
        pending_bookings = Booking.query.filter_by(status='pending').count()
        confirmed_bookings = Booking.query.filter_by(status='confirmed').count()
        cancelled_bookings = Booking.query.filter_by(status='cancelled').count()
        
        # Revenue calculations
        confirmed_bookings_list = Booking.query.filter_by(status='confirmed').all()
        total_revenue = sum(booking.total_price for booking in confirmed_bookings_list)
        
        # Recent bookings revenue (last 30 days)
        recent_bookings = Booking.query.filter(
            Booking.status == 'confirmed',
            Booking.created_at >= start_date
        ).all()
        recent_revenue = sum(booking.total_price for booking in recent_bookings)
        
        # Room statistics
        total_rooms = Room.query.count()
        
        # Occupancy rate calculation
        occupied_rooms = Booking.query.filter(
            Booking.status.in_(['confirmed', 'pending']),
            Booking.check_in_date <= end_date,
            Booking.check_out_date >= start_date
        ).count()
        
        occupancy_rate = (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0
        
        # Staff statistics
        total_staff = User.query.filter_by(is_staff=True).count()
        active_staff = User.query.filter_by(is_staff=True, staff_status='active').count()
        
        # Guest statistics
        total_guests = User.query.filter_by(is_staff=False, is_admin=False).count()
        
        # Average booking value
        avg_booking_value = total_revenue / confirmed_bookings if confirmed_bookings > 0 else 0
        
        return jsonify({
            'dashboard_stats': {
                'total_bookings': total_bookings,
                'pending_bookings': pending_bookings,
                'confirmed_bookings': confirmed_bookings,
                'cancelled_bookings': cancelled_bookings,
                'total_revenue': total_revenue,
                'recent_revenue': recent_revenue,
                'total_rooms': total_rooms,
                'occupancy_rate': round(occupancy_rate, 2),
                'total_staff': total_staff,
                'active_staff': active_staff,
                'total_guests': total_guests,
                'avg_booking_value': round(avg_booking_value, 2)
            }
        })
    except Exception as e:
        return jsonify({'message': f'Error generating reports: {str(e)}'}), 500

@api_bp.route('/admin/reports/revenue', methods=['GET'])
@token_required
def get_revenue_report(current_user_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    try:
        from datetime import datetime, timedelta
        
        # Get last 12 months of revenue data
        monthly_revenue = []
        current_date = datetime.now().date()
        
        for i in range(12):
            month_start = current_date.replace(day=1) - timedelta(days=i*30)
            month_end = month_start + timedelta(days=30)
            
            month_bookings = Booking.query.filter(
                Booking.status == 'confirmed',
                Booking.created_at >= month_start,
                Booking.created_at < month_end
            ).all()
            
            month_revenue = sum(booking.total_price for booking in month_bookings)
            
            monthly_revenue.append({
                'month': month_start.strftime('%B %Y'),
                'revenue': month_revenue,
                'bookings_count': len(month_bookings)
            })
        
        # Room-wise revenue
        room_revenue = []
        rooms = Room.query.all()
        
        for room in rooms:
            room_bookings = Booking.query.filter_by(
                room_id=room.id,
                status='confirmed'
            ).all()
            
            room_total = sum(booking.total_price for booking in room_bookings)
            
            room_revenue.append({
                'room_name': room.name,
                'revenue': room_total,
                'bookings_count': len(room_bookings)
            })
        
        return jsonify({
            'monthly_revenue': monthly_revenue[::-1],  # Reverse to show oldest first
            'room_revenue': sorted(room_revenue, key=lambda x: x['revenue'], reverse=True)
        })
    except Exception as e:
        return jsonify({'message': f'Error generating revenue report: {str(e)}'}), 500

@api_bp.route('/admin/reports/occupancy', methods=['GET'])
@token_required
def get_occupancy_report(current_user_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    try:
        from datetime import datetime, timedelta
        
        # Get last 30 days occupancy data
        occupancy_data = []
        current_date = datetime.now().date()
        
        for i in range(30):
            date = current_date - timedelta(days=i)
            
            # Count occupied rooms for this date
            occupied = Booking.query.filter(
                Booking.status.in_(['confirmed', 'pending']),
                Booking.check_in_date <= date,
                Booking.check_out_date > date
            ).count()
            
            total_rooms = Room.query.count()
            occupancy_rate = (occupied / total_rooms * 100) if total_rooms > 0 else 0
            
            occupancy_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'occupied_rooms': occupied,
                'total_rooms': total_rooms,
                'occupancy_rate': round(occupancy_rate, 2)
            })
        
        return jsonify({
            'occupancy_data': occupancy_data[::-1]  # Reverse to show oldest first
        })
    except Exception as e:
        return jsonify({'message': f'Error generating occupancy report: {str(e)}'}), 500

@api_bp.route('/admin/reports/guests', methods=['GET'])
@token_required
def get_guest_analytics(current_user_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    try:
        # Guest registration trends
        from datetime import datetime, timedelta
        
        guest_trends = []
        current_date = datetime.now().date()
        
        for i in range(12):
            month_start = current_date.replace(day=1) - timedelta(days=i*30)
            month_end = month_start + timedelta(days=30)
            
            new_guests = User.query.filter(
                User.is_staff == False,
                User.is_admin == False,
                User.created_at >= month_start,
                User.created_at < month_end
            ).count()
            
            guest_trends.append({
                'month': month_start.strftime('%B %Y'),
                'new_guests': new_guests
            })
        
        # Top guests by bookings
        top_guests = []
        guests = User.query.filter_by(is_staff=False, is_admin=False).all()
        
        for guest in guests:
            booking_count = Booking.query.filter_by(user_id=guest.id).count()
            total_spent = sum(
                booking.total_price 
                for booking in Booking.query.filter_by(user_id=guest.id, status='confirmed').all()
            )
            
            if booking_count > 0:
                top_guests.append({
                    'guest_name': guest.username,
                    'email': guest.email,
                    'total_bookings': booking_count,
                    'total_spent': total_spent
                })
        
        # Sort by total spent
        top_guests = sorted(top_guests, key=lambda x: x['total_spent'], reverse=True)[:10]
        
        return jsonify({
            'guest_trends': guest_trends[::-1],
            'top_guests': top_guests
        })
    except Exception as e:
        return jsonify({'message': f'Error generating guest analytics: {str(e)}'}), 500

# Notification Routes
@api_bp.route('/notifications', methods=['GET'])
@token_required
def get_notifications(current_user_id):
    notifications = Notification.query.filter_by(user_id=current_user_id).all()
    return jsonify({
        'notifications': [notification.to_dict() for notification in notifications]
    })

@api_bp.route('/notifications/mark-all-read', methods=['POST'])
@token_required
def mark_notifications_read(current_user_id):
    notifications = Notification.query.filter_by(user_id=current_user_id, is_read=False).all()
    for notification in notifications:
        notification.is_read = True
    db.session.commit()
    
    return jsonify({'success': True})

# Payment Routes
@api_bp.route('/payment/methods', methods=['GET'])
def get_payment_methods():
    """Get available payment methods"""
    try:
        from models import PaymentMethod
        
        methods = PaymentMethod.query.filter_by(is_active=True).all()
        
        payment_methods = []
        for method in methods:
            payment_methods.append({
                'id': method.id,
                'name': method.name,
                'code': method.code,
                'is_online': method.is_online,
                'description': method.description,
                'icon_url': method.icon_url
            })
        
        return jsonify({
            'payment_methods': payment_methods
        })
        
    except Exception as e:
        return jsonify({'message': f'Error fetching payment methods: {str(e)}'}), 500

@api_bp.route('/payment/gcash/create', methods=['POST'])
@token_required
def create_gcash_payment(current_user_id):
    """Create GCash payment for booking"""
    try:
        data = request.get_json()
        booking_id = data.get('booking_id')
        phone_number = data.get('phone_number')
        
        if not booking_id or not phone_number:
            return jsonify({'success': False, 'message': 'Missing booking_id or phone_number'}), 400
        
        # Verify booking belongs to user
        booking = Booking.query.filter_by(id=booking_id, user_id=current_user_id).first()
        if not booking:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404
        
        # Check if booking is already paid
        existing_payment = Payment.query.filter_by(
            booking_id=booking_id, 
            payment_status='completed'
        ).first()
        
        if existing_payment:
            return jsonify({'success': False, 'message': 'Booking already paid'}), 400
        
        # Create GCash payment
        result = gcash_service.create_gcash_payment_intent(
            booking_id=booking_id,
            amount=booking.total_price,
            user_phone=phone_number
        )
        
        if result['success']:
            # Also create payment source for redirect
            source_result = gcash_service.create_gcash_source(
                payment_intent_id=result['payment_intent_id'],
                amount=booking.total_price,
                user_phone=phone_number
            )
            
            if source_result['success']:
                return jsonify({
                    'success': True,
                    'payment_id': result['payment_id'],
                    'payment_intent_id': result['payment_intent_id'],
                    'client_key': result['client_key'],
                    'redirect_url': source_result['redirect_url'],
                    'amount': booking.total_price
                })
            else:
                return jsonify(source_result), 400
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@api_bp.route('/payment/<int:payment_id>/verify', methods=['POST'])
@token_required
def verify_payment(current_user_id, payment_id):
    """Verify payment status"""
    try:
        # Verify payment belongs to user
        payment = Payment.query.filter_by(id=payment_id).first()
        if not payment or payment.user_id != current_user_id:
            return jsonify({'success': False, 'message': 'Payment not found'}), 404
        
        result = gcash_service.verify_payment(payment_id)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@api_bp.route('/payment/success', methods=['GET'])
def payment_success():
    """Payment success callback"""
    return """
    <html>
    <head>
        <title>Payment Successful</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f5f5f5; }
            .success-card { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 400px; margin: 0 auto; }
            .success-icon { color: #4CAF50; font-size: 64px; margin-bottom: 20px; }
            .btn { background: #4CAF50; color: white; padding: 12px 24px; border: none; border-radius: 5px; text-decoration: none; display: inline-block; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="success-card">
            <div class="success-icon">✅</div>
            <h2>Payment Successful!</h2>
            <p>Your hotel booking payment has been processed successfully.</p>
            <p>You will receive a confirmation email shortly.</p>
            <a href="http://192.168.100.159:53024" class="btn">Return to Hotel App</a>
        </div>
        <script>
            // Auto redirect after 5 seconds
            setTimeout(() => {
                window.location.href = 'http://192.168.100.159:53024';
            }, 5000);
        </script>
    </body>
    </html>
    """

@api_bp.route('/payment/cash/create', methods=['POST'])
@token_required
def create_cash_payment(current_user_id):
    """Create cash payment for booking"""
    try:
        data = request.get_json()
        booking_id = data.get('booking_id')
        
        if not booking_id:
            return jsonify({'success': False, 'message': 'Missing booking_id'}), 400
        
        # Verify booking belongs to user
        booking = Booking.query.filter_by(id=booking_id, user_id=current_user_id).first()
        if not booking:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404
        
        # Create cash payment record
        from models import Payment
        payment = Payment(
            booking_id=booking_id,
            user_id=current_user_id,
            amount=booking.total_price,
            payment_method='cash',
            payment_status='pending'  # Will be completed at check-in
        )
        
        db.session.add(payment)
        
        # Update booking status to confirmed (cash payment)
        booking.status = 'confirmed'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Cash payment confirmed. Pay at check-in.',
            'payment_id': payment.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@api_bp.route('/payment/demo-gcash', methods=['GET'])
def demo_gcash_payment():
    """Demo GCash payment page for testing"""
    amount = request.args.get('amount', '0')
    phone = request.args.get('phone', '')
    intent_id = request.args.get('intent_id', '')
    
    return f"""
    <html>
    <head>
        <title>Demo GCash Payment</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }}
            .payment-card {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 400px; margin: 0 auto; }}
            .gcash-logo {{ color: #007bff; font-size: 32px; font-weight: bold; text-align: center; margin-bottom: 20px; }}
            .amount {{ font-size: 24px; font-weight: bold; color: #28a745; text-align: center; margin: 20px 0; }}
            .btn {{ background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; width: 100%; margin: 10px 0; font-size: 16px; }}
            .btn:hover {{ background: #0056b3; }}
            .btn-cancel {{ background: #dc3545; }}
            .btn-cancel:hover {{ background: #c82333; }}
            .info {{ background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="payment-card">
            <div class="gcash-logo">📱 GCash Demo</div>
            <div class="info">
                <strong>Demo Payment Mode</strong><br>
                This is a simulation of GCash payment for testing purposes.
            </div>
            <div class="amount">₱{amount}</div>
            <p><strong>Phone:</strong> {phone}</p>
            <p><strong>Merchant:</strong> Easy Hotel Booking</p>
            
            <button class="btn" onclick="simulateSuccess()">✅ Simulate Successful Payment</button>
            <button class="btn btn-cancel" onclick="simulateFailure()">❌ Simulate Failed Payment</button>
            
            <div class="info" style="margin-top: 20px; font-size: 14px;">
                <strong>Instructions:</strong><br>
                • Click "Simulate Successful Payment" to test successful payment flow<br>
                • Click "Simulate Failed Payment" to test error handling<br>
                • This will redirect back to your hotel app
            </div>
        </div>
        
        <script>
            function simulateSuccess() {{
                // Simulate payment processing delay
                document.querySelector('.payment-card').innerHTML = `
                    <div class="gcash-logo">📱 GCash Demo</div>
                    <div style="text-align: center; padding: 40px;">
                        <div style="font-size: 48px; color: #28a745;">✅</div>
                        <h3>Payment Successful!</h3>
                        <p>Redirecting back to hotel app...</p>
                    </div>
                `;
                
                setTimeout(() => {{
                    window.location.href = 'http://192.168.100.159:5000/api/payment/success';
                }}, 2000);
            }}
            
            function simulateFailure() {{
                document.querySelector('.payment-card').innerHTML = `
                    <div class="gcash-logo">📱 GCash Demo</div>
                    <div style="text-align: center; padding: 40px;">
                        <div style="font-size: 48px; color: #dc3545;">❌</div>
                        <h3>Payment Failed!</h3>
                        <p>Redirecting back to hotel app...</p>
                    </div>
                `;
                
                setTimeout(() => {{
                    window.location.href = 'http://192.168.100.159:5000/api/payment/failed';
                }}, 2000);
            }}
        </script>
    </body>
    </html>
    """

@api_bp.route('/payment/failed', methods=['GET'])
def payment_failed():
    """Payment failed callback"""
    return """
    <html>
    <head>
        <title>Payment Failed</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f5f5f5; }
            .error-card { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 400px; margin: 0 auto; }
            .error-icon { color: #f44336; font-size: 64px; margin-bottom: 20px; }
            .btn { background: #2196F3; color: white; padding: 12px 24px; border: none; border-radius: 5px; text-decoration: none; display: inline-block; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="error-card">
            <div class="error-icon">❌</div>
            <h2>Payment Failed</h2>
            <p>Your payment could not be processed at this time.</p>
            <p>Please try again or contact support if the problem persists.</p>
            <a href="http://192.168.100.159:53024" class="btn">Return to Hotel App</a>
        </div>
        <script>
            // Auto redirect after 10 seconds
            setTimeout(() => {
                window.location.href = 'http://192.168.100.159:53024';
            }, 10000);
        </script>
    </body>
    </html>
    """

@api_bp.route('/admin/payments', methods=['GET'])
@token_required
def get_all_payments(current_user_id):
    """Get all payments (admin only)"""
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    try:
        from models import Payment
        
        payments = Payment.query.order_by(Payment.created_at.desc()).all()
        
        payment_list = []
        for payment in payments:
            payment_list.append({
                'id': payment.id,
                'booking_id': payment.booking_id,
                'user_id': payment.user_id,
                'amount': payment.amount,
                'payment_method': payment.payment_method,
                'payment_status': payment.payment_status,
                'gcash_phone_number': payment.gcash_phone_number,
                'created_at': payment.created_at.isoformat(),
                'paid_at': payment.paid_at.isoformat() if payment.paid_at else None,
                'user_name': payment.user.username if payment.user else 'Unknown',
                'booking_room': payment.booking.room.name if payment.booking and payment.booking.room else 'Unknown'
            })
        
        return jsonify({
            'payments': payment_list,
            'total_payments': len(payment_list)
        })
        
    except Exception as e:
        return jsonify({'message': f'Error fetching payments: {str(e)}'}), 500

# Role-Based Feature API Routes

# 1. Front Desk Operations
@api_bp.route('/staff/checkin/<int:booking_id>', methods=['POST'])
@token_required
def process_checkin(current_user_id, booking_id):
    """Process guest check-in"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff or user.staff_role.lower() not in ['front desk manager', 'receptionist']:
            return jsonify({'message': 'Unauthorized'}), 403
        
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'message': 'Booking not found'}), 404
        
        data = request.get_json()
        
        # Create check-in record
        checkin = CheckInOut(
            booking_id=booking_id,
            staff_id=current_user_id,
            action_type='check_in',
            notes=data.get('notes', ''),
            room_condition=data.get('room_condition', 'good')
        )
        
        # Update booking status
        booking.status = 'checked_in'
        
        # Update room status
        room_status = RoomStatus.query.filter_by(room_id=booking.room_id).first()
        if room_status:
            room_status.status = 'occupied'
        
        db.session.add(checkin)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Guest checked in successfully',
            'checkin_id': checkin.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/staff/checkout/<int:booking_id>', methods=['POST'])
@token_required
def process_checkout(current_user_id, booking_id):
    """Process guest check-out"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff or user.staff_role.lower() not in ['front desk manager', 'receptionist']:
            return jsonify({'message': 'Unauthorized'}), 403
        
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'message': 'Booking not found'}), 404
        
        data = request.get_json()
        
        # Create check-out record
        checkout = CheckInOut(
            booking_id=booking_id,
            staff_id=current_user_id,
            action_type='check_out',
            notes=data.get('notes', ''),
            room_condition=data.get('room_condition', 'good')
        )
        
        # Update booking status
        booking.status = 'checked_out'
        
        # Update room status to dirty (needs cleaning)
        room_status = RoomStatus.query.filter_by(room_id=booking.room_id).first()
        if not room_status:
            room_status = RoomStatus(room_id=booking.room_id, status='dirty')
            db.session.add(room_status)
        else:
            room_status.status = 'dirty'
        
        db.session.add(checkout)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Guest checked out successfully',
            'checkout_id': checkout.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/staff/front-desk/bookings', methods=['GET'])
@token_required
def get_front_desk_bookings(current_user_id):
    """Get bookings for front desk operations"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff or user.staff_role.lower() not in ['front desk manager', 'receptionist']:
            return jsonify({'message': 'Unauthorized'}), 403
        
        # Get today's check-ins and check-outs
        today = datetime.now().date()
        
        checkins_today = Booking.query.filter(
            Booking.check_in_date == today,
            Booking.status.in_(['confirmed', 'pending'])
        ).all()
        
        checkouts_today = Booking.query.filter(
            Booking.check_out_date == today,
            Booking.status == 'checked_in'
        ).all()
        
        return jsonify({
            'checkins_today': [booking.to_dict() for booking in checkins_today],
            'checkouts_today': [booking.to_dict() for booking in checkouts_today]
        })
        
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# 2. Housekeeping Management
@api_bp.route('/staff/housekeeping/rooms', methods=['GET'])
@token_required
def get_housekeeping_rooms(current_user_id):
    """Get room status for housekeeping"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff or user.staff_role.lower() not in ['housekeeping supervisor', 'housekeeper']:
            return jsonify({'message': 'Unauthorized'}), 403
        
        rooms = Room.query.all()
        room_data = []
        
        for room in rooms:
            status = RoomStatus.query.filter_by(room_id=room.id).first()
            room_info = room.to_dict()
            room_info['status'] = status.status if status else 'clean'
            room_info['last_cleaned'] = status.last_cleaned.isoformat() if status and status.last_cleaned else None
            room_info['inspection_status'] = status.inspection_status if status else 'pending'
            room_data.append(room_info)
        
        return jsonify({'rooms': room_data})
        
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@api_bp.route('/staff/housekeeping/clean-room/<int:room_id>', methods=['POST'])
@token_required
def mark_room_cleaned(current_user_id, room_id):
    """Mark room as cleaned"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff or user.staff_role.lower() not in ['housekeeping supervisor', 'housekeeper']:
            return jsonify({'message': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        # Update or create room status
        room_status = RoomStatus.query.filter_by(room_id=room_id).first()
        if not room_status:
            room_status = RoomStatus(room_id=room_id)
            db.session.add(room_status)
        
        room_status.status = 'clean'
        room_status.last_cleaned = datetime.utcnow()
        room_status.cleaned_by = current_user_id
        room_status.notes = data.get('notes', '')
        room_status.inspection_status = 'pending'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Room marked as cleaned'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/staff/housekeeping/tasks', methods=['GET'])
@token_required
def get_cleaning_tasks(current_user_id):
    """Get cleaning tasks for staff member"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff or user.staff_role.lower() not in ['housekeeping supervisor', 'housekeeper']:
            return jsonify({'message': 'Unauthorized'}), 403
        
        tasks = CleaningTask.query.filter_by(assigned_to=current_user_id).filter(
            CleaningTask.status.in_(['pending', 'in_progress'])
        ).all()
        
        task_data = []
        for task in tasks:
            task_info = {
                'id': task.id,
                'room_name': task.room.name,
                'task_type': task.task_type,
                'priority': task.priority,
                'status': task.status,
                'scheduled_time': task.scheduled_time.isoformat(),
                'estimated_duration': task.estimated_duration,
                'notes': task.notes
            }
            task_data.append(task_info)
        
        return jsonify({'tasks': task_data})
        
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# 3. Security System
@api_bp.route('/staff/security/start-patrol', methods=['POST'])
@token_required
def start_security_patrol(current_user_id):
    """Start a security patrol"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff or user.staff_role.lower() != 'security guard':
            return jsonify({'message': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        patrol = SecurityPatrol(
            guard_id=current_user_id,
            patrol_route=data.get('patrol_route', 'general'),
            start_time=datetime.utcnow()
        )
        
        db.session.add(patrol)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'patrol_id': patrol.id,
            'message': 'Patrol started'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/staff/security/report-incident', methods=['POST'])
@token_required
def report_security_incident(current_user_id):
    """Report a security incident"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff:
            return jsonify({'message': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        incident = SecurityIncident(
            reported_by=current_user_id,
            incident_type=data.get('incident_type'),
            severity=data.get('severity'),
            location=data.get('location'),
            description=data.get('description'),
            incident_time=datetime.fromisoformat(data.get('incident_time', datetime.utcnow().isoformat()))
        )
        
        db.session.add(incident)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'incident_id': incident.id,
            'message': 'Incident reported successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# 4. Maintenance Module
@api_bp.route('/staff/maintenance/work-orders', methods=['GET'])
@token_required
def get_work_orders(current_user_id):
    """Get work orders for maintenance staff"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff or user.staff_role.lower() != 'maintenance':
            return jsonify({'message': 'Unauthorized'}), 403
        
        work_orders = WorkOrder.query.filter_by(assigned_to=current_user_id).filter(
            WorkOrder.status.in_(['assigned', 'in_progress'])
        ).all()
        
        order_data = []
        for order in work_orders:
            order_info = {
                'id': order.id,
                'title': order.title,
                'description': order.description,
                'room_name': order.room.name if order.room else None,
                'location': order.location,
                'category': order.category,
                'priority': order.priority,
                'status': order.status,
                'estimated_hours': order.estimated_hours,
                'scheduled_date': order.scheduled_date.isoformat() if order.scheduled_date else None
            }
            order_data.append(order_info)
        
        return jsonify({'work_orders': order_data})
        
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@api_bp.route('/staff/maintenance/work-order/<int:order_id>/update', methods=['POST'])
@token_required
def update_work_order(current_user_id, order_id):
    """Update work order status"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff or user.staff_role.lower() != 'maintenance':
            return jsonify({'message': 'Unauthorized'}), 403
        
        work_order = WorkOrder.query.get(order_id)
        if not work_order or work_order.assigned_to != current_user_id:
            return jsonify({'message': 'Work order not found'}), 404
        
        data = request.get_json()
        
        if 'status' in data:
            work_order.status = data['status']
            if data['status'] == 'in_progress' and not work_order.started_date:
                work_order.started_date = datetime.utcnow()
            elif data['status'] == 'completed':
                work_order.completed_date = datetime.utcnow()
        
        if 'actual_hours' in data:
            work_order.actual_hours = data['actual_hours']
        if 'actual_cost' in data:
            work_order.actual_cost = data['actual_cost']
        if 'notes' in data:
            work_order.notes = data['notes']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Work order updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# Staff Reservations Management
@api_bp.route('/staff/reservations/all', methods=['GET'])
@token_required
def get_all_reservations(current_user_id):
    """Get all reservations for staff management"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff:
            return jsonify({'message': 'Unauthorized'}), 403
        
        # Get all bookings with user and room information
        bookings = Booking.query.order_by(Booking.created_at.desc()).all()
        
        booking_data = []
        for booking in bookings:
            booking_info = booking.to_dict()
            booking_data.append(booking_info)
        
        return jsonify({
            'bookings': booking_data,
            'total_count': len(booking_data)
        })
        
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@api_bp.route('/staff/reservations/confirm/<int:booking_id>', methods=['POST'])
@token_required
def confirm_reservation(current_user_id, booking_id):
    """Confirm a pending reservation"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff:
            return jsonify({'message': 'Unauthorized'}), 403
        
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'message': 'Booking not found'}), 404
        
        if booking.status != 'pending':
            return jsonify({'message': 'Booking is not pending'}), 400
        
        booking.status = 'confirmed'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Reservation confirmed successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/staff/reservations/cancel/<int:booking_id>', methods=['POST'])
@token_required
def cancel_reservation(current_user_id, booking_id):
    """Cancel a reservation"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff:
            return jsonify({'message': 'Unauthorized'}), 403
        
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'message': 'Booking not found'}), 404
        
        data = request.get_json()
        reason = data.get('reason', 'Cancelled by staff')
        
        booking.status = 'cancelled'
        booking.cancellation_reason = reason
        booking.cancelled_by = 'staff'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Reservation cancelled successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# 5. Manager Dashboard
@api_bp.route('/staff/manager/overview', methods=['GET'])
@token_required
def get_manager_overview(current_user_id):
    """Get manager dashboard overview"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff or user.staff_role.lower() != 'manager':
            return jsonify({'message': 'Unauthorized'}), 403
        
        today = datetime.now().date()
        
        # Get today's statistics
        checkins_today = CheckInOut.query.filter(
            CheckInOut.action_type == 'check_in',
            db.func.date(CheckInOut.action_time) == today
        ).count()
        
        checkouts_today = CheckInOut.query.filter(
            CheckInOut.action_type == 'check_out',
            db.func.date(CheckInOut.action_time) == today
        ).count()
        
        open_work_orders = WorkOrder.query.filter(
            WorkOrder.status.in_(['open', 'assigned', 'in_progress'])
        ).count()
        
        security_incidents_today = SecurityIncident.query.filter(
            db.func.date(SecurityIncident.created_at) == today
        ).count()
        
        # Staff attendance today
        total_staff = User.query.filter_by(is_staff=True, staff_status='active').count()
        clocked_in_today = Attendance.query.filter(
            Attendance.date == today,
            Attendance.clock_in.isnot(None)
        ).count()
        
        attendance_rate = (clocked_in_today / total_staff * 100) if total_staff > 0 else 0
        
        return jsonify({
            'overview': {
                'checkins_today': checkins_today,
                'checkouts_today': checkouts_today,
                'open_work_orders': open_work_orders,
                'security_incidents_today': security_incidents_today,
                'staff_attendance_rate': round(attendance_rate, 1),
                'total_staff': total_staff,
                'clocked_in_staff': clocked_in_today
            }
        })
        
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# Helper method to add to_dict methods to models
def add_to_dict_methods():
    def user_to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'phone_number': self.phone_number,
            'is_admin': self.is_admin,
            'is_staff': self.is_staff,
            'staff_role': self.staff_role,
            'staff_status': self.staff_status,
            'staff_shift': self.staff_shift,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat()
        }
    
    def room_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price_per_night': self.price_per_night,
            'capacity': self.capacity,
            'image_url': self.image_url
        }
    
    def booking_to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'room_id': self.room_id,
            'check_in_date': self.check_in_date.isoformat(),
            'check_out_date': self.check_out_date.isoformat(),
            'guests': self.guests,
            'total_price': self.total_price,
            'status': self.status,
            'cancellation_reason': self.cancellation_reason,
            'cancelled_by': self.cancelled_by,
            'created_at': self.created_at.isoformat(),
            'room': self.room.to_dict() if self.room else None,
            'user': self.user.to_dict() if self.user else None
        }
    
    def notification_to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat()
        }
    
    # Add methods to models
    User.to_dict = user_to_dict
    Room.to_dict = room_to_dict
    Booking.to_dict = booking_to_dict
    Notification.to_dict = notification_to_dict

# Add to_dict methods
add_to_dict_methods()

# ============================================
# RFID CARD MANAGEMENT API ROUTES
# ============================================

@api_bp.route('/rfid/register', methods=['POST'])
@token_required
def register_rfid_card(current_user_id):
    """Register a new RFID card for a user"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'message': 'Unauthorized - Admin only'}), 403
        
        from models import RFIDCard
        data = request.get_json()
        
        card_uid = data.get('card_uid')
        target_user_id = data.get('user_id')
        card_type = data.get('card_type', 'staff_badge')  # staff_badge, room_key, access_card
        expiry_days = data.get('expiry_days', 365)
        
        if not card_uid or not target_user_id:
            return jsonify({'success': False, 'message': 'Missing card_uid or user_id'}), 400
        
        # Check if card already exists
        existing_card = RFIDCard.query.filter_by(card_uid=card_uid).first()
        if existing_card:
            return jsonify({'success': False, 'message': 'RFID card already registered'}), 400
        
        # Check if user exists
        target_user = User.query.get(target_user_id)
        if not target_user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Create new RFID card
        from datetime import timedelta
        new_card = RFIDCard(
            card_uid=card_uid,
            user_id=target_user_id,
            card_type=card_type,
            is_active=True,
            issued_date=datetime.utcnow(),
            expiry_date=datetime.utcnow() + timedelta(days=expiry_days),
            notes=data.get('notes', '')
        )
        
        db.session.add(new_card)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'RFID card registered successfully',
            'card': {
                'id': new_card.id,
                'card_uid': new_card.card_uid,
                'user_id': new_card.user_id,
                'user_name': target_user.username,
                'card_type': new_card.card_type,
                'issued_date': new_card.issued_date.isoformat(),
                'expiry_date': new_card.expiry_date.isoformat() if new_card.expiry_date else None
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@api_bp.route('/rfid/verify', methods=['POST'])
@token_required
def verify_rfid_card(current_user_id):
    """Verify RFID card and log access"""
    try:
        from models import RFIDCard, RFIDAccessLog
        data = request.get_json()
        
        card_uid = data.get('card_uid')
        access_type = data.get('access_type', 'attendance')  # attendance, room_access, checkpoint
        access_location = data.get('access_location', 'unknown')
        
        if not card_uid:
            return jsonify({'success': False, 'message': 'Missing card_uid'}), 400
        
        # Find RFID card
        rfid_card = RFIDCard.query.filter_by(card_uid=card_uid).first()
        
        if not rfid_card:
            # Log failed access attempt
            access_log = RFIDAccessLog(
                rfid_card_id=0,  # Unknown card
                user_id=current_user_id,
                access_type=access_type,
                access_location=access_location,
                access_granted=False,
                denial_reason='Card not registered'
            )
            db.session.add(access_log)
            db.session.commit()
            
            return jsonify({
                'success': False,
                'access_granted': False,
                'message': 'RFID card not registered'
            }), 404
        
        # Check if card is active
        if not rfid_card.is_active:
            access_log = RFIDAccessLog(
                rfid_card_id=rfid_card.id,
                user_id=rfid_card.user_id,
                access_type=access_type,
                access_location=access_location,
                access_granted=False,
                denial_reason='Card is inactive'
            )
            db.session.add(access_log)
            db.session.commit()
            
            return jsonify({
                'success': False,
                'access_granted': False,
                'message': 'RFID card is inactive'
            }), 403
        
        # Check if card is expired
        if rfid_card.expiry_date and rfid_card.expiry_date < datetime.utcnow():
            access_log = RFIDAccessLog(
                rfid_card_id=rfid_card.id,
                user_id=rfid_card.user_id,
                access_type=access_type,
                access_location=access_location,
                access_granted=False,
                denial_reason='Card expired'
            )
            db.session.add(access_log)
            db.session.commit()
            
            return jsonify({
                'success': False,
                'access_granted': False,
                'message': 'RFID card has expired'
            }), 403
        
        # Access granted - log successful access
        access_log = RFIDAccessLog(
            rfid_card_id=rfid_card.id,
            user_id=rfid_card.user_id,
            access_type=access_type,
            access_location=access_location,
            access_granted=True
        )
        
        # Update last used time
        rfid_card.last_used = datetime.utcnow()
        
        db.session.add(access_log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'access_granted': True,
            'message': 'Access granted',
            'user': {
                'id': rfid_card.user.id,
                'username': rfid_card.user.username,
                'email': rfid_card.user.email,
                'is_staff': rfid_card.user.is_staff,
                'staff_role': rfid_card.user.staff_role
            },
            'card': {
                'card_type': rfid_card.card_type,
                'issued_date': rfid_card.issued_date.isoformat()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@api_bp.route('/rfid/cards', methods=['GET'])
@token_required
def get_all_rfid_cards(current_user_id):
    """Get all RFID cards (admin only)"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'message': 'Unauthorized - Admin only'}), 403
        
        from models import RFIDCard
        
        cards = RFIDCard.query.all()
        
        card_list = []
        for card in cards:
            card_list.append({
                'id': card.id,
                'card_uid': card.card_uid,
                'user_id': card.user_id,
                'user_name': card.user.username if card.user else 'Unknown',
                'card_type': card.card_type,
                'is_active': card.is_active,
                'issued_date': card.issued_date.isoformat(),
                'expiry_date': card.expiry_date.isoformat() if card.expiry_date else None,
                'last_used': card.last_used.isoformat() if card.last_used else None,
                'notes': card.notes
            })
        
        return jsonify({
            'cards': card_list,
            'total_cards': len(card_list)
        })
        
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@api_bp.route('/rfid/cards/user/<int:user_id>', methods=['GET'])
@token_required
def get_user_rfid_cards(current_user_id, user_id):
    """Get RFID cards for a specific user"""
    try:
        # Users can view their own cards, admins can view any
        user = User.query.get(current_user_id)
        if current_user_id != user_id and (not user or not user.is_admin):
            return jsonify({'message': 'Unauthorized'}), 403
        
        from models import RFIDCard
        
        cards = RFIDCard.query.filter_by(user_id=user_id).all()
        
        card_list = []
        for card in cards:
            card_list.append({
                'id': card.id,
                'card_uid': card.card_uid,
                'card_type': card.card_type,
                'is_active': card.is_active,
                'issued_date': card.issued_date.isoformat(),
                'expiry_date': card.expiry_date.isoformat() if card.expiry_date else None,
                'last_used': card.last_used.isoformat() if card.last_used else None
            })
        
        return jsonify({
            'cards': card_list,
            'total_cards': len(card_list)
        })
        
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@api_bp.route('/rfid/cards/<int:card_id>/deactivate', methods=['POST'])
@token_required
def deactivate_rfid_card(current_user_id, card_id):
    """Deactivate an RFID card (admin only)"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'message': 'Unauthorized - Admin only'}), 403
        
        from models import RFIDCard
        
        card = RFIDCard.query.get(card_id)
        if not card:
            return jsonify({'success': False, 'message': 'Card not found'}), 404
        
        card.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'RFID card deactivated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@api_bp.route('/rfid/cards/<int:card_id>/activate', methods=['POST'])
@token_required
def activate_rfid_card(current_user_id, card_id):
    """Activate an RFID card (admin only)"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'message': 'Unauthorized - Admin only'}), 403
        
        from models import RFIDCard
        
        card = RFIDCard.query.get(card_id)
        if not card:
            return jsonify({'success': False, 'message': 'Card not found'}), 404
        
        card.is_active = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'RFID card activated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@api_bp.route('/rfid/access-logs', methods=['GET'])
@token_required
def get_rfid_access_logs(current_user_id):
    """Get RFID access logs (admin only)"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'message': 'Unauthorized - Admin only'}), 403
        
        from models import RFIDAccessLog
        from datetime import timedelta
        
        # Get logs from last 30 days by default
        days = int(request.args.get('days', 30))
        start_date = datetime.utcnow() - timedelta(days=days)
        
        logs = RFIDAccessLog.query.filter(
            RFIDAccessLog.access_time >= start_date
        ).order_by(RFIDAccessLog.access_time.desc()).all()
        
        log_list = []
        for log in logs:
            log_list.append({
                'id': log.id,
                'user_id': log.user_id,
                'user_name': log.user.username if log.user else 'Unknown',
                'card_uid': log.rfid_card.card_uid if log.rfid_card else 'Unknown',
                'access_type': log.access_type,
                'access_location': log.access_location,
                'access_time': log.access_time.isoformat(),
                'access_granted': log.access_granted,
                'denial_reason': log.denial_reason
            })
        
        return jsonify({
            'logs': log_list,
            'total_logs': len(log_list)
        })
        
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@api_bp.route('/rfid/access-logs/user/<int:user_id>', methods=['GET'])
@token_required
def get_user_rfid_access_logs(current_user_id, user_id):
    """Get RFID access logs for a specific user"""
    try:
        # Users can view their own logs, admins can view any
        user = User.query.get(current_user_id)
        if current_user_id != user_id and (not user or not user.is_admin):
            return jsonify({'message': 'Unauthorized'}), 403
        
        from models import RFIDAccessLog
        from datetime import timedelta
        
        # Get logs from last 30 days by default
        days = int(request.args.get('days', 30))
        start_date = datetime.utcnow() - timedelta(days=days)
        
        logs = RFIDAccessLog.query.filter(
            RFIDAccessLog.user_id == user_id,
            RFIDAccessLog.access_time >= start_date
        ).order_by(RFIDAccessLog.access_time.desc()).all()
        
        log_list = []
        for log in logs:
            log_list.append({
                'id': log.id,
                'access_type': log.access_type,
                'access_location': log.access_location,
                'access_time': log.access_time.isoformat(),
                'access_granted': log.access_granted,
                'denial_reason': log.denial_reason
            })
        
        return jsonify({
            'logs': log_list,
            'total_logs': len(log_list)
        })
        
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500


# ==================== ADMIN ATTENDANCE MANAGEMENT ====================

@api_bp.route('/admin/attendance', methods=['GET'])
@token_required
def get_all_attendance_records(current_user_id):
    """Get all attendance records with filters (Admin only)"""
    try:
        # Check if user is admin
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'message': 'Unauthorized - Admin access required'}), 403

        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        staff_id = request.args.get('staff_id')

        # Build query
        query = Attendance.query

        # Apply filters
        if start_date:
            query = query.filter(Attendance.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(Attendance.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
        if staff_id:
            query = query.filter(Attendance.user_id == int(staff_id))

        # Get attendance records with staff info
        attendance_records = query.order_by(Attendance.date.desc(), Attendance.clock_in.desc()).all()

        attendance_list = []
        for record in attendance_records:
            staff = User.query.get(record.user_id)
            attendance_list.append({
                'id': record.id,
                'user_id': record.user_id,
                'staff_name': staff.username if staff else 'Unknown',
                'staff_role': staff.staff_role if staff else 'N/A',
                'date': record.date.isoformat(),
                'clock_in': record.clock_in.strftime('%H:%M:%S') if record.clock_in else None,
                'clock_out': record.clock_out.strftime('%H:%M:%S') if record.clock_out else None,
                'hours_worked': float(record.hours_worked) if record.hours_worked else 0.0,
                'approved': record.approved,
                'notes': record.notes
            })

        return jsonify({
            'success': True,
            'attendance': attendance_list,
            'total': len(attendance_list)
        })

    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500


@api_bp.route('/admin/attendance/<int:attendance_id>/approve', methods=['POST'])
@token_required
def approve_attendance_record(current_user_id, attendance_id):
    """Approve or reject an attendance record (Admin only)"""
    try:
        # Check if user is admin
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'message': 'Unauthorized - Admin access required'}), 403

        # Get attendance record
        attendance = Attendance.query.get(attendance_id)
        if not attendance:
            return jsonify({'message': 'Attendance record not found'}), 404

        # Get approval status from request
        data = request.get_json()
        approved = data.get('approved', True)

        # Update attendance record
        attendance.approved = approved
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Attendance record {"approved" if approved else "rejected"} successfully',
            'attendance': {
                'id': attendance.id,
                'approved': attendance.approved
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}'}), 500


@api_bp.route('/admin/attendance/stats', methods=['GET'])
@token_required
def get_attendance_stats(current_user_id):
    """Get attendance statistics (Admin only)"""
    try:
        # Check if user is admin
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'message': 'Unauthorized - Admin access required'}), 403

        # Get date range
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        query = Attendance.query

        if start_date:
            query = query.filter(Attendance.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(Attendance.date <= datetime.strptime(end_date, '%Y-%m-%d').date())

        all_records = query.all()

        # Calculate statistics
        total_records = len(all_records)
        approved_records = len([r for r in all_records if r.approved])
        pending_records = total_records - approved_records
        total_hours = sum([float(r.hours_worked) if r.hours_worked else 0 for r in all_records])

        # Get staff with most hours
        staff_hours = {}
        for record in all_records:
            if record.hours_worked:
                staff_hours[record.user_id] = staff_hours.get(record.user_id, 0) + float(record.hours_worked)

        top_staff = []
        for user_id, hours in sorted(staff_hours.items(), key=lambda x: x[1], reverse=True)[:5]:
            staff = User.query.get(user_id)
            if staff:
                top_staff.append({
                    'staff_name': staff.username,
                    'staff_role': staff.staff_role,
                    'total_hours': round(hours, 2)
                })

        return jsonify({
            'success': True,
            'stats': {
                'total_records': total_records,
                'approved_records': approved_records,
                'pending_records': pending_records,
                'total_hours': round(total_hours, 2),
                'average_hours_per_record': round(total_hours / total_records, 2) if total_records > 0 else 0,
                'top_staff': top_staff
            }
        })

    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500


# ==================== STAFF ATTENDANCE (CLOCK IN/OUT) ====================

@api_bp.route('/staff/attendance/clock-in', methods=['POST'])
@token_required
def staff_clock_in(current_user_id):
    """Staff clock in"""
    try:
        data = request.get_json()
        verify_id = data.get('verify_id')

        # Get current user
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404

        # Check if already clocked in today
        today = datetime.now().date()
        existing_attendance = Attendance.query.filter_by(
            user_id=current_user_id,
            date=today
        ).first()

        if existing_attendance and existing_attendance.clock_in and not existing_attendance.clock_out:
            return jsonify({
                'success': False,
                'message': 'You are already clocked in. Please clock out first.'
            }), 400

        # Create or update attendance record
        if existing_attendance:
            # If clocked out earlier, create new record for second shift
            attendance = Attendance(
                user_id=current_user_id,
                date=today,
                clock_in=datetime.now().time(),
                approved=False
            )
            db.session.add(attendance)
        else:
            attendance = Attendance(
                user_id=current_user_id,
                date=today,
                clock_in=datetime.now().time(),
                approved=False
            )
            db.session.add(attendance)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Clocked in successfully',
            'attendance': {
                'id': attendance.id,
                'clock_in': attendance.clock_in.strftime('%H:%M:%S'),
                'date': attendance.date.isoformat()
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@api_bp.route('/staff/attendance/clock-out', methods=['POST'])
@token_required
def staff_clock_out(current_user_id):
    """Staff clock out"""
    try:
        data = request.get_json()
        verify_id = data.get('verify_id')

        # Get current user
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404

        # Find today's attendance record
        today = datetime.now().date()
        attendance = Attendance.query.filter_by(
            user_id=current_user_id,
            date=today
        ).order_by(Attendance.id.desc()).first()

        if not attendance:
            return jsonify({
                'success': False,
                'message': 'No clock-in record found for today. Please clock in first.'
            }), 400

        if attendance.clock_out:
            return jsonify({
                'success': False,
                'message': 'You have already clocked out for this shift.'
            }), 400

        # Update clock out time
        attendance.clock_out = datetime.now().time()

        # Calculate hours worked
        clock_in_datetime = datetime.combine(attendance.date, attendance.clock_in)
        clock_out_datetime = datetime.combine(attendance.date, attendance.clock_out)
        hours_worked = (clock_out_datetime - clock_in_datetime).total_seconds() / 3600
        attendance.hours_worked = round(hours_worked, 2)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Clocked out successfully',
            'attendance': {
                'id': attendance.id,
                'clock_in': attendance.clock_in.strftime('%H:%M:%S'),
                'clock_out': attendance.clock_out.strftime('%H:%M:%S'),
                'hours_worked': float(attendance.hours_worked),
                'date': attendance.date.isoformat()
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@api_bp.route('/staff/attendance/status', methods=['GET'])
@token_required
def get_attendance_status(current_user_id):
    """Get current attendance status for staff"""
    try:
        today = datetime.now().date()
        attendance = Attendance.query.filter_by(
            user_id=current_user_id,
            date=today
        ).order_by(Attendance.id.desc()).first()

        if not attendance:
            return jsonify({
                'success': True,
                'is_clocked_in': False,
                'clock_in_time': None,
                'clock_out_time': None
            })

        return jsonify({
            'success': True,
            'is_clocked_in': attendance.clock_in is not None and attendance.clock_out is None,
            'clock_in_time': attendance.clock_in.strftime('%H:%M:%S') if attendance.clock_in else None,
            'clock_out_time': attendance.clock_out.strftime('%H:%M:%S') if attendance.clock_out else None,
            'hours_worked': float(attendance.hours_worked) if attendance.hours_worked else 0
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


# ============================================
# AMENITIES MASTER API ENDPOINTS
# ============================================

@api_bp.route('/amenities', methods=['GET'])
def get_amenities():
    """Get all amenities from amenity_master table"""
    try:
        from models import AmenityMaster
        amenities = AmenityMaster.query.order_by(AmenityMaster.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'amenities': [{
                'id': a.id,
                'name': a.name,
                'icon_url': a.icon_url,
                'description': a.description,
                'created_at': a.created_at.isoformat() if a.created_at else None
            } for a in amenities]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/amenities', methods=['POST'])
@token_required
def create_amenity(current_user_id):
    """Create a new amenity"""
    try:
        from models import AmenityMaster
        
        data = request.get_json()
        
        # Validation
        if not data.get('name'):
            return jsonify({'success': False, 'message': 'Amenity name is required'}), 400
        
        if not data.get('icon_url'):
            return jsonify({'success': False, 'message': 'Icon URL is required'}), 400
        
        # Check if amenity name already exists
        existing = AmenityMaster.query.filter_by(name=data['name']).first()
        if existing:
            return jsonify({'success': False, 'message': 'Amenity with this name already exists'}), 400
        
        # Create new amenity
        amenity = AmenityMaster(
            name=data['name'],
            icon_url=data['icon_url'],
            description=data.get('description', '')
        )
        
        db.session.add(amenity)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Amenity created successfully',
            'amenity': {
                'id': amenity.id,
                'name': amenity.name,
                'icon_url': amenity.icon_url,
                'description': amenity.description,
                'created_at': amenity.created_at.isoformat() if amenity.created_at else None
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/amenities/<int:amenity_id>', methods=['PUT'])
@token_required
def update_amenity(current_user_id, amenity_id):
    """Update an existing amenity"""
    try:
        from models import AmenityMaster
        
        amenity = AmenityMaster.query.get(amenity_id)
        if not amenity:
            return jsonify({'success': False, 'message': 'Amenity not found'}), 404
        
        data = request.get_json()
        
        # Validation
        if not data.get('name'):
            return jsonify({'success': False, 'message': 'Amenity name is required'}), 400
        
        if not data.get('icon_url'):
            return jsonify({'success': False, 'message': 'Icon URL is required'}), 400
        
        # Check if new name conflicts with another amenity
        if data['name'] != amenity.name:
            existing = AmenityMaster.query.filter_by(name=data['name']).first()
            if existing:
                return jsonify({'success': False, 'message': 'Amenity with this name already exists'}), 400
        
        # Update amenity
        amenity.name = data['name']
        amenity.icon_url = data['icon_url']
        amenity.description = data.get('description', '')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Amenity updated successfully',
            'amenity': {
                'id': amenity.id,
                'name': amenity.name,
                'icon_url': amenity.icon_url,
                'description': amenity.description,
                'created_at': amenity.created_at.isoformat() if amenity.created_at else None
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/amenities/<int:amenity_id>', methods=['DELETE'])
@token_required
def delete_amenity(current_user_id, amenity_id):
    """Delete an amenity"""
    try:
        from models import AmenityMaster, AmenityDetail
        
        amenity = AmenityMaster.query.get(amenity_id)
        if not amenity:
            return jsonify({'success': False, 'message': 'Amenity not found'}), 404
        
        # Check if amenity is used in amenity details
        usage_count = AmenityDetail.query.filter_by(amenity_id=amenity_id).count()
        if usage_count > 0:
            return jsonify({
                'success': False,
                'message': f'Cannot delete amenity. It is linked to {usage_count} room type(s). Remove the links first.'
            }), 400
        
        db.session.delete(amenity)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Amenity deleted successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# ROOM SIZE (ROOM TYPES) API ENDPOINTS
# ============================================

@api_bp.route('/room-sizes', methods=['GET'])
def get_room_sizes():
    """Get all room sizes/types"""
    try:
        from models import RoomSize
        room_sizes = RoomSize.query.order_by(RoomSize.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'room_sizes': [{
                'id': rs.id,
                'room_type_name': rs.room_type_name,
                'features': rs.features,
                'max_adults': rs.max_adults,
                'max_children': rs.max_children,
                'created_at': rs.created_at.isoformat() if rs.created_at else None
            } for rs in room_sizes]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/room-sizes', methods=['POST'])
@token_required
def create_room_size(current_user_id):
    """Create a new room size/type"""
    try:
        from models import RoomSize
        
        data = request.get_json()
        
        # Validation
        if not data.get('room_type_name'):
            return jsonify({'success': False, 'message': 'Room type name is required'}), 400
        
        if not data.get('max_adults') or int(data.get('max_adults', 0)) <= 0:
            return jsonify({'success': False, 'message': 'Max adults must be greater than 0'}), 400
        
        if data.get('max_children') is None or int(data.get('max_children', -1)) < 0:
            return jsonify({'success': False, 'message': 'Max children must be 0 or greater'}), 400
        
        # Check if room type name already exists
        existing = RoomSize.query.filter_by(room_type_name=data['room_type_name']).first()
        if existing:
            return jsonify({'success': False, 'message': 'Room type with this name already exists'}), 400
        
        # Create new room size
        room_size = RoomSize(
            room_type_name=data['room_type_name'],
            features=data.get('features', ''),
            max_adults=int(data['max_adults']),
            max_children=int(data['max_children'])
        )
        
        db.session.add(room_size)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Room type created successfully',
            'room_size': {
                'id': room_size.id,
                'room_type_name': room_size.room_type_name,
                'features': room_size.features,
                'max_adults': room_size.max_adults,
                'max_children': room_size.max_children,
                'created_at': room_size.created_at.isoformat() if room_size.created_at else None
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/room-sizes/<int:room_size_id>', methods=['PUT'])
@token_required
def update_room_size(current_user_id, room_size_id):
    """Update an existing room size/type"""
    try:
        from models import RoomSize
        
        room_size = RoomSize.query.get(room_size_id)
        if not room_size:
            return jsonify({'success': False, 'message': 'Room type not found'}), 404
        
        data = request.get_json()
        
        # Validation
        if not data.get('room_type_name'):
            return jsonify({'success': False, 'message': 'Room type name is required'}), 400
        
        if not data.get('max_adults') or int(data.get('max_adults', 0)) <= 0:
            return jsonify({'success': False, 'message': 'Max adults must be greater than 0'}), 400
        
        if data.get('max_children') is None or int(data.get('max_children', -1)) < 0:
            return jsonify({'success': False, 'message': 'Max children must be 0 or greater'}), 400
        
        # Check if new name conflicts with another room type
        if data['room_type_name'] != room_size.room_type_name:
            existing = RoomSize.query.filter_by(room_type_name=data['room_type_name']).first()
            if existing:
                return jsonify({'success': False, 'message': 'Room type with this name already exists'}), 400
        
        # Update room size
        room_size.room_type_name = data['room_type_name']
        room_size.features = data.get('features', '')
        room_size.max_adults = int(data['max_adults'])
        room_size.max_children = int(data['max_children'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Room type updated successfully',
            'room_size': {
                'id': room_size.id,
                'room_type_name': room_size.room_type_name,
                'features': room_size.features,
                'max_adults': room_size.max_adults,
                'max_children': room_size.max_children,
                'created_at': room_size.created_at.isoformat() if room_size.created_at else None
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/room-sizes/<int:room_size_id>', methods=['DELETE'])
@token_required
def delete_room_size(current_user_id, room_size_id):
    """Delete a room size/type"""
    try:
        from models import RoomSize, Room, FloorPlan, AmenityDetail
        
        room_size = RoomSize.query.get(room_size_id)
        if not room_size:
            return jsonify({'success': False, 'message': 'Room type not found'}), 404
        
        # Check if room type is used in rooms
        rooms_count = Room.query.filter_by(room_size_id=room_size_id).count()
        if rooms_count > 0:
            return jsonify({
                'success': False,
                'message': f'Cannot delete room type. It is used by {rooms_count} room(s). Delete or reassign the rooms first.'
            }), 400
        
        # Check if room type is used in floor plans
        floors_count = FloorPlan.query.filter_by(room_size_id=room_size_id).count()
        if floors_count > 0:
            return jsonify({
                'success': False,
                'message': f'Cannot delete room type. It is used in {floors_count} floor plan(s). Delete or reassign the floor plans first.'
            }), 400
        
        # Check if room type is used in amenity details
        amenities_count = AmenityDetail.query.filter_by(room_size_id=room_size_id).count()
        if amenities_count > 0:
            return jsonify({
                'success': False,
                'message': f'Cannot delete room type. It has {amenities_count} amenity link(s). Remove the amenity links first.'
            }), 400
        
        db.session.delete(room_size)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Room type deleted successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# AMENITY DETAILS (AMENITY-ROOM TYPE MAPPING) API ENDPOINTS
# ============================================

@api_bp.route('/amenity-details', methods=['GET'])
def get_amenity_details():
    """Get all amenity-room type mappings"""
    try:
        from models import AmenityDetail, AmenityMaster, RoomSize
        
        details = AmenityDetail.query.all()
        
        return jsonify({
            'success': True,
            'amenity_details': [{
                'id': ad.id,
                'amenity_id': ad.amenity_id,
                'amenity_name': ad.amenity.name if ad.amenity else 'Unknown',
                'amenity_icon': ad.amenity.icon_url if ad.amenity else '',
                'room_size_id': ad.room_size_id,
                'room_type_name': ad.room_size.room_type_name if ad.room_size else 'Unknown',
                'created_at': ad.created_at.isoformat() if ad.created_at else None
            } for ad in details]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/amenity-details', methods=['POST'])
@token_required
def create_amenity_detail(current_user_id):
    """Create a new amenity-room type mapping"""
    try:
        from models import AmenityDetail, AmenityMaster, RoomSize
        
        data = request.get_json()
        
        # Validation
        if not data.get('amenity_id'):
            return jsonify({'success': False, 'message': 'Amenity is required'}), 400
        
        if not data.get('room_size_id'):
            return jsonify({'success': False, 'message': 'Room type is required'}), 400
        
        # Check if amenity exists
        amenity = AmenityMaster.query.get(data['amenity_id'])
        if not amenity:
            return jsonify({'success': False, 'message': 'Amenity not found'}), 404
        
        # Check if room size exists
        room_size = RoomSize.query.get(data['room_size_id'])
        if not room_size:
            return jsonify({'success': False, 'message': 'Room type not found'}), 404
        
        # Check if mapping already exists
        existing = AmenityDetail.query.filter_by(
            amenity_id=data['amenity_id'],
            room_size_id=data['room_size_id']
        ).first()
        
        if existing:
            return jsonify({
                'success': False,
                'message': f'{amenity.name} is already linked to {room_size.room_type_name}'
            }), 400
        
        # Create new mapping
        detail = AmenityDetail(
            amenity_id=data['amenity_id'],
            room_size_id=data['room_size_id']
        )
        
        db.session.add(detail)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Amenity linked to room type successfully',
            'amenity_detail': {
                'id': detail.id,
                'amenity_id': detail.amenity_id,
                'amenity_name': detail.amenity.name,
                'amenity_icon': detail.amenity.icon_url,
                'room_size_id': detail.room_size_id,
                'room_type_name': detail.room_size.room_type_name,
                'created_at': detail.created_at.isoformat() if detail.created_at else None
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/amenity-details/<int:detail_id>', methods=['DELETE'])
@token_required
def delete_amenity_detail(current_user_id, detail_id):
    """Delete an amenity-room type mapping"""
    try:
        from models import AmenityDetail
        
        detail = AmenityDetail.query.get(detail_id)
        if not detail:
            return jsonify({'success': False, 'message': 'Mapping not found'}), 404
        
        amenity_name = detail.amenity.name if detail.amenity else 'Unknown'
        room_type_name = detail.room_size.room_type_name if detail.room_size else 'Unknown'
        
        db.session.delete(detail)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{amenity_name} unlinked from {room_type_name} successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# FLOOR PLANS API ENDPOINTS
# ============================================

@api_bp.route('/floor-plans', methods=['GET'])
def get_floor_plans():
    """Get all floor plans"""
    try:
        from models import FloorPlan, RoomSize
        
        floor_plans = FloorPlan.query.all()
        
        return jsonify({
            'success': True,
            'floor_plans': [{
                'id': fp.id,
                'floor_name': fp.floor_name,
                'room_size_id': fp.room_size_id,
                'room_type_name': fp.room_size.room_type_name if fp.room_size else 'Unknown',
                'number_of_rooms': fp.number_of_rooms,
                'start_room_number': fp.start_room_number,
                'generated_room_numbers': fp.generate_room_numbers(),
                'created_at': fp.created_at.isoformat() if fp.created_at else None
            } for fp in floor_plans]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/floor-plans', methods=['POST'])
@token_required
def create_floor_plan(current_user_id):
    """Create a new floor plan"""
    try:
        from models import FloorPlan, RoomSize
        
        data = request.get_json()
        
        # Validation
        if not data.get('floor_name'):
            return jsonify({'success': False, 'message': 'Floor name is required'}), 400
        
        if not data.get('room_size_id'):
            return jsonify({'success': False, 'message': 'Room type is required'}), 400
        
        if not data.get('number_of_rooms'):
            return jsonify({'success': False, 'message': 'Number of rooms is required'}), 400
        
        if not data.get('start_room_number'):
            return jsonify({'success': False, 'message': 'Start room number is required'}), 400
        
        # Check if room size exists
        room_size = RoomSize.query.get(data['room_size_id'])
        if not room_size:
            return jsonify({'success': False, 'message': 'Room type not found'}), 404
        
        # Check if floor name already exists
        existing = FloorPlan.query.filter_by(floor_name=data['floor_name']).first()
        if existing:
            return jsonify({'success': False, 'message': 'Floor with this name already exists'}), 400
        
        # Validate number of rooms
        try:
            number_of_rooms = int(data['number_of_rooms'])
            if number_of_rooms <= 0 or number_of_rooms > 100:
                return jsonify({'success': False, 'message': 'Number of rooms must be between 1 and 100'}), 400
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid number of rooms'}), 400
        
        # Validate start room number
        try:
            int(data['start_room_number'])
        except ValueError:
            return jsonify({'success': False, 'message': 'Start room number must be numeric'}), 400
        
        # Create new floor plan
        floor_plan = FloorPlan(
            floor_name=data['floor_name'],
            room_size_id=data['room_size_id'],
            number_of_rooms=number_of_rooms,
            start_room_number=data['start_room_number']
        )
        
        db.session.add(floor_plan)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Floor plan created successfully',
            'floor_plan': {
                'id': floor_plan.id,
                'floor_name': floor_plan.floor_name,
                'room_size_id': floor_plan.room_size_id,
                'room_type_name': floor_plan.room_size.room_type_name,
                'number_of_rooms': floor_plan.number_of_rooms,
                'start_room_number': floor_plan.start_room_number,
                'generated_room_numbers': floor_plan.generate_room_numbers(),
                'created_at': floor_plan.created_at.isoformat() if floor_plan.created_at else None
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/floor-plans/<int:floor_plan_id>', methods=['PUT'])
@token_required
def update_floor_plan(current_user_id, floor_plan_id):
    """Update an existing floor plan"""
    try:
        from models import FloorPlan, RoomSize, Room
        
        floor_plan = FloorPlan.query.get(floor_plan_id)
        if not floor_plan:
            return jsonify({'success': False, 'message': 'Floor plan not found'}), 404
        
        data = request.get_json()
        
        # Validation
        if not data.get('floor_name'):
            return jsonify({'success': False, 'message': 'Floor name is required'}), 400
        
        if not data.get('room_size_id'):
            return jsonify({'success': False, 'message': 'Room type is required'}), 400
        
        if not data.get('number_of_rooms'):
            return jsonify({'success': False, 'message': 'Number of rooms is required'}), 400
        
        if not data.get('start_room_number'):
            return jsonify({'success': False, 'message': 'Start room number is required'}), 400
        
        # Check if new floor name conflicts with another floor
        if data['floor_name'] != floor_plan.floor_name:
            existing = FloorPlan.query.filter_by(floor_name=data['floor_name']).first()
            if existing:
                return jsonify({'success': False, 'message': 'Floor with this name already exists'}), 400
        
        # Check if room size exists
        room_size = RoomSize.query.get(data['room_size_id'])
        if not room_size:
            return jsonify({'success': False, 'message': 'Room type not found'}), 404
        
        # Validate number of rooms
        try:
            number_of_rooms = int(data['number_of_rooms'])
            if number_of_rooms <= 0 or number_of_rooms > 100:
                return jsonify({'success': False, 'message': 'Number of rooms must be between 1 and 100'}), 400
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid number of rooms'}), 400
        
        # Validate start room number
        try:
            int(data['start_room_number'])
        except ValueError:
            return jsonify({'success': False, 'message': 'Start room number must be numeric'}), 400
        
        # Check if floor has rooms already created
        rooms_count = Room.query.filter_by(floor_id=floor_plan_id).count()
        if rooms_count > 0:
            return jsonify({
                'success': False,
                'message': f'Cannot modify floor plan. It has {rooms_count} room(s) already created. Delete the rooms first.'
            }), 400
        
        # Update floor plan
        floor_plan.floor_name = data['floor_name']
        floor_plan.room_size_id = data['room_size_id']
        floor_plan.number_of_rooms = number_of_rooms
        floor_plan.start_room_number = data['start_room_number']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Floor plan updated successfully',
            'floor_plan': {
                'id': floor_plan.id,
                'floor_name': floor_plan.floor_name,
                'room_size_id': floor_plan.room_size_id,
                'room_type_name': floor_plan.room_size.room_type_name,
                'number_of_rooms': floor_plan.number_of_rooms,
                'start_room_number': floor_plan.start_room_number,
                'generated_room_numbers': floor_plan.generate_room_numbers(),
                'created_at': floor_plan.created_at.isoformat() if floor_plan.created_at else None
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/floor-plans/<int:floor_plan_id>', methods=['DELETE'])
@token_required
def delete_floor_plan(current_user_id, floor_plan_id):
    """Delete a floor plan"""
    try:
        from models import FloorPlan, Room
        
        floor_plan = FloorPlan.query.get(floor_plan_id)
        if not floor_plan:
            return jsonify({'success': False, 'message': 'Floor plan not found'}), 404
        
        # Check if floor has rooms
        rooms_count = Room.query.filter_by(floor_id=floor_plan_id).count()
        if rooms_count > 0:
            return jsonify({
                'success': False,
                'message': f'Cannot delete floor plan. It has {rooms_count} room(s). Delete the rooms first.'
            }), 400
        
        floor_name = floor_plan.floor_name
        
        db.session.delete(floor_plan)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Floor plan "{floor_name}" deleted successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
