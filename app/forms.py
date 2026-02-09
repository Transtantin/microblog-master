from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo, Length, Regexp, Optional
import sqlalchemy as sa
from app import db
from app.models import User
import re
from flask_wtf.file import FileField, FileAllowed

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
                
    
class EditProfileForm(FlaskForm):
    username= StringField('Имя пользователя', validators=[DataRequired()])
    about_me = TextAreaField('О себе', validators=[Length(min=0, max=140)]) 
    avatar = FileField('Обновить фото профиля', validators=[
        FileAllowed(['jpg', 'png', 'jpeg'], 'Только картинки (jpg, png)!') 
    ])
    submit = SubmitField('Подтвердить')      

    def __init__(self, original_username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = db.session.scalar(sa.select(User).where(User.username == username.data))
            if user is not None:
                raise ValidationError('Это имя уже занято. Пожалуйста, используйте другое имя пользователя.')


class PostForm(FlaskForm):
    post = TextAreaField('Напишите что-нибудь...', validators=[
        DataRequired(),
        Length(min=1, max=140)
    ])
    submit = SubmitField('Опубликовать')


class SearchForm(FlaskForm):
    q=StringField('Поиск', validators=[])
    date_from = DateField('С даты', format='%Y-%m-%d', validators=[Optional()], render_kw={"type": "date"})
    date_to = DateField('По дату', format='%Y-%m-%d', validators=[Optional()], render_kw={"type": "date"})
    sort_by = SelectField('Сортировка', choices=[
        ('newest', 'Сначала новые'),
        ('oldest', 'Сначала старые'),
        ('author_asc', 'Автор (А-Я)'),
        ('author_desc', 'Автор (Я-А)')
    ])
    submit = SubmitField('Найти')

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Старый пароль', validators=[DataRequired()])
    
    new_password = PasswordField('Новый пароль', validators=[
        DataRequired(),
        Length(min=4, max=16, message="Пароль должен быть от 4 до 16 символов")
    ])
    
    confirm_password = PasswordField('Повторите новый пароль', validators=[
        DataRequired(),
        EqualTo('new_password', message="Пароли должны совпадать")
    ])
    
    submit = SubmitField('Сменить пароль')

    def validate_new_password(self, password):
        pwd = password.data
        if re.search(r'[\*&{}|+]', pwd):
            raise ValidationError('Пароль содержит запрещенные символы (* & { } | +)')
        if not re.search(r'[A-ZА-Я]', pwd):
            raise ValidationError('Пароль должен содержать хотя бы одну заглавную букву')
        if not re.search(r'\d', pwd):
            raise ValidationError('Пароль должен содержать хотя бы одну цифру')