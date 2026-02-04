from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo, Length, Regexp
import sqlalchemy as sa
from app import db
from app.models import User
import re

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(message="Пожалуйста, введите email")])

    password = PasswordField('Пароль', validators=[
        DataRequired(),
        Length(min=4, max=16, message="Пароль должен быть от 4 до 16 символов")
    ])

    password2 = PasswordField('Повторите пароль', validators=[
        DataRequired(),
        EqualTo('password', message="Пароли должны совпадать")
        ])

    submit = SubmitField('Зарегистрироваться')

    def validate_username(self, username):
        user= db.session.scalar(sa.select(User).where(User.username==username.data))
        if user is not None:
            raise ValidationError('Это имя уже занято. Пожалуйста, используйте другое имя пользователя.')

    def validate_email(self, email):
        user= db.session.scalar(sa.select(User).where(User.email==email.data))
        if user is not None:
            raise ValidationError('Эта почта уже занято. Пожалуйста, используйте другой адрес электронной почты.')
    
    def validate_password(self, password):
        pwd=password.data
        if len(pwd) < 4 or len(pwd) > 16:
            raise ValidationError('Пароль должен содержать от 4 до 16 символов')

        if re.search(r'[\*&{}|+]', pwd):
            raise ValidationError('Пароль не должен содержать запрещенных символов (* & { } | +)')
        
        if not re.search(r'[A-ZА-Я]', pwd): # Учитываем и русские и английские
            raise ValidationError('Пароль должен содержать хотя бы одну заглавную букву')
        
        if not re.search(r'\d', pwd):
            raise ValidationError('Пароль должен содержать хотя бы одну цифру')
                
    
        