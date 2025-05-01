# backend/api/auth.py
from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from user import User # اطمینان حاصل کنید که User قابل ایمپورت است

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    user = User.get_user(username)

    if user and check_password_hash(user.password_hash, password):
        login_user(user) # مدیریت سشن با Flask-Login
        # در صورت موفقیت‌آمیز بودن، می‌توانید اطلاعات کاربر یا توکن را برگردانید
        return jsonify({"message": "Login successful", "user": {"username": user.username}}), 200
    else:
        return jsonify({"error": "Invalid username or password"}), 401

@auth_bp.route('/logout', methods=['POST'])
@login_required # اطمینان از اینکه کاربر لاگین کرده است
def logout():
    logout_user()
    return jsonify({"message": "Logout successful"}), 200

@auth_bp.route('/status', methods=['GET'])
@login_required
def status():
    # یک اندپوینت برای چک کردن وضعیت لاگین کاربر
    return jsonify({"logged_in": True, "user": {"username": current_user.username}}), 200

@auth_bp.errorhandler(401) # مدیریت خطای عدم احراز هویت در این blueprint
def unauthorized(error):
    return jsonify(error="Unauthorized access - please log in"), 401