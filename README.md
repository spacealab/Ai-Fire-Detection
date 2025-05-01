# 🔥 AI-Based Fire Detection System

This project is an **Artificial Intelligence (AI)-based fire detection system** designed to monitor and display a live camera feed to detect **fire or smoke** in real-time.

## 🔧 Features

- **View Live Feed:** Displays the video stream processed by the AI model, highlighting areas with suspected fire or smoke.
- **Control System Status:** Start and stop the fire detection processes via a web-based dashboard.
- **Auxiliary Info Display:** Show map, camera status, and statistics (some parts under development).

---

## 🧠 How It Works

The system consists of two main components:

### 🖥️ Frontend (Client-Side)

- **Framework:** [NiceGUI](https://nicegui.io/)
- **File:** `frontend/dashboard/dashboard.py`
- **Key Functionalities:**
  - Web-based dashboard accessible via browser (typically on port `8080`)
  - Button to start/stop detection (`CAMERA`)
  - Displays live feed from `/mjpeg_stream` endpoint
  - Periodically checks backend status via `/stats` endpoint
  - Uses `subprocess` to launch/terminate backend scripts:  
    - `Fire_Detection.py`  
    - `ws_server.py`

---

### 🖥️ Backend (Server-Side)

#### 🔍 Fire Detection  
- **File:** `backend/Fire_Detection.py`  
- **Model:** YOLO (loaded from `best.pt`)  
- **Functionality:**
  - Captures frames from the webcam
  - Detects fire/smoke and draws bounding boxes
  - Sends processed frames (Base64 encoded) to WebSocket server via HTTP POST

#### 🌐 WebSocket + MJPEG Server  
- **File:** `backend/ws_server.py`  
- **Framework:** FastAPI  
- **Default Port:** `8010`  
- **Endpoints:**
  - `POST /push_image`: Receives processed images from Fire_Detection.py
  - `GET /mjpeg_stream`: Provides MJPEG stream for frontend display
  - `GET /ws/video_stream`: WebSocket stream (optional/legacy)
  - `GET /stats`: Returns server status (e.g. active state, client count)

#### 🧩 Other Backend Components
Files like `app.py`, `api/processing.py`, and `api/auth.py` are built with Flask for:
- Image/video upload and processing
- User authentication  
*These are not central to the current dashboard but might support future features.*

---

## 🔁 Workflow Summary

1. User opens the dashboard in their web browser.
2. User clicks the **"CAMERA"** button.
3. Frontend starts `Fire_Detection.py` and `ws_server.py` using `subprocess`.
4. `Fire_Detection.py` reads webcam frames and detects fire/smoke.
5. Processed frames are sent to `/push_image` on `ws_server.py`.
6. `ws_server.py` stores the latest frame and makes it available at `/mjpeg_stream`.
7. Frontend fetches images from `/mjpeg_stream` and displays them.
8. Frontend polls `/stats` for system status and updates the UI.
9. Clicking the **"CAMERA"** button again stops the backend processes.



