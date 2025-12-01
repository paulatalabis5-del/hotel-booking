from extensions import db
from models import User, Room, Amenity, RoomSize, FloorPlan

def create_initial_data():
    # Check if we already have data
    if User.query.count() > 0:
        return
    
    # Create room sizes first
    standard = RoomSize(room_type_name='Standard', max_adults=2, max_children=1, features='Comfortable room with basic amenities')
    deluxe = RoomSize(room_type_name='Deluxe', max_adults=2, max_children=2, features='Spacious room with premium amenities')
    suite = RoomSize(room_type_name='Suite', max_adults=4, max_children=2, features='Luxury suite with separate living area')
    
    db.session.add_all([standard, deluxe, suite])
    db.session.flush()  # Get IDs without committing
    
    # Create floor plans
    floor1 = FloorPlan(floor_name='Ground Floor', room_size_id=standard.id, number_of_rooms=10, start_room_number='101')
    floor2 = FloorPlan(floor_name='First Floor', room_size_id=deluxe.id, number_of_rooms=10, start_room_number='201')
    
    db.session.add_all([floor1, floor2])
    db.session.flush()  # Get IDs without committing
    
    # Create admin user
    admin = User(
        username="admin",
        email="admin@easyhotel.com",
        is_admin=True
    )
    admin.set_password("admin123")
    
    # Create sample staff members
    staff_members = [
        User(
            username="john_doe",
            email="john@easyhotel.com",
            phone_number="09123456789",
            is_staff=True,
            staff_role="Front Desk Manager",
            staff_shift="Morning (6AM - 2PM)",
            staff_status="active",
            is_verified=True
        ),
        User(
            username="jane_smith",
            email="jane@easyhotel.com",
            phone_number="09123456790",
            is_staff=True,
            staff_role="Housekeeping Supervisor",
            staff_shift="Day (8AM - 4PM)",
            staff_status="active",
            is_verified=True
        ),
        User(
            username="mike_johnson",
            email="mike@easyhotel.com",
            phone_number="09123456791",
            is_staff=True,
            staff_role="Security Guard",
            staff_shift="Night (10PM - 6AM)",
            staff_status="active",
            is_verified=True
        ),
    ]
    
    # Set passwords for staff
    for staff in staff_members:
        staff.set_password("staff123")
    
    # Create rooms with new schema
    rooms = [
        Room(
            room_number="101",
            room_size_id=standard.id,
            floor_id=floor1.id,
            name="Standard Room",
            description="Comfortable room with a queen-size bed, private bathroom, and basic amenities.",
            price_per_night=500.00,
            capacity=2,
            image_1="https://images.unsplash.com/photo-1631049307264-da0ec9d70304?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2070&q=80",
            image_url="https://images.unsplash.com/photo-1631049307264-da0ec9d70304?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2070&q=80"
        ),
        Room(
            room_number="102",
            room_size_id=deluxe.id,
            floor_id=floor1.id,
            name="Deluxe Room",
            description="Spacious room with a king-size bed, private bathroom, sitting area, and premium amenities.",
            price_per_night=750.00,
            capacity=2,
            image_1="https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2070&q=80",
            image_url="https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2070&q=80"
        ),
        Room(
            room_number="201",
            room_size_id=suite.id,
            floor_id=floor2.id,
            name="Family Suite",
            description="Large suite with three single beds, private bathroom, sitting area, and family-friendly amenities.",
            price_per_night=1000.00,
            capacity=4,
            image_1="https://images.unsplash.com/photo-1566665797739-1674de7a421a?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2074&q=80",
            image_url="https://images.unsplash.com/photo-1566665797739-1674de7a421a?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2074&q=80"
        ),
        Room(
            room_number="202",
            room_size_id=suite.id,
            floor_id=floor2.id,
            name="Presidential Suite",
            description="Luxurious suite with twin beds, premium view, separate living area, and exclusive amenities.",
            price_per_night=2000.00,
            capacity=2,
            image_1="https://images.unsplash.com/photo-1578683010236-d716f9a3f461?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2070&q=80",
            image_url="https://images.unsplash.com/photo-1578683010236-d716f9a3f461?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2070&q=80"
        )
    ]
    
    # Create amenities
    amenities = [
        Amenity(name="Full Board Meal", description="Includes breakfast, lunch, and dinner(per pax)", price=550.00),
        Amenity(name="Pool", description="Relaxing and refreshing pool", price=250.00),
        Amenity(name="Spa Access", description="Access to hotel spa facilities", price=500.00),
        Amenity(name="Gym", description="Fitness center with modern equipment 24/7", price=150.00),
        Amenity(name="Indoor Playground", description="Indoor playground for children(per hour)", price=150.00)
    ]
    
    # Create payment methods
    from models import PaymentMethod
    
    payment_methods = [
        PaymentMethod(
            name='GCash',
            code='gcash',
            is_active=True,
            is_online=True,
            description='Pay using your GCash wallet',
            icon_url='/static/images/gcash-logo.png'
        ),
        PaymentMethod(
            name='Cash on Arrival',
            code='cash',
            is_active=True,
            is_online=False,
            description='Pay when you check in at the hotel',
            icon_url='/static/images/cash-icon.png'
        ),
        PaymentMethod(
            name='Credit/Debit Card',
            code='card',
            is_active=False,  # Disabled for now
            is_online=True,
            description='Pay with your credit or debit card (Coming Soon)',
            icon_url='/static/images/card-icon.png'
        ),
        PaymentMethod(
            name='PayMaya',
            code='paymaya',
            is_active=False,  # Disabled for now
            is_online=True,
            description='Pay using your PayMaya wallet (Coming Soon)',
            icon_url='/static/images/paymaya-logo.png'
        )
    ]
    
    # Add to database
    db.session.add(admin)
    for staff in staff_members:
        db.session.add(staff)
    for room in rooms:
        db.session.add(room)
    for amenity in amenities:
        db.session.add(amenity)
    for method in payment_methods:
        db.session.add(method)
    
    db.session.commit() 