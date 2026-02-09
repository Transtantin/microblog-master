from flask import render_template, flash, redirect, url_for, request
from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, SearchForm, PostForm, ChangePasswordForm 
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User
from urllib.parse import urlsplit
import sqlalchemy as sa
from datetime import datetime, timezone
from app.models import Post 
from wtforms.validators import Optional
from functools import wraps
from flask import abort
import os
import secrets
from PIL import Image


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    # 1. Форма создания поста
    post_form = PostForm()
    if post_form.validate_on_submit():
        post = Post(body=post_form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('index'))

    # 2. Форма поиска
    search_form = SearchForm(request.args, meta={'csrf': False})

    # НАЧАЛО БЛОКА ВЫБОРКИ
    show_followed = False

    if current_user.is_authenticated and request.args.get('feed') == 'following':
        show_followed = True
        query = current_user.following_posts()
    else:
        # ВОТ ЭТОТ ELSE ОБЯЗАТЕЛЕН
        query = sa.select(Post).join(Post.author)

    # 4. Фильтрация
    if search_form.q.data:
        search_term = f"%{search_form.q.data}%"
        query = query.where(
            sa.or_(
                Post.body.ilike(search_term),
                User.username.ilike(search_term)
            )
        )
    
    if search_form.date_from.data:
        date_from = datetime.combine(search_form.date_from.data, datetime.min.time())
        query = query.where(Post.timestamp >= date_from)

    if search_form.date_to.data:
        date_to = datetime.combine(search_form.date_to.data, datetime.max.time())
        query = query.where(Post.timestamp <= date_to)

    # 5. Сортировка
    if search_form.sort_by.data == 'oldest':
        query = query.order_by(Post.timestamp.asc())
    elif search_form.sort_by.data == 'author_asc':
        query = query.order_by(User.username.asc())
    elif search_form.sort_by.data == 'author_desc':
        query = query.order_by(User.username.desc())
    else:
        query = query.order_by(Post.timestamp.desc())

    page = request.args.get('page', 1, type=int)
    posts = db.paginate(query, page=page, per_page=app.config['POSTS_PER_PAGE'], error_out=False)

    next_url = url_for('index', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) if posts.has_prev else None
    
    if current_user.is_authenticated:
    # Передаем ОБЕ формы
        return render_template("index.html", title='Главная', 
                            post_form=post_form, 
                            search_form=search_form, 
                            posts=posts.items, 
                            next_url=next_url,
                            prev_url=prev_url,
                            show_followed=show_followed)
    else:
        return render_template("index.html", title='Главная',
                            search_form=search_form, 
                            posts=posts.items,
                            next_url=next_url,
                            prev_url=prev_url)
                           

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username==form.username.data))

        if user is None or not user.check_password(form.password.data):
            flash('Неверный логин или пароль')
            return redirect(url_for('login'))
        if user.blocked:
            flash('Ваш аккаунт заблокирован администратором.')
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

    page = request.args.get('page', 1, type=int)
    query = sa.select(Post).where(Post.author == user).order_by(Post.timestamp.desc())

    posts = db.paginate(query, page=page, per_page=app.config['POSTS_PER_PAGE'], error_out=False)
    
    next_url = url_for('user', username=user.username, page=posts.next_num) if posts.has_next else None
    prev_url = url_for('user', username=user.username, page=posts.prev_num) if posts.has_prev else None

    return render_template('user.html', user=user, posts=posts.items, 
                           next_url=next_url, prev_url=prev_url)



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
        if form.avatar.data:
            picture_file = save_picture(form.avatar.data)
            current_user.avatar_file = picture_file

        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Ваши изменения сохранены.')
        return redirect(url_for('edit_profile'))
    elif request.method =='GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title = 'Редактировать профиль', form = form)


@app.route('/edit_post/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_post(id):
    post = db.first_or_404(sa.select(Post).where(Post.id == id))

    if post.author != current_user:
        flash('Вы не можете редактировать этот пост.')
        return redirect(url_for('index'))

    form = PostForm()
    if form.validate_on_submit():
        post.body = form.post.data
        db.session.commit()
        return redirect(url_for('index'))
    elif request.method == 'GET':
        form.post.data = post.body

    return render_template('edit_post.html', title='Редактирование поста', form=form)


@app.route('/delete_post/<int:id>')
@login_required
def delete_post(id):
    post = db.first_or_404(sa.select(Post).where(Post.id == id))

    if post.author != current_user and not current_user.is_admin():
        flash('Вы не можете удалить этот пост.')
        return redirect(url_for('index'))

    db.session.delete(post)
    db.session.commit()
    
        
    return redirect(url_for('index'))



@app.route('/follow/<username>')
@login_required
def follow(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    if user == current_user:
        flash('Вы не можете подписаться на самого себя!')
        return redirect(url_for('user', username= username))
    
    current_user.follow(user)
    db.session.commit()
    flash(f'Вы подписались на {username}!')
    return redirect(url_for('user', username = username))


@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    if user == current_user:
        flash('Вы не можете отписаться от самого себя!')
        return redirect(url_for('user', username= username))
    
    current_user.unfollow(user)
    db.session.commit()
    flash(f'Вы отписались от {username}!')
    return redirect(url_for('user', username = username))



@app.route('/search')
@login_required
def search():
    form = SearchForm(request.args, meta={'csrf': False})

    query = sa.select(Post).join(Post.author)

    # поиск по тексту или автору
    if form.q.data:
        search_term = f"%{form.q.data}%"
        query = query.where(
            sa.or_(
                Post.body.ilike(search_term),
                User.username.ilike(search_term)
            )
        )

    # с даты
    if form.date_from.data:
        date_from = datetime.combine(form.date_from.data, datetime.min.time())
        query = query.where(Post.timestamp >= date_from)

    # по дату
    if form.date_to.data:
        date_to = datetime.combine(form.date_to.data, datetime.max.time())
        query = query.where(Post.timestamp <= date_to)  

    # сортировка
    if form.sort_by.data == 'oldest':
        query = query.order_by(Post.timestamp.asc())
    elif form.sort_by.data == 'author_asc':
        query = query.order_by(User.username.asc())  
    elif form.sort_by.data == 'author_desc':
        query = query.order_by(User.username.desc()) 
    else:
        query = query.order_by(Post.timestamp.desc())

    posts = db.session.scalars(query).all()

    return render_template('search.html', title='Поиск', form=form, posts=posts)


def admin_required(f):
    @wraps(f)
    def decorated_functions(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated_functions


@app.route('/admin/stats')
@login_required
@admin_required
def admin_stats():
    user_count = db.session.scalar(sa.select(sa.func.count(User.id)))
    posts_count = db.session.scalar(sa.select(sa.func.count(Post.id)))
    avg_post_len = db.session.scalar(sa.select(sa.func.avg(sa.func.length(Post.body))))
    if avg_post_len:
        avg_post_len = round(avg_post_len, 1)
    else:
        avg_post_len = 0
    
    acctive_users = db.session.execute(
        sa.select(User.username, sa.func.count(Post.id).label('total'))
        .join(Post)
        .group_by(User.id)
        .order_by(sa.desc('total'))
        .limit(3)
    ).all()
    return render_template('admin_stats.html',
                            users_count=user_count,
                            posts_count=posts_count,
                            avg_post_len=avg_post_len,
                            active_users=acctive_users)


@app.route('/admin/block/<int:user_id>')
@login_required
@admin_required
def block_user(user_id):
    user = db.session.get(User, user_id)
    if user and user.role != 'admin': 
        user.blocked = True
        db.session.commit()
        flash(f'Пользователь {user.username} заблокирован.')
    return redirect(url_for('admin_users')) 

@app.route('/admin/unblock/<int:user_id>')
@login_required
@admin_required
def unblock_user(user_id):
    user = db.session.get(User, user_id)
    if user:
        user.blocked = False
        db.session.commit()
        flash(f'Пользователь {user.username} разблокирован.')
    return redirect(url_for('admin_users'))


@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = db.session.scalars(sa.select(User).order_by(User.id)).all()
    return render_template('admin_users.html', users=users)


@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        if not current_user.check_password(form.old_password.data):
            flash('Неверный старый пароль.')
            return redirect(url_for('change_password'))
        
        current_user.set_password(form.new_password.data)
        db.session.commit()
        
        flash('Ваш пароль был успешно изменен.')
        return redirect(url_for('user', username=current_user.username))
        
    return render_template('change_password.html', title='Смена пароля', form=form)


def save_picture(form_picture):
    # Генерируем случайное имя (чтобы не было коллизий)
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    
    # Полный путь для сохранения
    picture_path = os.path.join(app.root_path, 'static/avatars', picture_fn)
    
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    
    return picture_fn