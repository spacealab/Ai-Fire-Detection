# import cv2
# import os
# import numpy as np
# import logging
# import datetime
# import ffmpeg
# import concurrent.futures
# import time

# from model_config import detection_order, yolo_models, model_lock
# from image_processing import iou

# logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)
# file_handler = logging.FileHandler('video_processing.log')
# file_handler.setLevel(logging.INFO)
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# file_handler.setFormatter(formatter)
# logger.addHandler(file_handler)

# def generate_unique_filename(folder, prefix, extension):
#     timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
#     file_number = 1
#     while True:
#         filename = f"{prefix}_{timestamp}_{file_number}.{extension}"
#         file_path = os.path.join(folder, filename)
#         if not os.path.exists(file_path):
#             return filename
#         file_number += 1

# def process_frame_section(frame, start_row, end_row):
#     height, width, channels = frame.shape
#     cropped_part = frame[start_row:end_row, 0:width]
#     processed_input_image = np.zeros((640, 640, channels), dtype=np.uint8)
#     processed_input_image[0:(end_row - start_row), 0:width] = cropped_part

#     results = None
#     detected_model = None
#     fire_detected = False  # متغیر جدید برای نشان دادن تشخیص آتش
#     for model_name in detection_order:
#         if model_name not in yolo_models:
#             logger.warning(f"Model '{model_name}' not loaded. Skipping.")
#             continue
#         with model_lock:
#             results = yolo_models[model_name](processed_input_image)
#         if results and results[0].boxes.shape[0] > 0:
#             detected_model = model_name
#             # بررسی اینکه آیا آتش تشخیص داده شده یا نه
#             for class_id in results[0].boxes.cls.cpu().numpy():
#                 detected_class = yolo_models[model_name].names[int(class_id)].lower()
#                 if detected_class in ['fire', 'smoke']:  # فرض می‌کنیم این‌ها کلاس‌های آتش و دود هستن
#                     fire_detected = True
#                     break
#             if fire_detected:
#                 break

#     frame_results = []
#     if detected_model and results and results[0].boxes.shape[0] > 0:
#         boxes = results[0].boxes.xyxy.cpu().numpy()
#         confidences = results[0].boxes.conf.cpu().numpy()
#         class_ids = results[0].boxes.cls.cpu().numpy()

#         for box, confidence, class_id in zip(boxes, confidences, class_ids):
#             x1, y1, x2, y2 = map(int, box)
#             adjusted_x1 = x1
#             adjusted_y1 = y1 + start_row
#             adjusted_x2 = x2
#             adjusted_y2 = y2 + start_row
#             frame_results.append({
#                 'box': [adjusted_x1, adjusted_y1, adjusted_x2, adjusted_y2],
#                 'confidence': float(confidence),
#                 'class_id': class_id,
#                 'model_name': detected_model
#             })

#     return frame_results, fire_detected  # برگردوندن نتایج و وضعیت تشخیص آتش

# def iou_np(box1, box2):
#     x1_inter = max(box1[0], box2[0])
#     y1_inter = max(box1[1], box2[1])
#     x2_inter = min(box1[2], box2[2])
#     y2_inter = min(box1[3], box2[3])

#     inter_area = max(0, x2_inter - x1_inter + 1) * max(0, y2_inter - y1_inter + 1)
#     box1_area = (box1[2] - box1[0] + 1) * (box1[3] - box1[1] + 1)
#     box2_area = (box2[2] - box2[0] + 1) * (box2[3] - box2[1] + 1)
#     iou = inter_area / float(box1_area + box2_area - inter_area)
#     return iou

# def merge_boxes(frame_results, iou_threshold=0.5):
#     if not frame_results:
#         return []

#     boxes_all = np.array([res['box'] for res in frame_results])
#     confidences_all = np.array([res['confidence'] for res in frame_results])
#     class_ids_all = np.array([res['class_id'] for res in frame_results])
#     model_names_all = [res['model_name'] for res in frame_results]

#     sorted_indices = np.argsort(confidences_all)[::-1]
#     boxes_all = boxes_all[sorted_indices]
#     confidences_all = confidences_all[sorted_indices]
#     class_ids_all = class_ids_all[sorted_indices]
#     model_names_all = [model_names_all[i] for i in sorted_indices]

#     merged_boxes = []
#     used_mask = np.zeros(len(boxes_all), dtype=bool)

#     for i in range(len(boxes_all)):
#         if used_mask[i]:
#             continue

#         main_box = boxes_all[i]
#         main_class_id = class_ids_all[i]
#         main_model_name = model_names_all[i]
        
#         merged_box = main_box.copy()

#         for j in range(i + 1, len(boxes_all)):
#             if used_mask[j]:
#                 continue

#             other_box = boxes_all[j]
#             if class_ids_all[j] == main_class_id:
#                 iou_value = iou_np(main_box, other_box)
#                 if iou_value > iou_threshold:
#                     merged_box[0] = min(merged_box[0], other_box[0])
#                     merged_box[1] = min(merged_box[1], other_box[1])
#                     merged_box[2] = max(merged_box[2], other_box[2])
#                     merged_box[3] = max(merged_box[3], other_box[3])
#                     used_mask[j] = True

#         merged_boxes.append({
#             'box': merged_box,
#             'confidence': confidences_all[i],
#             'class_id': main_class_id,
#             'model_name': main_model_name
#         })

#     return merged_boxes

# def overlay_four_frames(frame1, frame2, frame3, frame4, alpha=0.25):
#     """Overlay four frames with 25% opacity each."""
#     temp1 = cv2.addWeighted(frame1, alpha, frame2, alpha, 0.0)
#     temp2 = cv2.addWeighted(frame3, alpha, frame4, alpha, 0.0)
#     combined_frame = cv2.addWeighted(temp1, 0.5, temp2, 0.5, 0.0)
#     return combined_frame

# def draw_boxes(frame, boxes):
#     """Draw bounding boxes on the frame without confidence score."""
#     for res in boxes:
#         box = res['box']
#         class_id = int(res['class_id'])
#         model_name = res['model_name']
#         label = yolo_models[model_name].names[class_id]  # فقط نام کلاس (بدون عدد اطمینان)
#         x1, y1, x2, y2 = map(int, box)
#         cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
#         cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
#     return frame

# def process_video(video_path, output_folder, max_duration=10):
#     try:
#         cap = cv2.VideoCapture(video_path)
#         if not cap.isOpened():
#             os.remove(video_path)
#             return "Error opening video file with OpenCV", None, 400, []

#         fps = cap.get(cv2.CAP_PROP_FPS)
#         video_duration_seconds = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps

#         if video_duration_seconds > max_duration:
#             cap.release()
#             os.remove(video_path)
#             return "Video duration exceeds the limit of 10 seconds", None, 400, []

#         output_filename = generate_unique_filename(output_folder, 'processed_video', 'mkv')
#         output_path = os.path.join(output_folder, output_filename)

#         process = (
#             ffmpeg
#             .input('pipe:', format='rawvideo', pix_fmt='bgr24', s='640x640', r=fps)
#             .output(output_path, vcodec='libx264', acodec='aac', format='matroska', preset='medium')
#             .overwrite_output()
#             .run_async(pipe_stdin=True)
#         )

#         frame_count = 0
#         all_video_results = []
#         start_time = time.time()
#         frame_buffer = []  # برای ذخیره چهار فریم
#         fire_smoke_frame_count = 0  # متغیر برای شمارش فریم‌های حاوی آتش یا دود
#         focus_on_lower = False  # متغیر برای تمرکز روی ۷۰ درصد پایین
#         focus_on_upper = False  # متغیر جدید برای تمرکز روی ۷۰ درصد بالا
#         fire_detection_times = []  # لیست برای ذخیره زمان تشخیص آتش
#         last_detection_time = 0  # زمان آخرین تشخیص
#         last_process_time = 0  # زمان آخرین پردازش
#         hold_box_mode = False  # حالت نگه داشتن باکس

#         with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
#             while True:
#                 ret, frame = cap.read()
#                 if not ret:
#                     logger.info(f"End of video after {frame_count} frames")
#                     break

#                 frame_count += 1
#                 logger.info(f"Processing frame {frame_count}")

#                 resized_frame = cv2.resize(frame, (640, 640))
#                 frame_buffer.append(resized_frame.copy())

#                 if len(frame_buffer) == 4:  # وقتی چهار فریم جمع شد
#                     # ترکیب چهار فریم با شفافیت ۲۵٪
#                     combined_frame = overlay_four_frames(
#                         frame_buffer[0], frame_buffer[1], frame_buffer[2], frame_buffer[3], alpha=0.25
#                     )

#                     # پردازش فریم ترکیبی
#                     height, width, channels = combined_frame.shape
#                     upper_70_height = int(height * 0.7)
#                     lower_70_height = int(height * 0.7)
#                     upper_start = 0
#                     upper_end = upper_70_height
#                     lower_start = height - lower_70_height
#                     lower_end = height

#                     current_time = time.time()

#                     # مدیریت حالت نگه داشتن باکس
#                     if hold_box_mode:
#                         if current_time - last_detection_time >= 0.5:  # اگر ۰.۵ ثانیه گذشته
#                             hold_box_mode = False
#                         if current_time - last_process_time < 0.5:  # اگر کمتر از ۰.۵ ثانیه از آخرین پردازش گذشته
#                             # فقط باکس‌های قبلی رو نگه می‌داریم
#                             filtered_results = all_video_results[-1] if all_video_results else []
#                             for i in range(4):
#                                 frame_buffer[i] = draw_boxes(frame_buffer[i].copy(), filtered_results)
#                             process.stdin.write(frame_buffer[3].tobytes())
#                             logger.info(f"Wrote frame {frame_count} to video stream (holding box)")
#                             frame_buffer.pop(0)
#                             continue  # به سیکل بعدی برو بدون پردازش جدید

#                     # اگر توی حالت نگه داشتن باکس نیستیم یا ۰.۵ ثانیه گذشته، پردازش رو انجام می‌دیم
#                     last_process_time = current_time
#                     lower_future = executor.submit(process_frame_section, combined_frame, lower_start, lower_end)
#                     upper_future = executor.submit(process_frame_section, combined_frame, upper_start, upper_end)
#                     lower_results, fire_detected_lower = lower_future.result()
#                     upper_results, fire_detected_upper = upper_future.result()

#                     # مدیریت حالت‌های تمرکز
#                     if not focus_on_lower and not focus_on_upper:  # حالت عادی
#                         frame_results = lower_results + upper_results
#                     elif focus_on_lower:  # فقط ۷۰ درصد پایین
#                         frame_results = lower_results
#                     elif focus_on_upper:  # فقط ۷۰ درصد بالا
#                         frame_results = upper_results

#                     # بررسی تشخیص آتش
#                     fire_detected = fire_detected_lower or fire_detected_upper
#                     if fire_detected:
#                         fire_detection_times.append(current_time)
#                         last_detection_time = current_time
#                         hold_box_mode = True
#                         if fire_detected_lower and not focus_on_upper:
#                             focus_on_lower = True
#                             focus_on_upper = False
#                         elif fire_detected_upper and not focus_on_lower:
#                             focus_on_upper = True
#                             focus_on_lower = False
#                     else:
#                         # چک کردن ۰.۵ ثانیه عدم تشخیص برای بازگشت به حالت عادی
#                         if fire_detection_times:
#                             last_detection_time_check = max(fire_detection_times)
#                             if current_time - last_detection_time_check > 0.5:
#                                 focus_on_lower = False
#                                 focus_on_upper = False
#                                 fire_detection_times = []

#                     # ادغام باکس‌ها
#                     filtered_results = merge_boxes(frame_results)

#                     # شمارش فریم‌های حاوی آتش یا دود
#                     if filtered_results:
#                         for res in filtered_results:
#                             class_id = res['class_id']
#                             model_name = res['model_name']
#                             detected_class = yolo_models[model_name].names[int(class_id)].lower()
#                             if detected_class in ['fire', 'smoke']:
#                                 fire_smoke_frame_count += 1
#                                 break

#                     # رسم باکس‌ها روی هر چهار فریم
#                     for i in range(4):
#                         frame_buffer[i] = draw_boxes(frame_buffer[i].copy(), filtered_results)

#                     # فقط فریم آخر رو توی خروجی می‌نویسیم
#                     process.stdin.write(frame_buffer[3].tobytes())
#                     logger.info(f"Wrote frame {frame_count} to video stream")
#                     all_video_results.append(filtered_results)

#                     # حذف فریم اول و آماده‌سازی برای فریم بعدی
#                     frame_buffer.pop(0)

#         end_time = time.time()
#         elapsed_time = end_time - start_time
#         fps_processed = frame_count / elapsed_time
#         logger.info(f"Processed {frame_count} frames in {elapsed_time:.2f} seconds. FPS: {fps_processed:.2f}")

#         process.stdin.close()
#         process.wait()
#         logger.info(f"Video processing and streaming to FFmpeg completed for: {output_path}")

#         # نمایش تعداد فریم‌های حاوی آتش یا دود در کنسول
#         print(f"Fire or smoke detected in {fire_smoke_frame_count} sets of frames (each set contains 4 frames).")

#         if frame_count > 0:
#             os.remove(video_path)
#             logger.info(f"Video processing complete. Output saved to: {output_path}")
#             return "Video processed successfully, fire detected in video.", output_filename, 200, all_video_results
#         else:
#             os.remove(video_path)
#             return "No frames detected in video.", None, 200, []

#     except Exception as e:
#         logger.exception(f"Error processing video: {e}")
#         if os.path.exists(video_path):
#             os.remove(video_path)
#         return f"Error processing video: {e}", None, 500, []

# if __name__ == "__main__":
#     result = process_video("sample_video.mp4", "output_folder")
#     print(result)