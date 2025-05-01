# from werkzeug.security import generate_password_hash
# from db_config import db  # Import the db connection

# def create_initial_user():
#     """ایجاد کاربر اولیه در دیتابیس (فقط برای تست)."""
#     users_collection = db.users  # دسترسی به کالکشن 'users' از شیء db که از db_config.py import کردیم
#     existing_user = users_collection.find_one({'username': 'spacelab'})  # جستجو برای کاربر با نام کاربری 'spacelab'
#     if not existing_user: # اگر کاربر با این نام کاربری وجود نداشت
#         password_hash = generate_password_hash('00000000') # هش کردن رمز عبور 
#         user_data = {'username': 'spacelab', 'password_hash': password_hash} # ایجاد دیکشنری اطلاعات کاربر
#         users_collection.insert_one(user_data) # درج سند کاربر جدید در کالکشن
#         print("Initial test user created.") # چاپ پیام موفقیت
#     else:
#         print("Initial test user already exists.") # چاپ پیام اگر کاربر از قبل وجود داشته

# if __name__ == '__main__':
#     create_initial_user() # اجرای تابع create_initial_user وقتی فایل مستقیماً اجرا میشه