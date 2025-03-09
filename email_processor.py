import email
from email import policy
from datetime import datetime
from models import Email
from app import db, ix
from whoosh.writing import AsyncWriter
import logging
import base64

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def process_email(raw_email_data, folder='Inbox'):
    try:
        # Parse email using SMTP policy for exact format preservation
        email_message = email.message_from_bytes(raw_email_data, policy=policy.SMTP)

        # Extract headers without decoding to preserve original format
        message_id = str(email_message.get('Message-ID', ''))
        sender = str(email_message.get('From', ''))
        subject = str(email_message.get('Subject', ''))
        recipients = str(email_message.get('To', ''))

        # Determine folder based on headers
        if folder == 'Inbox' and sender.lower() == email_message.get('Return-Path', '').lower():
            folder = 'Sent'

        # Extract body content for display only
        body_content = ''
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/html":
                    body_content = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace')
                    break
                elif part.get_content_type() == "text/plain" and not body_content:
                    body_content = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace')
        else:
            body_content = email_message.get_payload(decode=True).decode(email_message.get_content_charset() or 'utf-8', errors='replace')

        # Check for attachments
        attachments = []
        for part in email_message.walk():
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename()
                if filename:
                    payload = part.get_payload(decode=True)
                    attachments.append({
                        'filename': filename,
                        'content_type': part.get_content_type(),
                        'size': len(payload),
                        'payload': base64.b64encode(payload).decode()
                    })

        # Add X-Folder header to raw email data for Zimbra
        folder_header = f'X-Folder: {folder}\r\n'
        raw_email_with_folder = folder_header.encode('utf-8') + raw_email_data

        # Create Email record with exact original data
        email_record = Email(
            message_id=message_id,
            sender=sender,
            recipients=recipients,
            subject=subject,
            body=body_content,
            received_date=datetime.now(),
            raw_email=raw_email_with_folder,  # Store modified email data with folder header
            attachments=bool(attachments),
            folder=folder  # Store folder information
        )

        # Set attachments if any
        if attachments:
            email_record.set_attachments(attachments)

        # Save to database
        db.session.add(email_record)
        db.session.commit()

        logger.info(f"Successfully processed email: {message_id} to folder: {folder}")

        # Index for search
        writer = AsyncWriter(ix)
        writer.add_document(
            message_id=message_id,
            sender=sender,
            subject=subject,
            content=body_content,
            date=datetime.now()
        )
        writer.commit()

    except Exception as e:
        logger.error(f"Error processing email: {str(e)}")
        db.session.rollback()
        raise