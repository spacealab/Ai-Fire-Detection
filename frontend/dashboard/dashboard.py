# dashboard.py
import logging
from nicegui import ui, app
from state import app_state
import asyncio
import subprocess
import os
import sys
import httpx
import base64
from .styles import STYLES  # Importing styles from styles.py
import time  # Added import for map setup retry logic
import shutil # Import shutil for shutil.which

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("dashboard")

# Add backend running status to shared state
app_state['backend_running'] = False # Assume not running initially
app_state['backend_start_requested'] = False # Track if user *tried* to start

# Menu settings
menu_config = {
    "width": "250px",
    "font_size": "16px",
    "item_padding": "15px",
    "item_margin": "5px",
    "icon_size": "22px",
    "active_color": "#3311db",
    "inactive_color": "#8a96a3",
    "header_font_size": "20px",
}

# Grid settings
grid_config = {
    "box_height": "200px",
    "gap": "20px",
    "padding": "15px",
    "shadow": "0 4px 8px rgba(0, 0, 0, 0.1)",
    "border_radius": "10px",
    "content_height": "calc(100vh - 120px)"
}

@ui.page('/home')
def home_page():
    # Always show login as active for testing
    app_state["login_success"] = True

    # store subprocess handles for toggling
    backend_process = {'fire': None, 'ws': None}

    # --- Function to update camera status and shared state ---
    def update_camera_status(button):
        """Update camera button status and shared state based on server reachability."""
        try:
            # Use synchronous httpx.get
            resp = httpx.get("http://localhost:8010/stats", timeout=0.5)
            
            if resp.status_code == 200:
                data = resp.json()
                is_running = data.get('status') == 'running'
                app_state['backend_running'] = is_running # Update shared state
                if is_running:
                    button.style('background-color: #4CAF50; color: white; padding: 8px 16px;')
                else:
                    # Server responded but status is not 'running' (e.g., 'idle')
                    button.style('background-color: #F44336; color: white; padding: 8px 16px;')
                    # If we didn't request it to stop, maybe it stopped on its own?
                    if app_state['backend_start_requested']:
                        logger.warning("Backend server responded but is not in 'running' state.")
            else:
                # Server responded with non-200 status
                app_state['backend_running'] = False
                button.style('background-color: #F44336; color: white; padding: 8px 16px;')
                logger.warning(f"Backend server responded with status {resp.status_code}")

        except httpx.RequestError as e:
            # Network error, server likely not running or unreachable
            if app_state['backend_running']: # Log only if we thought it was running
                logger.warning(f"Backend server connection failed: {e}")
            app_state['backend_running'] = False
            button.style('background-color: #F44336; color: white; padding: 8px 16px;')
        except Exception as e:
            # Other unexpected errors
            logger.error(f"Error updating camera status: {e}", exc_info=True)
            app_state['backend_running'] = False
            button.style('background-color: #F44336; color: white; padding: 8px 16px;')
            
    # --- Function to toggle backend processes ---
    def toggle_fire_detection():
        fire_p = backend_process.get('fire')
        ws_p = backend_process.get('ws')
        logger.info("Toggle button clicked.")

        fire_running_handle = fire_p is not None and fire_p.poll() is None
        ws_running_handle = ws_p is not None and ws_p.poll() is None
        logger.info(f"Local handles state: Fire Detection running = {fire_running_handle}, WS Server running = {ws_running_handle}")
        logger.info(f"Shared state: Backend running = {app_state['backend_running']}")

        # --- STOPPING LOGIC --- 
        # Try stopping if we have handles OR if shared state says it's running (attempt best effort)
        if fire_running_handle or ws_running_handle or app_state['backend_running']:
            app_state['backend_start_requested'] = False # Mark as intentionally stopped
            if not (fire_running_handle or ws_running_handle):
                 logger.warning("Attempting to stop backend, but no local process handles found (likely due to refresh). Stop may fail.")
            
            logger.info("Attempting to terminate backend processes...")
            stopped_fire = False
            stopped_ws = False
            
            # Stop fire_p if handle exists
            if fire_running_handle:
                logger.info(f"Terminating Fire_Detection.py (PID: {fire_p.pid}) using handle...")
                try:
                    fire_p.terminate()
                    fire_p.wait(timeout=5)
                    logger.info(f"Stopped Fire_Detection.py (PID: {fire_p.pid})")
                    stopped_fire = True
                except subprocess.TimeoutExpired:
                    logger.warning(f"Fire_Detection.py (PID: {fire_p.pid}) did not terminate gracefully, killing.")
                    fire_p.kill()
                    stopped_fire = True # Assume killed
                except Exception as e:
                    logger.error(f"Failed to stop Fire_Detection.py using handle: {e}", exc_info=True)
                finally:
                    backend_process['fire'] = None
            
            # Stop ws_p if handle exists
            if ws_running_handle:
                logger.info(f"Terminating ws_server.py (PID: {ws_p.pid}) using handle...")
                try:
                    ws_p.terminate()
                    ws_p.wait(timeout=5)
                    logger.info(f"Stopped ws_server.py (PID: {ws_p.pid})")
                    stopped_ws = True
                except subprocess.TimeoutExpired:
                    logger.warning(f"ws_server.py (PID: {ws_p.pid}) did not terminate gracefully, killing.")
                    ws_p.kill()
                    stopped_ws = True # Assume killed
                except Exception as e:
                    logger.error(f"Failed to stop ws_server.py using handle: {e}", exc_info=True)
                finally:
                    backend_process['ws'] = None

            # Update shared state immediately after attempting stop
            app_state['backend_running'] = False 
            
            # Notify based on whether we had handles
            if fire_running_handle or ws_running_handle:
                 ui.notify("Backend stop requested.", type='info')
            else:
                 ui.notify("Backend might be stopped (attempted without handles). Please verify manually.", type='warning')
            return

        # --- STARTING LOGIC --- 
        # Only start if handles are None AND shared state says it's not running
        if not fire_running_handle and not ws_running_handle and not app_state['backend_running']:
            logger.info("Attempting to start backend processes...")
            app_state['backend_start_requested'] = True # Mark as intentionally started
            proc_fire = None
            proc_ws = None
            
            # --- Start Fire Detection ---
            try:
                script_path_fire = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'Fire_Detection.py'))
                backend_dir = os.path.dirname(script_path_fire)
                log_file_fire = os.path.join(backend_dir, "fire_detection.log")
                logger.info(f"Starting Fire_Detection.py, logging to {log_file_fire}")
                with open(log_file_fire, 'ab') as logf:
                    proc_fire = subprocess.Popen([sys.executable, script_path_fire], cwd=backend_dir, stdout=logf, stderr=subprocess.STDOUT)
                backend_process['fire'] = proc_fire
                logger.info(f"Started Fire_Detection.py (PID: {proc_fire.pid})")
            except Exception as e:
                logger.error(f"Failed to start Fire_Detection.py: {e}", exc_info=True)
                ui.notify(f"Error starting Fire Detection: {e}", type='negative')
                backend_process['fire'] = None
                app_state['backend_start_requested'] = False # Failed start

            # --- Start WS Server --- 
            if backend_process.get('fire'): # Only if fire detection started
                try:
                    uvicorn_path = os.path.join(os.path.dirname(sys.executable), 'uvicorn')
                    if not os.path.exists(uvicorn_path):
                        uvicorn_path = shutil.which('uvicorn')
                        if not uvicorn_path:
                            raise FileNotFoundError("uvicorn command not found in venv or PATH")

                    script_path_ws = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'ws_server.py'))
                    backend_dir_ws = os.path.dirname(script_path_ws)
                    log_file_ws = os.path.join(backend_dir_ws, "ws_server.log")
                    logger.info(f"Starting ws_server.py with uvicorn ({uvicorn_path}), logging to {log_file_ws}")
                    with open(log_file_ws, 'ab') as logf:
                        proc_ws = subprocess.Popen([
                            uvicorn_path,
                            'ws_server:app',
                            '--host', '0.0.0.0',
                            '--port', '8010',
                            '--log-level', 'info'
                        ], cwd=backend_dir_ws, stdout=logf, stderr=subprocess.STDOUT)
                    backend_process['ws'] = proc_ws
                    logger.info(f"Started ws_server.py with uvicorn (PID: {proc_ws.pid})")
                    ui.notify("Backend started.", type='positive')
                    # Give server a moment to start before first status check potentially runs
                    time.sleep(1.0) 
                    app_state['backend_running'] = True # Tentatively set to true
                    
                except Exception as e:
                    logger.error(f"Failed to start ws_server.py: {e}", exc_info=True)
                    ui.notify(f"Error starting WebSocket Server: {e}", type='negative')
                    backend_process['ws'] = None
                    app_state['backend_start_requested'] = False # Failed start
                    # Stop Fire Detection if WS server failed
                    fire_p_check = backend_process.get('fire')
                    if fire_p_check and fire_p_check.poll() is None:
                        logger.warning("Stopping Fire Detection because WS Server failed to start.")
                        try:
                            fire_p_check.terminate()
                            fire_p_check.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            fire_p_check.kill()
                        except Exception as stop_e:
                             logger.error(f"Failed to stop Fire Detection after WS fail: {stop_e}")
                        finally:
                             backend_process['fire'] = None
            else:
                logger.warning("Skipping start of ws_server because Fire_Detection failed to start.")
                app_state['backend_start_requested'] = False # Failed start
        
        # Handle case where button clicked while backend is running (due to refresh)
        elif not fire_running_handle and not ws_running_handle and app_state['backend_running']:
             logger.warning("Start requested, but backend appears to be running already (state detected via HTTP). Cannot start new instance.")
             ui.notify("Backend seems to be running already. Refresh might have lost UI control.", type='warning')
        
        else:
            # This case might happen if stop was clicked but handles were already None
            logger.info("Button clicked, but no action taken (backend likely already stopped or handles lost).")
            

    ui.colors(primary='#3311db')

    # Apply styles from styles.py
    ui.add_css(STYLES)
    
    # Add custom CSS to adjust grid column widths
    ui.add_css('''
        .content .grid-container {
            /* Adjust column ratios: 1.5fr for Live Feed, 1fr for Map, 0.5fr for Camera Info */
            grid-template-columns: 1.5fr 1fr 0.5fr;
        }
    ''')

    # Create page structure
    with ui.element('div').classes('main-container'):
        # Left menu
        with ui.element('div').classes('sidebar'):
            # Title with "AI" in bold
            with ui.row().classes('sidebar-header justify-center w-full'):
                ui.label('AI').classes('bold')
                ui.label(' FIRE DETECTION')

            # Menu items
            with ui.element('div').classes('menu-item active'):
                ui.icon('home').classes('menu-icon')
                ui.label('Dashboard').classes('menu-text')

            with ui.element('div').classes('menu-item'):
                ui.icon('speed').classes('menu-icon')
                ui.label('Benchmark').classes('menu-text')

            with ui.element('div').classes('menu-item'):
                ui.icon('computer').classes('menu-icon')
                ui.label('AI Modules').classes('menu-text')

            with ui.element('div').classes('menu-item'):
                ui.icon('location_on').classes('menu-icon')
                ui.label('Location').classes('menu-text')

            with ui.element('div').classes('menu-item'):
                ui.icon('alarm').classes('menu-icon')
                ui.label('Alarms').classes('menu-text')

            with ui.element('div').classes('menu-item'):
                ui.icon('login').classes('menu-icon')
                ui.label('Logout').classes('menu-text')

        # Main content
        with ui.element('div').classes('content-wrapper'):
            with ui.element('div').classes('content'):
                with ui.element('div').classes('grid-container'):
                    # First row - three boxes
                    with ui.element('div').classes('grid-box') as status_box:
                        ui.label('Live Fire Detection Feed').classes('grid-box-title')
                        with ui.element('div').style('height: 300px; display: flex; align-items: center; justify-content: center; border: 1px solid #ddd; border-radius: 8px; background: #f6f6fa; margin: 0 15px 15px 15px;') as image_container:
                            # MJPEG Stream Image - Initially hidden, adjust max-width/height to fill container
                            mjpeg_image = ui.html('''
                                <img id="mjpeg_stream" src="" 
                                     style="max-width: 100%; max-height: 100%; border-radius: 8px; box-shadow: 0 2px 8px #aaa; display: none; object-fit: contain;" />
                            ''').style('display: none; width: 100%; height: 100%;') # Make HTML element fill container too
                            # Status Label - Initially shown
                            stream_status_label = ui.label('Click the CAMERA button to start the feed.').style('font-size: 18px; color: #888;')

                    # Map Box
                    with ui.element('div').classes('grid-box') as map_box:
                        ui.label('Map').classes('grid-box-title')
                        with ui.element('div').classes('map-container') as map_container:
                            loading_label = ui.label('Loading map...').classes('loading-overlay')
                            map_view = ui.leaflet(center=(52.1797832, 10.5599424), zoom=15).classes('w-full h-full')

                    with ui.element('div').classes('grid-box'):  # Info Box
                        ui.label('Cameras Information').classes('grid-box-title')
                        with ui.row().classes('w-full justify-start mt-4'):
                            camera_button = ui.button('CAMERA', on_click=toggle_fire_detection).style('padding: 8px 16px; background-color: #F44336; color: white;')
                            
                            # Timer to update button color and shared state
                            ui.timer(3.0, lambda: update_camera_status(camera_button), active=True)

                    # Second row - three boxes
                    with ui.element('div').classes('grid-box'):
                        ui.label('Last Alerts').classes('grid-box-title')
                        ui.label('No Recent Alerts')

                    with ui.element('div').classes('grid-box'):
                        ui.label('Detection Statistics').classes('grid-box-title')
                        ui.label('Feature currently disabled')

                    with ui.element('div').classes('grid-box'):
                        ui.label('Calendar').classes('grid-box-title')
                        ui.date().props('color="primary" minimal').classes('w-full h-full')

            # Footer
            with ui.element('div').classes('footer'):
                with ui.element('div').classes('footer-container'):
                    with ui.element('div').classes('footer-row'):
                        with ui.element('div').classes('footer-half'):
                            ui.label('©2025 AI FIRE DETECTION. ALL RIGHTS RESERVED.').classes('footer-text')
                        with ui.element('div').classes('footer-half'):
                            with ui.element('div').classes('footer-menu'):
                                for menu_item in ['Support', 'License', 'Terms of Use', 'Blog']:
                                    ui.link(menu_item, '#').style('color: white; margin: 0 10px; text-decoration: none; font-size: 14px;')

    # Show marker on map
    def setup_map():
        try:
            lat = 52.1797832
            lng = 10.5599424
            js_func_name = f"setup_map_js_{int(time.time()*1000)}"
            ui.run_javascript(f"""
                function {js_func_name}() {{
                    try {{
                        if (typeof map !== 'undefined' && typeof L !== 'undefined') {{
                            console.log('Setting up map marker at {lat}, {lng}');
                            const marker = L.marker([{lat}, {lng}]).addTo(map);
                            marker.bindTooltip(
                                "<b>Drag marker to required location.</b><br>Latitude: {lat}<br>Longitude: {lng}",
                                {{ permanent: true, direction: 'top' }}
                            ).openTooltip();
                            map.setView([{lat}, {lng}], 15);
                            const loadingLabel = document.querySelector('.loading-overlay');
                            if (loadingLabel) loadingLabel.style.display = 'none';
                            console.log('Map setup complete.');
                        }} else {{
                            console.warn('Map object (map or L) not ready yet for marker setup. Retrying...');
                            setTimeout({js_func_name}, 500);
                        }}
                    }} catch (e) {{
                        console.error('Error during map marker setup:', e);
                        const loadingLabel = document.querySelector('.loading-overlay');
                        if (loadingLabel) loadingLabel.textContent = 'Error loading map marker: ' + e.message;
                    }}
                }}
                {js_func_name}();
            """)
            logger.info(f"Map setup initiated with coordinates: Lat {lat}, Lng {lng}")
        except Exception as e:
            logger.error(f"Error initiating map setup: {e}", exc_info=True)
            try:
                loading_label.set_text(f"Error setting up map: {str(e)}")
            except NameError:
                logger.error("Could not update loading_label text as it's not defined.")

    ui.timer(1.0, setup_map, once=True)

    # Script to manage MJPEG stream visibility and source based on server status
    mjpeg_stream_script = f"""
        const streamImage = document.getElementById('mjpeg_stream');
        const statusLabel = getElement({stream_status_label.id}); // Get NiceGUI label element
        const imageElement = getElement({mjpeg_image.id}); // Get NiceGUI html element containing the img
        let currentSrc = '';
        const streamUrl = 'http://{os.environ.get("SERVER_HOST", "localhost")}:8010/mjpeg_stream';

        // Function to check camera status and manage stream visibility
        function checkCameraStatus() {{
            // console.log('Checking camera status...');
            fetch(`http://{os.environ.get("SERVER_HOST", "localhost")}:8010/stats`)
                .then(response => {{
                    // Check if response status is OK (200-299)
                    if (!response.ok) {{
                        // If not OK, throw an error to be caught by .catch
                        throw new Error(`HTTP error! status: ${{response.status}}`); 
                    }}
                    return response.json();
                }})
                .then(data => {{
                    // console.log('Camera status:', data);
                    const cameraActive = data.status === 'running';
                    
                    if (cameraActive) {{
                        // Camera is active, try to show stream
                        if (currentSrc !== streamUrl) {{
                           console.log('Camera active, setting MJPEG stream source...');
                           streamImage.src = streamUrl;
                           currentSrc = streamUrl;
                           imageElement.style.display = 'block'; // Show the container
                           streamImage.style.display = 'block'; // Show the image itself
                           statusLabel.style.display = 'none';
                        }}
                        // If src is already set, just ensure visibility is correct
                        else if (streamImage.style.display === 'none') {{
                           imageElement.style.display = 'block';
                           streamImage.style.display = 'block'; 
                           statusLabel.style.display = 'none';
                        }}
                    }} else {{
                        // Camera is inactive, hide stream and show message
                        if (currentSrc !== '') {{
                            console.log('Camera inactive, clearing MJPEG stream source.');
                            streamImage.src = ''; // Stop the stream
                            currentSrc = '';
                        }}
                        imageElement.style.display = 'none';
                        streamImage.style.display = 'none';
                        statusLabel.textContent = 'Camera inactive - Click the CAMERA button';
                        statusLabel.style.color = '#F44336';
                        statusLabel.style.display = 'block';
                        // console.log('Camera inactive, hiding stream');
                    }}
                }})
                .catch(error => {{
                    // This catch block now handles network errors OR the error thrown above
                    // console.error('Error checking camera status or processing response:', error); // Optional: Keep for debugging
                    if (currentSrc !== '') {{
                       streamImage.src = ''; // Stop stream on error
                       currentSrc = '';
                    }}
                    imageElement.style.display = 'none';
                    streamImage.style.display = 'none';
                    // Display the desired message when connection fails or server stopped
                    statusLabel.textContent = 'Waiting for camera connection...'; 
                    statusLabel.style.color = '#888'; // Use a neutral color like grey
                    statusLabel.style.display = 'block';
                }});
        }}
        
        // Handle image load event - ensures status label is hidden once image loads
        streamImage.onload = function() {{
            console.log('MJPEG stream image frame loaded successfully');
            // Double check if camera is still supposed to be active
             fetch(`http://{os.environ.get("SERVER_HOST", "localhost")}:8010/stats`)
                .then(r => r.json())
                .then(d => {{ if (d.status === 'running') statusLabel.style.display = 'none'; }})
                .catch(e => console.warn('Minor error checking status on img load', e));
        }};
        
        // Handle image error event - show error message if stream fails
        streamImage.onerror = function() {{
            // Avoid logging errors if src is intentionally blank
            if (currentSrc === streamUrl) {{
                 console.error('Error loading MJPEG stream frame.');
                 currentSrc = ''; // Reset src tracking on error
                 imageElement.style.display = 'none';
                 streamImage.style.display = 'none';
                 statusLabel.textContent = 'Error loading video stream';
                 statusLabel.style.display = 'block';
                 statusLabel.style.color = '#F44336';
            }}
        }};
        
        // Check camera status every 3 seconds
        const statusInterval = setInterval(checkCameraStatus, 3000);
        
        // Perform an initial check slightly delayed to allow server startup time if needed
        // setTimeout(checkCameraStatus, 1500); 
        // We rely on the regular interval check now

        // Cleanup interval on disconnect (important for NiceGUI)
        // This requires finding a way to reliably detect page unload/disconnect in NiceGUI
        // For now, the interval keeps running.

    """
    ui.run_javascript(mjpeg_stream_script)
    
    logger.info("MJPEG streaming setup complete - providing real-time video feed")

    logger.info("Dashboard page loaded and MJPEG stream script initiated.")