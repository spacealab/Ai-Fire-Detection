# backend/app.py
from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.security import check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user # اگر از flask_login استفاده می‌کنید
import os # اضافه کردن import os

# Import تنظیمات و مدل‌ها
from model_config import load_yolo_models, get_config
from db_config import db
from user import User
# from create_initial_user import create_initial_user

# Import Blueprints
from api.auth import auth_bp
from api.processing import processing_bp

# --- Initialization ---
load_yolo_models()
config = get_config()
# create_initial_user() # ساخت کاربر اولیه اگر وجود نداشته باشد

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_default_secret_key') # کلید امنیتی برای سشن‌ها

# --- CORS Configuration ---
# اجازه دسترسی از فرانت‌اند NiceGUI که روی پورت دیگری است
CORS(app, resources={r"/api/*": {"origins": "http://localhost:8080"}}, supports_credentials=True) # پورت فرانت را تنظیم کنید

# --- Flask-Login Configuration (اگر استفاده می‌کنید) ---
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.get_user(user_id)

# --- Register Blueprints ---
app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
app.register_blueprint(processing_bp, url_prefix='/api/v1/process')

# --- Basic Routes (مثال) ---
@app.route('/ping') # مسیر ساده برای چک کردن اتصال اولیه فرانت
def ping():
    return jsonify(message="Pong from Backend!")

# --- Error Handling (مثال) ---
@app.errorhandler(404)
def not_found(error):
    return jsonify(error="Not Found"), 404

@app.errorhandler(500)
def internal_error(error):
    # لاگ کردن خطا می‌تواند اینجا اضافه شود
    return jsonify(error="Internal Server Error"), 500


# --- Main Execution ---
if __name__ == '__main__':
    # Note: app.run() is typically used for development.
    # For production, use a WSGI server like Gunicorn behind a reverse proxy like Nginx.
    # The command `flask run` or running wsgi.py might be used instead.
    app.run(debug=True) # debug=True فقط برای توسعه
