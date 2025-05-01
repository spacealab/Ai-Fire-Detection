# ws_server.py
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import base64
import os
from datetime import datetime
from typing import List
import asyncio
import io

app = FastAPI()

# Add CORS middleware for browser compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ws_server")

# وضعیت آخرین دریافت تصویر
last_image_status = {"ok": False, "last_time": None}
last_image_b64 = None  # ذخیره آخرین تصویر
last_image_bytes = None  # ذخیره تصویر به صورت باینری برای استریم

# List to keep track of active WebSocket connections for broadcasting new images
active_broadcast_connections: List[WebSocket] = []
# List to keep track of active WebSocket connections for streaming video
active_streaming_connections: List[WebSocket] = []

# MJPEG boundary for streaming
BOUNDARY = "frame"
MULTIPART_FRAME_HEADER = f"--{BOUNDARY}\r\nContent-Type: image/jpeg\r\nContent-Length: "

async def broadcast_image(image_b64: str):
    """Sends the image data to all connected WebSocket clients (broadcast and streaming)."""
    disconnected_broadcast = []
    disconnected_streaming = []

    # Broadcast to broadcast connections
    logger.info(f"Broadcasting image to {len(active_broadcast_connections)} broadcast clients.")
    for connection in active_broadcast_connections:
        try:
            await connection.send_text(image_b64)
        except WebSocketDisconnect:
            disconnected_broadcast.append(connection)
            logger.info("Broadcast client disconnected")
        except Exception as e:
            logger.error(f"Error sending message to broadcast client: {e}")
            disconnected_broadcast.append(connection)

    # Stream to streaming connections
    logger.info(f"Streaming image to {len(active_streaming_connections)} streaming clients.")
    for connection in active_streaming_connections:
        try:
            await connection.send_text(image_b64)
        except WebSocketDisconnect:
            disconnected_streaming.append(connection)
            logger.info("Streaming client disconnected")
        except Exception as e:
            logger.error(f"Error sending message to streaming client: {e}")
            disconnected_streaming.append(connection)

    # Remove disconnected connections
    for connection in disconnected_broadcast:
        if connection in active_broadcast_connections:
            active_broadcast_connections.remove(connection)
            logger.debug("Removed disconnected broadcast client.")
    for connection in disconnected_streaming:
        if connection in active_streaming_connections:
            active_streaming_connections.remove(connection)
            logger.debug("Removed disconnected streaming client.")

@app.post("/push_image")
async def push_image(request: Request):
    global last_image_b64, last_image_bytes, last_image_status
    try:
        data = await request.json()
        image_b64 = data.get("image_b64")
        if not image_b64:
            logger.error("No image_b64 in request to /push_image")
            return JSONResponse({"status": "error", "detail": "No image_b64"}, status_code=400)

        # Decode the image for MJPEG streaming
        try:
            last_image_bytes = base64.b64decode(image_b64)
        except Exception as e:
            logger.error(f"Error decoding base64 image: {e}")
            
        # Decode and save image (optional, consider if needed for debugging)
        # img_data = base64.b64decode(image_b64)
        now_dt = datetime.now()
        now_str = now_dt.strftime("%Y%m%d_%H%M%S_%f")
        # img_path = os.path.join("/tmp", f"fire_frame_{now_str}.jpg")
        # with open(img_path, "wb") as f:
        #     f.write(img_data)
        logger.info(f"Image received via /push_image at {now_str}")

        last_image_b64 = image_b64  # ذخیره آخرین تصویر
        last_image_status["ok"] = True
        last_image_status["last_time"] = now_str

        # Broadcast the new image to all connected WebSocket clients
        await broadcast_image(image_b64)

        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error in /push_image: {e}", exc_info=True)
        last_image_status["ok"] = False
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)

@app.get("/fire_status")
def fire_status():
    # وضعیت را برای فرانت ارسال می‌کند
    logger.debug(f"GET /fire_status requested. Status: {last_image_status}")
    if last_image_status["ok"]:
        return {"status": "good", "last_time": last_image_status["last_time"]}
    else:
        return {"status": "waiting"}

@app.get("/last_image")
def last_image():
    logger.debug("GET /last_image requested.")
    try:
        if last_image_b64:
            logger.debug("Returning last image.")
            return JSONResponse({"image_b64": last_image_b64})
        else:
            logger.warning("No last image available for GET /last_image.")
            return JSONResponse({"error": "No image available"}, status_code=404)
    except Exception as e:
        logger.error(f"Error in /last_image: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.websocket("/ws/fire_image")
async def websocket_broadcast_endpoint(websocket: WebSocket):
    """WebSocket endpoint for broadcasting new images."""
    await websocket.accept()
    active_broadcast_connections.append(websocket)
    logger.info("Client connected to broadcast WebSocket /ws/fire_image")
    try:
        # Keep the connection alive, waiting for broadcasts
        while True:
            # We don't expect messages from the client here, just keep alive
            await websocket.receive_text()
            logger.debug("Received keep-alive or unexpected message on broadcast WebSocket.")
    except WebSocketDisconnect:
        logger.info("Client disconnected from broadcast WebSocket /ws/fire_image")
    except Exception as e:
        logger.error(f"Broadcast WebSocket error: {e}", exc_info=True)
    finally:
        if websocket in active_broadcast_connections:
            active_broadcast_connections.remove(websocket)
            logger.debug("Removed client from active_broadcast_connections.")

@app.websocket("/ws/video_stream")
async def websocket_stream_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time video streaming."""
    await websocket.accept()
    active_streaming_connections.append(websocket)
    logger.info(f"Client connected to streaming WebSocket /ws/video_stream. Total streaming clients: {len(active_streaming_connections)}")

    # Send the last known image immediately if available
    if last_image_b64:
        try:
            logger.debug("Sending initial last image to new streaming client.")
            await websocket.send_text(last_image_b64)
        except Exception as e:
            logger.error(f"Error sending initial image to streaming client: {e}", exc_info=True)
            if websocket in active_streaming_connections:
                 active_streaming_connections.remove(websocket)
            return

    try:
        # Keep the connection alive, waiting for broadcasts via broadcast_image
        while True:
            # We don't expect messages from the client here, just keep alive
            await websocket.receive_text()
            logger.debug("Received keep-alive or unexpected message on streaming WebSocket.")
    except WebSocketDisconnect:
        logger.info("Client disconnected from streaming WebSocket /ws/video_stream")
    except Exception as e:
        logger.error(f"Streaming WebSocket error: {e}", exc_info=True)
    finally:
        if websocket in active_streaming_connections:
            active_streaming_connections.remove(websocket)
            logger.debug(f"Removed client from active_streaming_connections. Remaining: {len(active_streaming_connections)}")

# MJPEG Streaming - used for real-time video directly in browser
async def mjpeg_generator():
    """Generate MJPEG Stream for real-time video"""
    while True:
        if last_image_bytes:
            # Send multipart JPEG frame
            frame_len = len(last_image_bytes)
            frame_header = f"{MULTIPART_FRAME_HEADER}{frame_len}\r\n\r\n"
            frame_data = last_image_bytes
            frame_end = b"\r\n"
            
            yield frame_header.encode('utf-8')
            yield frame_data
            yield frame_end
        
        # Continue sending frames with a small delay
        await asyncio.sleep(0.03)  # Approx 30 FPS

@app.get("/mjpeg_stream")
async def mjpeg_stream():
    """Endpoint for MJPEG streaming - can be directly used as img src in browser"""
    return StreamingResponse(
        mjpeg_generator(),
        media_type=f"multipart/x-mixed-replace; boundary={BOUNDARY}"
    )

@app.get("/ping")
def ping():
    """Endpoint to check if the server is running"""
    return {"status": "OK", "message": "Server is running", "timestamp": datetime.now().isoformat()}

@app.get("/stats")
def get_stats():
    """Get server statistics"""
    return {
        "status": "running" if last_image_status["ok"] else "idle",
        "images_received": sum(1 for _ in range(1)) if last_image_bytes else 0,
        "active_clients": len(active_streaming_connections) + len(active_broadcast_connections),
        "streaming_clients": len(active_streaming_connections),
        "broadcast_clients": len(active_broadcast_connections),
        "last_image_time": last_image_status["last_time"]
    }