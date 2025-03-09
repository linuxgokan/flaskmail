-- Create database and user
DROP DATABASE IF EXISTS email_archive_db;
CREATE DATABASE email_archive_db;

DROP USER IF EXISTS email_archive;
CREATE USER email_archive WITH PASSWORD '123123aa';
ALTER USER email_archive WITH SUPERUSER;
GRANT ALL PRIVILEGES ON DATABASE email_archive_db TO email_archive;

-- Connect to the database
\c email_archive_db;

-- Create sequences
CREATE SEQUENCE user_id_seq;
CREATE SEQUENCE email_id_seq;

-- Create tables
CREATE TABLE IF NOT EXISTS "user" (
    id INTEGER PRIMARY KEY DEFAULT nextval('user_id_seq'),
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS email (
    id INTEGER PRIMARY KEY DEFAULT nextval('email_id_seq'),
    message_id VARCHAR(255) UNIQUE,
    sender VARCHAR(255),
    recipients TEXT,
    subject TEXT,
    body TEXT,
    received_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    raw_email TEXT,
    attachments BOOLEAN DEFAULT FALSE
);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO email_archive;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO email_archive;
GRANT ALL PRIVILEGES ON SCHEMA public TO email_archive;

-- Create default admin user (username: ob, password: ob123)
INSERT INTO "user" (username, email, password_hash, is_admin) 
VALUES (
    'ob', 
    'ob@example.com', 
    'scrypt:32768:8:1$3NeXKpn5xzMD4zWq$1b52c2476971da1ac07bb90e8492cd95be88d5dc1b6c4b0e5ff7f8506dea170f3c0c63a5f2e3c9a9c91b3a8abba8465e2f38f5a75fc7c1c17ae5f0dd7e8c7e6',
    TRUE
);

-- Insert example emails
INSERT INTO email (message_id, sender, recipients, subject, body, received_date, raw_email, attachments) 
VALUES (
    'test-email-1@example.com',
    'sender@example.com',
    'ob@example.com',
    'Test E-posta 1',
    'Bu bir test e-postasıdır.',
    '2025-03-09 10:00:00',
    'From: sender@example.com\nTo: ob@example.com\nSubject: Test E-posta 1\n\nBu bir test e-postasıdır.',
    false
);

INSERT INTO email (message_id, sender, recipients, subject, body, received_date, raw_email, attachments) 
VALUES (
    'test-email-2@example.com',
    'other@example.com',
    'ob@example.com',
    'Test E-posta 2 - Ekli',
    'Bu e-postada ek vardır.',
    '2025-03-09 11:00:00',
    'From: other@example.com\nTo: ob@example.com\nSubject: Test E-posta 2 - Ekli\n\nBu e-postada ek vardır.',
    true
);