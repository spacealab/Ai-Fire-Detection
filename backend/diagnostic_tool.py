#!/usr/bin/env python
import os
import sys
import time
import json
import asyncio
import websockets
import requests
import base64
from datetime import datetime

def print_colored(text, color_code):
    """Print text with specific color"""
    print(f"\033[{color_code}m{text}\033[0m")

async def test_websocket_connection(hostname="localhost", port=8010, timeout=30):
    """Test WebSocket connection and image reception"""
    url = f"ws://{hostname}:{port}/ws/video_stream"
    
    print_colored(f"[{datetime.now().strftime('%H:%M:%S')}] Testing WebSocket connection to: {url}", "36")
    print_colored("Waiting for images for up to 30 seconds...", "33")
    
    try:
        images_received = 0
        start_time = time.time()
        
        async with websockets.connect(url, ping_interval=None) as websocket:
            print_colored(f"[{datetime.now().strftime('%H:%M:%S')}] WebSocket connection established", "32")
            
            while time.time() - start_time < timeout:
                try:
                    # Set a timeout for receiving messages
                    image_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    
                    # Check if we got valid image data
                    if len(image_data) > 1000:  # Assuming valid base64 image is longer
                        images_received += 1
                        print_colored(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Received image #{images_received} (size: {len(image_data)} bytes)", "32")
                        
                        # Try to save the first image for verification
                        if images_received == 1:
                            try:
                                img_data = base64.b64decode(image_data)
                                with open("test_received_image.jpg", "wb") as f:
                                    f.write(img_data)
                                print_colored(f"Saved first received image to 'test_received_image.jpg'", "32")
                            except Exception as e:
                                print_colored(f"Error saving image: {e}", "31")
                    else:
                        print_colored(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Received suspicious data (size: {len(image_data)} bytes). Not a valid image.", "31")
                        print_colored(f"Content: {image_data[:100]}...", "33")
                except asyncio.TimeoutError:
                    print_colored(f"[{datetime.now().strftime('%H:%M:%S')}] No data received in the last 5 seconds", "33")
                except Exception as e:
                    print_colored(f"[{datetime.now().strftime('%H:%M:%S')}] Error receiving data: {e}", "31")
                    break
        
        if images_received > 0:
            print_colored(f"\n✓ SUCCESS: Received {images_received} images in {int(time.time() - start_time)} seconds", "32")
        else:
            print_colored("\n✗ FAILURE: No images received. The camera may not be active or there's a problem with the WebSocket server.", "31")
            
    except Exception as e:
        print_colored(f"\n✗ CONNECTION ERROR: {e}", "31")
        print_colored("The ws_server.py may not be running or there's a network issue.", "31")

def check_server_status(hostname="localhost", port=8010):
    """Check if the server is running and its current status"""
    print_colored(f"[{datetime.now().strftime('%H:%M:%S')}] Checking server status...", "36")
    
    try:
        ping_response = requests.get(f"http://{hostname}:{port}/ping", timeout=2)
        print_colored(f"Server ping: {ping_response.status_code} {ping_response.text}", "32")
        
        stats_response = requests.get(f"http://{hostname}:{port}/stats", timeout=2)
        if stats_response.status_code == 200:
            stats = stats_response.json()
            print_colored("\n=== Server Statistics ===", "36")
            print_colored(f"Status: {stats['status']}", "36")
            print_colored(f"Uptime: {stats['uptime_formatted']}", "36")
            print_colored(f"Images received: {stats['images_received']}", "36")
            print_colored(f"Current FPS: {stats['fps']}", "36")
            print_colored(f"Active clients: {stats['active_clients']} (streaming: {stats['streaming_clients']})", "36")
            
            if stats['status'] == 'idle':
                print_colored("\n✗ WARNING: Camera is not active. Press the 'Camera' button in the dashboard.", "33")
            return stats
        else:
            print_colored(f"✗ ERROR: Could not get server stats. Status code: {stats_response.status_code}", "31")
            return None
    except requests.exceptions.ConnectionError:
        print_colored("✗ ERROR: Server is not responding. Make sure ws_server.py is running.", "31")
        return None
    except Exception as e:
        print_colored(f"✗ ERROR: {e}", "31")
        return None

def check_last_image(hostname="localhost", port=8010):
    """Try to get the last image directly"""
    print_colored(f"[{datetime.now().strftime('%H:%M:%S')}] Checking last image...", "36")
    
    try:
        response = requests.get(f"http://{hostname}:{port}/last_image", timeout=2)
        if response.status_code == 200:
            data = response.json()
            if data.get('image_b64'):
                print_colored("✓ Last image is available on the server", "32")
                try:
                    img_data = base64.b64decode(data['image_b64'])
                    with open("last_image.jpg", "wb") as f:
                        f.write(img_data)
                    print_colored("✓ Saved last image to 'last_image.jpg'", "32")
                except Exception as e:
                    print_colored(f"✗ Error saving last image: {e}", "31")
                return True
            else:
                print_colored("✗ No image data in the response", "31")
                return False
        else:
            print_colored(f"✗ Failed to get last image. Status code: {response.status_code}", "31")
            return False
    except Exception as e:
        print_colored(f"✗ Error getting last image: {e}", "31")
        return False

async def main():
    """Main diagnostic function"""
    print_colored("\n===== WebSocket Connection Diagnostic Tool =====", "36")
    print_colored("This tool helps diagnose issues with the WebSocket connection between\nws_server.py and the dashboard.", "36")
    
    # First check if the server is running
    server_stats = check_server_status()
    
    if server_stats:
        # Try to get the last image
        last_image_ok = check_last_image()
        
        # Then test WebSocket connection
        await test_websocket_connection()
        
        # Print summary
        print_colored("\n===== Diagnostic Summary =====", "36")
        print_colored(f"Server Status: {'✓ Running' if server_stats else '✗ Not running'}", "32" if server_stats else "31")
        print_colored(f"Camera Active: {'✓ Yes' if server_stats and server_stats['status'] == 'running' else '✗ No'}", 
                     "32" if server_stats and server_stats['status'] == 'running' else "31")
        print_colored(f"Images Available: {'✓ Yes' if last_image_ok else '✗ No'}", "32" if last_image_ok else "31")
        
        # Give recommendations based on findings
        print_colored("\n===== Recommendations =====", "36")
        
        if not server_stats:
            print_colored("1. Start the WebSocket server by running: cd backend && uvicorn ws_server:app --host 0.0.0.0 --port 8010", "33")
        
        if server_stats and server_stats['status'] != 'running':
            print_colored("1. Make sure you've clicked the 'Camera' button in the dashboard to start the camera.", "33")
            print_colored("2. Check if Fire_Detection.py is running correctly and can access your webcam.", "33")
        
        if server_stats and server_stats['streaming_clients'] == 0:
            print_colored("1. Make sure your dashboard page is open at http://localhost:8080/home", "33")
            print_colored("2. Try refreshing the page and check browser console for WebSocket errors.", "33")
            
        if server_stats and server_stats['status'] == 'running' and server_stats['images_received'] > 0 and not last_image_ok:
            print_colored("There might be an issue with image data format or transmission.", "33")
    else:
        print_colored("\n✗ CRITICAL: The WebSocket server is not running or not accessible.", "31")
        print_colored("1. Make sure ws_server.py is running: cd backend && uvicorn ws_server:app --host 0.0.0.0 --port 8010", "33")
        print_colored("2. Check if there are any errors in the ws_server.log file.", "33")

if __name__ == "__main__":
    asyncio.run(main()) 