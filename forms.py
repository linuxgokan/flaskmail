from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DateField
from wtforms.validators import DataRequired, Email, Length
from datetime import datetime

class LoginForm(FlaskForm):
    username = StringField('Kullanıcı', validators=[DataRequired()])
    password = PasswordField('Parola', validators=[DataRequired()])
    submit = SubmitField('Giriş')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField('Register')

class SearchForm(FlaskForm):
    query = StringField('Arama', validators=[DataRequired()])
    start_date = DateField('Başlangıç Tarihi', format='%Y-%m-%d')  # HTML5 date input format
    end_date = DateField('Bitiş Tarihi', format='%Y-%m-%d')  # HTML5 date input format
    submit = SubmitField('Ara')

    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)
        # Türkçe ay isimleri
        self.tr_months = {
            '01': 'Ocak', '02': 'Şubat', '03': 'Mart', '04': 'Nisan',
            '05': 'Mayıs', '06': 'Haziran', '07': 'Temmuz', '08': 'Ağustos',
            '09': 'Eylül', '10': 'Ekim', '11': 'Kasım', '12': 'Aralık'
        }

    def format_date(self, date):
        if date:
            return date.strftime(f"{self.tr_months[date.strftime('%m')]} %d, %Y")
        return ""

class AdminUserCreateForm(FlaskForm):
    username = StringField('Kullanıcı Adı', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('E-posta', validators=[DataRequired(), Email()])
    password = PasswordField('Şifre', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField('Kullanıcı Oluştur')