# backend/api/processing.py
from flask import Blueprint, request, jsonify, current_app
import os
import cv2 # اضافه کردن ایمپورت OpenCV
import numpy as np # اضافه کردن ایمپورت NumPy
import base64 # اضافه کردن ایمپورت base64
from werkzeug.utils import secure_filename
from model_config import get_config, get_detection_order # اضافه کردن get_detection_order
# from image_processing import process_fire_detection # استفاده از تابع پردازش موجود
# from video_processing import process_video
from model_config import yolo_models, model_lock
import logging

# تنظیم لاگر
logger = logging.getLogger(__name__)

# ایجاد Blueprint
processing_bp = Blueprint('processing', __name__)

# --- Image Processing Routes ---
@processing_bp.route('/image', methods=['POST'])
def process_image():
    """API برای پردازش تصویر آپلود شده"""
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No image selected"}), 400
    
    # چک کردن پسوند فایل
    config = get_config()
    allowed_extensions = config["ALLOWED_EXTENSIONS"]
    if not file.filename.lower().endswith(tuple(f'.{ext}' for ext in allowed_extensions if ext in ['png', 'jpg', 'jpeg'])):
        return jsonify({"error": f"File type not allowed. Allowed types: {', '.join(['png', 'jpg', 'jpeg'])}"}), 400
    
    # خواندن تصویر به حافظه
    try:
        in_memory_file = file.read()
        np_arr = np.frombuffer(in_memory_file, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Could not decode image")
    except Exception as decode_err:
         logger.error(f"Error reading/decoding uploaded image: {decode_err}")
         return jsonify({"error": "Could not read or decode image file"}), 400

    try:
        detection_order = get_detection_order()
        # پردازش تصویر با تابع موجود
        # processed_image, results = process_fire_detection(image, detection_order, yolo_models, model_lock)
        
        # انکود تصویر پردازش شده به base64
        # _, buffer = cv2.imencode('.jpg', processed_image)
        # jpg_as_text = base64.b64encode(buffer).decode('utf-8')

        return jsonify({
            "message": "Image processed successfully",
            "status": "success",
            # "annotated_image": 'data:image/jpeg;base64,' + jpg_as_text,
            # "detections": results # ارسال نتایج تشخیص
        }), 200
    except Exception as e:
        logger.exception(f"Error processing image: {e}")
        return jsonify({"error": f"Error processing image: {str(e)}"}), 500

# --- Video Processing Routes ---
@processing_bp.route('/video', methods=['POST'])
def process_video_api():
    """API برای پردازش ویدیو"""
    if 'video' not in request.files:
        return jsonify({"error": "No video file provided"}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({"error": "No video selected"}), 400
    
    # چک کردن پسوند فایل
    config = get_config()
    allowed_extensions = config["ALLOWED_EXTENSIONS"]
    if not file.filename.lower().endswith(tuple(f'.{ext}' for ext in allowed_extensions if ext in ['mp4', 'mkv'])):
        return jsonify({"error": f"File type not allowed. Allowed types: {', '.join(['mp4', 'mkv'])}"}), 400
    
    # ذخیره فایل
    filename = secure_filename(file.filename)
    upload_folder = config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    
    try:
        result_message, output_filename, status_code, results = process_video(file_path, config["RESULTS_FOLDER"])
        
        if status_code == 200:
            # TODO: شاید بخواهید مسیر فایل خروجی را برگردانید یا کار دیگری انجام دهید
            return jsonify({
                "message": result_message,
                "status": "success",
                "output_filename": output_filename # نام فایل ویدئوی پردازش شده
                # "detections": results # نتایج خام ممکن است خیلی بزرگ باشد
            }), 200
        else:
            return jsonify({"error": result_message}), status_code

    except Exception as e:
        logger.exception(f"Error processing video: {e}")
        # پاک کردن فایل آپلود شده در صورت خطا
        if os.path.exists(file_path):
             try:
                 os.remove(file_path)
             except OSError as remove_error:
                 logger.error(f"Error removing uploaded file {file_path} after error: {remove_error}")
        return jsonify({"error": f"Error processing video: {str(e)}"}), 500

# --- Webcam Frame Processing Route --- New Route
@processing_bp.route('/webcam_frame', methods=['POST'])
def process_webcam_frame_api():
    """API برای پردازش یک فریم از وبکم"""
    data = request.get_json()
    if not data or 'frame' not in data:
        return jsonify({"error": "No frame data provided"}), 400

    frame_b64 = data['frame']
    # حذف پیشوند 'data:image/jpeg;base64,' اگر وجود دارد
    if ',' in frame_b64:
        frame_b64 = frame_b64.split(',')[1]

    try:
        # دیکود کردن base64 به تصویر OpenCV
        img_bytes = base64.b64decode(frame_b64)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Could not decode frame from base64")
            
    except Exception as decode_err:
        logger.error(f"Error decoding base64 frame: {decode_err}")
        return jsonify({"error": "Could not decode base64 frame"}), 400

    try:
        detection_order = get_detection_order() # گرفتن ترتیب مدل‌ها
        # استفاده از تابع process_fire_detection موجود برای پردازش فریم
        # این تابع هم تصویر پردازش شده و هم لیست نتایج را برمی‌گرداند
        # processed_frame, results = process_fire_detection(
        #     frame, 
        #     detection_order, 
        #     yolo_models, 
        #     model_lock
        # )

        # انکود کردن فریم پردازش شده به base64
        # _, buffer = cv2.imencode('.jpg', processed_frame)
        # jpg_as_text = base64.b64encode(buffer).decode('utf-8')

        # برگرداندن فریم پردازش شده و نتایج تشخیص
        return jsonify({
            "status": "success",
            # "annotated_frame": 'data:image/jpeg;base64,' + jpg_as_text,
            # "detections": results
        }), 200

    except Exception as e:
        logger.exception(f"Error processing webcam frame: {e}")
        return jsonify({"error": f"Error processing webcam frame: {str(e)}"}), 500
