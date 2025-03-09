from app import db
from flask_login import UserMixin
from datetime import datetime
import json

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # Added admin flag

class Email(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.String(255), unique=True)
    sender = db.Column(db.String(255))
    recipients = db.Column(db.Text)
    subject = db.Column(db.Text)
    body = db.Column(db.Text)
    received_date = db.Column(db.DateTime, default=datetime.utcnow)
    raw_email = db.Column(db.LargeBinary)  # Store as binary for proper EML format
    attachments = db.Column(db.Boolean, default=False)
    attachment_data = db.Column(db.Text)  # JSON string containing attachment info
    folder = db.Column(db.String(50), default='Inbox')  # Added folder field

    def set_attachments(self, attachments_list):
        """Store attachment information as JSON string"""
        self.attachment_data = json.dumps(attachments_list)
        self.attachments = bool(attachments_list)

    def get_attachments(self):
        """Get attachment information as list of dictionaries"""
        if self.attachment_data:
            return json.loads(self.attachment_data)
        return []

    def to_dict(self):
        return {
            'id': self.id,
            'message_id': self.message_id,
            'sender': self.sender,
            'subject': self.subject,
            'received_date': self.received_date.isoformat(),
            'has_attachments': self.attachments,
            'attachments': self.get_attachments(),
            'folder': self.folder
        }