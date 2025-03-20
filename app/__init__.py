from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
import os


db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'app\\static\\uploads\\')  # Папка для загрузки аватарок
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}  # Разрешенные форматы файлов
print(f"#################################3 {os.getcwd()}")

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    # Инициализация расширений
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    # Указываем страницу для перенаправления неавторизованных пользователей
    login_manager.login_view = 'auth.login'

    # Регистрация маршрутов
    from .routes import bp as main_bp
    from .auth import auth_bp
    
    with app.app_context():
        if not os.path.exists('db.sqlite'):
            print("База данных не найдена. Создаём новую...")
            db.create_all()
            print("База данных успешно создана.")

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')

    return app

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))