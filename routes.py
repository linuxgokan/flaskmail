import base64
import logging
import zipfile # Added import statement for zipfile library

from flask import render_template, redirect, url_for, flash, request, send_file, Response, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, Email
from forms import LoginForm, RegisterForm, SearchForm, AdminUserCreateForm
from search import search_emails
from app import app, db, login_manager
from io import BytesIO
import os
from backup import create_backup
from datetime import datetime, timedelta
from functools import wraps
import psutil
from collections import defaultdict


logger = logging.getLogger(__name__)

def get_email_stats(user_email=None):
    now = datetime.utcnow()
    today_start = datetime.combine(now.date(), datetime.min.time())
    yesterday = now - timedelta(days=1)

    # Base query
    base_query = Email.query

    # Add email filter if not admin
    if user_email:
        base_query = base_query.filter(Email.recipients.like(f'%{user_email}%'))

    # Toplam e-posta sayısı
    total_emails = base_query.count()

    # Bugün gelen e-posta sayısı
    today_emails = base_query.filter(
        Email.received_date >= today_start
    ).count()

    # Ekli dosya içeren e-posta sayısı
    emails_with_attachments = base_query.filter(
        Email.attachments == True
    ).count()

    # Son 24 saat içinde gelen e-posta sayısı
    last_24h_emails = base_query.filter(
        Email.received_date >= yesterday
    ).count()

    return {
        'total_emails': total_emails,
        'today_emails': today_emails,
        'emails_with_attachments': emails_with_attachments,
        'last_24h_emails': last_24h_emails
    }

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(id):
    return db.session.get(User, int(id))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form = SearchForm()
    emails = []

    # E-posta istatistiklerini al
    stats = get_email_stats(current_user.email if not current_user.is_admin else None)

    if form.validate_on_submit():
        query = form.query.data
        start_date = form.start_date.data
        end_date = form.end_date.data

        if query:
            search_results = search_emails(query, start_date, end_date)
            email_ids = [result['message_id'] for result in search_results]
            if current_user.is_admin:
                emails = Email.query.filter(
                    Email.message_id.in_(email_ids)
                ).order_by(Email.received_date.desc()).all()
            else:
                emails = Email.query.filter(
                    Email.message_id.in_(email_ids),
                    Email.recipients.like(f'%{current_user.email}%')
                ).order_by(Email.received_date.desc()).all()
        else:
            if current_user.is_admin:
                emails = Email.query.order_by(Email.received_date.desc()).limit(50).all()
            else:
                emails = Email.query.filter(
                    Email.recipients.like(f'%{current_user.email}%')
                ).order_by(Email.received_date.desc()).limit(50).all()
    else:
        if current_user.is_admin:
            emails = Email.query.order_by(Email.received_date.desc()).limit(50).all()
        else:
            emails = Email.query.filter(
                Email.recipients.like(f'%{current_user.email}%')
            ).order_by(Email.received_date.desc()).limit(50).all()

    return render_template('index.html', form=form, emails=emails, stats=stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            flash('Başarıyla giriş yaptınız.', 'success')
            return redirect(url_for('index'))
        flash('Hatalı kullanıcı adı veya parola', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin/users', methods=['GET'])
@login_required
@admin_required
def admin_users():
    users = User.query.all()
    form = AdminUserCreateForm()
    return render_template('admin/users.html', users=users, form=form)

@app.route('/admin/users/create', methods=['POST'])
@login_required
@admin_required
def admin_create_user():
    form = AdminUserCreateForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Bu kullanıcı adı zaten kullanılıyor.', 'danger')
            return redirect(url_for('admin_users'))

        if User.query.filter_by(email=form.email.data).first():
            flash('Bu e-posta adresi zaten kayıtlı.', 'danger')
            return redirect(url_for('admin_users'))

        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data)
        )
        db.session.add(user)
        db.session.commit()
        flash('Kullanıcı başarıyla oluşturuldu.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Admin kullanıcısı silinemez.', 'danger')
    else:
        db.session.delete(user)
        db.session.commit()
        flash('Kullanıcı başarıyla silindi.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/email/<int:email_id>')
@login_required
def view_email(email_id):
    email = db.session.get(Email, email_id)
    if not email or (not current_user.is_admin and current_user.email not in email.recipients):
        flash('Bu e-postaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('index'))
    return render_template('view_email.html', email=email)

@app.route('/email/<int:email_id>/download')
@login_required
def download_eml(email_id):
    email = db.session.get(Email, email_id)
    if not email or (not current_user.is_admin and current_user.email not in email.recipients):
        flash('Bu e-postaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('index'))

    try:
        response = Response(
            email.raw_email,  # Raw binary data
            mimetype='message/rfc822',
            headers={
                'Content-Type': 'message/rfc822',
                'Content-Disposition': f'attachment; filename="{email.message_id.strip("<>")}.eml"'
            }
        )
        return response
    except Exception as e:
        logger.error(f"Error downloading EML: {str(e)}")
        flash('EML dosyası indirilirken bir hata oluştu.', 'danger')
        return redirect(url_for('view_email', email_id=email_id))


@app.route('/backup/download')
@login_required
def download_backup():
    try:
        backup_file = create_backup()
        return send_file(
            backup_file,
            mimetype='application/sql',
            as_attachment=True,
            download_name=f"email_archive_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        )
    except Exception as e:
        flash('Backup creation failed', 'danger')
        return redirect(url_for('index'))


@app.route('/statistics')
@login_required
@admin_required
def statistics():
    # Günlük istatistikler
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)

    daily_emails = Email.query.filter(
        Email.received_date >= seven_days_ago
    ).all()

    daily_stats = defaultdict(int)
    for email in daily_emails:
        date_str = email.received_date.strftime('%Y-%m-%d')
        daily_stats[date_str] += 1

    # Son 7 günü listele
    daily_stats = [
        {
            'date': (now - timedelta(days=i)).strftime('%d %B'),
            'count': daily_stats[(now - timedelta(days=i)).strftime('%Y-%m-%d')]
        }
        for i in range(7)
    ]

    # Aylık istatistikler
    monthly_emails = Email.query.filter(
        Email.received_date >= now - timedelta(days=180)
    ).all()

    monthly_stats = defaultdict(int)
    for email in monthly_emails:
        month_str = email.received_date.strftime('%Y-%m')
        monthly_stats[month_str] += 1

    tr_months = {
        '01': 'Ocak', '02': 'Şubat', '03': 'Mart', '04': 'Nisan',
        '05': 'Mayıs', '06': 'Haziran', '07': 'Temmuz', '08': 'Ağustos',
        '09': 'Eylül', '10': 'Ekim', '11': 'Kasım', '12': 'Aralık'
    }

    # Son 6 ayı listele
    monthly_stats = [
        {
            'month': f"{tr_months[date.strftime('%m')]} {date.strftime('%Y')}",
            'count': monthly_stats[date.strftime('%Y-%m')]
        }
        for date in [now - timedelta(days=30*i) for i in range(6)]
    ]

    return render_template('statistics.html', daily_stats=daily_stats, monthly_stats=monthly_stats)

@app.route('/system-health')
@login_required
@admin_required
def system_health():
    # CPU bilgileri
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_cores = psutil.cpu_count()

    # Bellek kullanımı
    memory = psutil.virtual_memory()
    memory_total = f"{memory.total / (1024**3):.1f} GB"

    # Disk kullanımı
    disk = psutil.disk_usage('/')
    disk_total = f"{disk.total / (1024**3):.1f} GB"
    disk_used = f"{disk.used / (1024**3):.1f} GB"
    disk_free = f"{disk.free / (1024**3):.1f} GB"
    disk_percent = disk.percent

    # Çalışma süresi
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    uptime_str = f"{uptime.days} gün, {uptime.seconds // 3600} saat"

    # İşletim sistemi bilgisi
    uname = os.uname()
    os_info = f"{uname.sysname} {uname.release}"

    # E-posta sistemi durumu
    smtp_status = 'active'  # SMTP sunucusu çalışıyor varsayalım

    # Son e-posta işleme zamanı - son 5 dakika içindeki e-postaları say
    five_mins_ago = datetime.now() - timedelta(minutes=5)
    recent_emails = Email.query.filter(Email.received_date >= five_mins_ago).count()
    email_processing_rate = f"{recent_emails / 5:.1f}"  # e-posta/dakika

    # Son işlenen e-posta zamanı
    last_email = Email.query.order_by(Email.received_date.desc()).first()
    last_email_time = last_email.received_date.strftime("%Y-%m-%d %H:%M") if last_email else "Veri yok"

    health_stats = {
        'cpu_usage': cpu_percent,
        'cpu_cores': cpu_cores,
        'memory_usage': memory.percent,
        'memory_total': memory_total,
        'uptime': uptime_str,
        'os_info': os_info,
        'disk_total': disk_total,
        'disk_used': disk_used,
        'disk_free': disk_free,
        'disk_percent': disk_percent,
        'smtp_status': smtp_status,
        'email_processing_rate': email_processing_rate,
        'last_email_time': last_email_time
    }

    return render_template('system_health.html', health_stats=health_stats)


# Add new route for downloading attachments
@app.route('/email/<int:email_id>/attachment/<filename>')
@login_required
def download_attachment(email_id, filename):
    email = db.session.get(Email, email_id)
    if not email or (not current_user.is_admin and current_user.email not in email.recipients):
        flash('Bu e-postaya erişim yetkiniz yok.', 'danger')
        return redirect(url_for('index'))

    attachments = email.get_attachments()
    attachment = next((a for a in attachments if a['filename'] == filename), None)

    if not attachment:
        flash('Ek bulunamadı.', 'danger')
        return redirect(url_for('view_email', email_id=email_id))

    try:
        file_data = base64.b64decode(attachment['payload'])
        return send_file(
            BytesIO(file_data),
            mimetype=attachment['content_type'],
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Error downloading attachment: {str(e)}")
        flash('Ek indirilirken bir hata oluştu.', 'danger')
        return redirect(url_for('view_email', email_id=email_id))

from werkzeug.security import generate_password_hash

def create_admin_user():
    from app import db
    from models import User

    # Create admin user with proper password hashing
    admin = User(
        username='ob',
        email='ob@example.com',
        password_hash=generate_password_hash('ob123'),
        is_admin=True
    )
    db.session.add(admin)
    db.session.commit()

@app.route('/email/download-selected', methods=['POST'])
@login_required
def download_selected_emails():
    email_ids = request.form.getlist('email_ids[]')
    if not email_ids:
        flash('Lütfen en az bir e-posta seçin.', 'warning')
        return redirect(url_for('index'))

    try:
        # Create a ZIP file containing selected EML files
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for email_id in email_ids:
                email = db.session.get(Email, int(email_id))
                if email and (current_user.is_admin or current_user.email in email.recipients):
                    logger.debug(f"Adding email {email.message_id} to ZIP with folder: {email.folder}")
                    # Write raw binary email data directly to ZIP
                    filename = f"{email.message_id.strip('<>')}.eml"
                    zip_file.writestr(filename, email.raw_email)
                    logger.debug(f"Successfully added email {email.message_id} to ZIP")

        zip_buffer.seek(0)
        response = send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"selected_emails_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        )

        # Add headers to ensure proper handling
        response.headers['Content-Type'] = 'application/zip'
        response.headers['Content-Disposition'] = f'attachment; filename="selected_emails_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip"'
        return response

    except Exception as e:
        logger.error(f"Error creating ZIP file: {str(e)}")
        flash('E-posta arşivi oluşturulurken bir hata oluştu.', 'danger')
        return redirect(url_for('index'))