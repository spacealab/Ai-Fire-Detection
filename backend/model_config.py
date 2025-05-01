# model_config.py
import os
import logging
import threading
from ultralytics import YOLO

# **پیکربندی لاگینگ**
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# **تنظیمات پیش‌فرض**
config = {
    "RESULTS_FOLDER": "results",
    "UPLOAD_FOLDER": "uploads",
    "ALLOWED_EXTENSIONS": ["png", "jpg", "jpeg", "mkv", "mp4"],
    "RESULTS_TEXT_FILE": "results.txt",
    "MODEL_FOLDER": "runs/detect",
    # --- ویرایش: مدل پیش‌فرض را به "Model" تغییر دهید ---
    "DEFAULT_MODEL": "Model",
    # --- ویرایش: فقط یک مدل با نام "Model" و مسیر صحیح آن را نگه دارید ---
    "AVAILABLE_MODELS": {
        "Model": "./runs/detect/best.pt" # مطمئن شوید این مسیر درست است
    },
    "MAX_CONTENT_LENGTH": 50 * 1024 * 1024  # 50MB - Increased file size limit
}

# --- ویرایش: ترتیب تشخیص را فقط به مدل جدید محدود کنید ---
detection_order = [config['DEFAULT_MODEL']]

# **بارگیری مدل‌های YOLO در startup**
yolo_models = {}
model_lock = threading.Lock()

def load_yolo_models():
    """ بارگیری مدل‌های YOLO و ذخیره در دیکشنری yolo_models. """
    global yolo_models, model_lock
    for model_name, model_path in config['AVAILABLE_MODELS'].items():
        # --- ویرایش: اطمینان از اینکه مسیر نسبت به دایرکتوری فعلی backend ساخته می‌شود ---
        # از os.path.abspath برای مسیر مطلق یا os.path.join برای مسیر نسبی دقیق استفاده کنید
        # فرض می‌کنیم مسیر مدل نسبت به دایرکتوری backend است
        full_model_path = os.path.join(os.path.dirname(__file__) or '.', model_path) # استفاده از __file__ برای مسیر دقیق‌تر
        if not os.path.exists(full_model_path):
            logging.error(f"Model file not found at path: {full_model_path} for {model_name}")
            continue
        try:
            with model_lock:
                # --- ویرایش: اضافه کردن task='detect' برای اطمینان از بارگیری صحیح مدل ---
                yolo_models[model_name] = YOLO(full_model_path, task='detect') # اضافه کردن task='detect'
            logging.info(f"Model '{model_name}' loaded successfully from {full_model_path}")
        except Exception as e:
            logging.error(f"Error loading model '{model_name}' from {full_model_path}: {e}")

def get_config():
    """ تابع دسترسی به config. """
    return config

# ... بقیه توابع بدون تغییر ...
def get_detection_order():
    """ تابع دسترسی به detection_order. """
    return detection_order

def get_yolo_models():
    """ تابع دسترسی به yolo_models. """
    return yolo_models

def get_model_lock():
    """ تابع دسترسی به model_lock. """
    return model_lock