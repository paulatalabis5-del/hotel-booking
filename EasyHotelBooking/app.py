import os
import logging
import pytz

from flask import Flask
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from extensions import db, login_manager
from models import User, Room, Amenity, Booking, BookingAmenity, Rating, Notification
from flask_migrate import Migrate

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "easy_hotel_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Enable CORS for Flutter web and mobile
CORS(app, resources={r"/api/*": {"origins": [
    "http://localhost:*",
    "http://127.0.0.1:*",
    "http://192.168.100.159:*",
    "http://localhost:54391",
    "http://127.0.0.1:54391",
    "http://192.168.100.159:54391"
]}}, supports_credentials=True)

# Configure the database
# Supports both SQLite (local) and PostgreSQL (Supabase/production)
database_url = os.environ.get("DATABASE_URL", "sqlite:///hotel.db")

# Fix for Heroku/Render postgres:// URLs (should be postgresql://)
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url

# Log which database we're using
if "postgresql" in database_url or "postgres" in database_url:
    print("✅ Connected to PostgreSQL (Supabase)")
else:
    print("📁 Using SQLite (Local Development)")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
migrate = Migrate(app, db)

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

with app.app_context():
    # Import the models here so their tables will be created
    import models  # noqa: F401
    db.create_all()  # Create new tables
    
    # Import routes after models to avoid circular imports
    from routes import *  # noqa: F401, F403
    
    # Import and register API routes for Flutter app
    try:
        from api_routes import api_bp
        if 'unique_api_blueprint_xyz789' not in [bp.name for bp in app.blueprints.values()]:
            app.register_blueprint(api_bp)
    except ValueError:
        pass  # Blueprint already registered
    
    # Create initial data
    from init_data import create_initial_data
    create_initial_data()

# Add Jinja filter for Philippine time
@app.template_filter('to_ph_time')
def to_ph_time(dt):
    if not dt:
        return dt
    utc = pytz.utc
    ph_tz = pytz.timezone('Asia/Manila')
    if dt.tzinfo is None:
        dt = utc.localize(dt)
    return dt.astimezone(ph_tz)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
