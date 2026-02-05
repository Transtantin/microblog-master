from flask import render_template, flash, redirect, url_for, request
from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User
from urllib.parse import urlsplit
import sqlalchemy as sa
from datetime import datetime, timezone
from app.forms import PostForm
from app.models import Post 


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    
    # ЛОГИКА СОХРАНЕНИЯ ПОСТА
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Ваш пост опубликован!')
        return redirect(url_for('index'))
    
    # ЛОГИКА ОТОБРАЖЕНИЯ ПОСТОВ
    # sa.select(Post) - выбрать посты
    # .order_by(Post.timestamp.desc()) - сортировать по времени (сначала новые)
    # db.session.scalars(...) - выполнить запрос и получить список объектов
    posts = db.session.scalars(sa.select(Post).order_by(Post.timestamp.desc())).all()
        
    return render_template("index.html", title='Home Page', form=form, posts=posts)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username==form.username.data))

        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))

        login_user(user, remember=form.remember_me.data)

        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)

    return render_template('login.html', title = 'Sign In', form = form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form =  RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f'Пользователь {form.username.data} успешно зарегистрирован!')
        return redirect(url_for('login'))

    return render_template('register.html', title='Register', form = form)


@app.route('/user/<username>')
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))

    posts = [
        {'author': user, 'body': 'Тестовый пост #1'},
        {'author': user, 'body': 'Тестовый пост #2'}
    ]
    return render_template('user.html', user=user, posts=posts)



@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()


@app.route('/edit_profile', methods = ['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Ваши изменения сохранены.')
        return redirect(url_for('edit_profile'))
    elif request.method =='GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title = 'Редактировать профиль', form = form)


@app.route('/edit_post/<int:id>', methods = ['GET', 'POST'])
@login_required
def edit_post(id):
    post = db.first_or_404(sa.select(Post).where(Post.id == id))

    if post.author != current_user:
        flash('Вы не можете едактировать этот пост.')
        return redirect(url_for('index'))

    form = PostForm()
    if form.validate_on_submit():
        post.body = form.post.data
        db.session.commit()
        flash('Ваш пост был обновлен.')
        return redirect(url_for('index'))
    elif request.method =='GET':
        form.post.data = post.body

    return render_template('edit_post.html', title = 'Редактирование поста', form = form)


@app.route('/delete_post/<int:id>')
@login_required
def delete_post(id):
    post = db.first_or_404(sa.select(Post).where(Post.id == id))

    if post.author != current_user:
        flash('Вы не можете удалить этот пост.')
        return redirect(url_for('index'))

    db.session.delete(post)
    db.session.commit()
    flash('Пост удален.')
    return redirect(url_for('index'))
