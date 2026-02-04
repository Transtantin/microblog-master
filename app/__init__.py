from flask import Flask
from config import Config # Импортируем наш класс
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)
app.config.from_object(Config) # Загружаем настройки

db = SQLAlchemy(app)
migrate = Migrate(app, db)

from app import routes, models # Импортируем модели (мы их сейчас создадим)