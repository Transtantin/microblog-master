from datetime import datetime, timezone
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from hashlib import md5
from flask import url_for

followers = db.Table('followers',
    db.Column('follower_id', sa.Integer, sa.ForeignKey('user.id'), primary_key=True),
    db.Column('followed_id', sa.Integer, sa.ForeignKey('user.id'), primary_key=True)
)

class User( UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    about_me: so.Mapped[Optional[str]] = so.mapped_column(sa.String(140))
    last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(default=lambda: datetime.now(timezone.utc))
    posts: so.WriteOnlyMapped['Post'] = so.relationship(back_populates='author')
    role: so.Mapped[str] = so.mapped_column(sa.String(20), default='user')
    blocked: so.Mapped[bool] = so.mapped_column(default=False)
    avatar_file: so.Mapped[str] = so.mapped_column(sa.String(20), default='default.png', server_default='default.jpg')

    def avatar(self, size):
        if not self.avatar_file:
            return url_for('static', filename='avatars/default.png')
        return url_for('static', filename='avatars/' + self.avatar_file)
    
    def is_admin(self):
        return self.role == 'admin'


    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    following: so.WriteOnlyMapped['User'] = so.relationship(
        secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'),
        lazy='dynamic'
    )

    # Методы управления подпиской
    def follow(self, user):
        if not self.is_following(user):
            self.following.add(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.following.remove(user)

    def is_following(self, user):
        query = self.following.select().where(User.id == user.id)
        return db.session.scalar(query) is not None

    # Самое главное: запрос постов от тех, на кого подписан
    def following_posts(self):
        Author = so.aliased(User)
        return (
            sa.select(Post)
            .join(Post.author.of_type(Author))
            .join(followers, followers.c.followed_id == Author.id)
            .where(followers.c.follower_id == self.id)
            .order_by(Post.timestamp.desc())
        )

class Post(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    body: so.Mapped[str] = so.mapped_column(sa.String(140))
    timestamp: so.Mapped[datetime] = so.mapped_column(index=True, default=lambda: datetime.now(timezone.utc))
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)

    # Связь: у каждого поста есть один автор (User)
    author: so.Mapped[User] = so.relationship(back_populates='posts')

    def __repr__(self):
        return f'<Post {self.body}>'
    

@login.user_loader
def load_user(id):
    return db.session.get(User,int(id))