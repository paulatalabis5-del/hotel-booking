from datetime import datetime
from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_staff = db.Column(db.Boolean, default=False)  # New: staff flag
    staff_role = db.Column(db.String(50))  # New: staff role (Front Desk, Manager, etc.)
    staff_status = db.Column(db.String(20), default='active')  # New: active/inactive
    staff_shift = db.Column(db.String(50))  # New: shift timing (optional)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    phone_number = db.Column(db.String(20))
    is_verified = db.Column(db.Boolean, default=True)  # Email verification status
    verification_code = db.Column(db.String(10))  # Email verification code
    
    # Relationships
    bookings = db.relationship('Booking', backref='user', lazy='dynamic')
    ratings = db.relationship('Rating', backref='user', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def __repr__(self):
        return f'<User {self.username}>'

# ============================================
# NEW HOTEL MANAGEMENT MODELS
# ============================================

# 1. Amenities Master List
class AmenityMaster(db.Model):
    """Master list of all available amenities"""
    __tablename__ = 'amenity_master'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    icon_url = db.Column(db.String(255))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    amenity_details = db.relationship('AmenityDetail', backref='amenity', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<AmenityMaster {self.name}>'

# 2. Room Sizes (Room Types)
class RoomSize(db.Model):
    """Room types with specifications"""
    __tablename__ = 'room_size'
    
    id = db.Column(db.Integer, primary_key=True)
    room_type_name = db.Column(db.String(50), nullable=False, unique=True)
    features = db.Column(db.Text)
    max_adults = db.Column(db.Integer, nullable=False)
    max_children = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    amenity_details = db.relationship('AmenityDetail', backref='room_size', lazy='dynamic', cascade='all, delete-orphan')
    rooms = db.relationship('Room', backref='room_size', lazy='dynamic')
    floor_plans = db.relationship('FloorPlan', backref='room_size', lazy='dynamic')
    
    def __repr__(self):
        return f'<RoomSize {self.room_type_name}>'

# 3. Amenity Details (Amenity-RoomType Mapping)
class AmenityDetail(db.Model):
    """Links amenities to specific room types"""
    __tablename__ = 'amenity_detail'
    
    id = db.Column(db.Integer, primary_key=True)
    amenity_id = db.Column(db.Integer, db.ForeignKey('amenity_master.id', ondelete='CASCADE'), nullable=False)
    room_size_id = db.Column(db.Integer, db.ForeignKey('room_size.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint to prevent duplicate mappings
    __table_args__ = (db.UniqueConstraint('amenity_id', 'room_size_id', name='_amenity_roomsize_uc'),)
    
    def __repr__(self):
        return f'<AmenityDetail {self.id}>'

# 4. Floor Plans
class FloorPlan(db.Model):
    """Hotel floors with auto-generated room numbers"""
    __tablename__ = 'floor_plan'
    
    id = db.Column(db.Integer, primary_key=True)
    floor_name = db.Column(db.String(50), nullable=False)
    room_size_id = db.Column(db.Integer, db.ForeignKey('room_size.id'), nullable=False)
    number_of_rooms = db.Column(db.Integer, nullable=False)
    start_room_number = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    rooms = db.relationship('Room', backref='floor', lazy='dynamic')
    
    def generate_room_numbers(self):
        """Generate list of room numbers based on start number and count"""
        try:
            start_num = int(self.start_room_number)
            return [str(start_num + i) for i in range(self.number_of_rooms)]
        except ValueError:
            # If start_room_number is not numeric, return empty list
            return []
    
    def __repr__(self):
        return f'<FloorPlan {self.floor_name}>'

# 5. Rooms (Updated)
class Room(db.Model):
    """Individual room records with all details"""
    __tablename__ = 'room'
    
    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(10), nullable=False, unique=True)
    room_size_id = db.Column(db.Integer, db.ForeignKey('room_size.id'), nullable=False)
    floor_id = db.Column(db.Integer, db.ForeignKey('floor_plan.id'), nullable=False)
    price_per_night = db.Column(db.Float, nullable=False)
    
    # 5 images for carousel
    image_1 = db.Column(db.String(255))
    image_2 = db.Column(db.String(255))
    image_3 = db.Column(db.String(255))
    image_4 = db.Column(db.String(255))
    image_5 = db.Column(db.String(255))
    
    status = db.Column(db.String(20), default='available')  # available, occupied, maintenance
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Legacy fields for backward compatibility
    name = db.Column(db.String(100))  # Can be auto-generated from room_type + room_number
    description = db.Column(db.Text)  # Can be auto-generated from room_size features
    capacity = db.Column(db.Integer)  # Inherited from room_size (max_adults + max_children)
    image_url = db.Column(db.String(255))  # Kept for backward compatibility, use image_1
    
    # Relationships
    bookings = db.relationship('Booking', backref='room', lazy='dynamic')
    
    @property
    def max_adults(self):
        """Inherited from room_size"""
        return self.room_size.max_adults if self.room_size else 0
    
    @property
    def max_children(self):
        """Inherited from room_size"""
        return self.room_size.max_children if self.room_size else 0
    
    @property
    def total_capacity(self):
        """Total capacity (adults + children)"""
        return self.max_adults + self.max_children
    
    @property
    def amenities(self):
        """Get all amenities for this room's type"""
        if self.room_size:
            return [detail.amenity for detail in self.room_size.amenity_details]
        return []
    
    @property
    def images(self):
        """Get list of all room images"""
        return [img for img in [self.image_1, self.image_2, self.image_3, self.image_4, self.image_5] if img]
    
    def __repr__(self):
        return f'<Room {self.room_number}>'

# Keep old Amenity model for backward compatibility with bookings
class Amenity(db.Model):
    """Legacy amenity model for booking add-ons"""
    __tablename__ = 'amenity'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    
    # Relationships
    booking_amenities = db.relationship('BookingAmenity', backref='amenity', lazy='dynamic')
    
    def __repr__(self):
        return f'<Amenity {self.name}>'

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date, nullable=False)
    guests = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending, confirmed, cancelled
    cancellation_reason = db.Column(db.Text)
    cancelled_by = db.Column(db.String(20))  # 'user' or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    booking_amenities = db.relationship('BookingAmenity', backref='booking', lazy='dynamic')
    
    def __repr__(self):
        return f'<Booking {self.id}>'

class BookingAmenity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    amenity_id = db.Column(db.Integer, db.ForeignKey('amenity.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    
    def __repr__(self):
        return f'<BookingAmenity {self.id}>'

class Rating(db.Model):
    __tablename__ = 'rating'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    overall_rating = db.Column(db.Integer, nullable=False)  # Overall hotel experience
    room_rating = db.Column(db.Integer, nullable=False)     # Room quality and comfort
    amenities_rating = db.Column(db.Integer, nullable=False) # Quality of amenities
    service_rating = db.Column(db.Integer, nullable=False)   # Staff service quality
    comment = db.Column(db.Text)
    admin_reply = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    booking = db.relationship('Booking', backref=db.backref('rating', uselist=False))
    
    def __repr__(self):
        return f'<Rating {self.id} by User {self.user_id}>'

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Notification {self.id}>'

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    clock_in = db.Column(db.Time)
    clock_out = db.Column(db.Time)
    verified_by_id = db.Column(db.String(64))  # e.g., staff ID or admin ID
    id_image = db.Column(db.String(255))  # Path to uploaded ID image
    approved = db.Column(db.Boolean, default=False)  # Admin approval

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    admin_comment = db.Column(db.Text)

class Payroll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    period_start = db.Column(db.Date)
    period_end = db.Column(db.Date)
    total_hours = db.Column(db.Float)
    overtime_hours = db.Column(db.Float)
    gross_pay = db.Column(db.Float)
    deductions = db.Column(db.Float)
    bonuses = db.Column(db.Float)
    net_pay = db.Column(db.Float)
    date_issued = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    staff = db.relationship('User', backref='payrolls')
    archived = db.Column(db.Boolean, default=False)

class PayrollBonus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payroll_id = db.Column(db.Integer, db.ForeignKey('payroll.id'))
    description = db.Column(db.String(128))
    amount = db.Column(db.Float)
    payroll = db.relationship('Payroll', backref='bonuses_list')

class PayrollDeduction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payroll_id = db.Column(db.Integer, db.ForeignKey('payroll.id'))
    description = db.Column(db.String(128))
    amount = db.Column(db.Float)
    payroll = db.relationship('Payroll', backref='deductions_list')

# Add payroll fields to User
User.salary_type = db.Column(db.String(20), default='fixed')  # 'fixed' or 'hourly'
User.base_salary = db.Column(db.Float, default=0.0)
User.hourly_rate = db.Column(db.Float, default=0.0)
User.overtime_rate = db.Column(db.Float, default=0.0)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)  # 'gcash', 'cash', 'card'
    payment_status = db.Column(db.String(20), default='pending')  # 'pending', 'completed', 'failed', 'refunded'
    
    # GCash specific fields
    gcash_reference_number = db.Column(db.String(100))
    gcash_transaction_id = db.Column(db.String(100))
    gcash_phone_number = db.Column(db.String(20))
    
    # Payment gateway fields
    gateway_response = db.Column(db.Text)  # Store full response from payment gateway
    gateway_transaction_id = db.Column(db.String(100))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime)
    
    # Relationships
    booking = db.relationship('Booking', backref=db.backref('payments', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('payments', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Payment {self.id} - {self.payment_method} - {self.amount}>'

class PaymentMethod(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # 'GCash', 'PayMaya', 'Cash', 'Card'
    code = db.Column(db.String(20), nullable=False)  # 'gcash', 'paymaya', 'cash', 'card'
    is_active = db.Column(db.Boolean, default=True)
    is_online = db.Column(db.Boolean, default=False)  # True for online payments
    description = db.Column(db.Text)
    icon_url = db.Column(db.String(255))
    
    # Configuration for online payment methods
    api_key = db.Column(db.String(255))
    secret_key = db.Column(db.String(255))
    merchant_id = db.Column(db.String(100))
    
    def __repr__(self):
        return f'<PaymentMethod {self.name}>'

# RFID Card Management
class RFIDCard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_uid = db.Column(db.String(50), unique=True, nullable=False)  # RFID unique identifier
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    card_type = db.Column(db.String(20), nullable=False)  # 'staff_badge', 'room_key', 'access_card'
    is_active = db.Column(db.Boolean, default=True)
    issued_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime)
    last_used = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    
    # Relationships
    user = db.relationship('User', backref='rfid_cards')
    
    def __repr__(self):
        return f'<RFIDCard {self.card_uid} - {self.card_type}>'

# RFID Access Log
class RFIDAccessLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rfid_card_id = db.Column(db.Integer, db.ForeignKey('rfid_card.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    access_type = db.Column(db.String(30), nullable=False)  # 'attendance', 'room_access', 'checkpoint'
    access_location = db.Column(db.String(100))  # 'front_desk', 'room_101', 'checkpoint_a'
    access_time = db.Column(db.DateTime, default=datetime.utcnow)
    access_granted = db.Column(db.Boolean, default=True)
    denial_reason = db.Column(db.String(100))  # If access denied
    
    # Relationships
    rfid_card = db.relationship('RFIDCard', backref='access_logs')
    user = db.relationship('User', backref='rfid_access_logs')
    
    def __repr__(self):
        return f'<RFIDAccessLog {self.id} - {self.access_type}>'

# Role-Based Feature Models

# 1. Front Desk Operations
class CheckInOut(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action_type = db.Column(db.String(20), nullable=False)  # 'check_in' or 'check_out'
    action_time = db.Column(db.DateTime, default=datetime.utcnow)
    guest_signature = db.Column(db.String(255))  # Path to signature image
    notes = db.Column(db.Text)
    room_condition = db.Column(db.String(50))  # 'excellent', 'good', 'needs_attention'
    
    # Relationships
    booking = db.relationship('Booking', backref='checkin_checkout_records')
    staff = db.relationship('User', backref='checkin_checkout_actions')

# 2. Housekeeping Management
class RoomStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    status = db.Column(db.String(30), nullable=False)  # 'clean', 'dirty', 'maintenance', 'out_of_order'
    last_cleaned = db.Column(db.DateTime)
    cleaned_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    inspection_status = db.Column(db.String(20), default='pending')  # 'pending', 'passed', 'failed'
    inspected_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    inspection_time = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    room = db.relationship('Room', backref='status_records')
    cleaner = db.relationship('User', foreign_keys=[cleaned_by], backref='cleaned_rooms')
    inspector = db.relationship('User', foreign_keys=[inspected_by], backref='inspected_rooms')

class CleaningTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_type = db.Column(db.String(50), nullable=False)  # 'daily_cleaning', 'deep_cleaning', 'maintenance_cleaning'
    priority = db.Column(db.String(20), default='normal')  # 'low', 'normal', 'high', 'urgent'
    status = db.Column(db.String(20), default='pending')  # 'pending', 'in_progress', 'completed', 'cancelled'
    scheduled_time = db.Column(db.DateTime, nullable=False)
    started_time = db.Column(db.DateTime)
    completed_time = db.Column(db.DateTime)
    estimated_duration = db.Column(db.Integer)  # in minutes
    actual_duration = db.Column(db.Integer)  # in minutes
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    room = db.relationship('Room', backref='cleaning_tasks')
    staff = db.relationship('User', backref='assigned_cleaning_tasks')

# 3. Security System
class SecurityPatrol(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guard_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    patrol_route = db.Column(db.String(100), nullable=False)  # 'lobby', 'floors_1_3', 'parking', 'perimeter'
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='in_progress')  # 'in_progress', 'completed', 'interrupted'
    checkpoints_visited = db.Column(db.Text)  # JSON array of checkpoint IDs
    observations = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    guard = db.relationship('User', backref='security_patrols')

class SecurityIncident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reported_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    incident_type = db.Column(db.String(50), nullable=False)  # 'theft', 'disturbance', 'medical', 'fire', 'other'
    severity = db.Column(db.String(20), nullable=False)  # 'low', 'medium', 'high', 'critical'
    location = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    action_taken = db.Column(db.Text)
    status = db.Column(db.String(20), default='open')  # 'open', 'investigating', 'resolved', 'closed'
    incident_time = db.Column(db.DateTime, nullable=False)
    resolved_time = db.Column(db.DateTime)
    resolved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    reporter = db.relationship('User', foreign_keys=[reported_by], backref='reported_incidents')
    resolver = db.relationship('User', foreign_keys=[resolved_by], backref='resolved_incidents')

# 4. Maintenance Module
class WorkOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'))
    location = db.Column(db.String(100))  # For non-room locations
    category = db.Column(db.String(50), nullable=False)  # 'plumbing', 'electrical', 'hvac', 'general'
    priority = db.Column(db.String(20), default='normal')  # 'low', 'normal', 'high', 'urgent'
    status = db.Column(db.String(20), default='open')  # 'open', 'assigned', 'in_progress', 'completed', 'cancelled'
    requested_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))
    estimated_cost = db.Column(db.Float)
    actual_cost = db.Column(db.Float)
    estimated_hours = db.Column(db.Float)
    actual_hours = db.Column(db.Float)
    scheduled_date = db.Column(db.DateTime)
    started_date = db.Column(db.DateTime)
    completed_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    room = db.relationship('Room', backref='work_orders')
    requester = db.relationship('User', foreign_keys=[requested_by], backref='requested_work_orders')
    assignee = db.relationship('User', foreign_keys=[assigned_to], backref='assigned_work_orders')

class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'hvac', 'elevator', 'generator', 'security', 'kitchen'
    location = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))
    purchase_date = db.Column(db.Date)
    warranty_expiry = db.Column(db.Date)
    last_maintenance = db.Column(db.DateTime)
    next_maintenance = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='operational')  # 'operational', 'maintenance', 'broken', 'retired'
    maintenance_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class EquipmentMaintenance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    maintenance_type = db.Column(db.String(50), nullable=False)  # 'routine', 'repair', 'inspection', 'replacement'
    performed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    maintenance_date = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text, nullable=False)
    cost = db.Column(db.Float)
    parts_used = db.Column(db.Text)  # JSON array of parts
    next_maintenance_due = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    equipment = db.relationship('Equipment', backref='maintenance_records')
    technician = db.relationship('User', backref='equipment_maintenance_performed')

# 5. Manager Dashboard - Additional Analytics Models
class DailyReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_date = db.Column(db.Date, nullable=False)
    total_revenue = db.Column(db.Float, default=0.0)
    occupancy_rate = db.Column(db.Float, default=0.0)
    new_bookings = db.Column(db.Integer, default=0)
    cancelled_bookings = db.Column(db.Integer, default=0)
    checkins = db.Column(db.Integer, default=0)
    checkouts = db.Column(db.Integer, default=0)
    maintenance_requests = db.Column(db.Integer, default=0)
    security_incidents = db.Column(db.Integer, default=0)
    staff_attendance = db.Column(db.Float, default=0.0)  # percentage
    guest_satisfaction = db.Column(db.Float, default=0.0)  # average rating
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class StaffPerformance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    evaluation_date = db.Column(db.Date, nullable=False)
    performance_score = db.Column(db.Float)  # 1-10 scale
    punctuality_score = db.Column(db.Float)  # 1-10 scale
    quality_score = db.Column(db.Float)  # 1-10 scale
    teamwork_score = db.Column(db.Float)  # 1-10 scale
    tasks_completed = db.Column(db.Integer, default=0)
    tasks_on_time = db.Column(db.Integer, default=0)
    customer_feedback_score = db.Column(db.Float)
    manager_notes = db.Column(db.Text)
    evaluated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    staff = db.relationship('User', foreign_keys=[staff_id], backref='performance_evaluations')
    evaluator = db.relationship('User', foreign_keys=[evaluated_by], backref='staff_evaluations_given')
