#db_config.py
from pymongo import MongoClient

def connect_to_mongodb():
    """اتصال به دیتابیس MongoDB."""
    try:
        # **رشته اتصال برای دیتابیس MongoDB محلی (بدون احراز هویت)**
        client = MongoClient("mongodb://localhost:27017/")  # 👈 رشته اتصال ساده برای localhost:27017
        db = client.fire_detection_db  # اسم دیتابیس دلخواهتون (fire_detection_db)
        print("Connected to MongoDB")
        return db
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return None

db = connect_to_mongodb()  # اتصال در هنگام import شدن این فایل