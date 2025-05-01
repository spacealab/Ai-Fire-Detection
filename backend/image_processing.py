# # image_processing.py
# import cv2
# import numpy as np
# import logging
# import threading # Keep threading for parallel section processing
# from ultralytics import YOLO

# logger = logging.getLogger(__name__)
# # ... (logger setup if needed) ...

# def iou(box1, box2):
#     # ... (IoU function remains the same) ...
#     x1_1, y1_1, x2_1, y2_1 = box1
#     x1_2, y1_2, x2_2, y2_2 = box2
#     x_left = max(x1_1, x1_2)
#     y_top = max(y1_1, y1_2)
#     x_right = min(x2_1, x2_2)
#     y_bottom = min(y2_1, y2_2)
#     if x_right < x_left or y_bottom < y_top: return 0.0
#     intersection_area = (x_right - x_left) * (y_bottom - y_top)
#     box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
#     box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
#     iou = intersection_area / float(box1_area + box2_area - intersection_area + 1e-6) # Add epsilon
#     return iou

# def process_fire_detection(image, detection_order, yolo_models, model_lock, progress_callback=None):
#     """
#     Processes an image (from upload or webcam frame) for fire detection.

#     Args:
#         image (numpy.ndarray): The input image.
#         detection_order (list): List of model names.
#         yolo_models (dict): Loaded YOLO models.
#         model_lock (threading.Lock): Lock for models.
#         progress_callback (callable, optional): Callback for progress update (0-100).

#     Returns:
#         tuple: (processed_image_with_boxes, results_list)
#                For webcam endpoint (/process_frame), only results_list is typically used.
#                For upload endpoint (/upload), both might be used.
#     """
#     if image is None:
#         logger.error("Received None image in process_fire_detection")
#         return None, []

#     original_height, original_width = image.shape[:2]
#     if original_height == 0 or original_width == 0:
#          logger.error(f"Received image with invalid dimensions: {original_width}x{original_height}")
#          return image, [] # Return original image on error

#     # Resize image to 640x640 for processing
#     try:
#         resized_image = cv2.resize(image, (640, 640))
#     except Exception as resize_err:
#         logger.error(f"Error resizing image: {resize_err}")
#         return image, [] # Return original on error

#     height, width, channels = resized_image.shape

#     # Define image sections (top 70%, bottom 70%)
#     upper_70_height = int(height * 0.7)
#     lower_70_height = int(height * 0.7)
#     upper_start = 0
#     upper_end = upper_70_height
#     lower_start = height - lower_70_height
#     lower_end = height

#     all_results_raw = [] # Store raw results before merging
#     detection_lock = threading.Lock() # Lock for appending results safely

#     if progress_callback: progress_callback(5)

#     # Function to process a section
#     def process_section(start_row, end_row):
#         nonlocal all_results_raw
#         section_results = []
#         # Create zero array matching model input size
#         processed_input_image = np.zeros((640, 640, channels), dtype=np.uint8)
#         # Copy the cropped part into the top-left of the zero array
#         cropped_part = resized_image[start_row:end_row, 0:width]
#         h_crop, w_crop, _ = cropped_part.shape
#         processed_input_image[0:h_crop, 0:w_crop] = cropped_part


#         detected_model = None
#         model_results = None # Store results from the model call
#         for model_name in detection_order:
#             if model_name not in yolo_models:
#                 logger.warning(f"Model '{model_name}' not loaded. Skipping.")
#                 continue
#             try:
#                 with model_lock: # Use the global lock for thread-safe model inference
#                     model_results = yolo_models[model_name](processed_input_image, verbose=False) # verbose=False reduces console spam
#             except Exception as model_err:
#                 logger.error(f"Error during model inference ({model_name}): {model_err}")
#                 continue # Try next model

#             # Check if model_results is not None and has boxes
#             if model_results and model_results[0].boxes and model_results[0].boxes.shape[0] > 0:
#                 detected_model = model_name
#                 break # Stop after first model detects something

#         if detected_model and model_results and model_results[0].boxes:
#             boxes = model_results[0].boxes.xyxy.cpu().numpy()
#             confidences = model_results[0].boxes.conf.cpu().numpy()
#             class_ids = model_results[0].boxes.cls.cpu().numpy()

#             for box, confidence, class_id in zip(boxes, confidences, class_ids):
#                 # Adjust box coordinates back relative to the *resized_image* (640x640)
#                 x1, y1, x2, y2 = map(int, box)
#                 # Check coordinates are within the cropped area before adjusting
#                 if y2 <= h_crop and x2 <= w_crop: # Only consider boxes fully within the input crop
#                     adjusted_x1 = x1
#                     adjusted_y1 = y1 + start_row # Add the offset
#                     adjusted_x2 = x2
#                     adjusted_y2 = y2 + start_row # Add the offset
#                     # Clip coordinates to be within the resized_image boundaries
#                     adjusted_x1 = max(0, adjusted_x1)
#                     adjusted_y1 = max(0, adjusted_y1)
#                     adjusted_x2 = min(width - 1, adjusted_x2)
#                     adjusted_y2 = min(height - 1, adjusted_y2)

#                     if adjusted_x1 < adjusted_x2 and adjusted_y1 < adjusted_y2: # Ensure valid box
#                         section_results.append({
#                             'box': [adjusted_x1, adjusted_y1, adjusted_x2, adjusted_y2],
#                             'confidence': float(confidence),
#                             'class_id': int(class_id),
#                             'model_name': detected_model
#                         })
#         # Safely append results from this thread
#         with detection_lock:
#             all_results_raw.extend(section_results)

#     # Run section processing in parallel
#     upper_thread = threading.Thread(target=process_section, args=(upper_start, upper_end))
#     lower_thread = threading.Thread(target=process_section, args=(lower_start, lower_end))
#     upper_thread.start()
#     lower_thread.start()
#     upper_thread.join()
#     lower_thread.join()

#     if progress_callback: progress_callback(70)

#     # Filter/Merge overlapping boxes (Non-Maximum Suppression logic simplified)
#     filtered_results_final = []
#     if all_results_raw:
#         # Sort by confidence descending
#         all_results_raw.sort(key=lambda x: x['confidence'], reverse=True)
#         suppressed = [False] * len(all_results_raw)
#         for i in range(len(all_results_raw)):
#             if suppressed[i]:
#                 continue
#             # Keep the box with highest confidence
#             filtered_results_final.append(all_results_raw[i])
#             # Suppress overlapping boxes with lower confidence
#             for j in range(i + 1, len(all_results_raw)):
#                 if not suppressed[j]:
#                     iou_value = iou(np.array(all_results_raw[i]['box']), np.array(all_results_raw[j]['box']))
#                     # Adjust IoU threshold as needed (e.g., 0.4)
#                     if iou_value > 0.4:
#                         suppressed[j] = True

#     if progress_callback: progress_callback(90)

#     # Draw boxes on a copy of the *resized* image for potential return
#     processed_image_resized = resized_image.copy()
#     if filtered_results_final:
#         for res in filtered_results_final:
#             box = res['box']
#             confidence = res['confidence']
#             class_id = res['class_id']
#             model_name = res['model_name']
#             class_name = "N/A"
#             if model_name in yolo_models:
#                 class_name = yolo_models[model_name].names.get(class_id, f"ID_{class_id}")

#             label = f"{class_name} {confidence:.2f}"
#             x1, y1, x2, y2 = map(int, box) # Coordinates are already for 640x640
#             # Draw rectangle
#             color = (0, 0, 255) if class_name.lower() in ['fire', 'smoke'] else (0, 255, 0)
#             cv2.rectangle(processed_image_resized, (x1, y1), (x2, y2), color, 2)
#             # Draw label background
#             (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
#             cv2.rectangle(processed_image_resized, (x1, y1 - h - 5), (x1 + w, y1), color, -1)
#             # Draw label text
#             cv2.putText(processed_image_resized, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)


#     # Resize the processed image back to original dimensions
#     processed_image_original_size = cv2.resize(processed_image_resized, (original_width, original_height))

#     if progress_callback: progress_callback(100)

#     # Return both the image with boxes and the list of detection results
#     return processed_image_original_size, filtered_results_final