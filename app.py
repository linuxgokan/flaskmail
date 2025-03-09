import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from whoosh.index import create_in
from whoosh.fields import Schema, TEXT, ID, DATETIME, BOOLEAN
import smtpd
import asyncore
import threading

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_key")

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "postgresql://email_archive:123123aa@localhost:5432/email_archive_db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize search index
if not os.path.exists("index"):
    os.mkdir("index")
schema = Schema(
    message_id=ID(stored=True, unique=True),
    sender=TEXT(stored=True),
    subject=TEXT(stored=True),
    content=TEXT(stored=True),
    date=DATETIME(stored=True),
    has_attachments=BOOLEAN(stored=True)
)
ix = create_in("index", schema)

# Import routes after app initialization to avoid circular imports
from routes import *  # noqa

with app.app_context():
    try:
        logger.info("Attempting to create database tables...")
        db.create_all()
        logger.info("Database tables created successfully")

        # Create admin user if it doesn't exist
        from models import User
        admin = User.query.filter_by(username='ob').first()
        if not admin:
            from routes import create_admin_user
            create_admin_user()
            logger.info("Admin user created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        raise

# Start SMTP server in a separate thread
def start_smtp_server():
    try:
        class CustomSMTPServer(smtpd.SMTPServer):
            def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
                logger.info(f"Received email from {mailfrom} to {rcpttos}")
                with app.app_context():  # Add application context here
                    from email_processor import process_email
                    try:
                        process_email(data)
                        logger.info("Email processed successfully")
                    except Exception as e:
                        logger.error(f"Error processing email: {str(e)}")
                return

        server = CustomSMTPServer(('0.0.0.0', 25), None)
        logger.info("SMTP server started on port 25")
        asyncore.loop()
    except Exception as e:
        logger.error(f"Failed to start SMTP server: {str(e)}")
        if "Permission denied" in str(e):
            logger.error("Port 25 requires root privileges. Consider using a higher port number or running with sudo.")
        return

smtp_thread = threading.Thread(target=start_smtp_server, daemon=True)
smtp_thread.start()
logger.info("SMTP server thread started")