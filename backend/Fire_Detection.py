#Fire_Detection.py
import cv2
import numpy as np
import time
from ultralytics import YOLO
from collections import defaultdict
import requests
import base64
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Fire_Detection")

# توجه: پورت ws_server.py به 8010 تغییر کرد
WS_SERVER_URL = 'http://localhost:8010/push_image'

def inference(
    model,
    mode,
    task,
    video_path=None,
    save_output=False,
    output_path="output.mp4",
    show_output=True,
    count=False,
    show_tracks=False,
    imgsz=320,  # Image size 320x320
    max_fps=30,  # Maximum FPS
):
    # Initialize video capture based on mode
    if mode == "cam":
        cap = cv2.VideoCapture(0)
    # Commenting out video input handling as we only want to use webcam
    # elif mode == "video":
    #     if video_path is None:
    #         raise ValueError("Please provide a valid video path for video mode.")
    #     cap = cv2.VideoCapture(video_path)

    # Commenting out invalid mode error for video
    # else:
    #     raise ValueError("Invalid mode. Use 'cam' or 'video'.")

    if not cap.isOpened():
        print("Error: Could not open video source")
        return

    # Initialize tracking and counting variables
    track_history = defaultdict(lambda: [])
    seen_ids_per_class = defaultdict(set)

    # Video writer setup
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    input_fps = cap.get(cv2.CAP_PROP_FPS) or 30  # Default to 30 FPS if not specified
    out = None

    # Minimum frame time for desired FPS
    min_frame_time = 1.0 / max_fps

    while cap.isOpened():
        frame_start_time = time.time()  # Start time for the frame

        success, frame = cap.read()
        if not success:
            print("Failed to read frame or end of video")
            break

        # Resize the webcam frame to 320x320 before processing
        # frame = cv2.resize(frame, (320, 320))

        start_time = time.time()
        class_counts = defaultdict(int)

        # Perform inference
        try:
            if task == "track":
                results = model.track(frame, conf=0.3, persist=True, tracker="bytetrack.yaml", imgsz=imgsz, device="cpu")
            elif task == "detect":
                results = model.predict(frame, conf=0.5, imgsz=imgsz, device="cpu")
            else:
                raise ValueError("Invalid task. Use 'detect' or 'track'.")
        except Exception as e:
            print(f"Inference failed with error: {e}")
            break

        end_time = time.time()
        annotated_frame = results[0].plot()

        # Process results
        if results[0].boxes and results[0].boxes.cls is not None:
            boxes = results[0].boxes.xywh.cpu()
            class_ids = results[0].boxes.cls.int().cpu().tolist()
            names = results[0].names

            if task == "track" and results[0].boxes.id is not None:
                track_ids = results[0].boxes.id.int().cpu().tolist()

                for box, cls_id, track_id in zip(boxes, class_ids, track_ids):
                    x, y, w, h = box
                    class_name = names[cls_id]

                    if count:
                        seen_ids_per_class[class_name].add(track_id)

                    if show_tracks:
                        track = track_history[track_id]
                        track.append((float(x), float(y)))
                        if len(track) > 30:
                            track.pop(0)
                        points = np.hstack(track).astype(np.int32).reshape((-1, 1, 2))
                        cv2.polylines(annotated_frame, [points], isClosed=False, color=(230, 230, 230), thickness=10)

            elif task == "detect" and count:
                for cls_id in class_ids:
                    class_counts[names[cls_id]] += 1

        # ارسال تصویر پردازش‌شده به ws_server.py از طریق POST (بدون تاخیر)
        try:
            _, buffer = cv2.imencode('.jpg', annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])  # کیفیت مناسب برای سرعت
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            response = requests.post(WS_SERVER_URL, json={"image_b64": jpg_as_text}, timeout=0.5)
            if response.status_code != 200:
                logger.error(f"Failed to send image via POST: {response.status_code} - {response.text}")
            else:
                logger.debug("Image sent to ws_server via POST.")
        except requests.exceptions.Timeout:
            logger.warning("Timeout sending image to ws_server (skip frame)")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error sending image via POST: {e}. Is ws_server.py running?")
        except Exception as e:
            logger.error(f"HTTP POST error sending image: {e}")

        # Commenting out class count display as it's not needed
        # if count:
        #     x0, y0 = 10, annotated_frame.shape[0] - 80
        #     if task == "track":
        #         for i, (cls_name, ids) in enumerate(seen_ids_per_class.items()):
        #             label = f"{cls_name}: {len(ids)}"
        #             y = y0 + i * 25
        #             cv2.putText(annotated_frame, label, (x0, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        #     elif task == "detect":
        #         for i, (cls_name, total) in enumerate(class_counts.items()):
        #             label = f"{cls_name}: {total}"
        #             y = y0 + i * 25
        #             cv2.putText(annotated_frame, label, (x0, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        # Calculate and display FPS
        processing_time = end_time - start_time
        fps = 1 / processing_time if processing_time > 0 else float('inf')
        cv2.putText(annotated_frame, f"FPS: {min(fps, max_fps):.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Save output video
        if save_output:
            if out is None:
                height, width = annotated_frame.shape[:2]
                out = cv2.VideoWriter(output_path, fourcc, min(input_fps, max_fps), (width, height))
            out.write(annotated_frame)

        # Show output in a window
        if show_output:
            cv2.imshow("Fire Inference", annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        # Frame rate control
        elapsed_time = time.time() - frame_start_time
        if elapsed_time < min_frame_time:
            time.sleep(min_frame_time - elapsed_time)

    # Release resources
    cap.release()
    if out is not None:
        out.release()
    cv2.destroyAllWindows()

# Example usage
model = YOLO("./runs/detect/best.pt", task="track")

inference(
    model,
    mode="cam",
    task="track",
    save_output=True,
    show_output=True,
    count=True,
    show_tracks=False,
    imgsz=320,
    max_fps=30,  # Maximum 30 FPS
)