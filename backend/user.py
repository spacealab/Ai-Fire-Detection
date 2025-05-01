#user.py
from flask_login import UserMixin
from db_config import db  # Import the db connection

class User(UserMixin):
    def __init__(self, username, password_hash):
        self.id = username  # Use username as ID for simplicity
        self.username = username
        self.password_hash = password_hash

    @staticmethod
    def get_user(username):
        """دریافت کاربر از دیتابیس بر اساس نام کاربری."""
        users_collection = db.users  # فرض میکنیم کالکشن کاربران 'users' نام دارد
        user_data = users_collection.find_one({'username': username})
        if user_data:
            return User(user_data['username'], user_data['password_hash'])
        return None

    @staticmethod
    def create_user(username, password_hash):
        """ایجاد کاربر جدید در دیتابیس."""
        users_collection = db.users
        try:
            user_data = {'username': username, 'password_hash': password_hash}
            users_collection.insert_one(user_data)
            return True  # کاربر با موفقیت ایجاد شد
        except Exception as e:
            print(f"Error creating user: {e}")
            return False  # خطایی در ایجاد کاربر رخ داد