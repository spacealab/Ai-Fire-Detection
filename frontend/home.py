import logging
import time
import requests
from nicegui import ui
from state import app_state  # وارد کردن وضعیت مشترک

# تنظیم لاگینگ
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("nicegui_front")

app_state["session"] = requests.Session()

def check_backend():
    logger.info('Checking backend connection...')
    for attempt in range(3):
        try:
            resp = app_state["session"].get("http://127.0.0.1:5000/ping", timeout=5)
            logger.info(f'Ping response: {resp.status_code} {resp.text}')
            if resp.status_code == 200:
                app_state["backend_ok"] = True
                logger.info('Backend is reachable.')
                return
            else:
                logger.error(f'Backend returned status: {resp.status_code}')
        except Exception as e:
            logger.error(f'Backend connection attempt {attempt + 1} failed: {e}')
        time.sleep(2)
    app_state["backend_ok"] = False
    logger.error('Backend is not reachable after retries.')

check_backend()

def do_login():
    logger.info(f'Sending login request for user: {username.value}')
    try:
        # تغییر آدرس به API endpoint جدید
        resp = app_state["session"].post(
            "http://127.0.0.1:5000/api/v1/auth/login", # <--- آدرس جدید
            json={"username": username.value, "password": password.value},
            timeout=10
        )
        logger.info(f'Login response: {resp.status_code} {resp.text}')
        if resp.status_code == 200:
            app_state["login_success"] = True
            app_state["last_error"] = ''
            logger.info('Login successful.')
            # کوکی‌ها باید به درستی توسط session مدیریت شوند اگر از flask-login استفاده شود
            app_state["session"].cookies.update(resp.cookies)
            user_info = resp.json().get("user", {}) # گرفتن اطلاعات کاربر از پاسخ
            logger.info(f"Logged in user: {user_info.get('username')}")
            ui.notify('Login successful!', color='positive')
            ui.navigate.to('/home') # یا صفحه داشبورد
        else:
            # دریافت پیام خطا از JSON پاسخ
            msg = resp.json().get('error', f'Login failed with status {resp.status_code}')
            app_state["last_error"] = f'Login failed: {msg}'
            logger.warning(app_state["last_error"])
            ui.notify(app_state["last_error"], color='negative')
    except requests.exceptions.RequestException as e:
        app_state["last_error"] = f'Connection error: {e}'
        logger.error(app_state["last_error"])
        ui.notify(app_state["last_error"], color='negative')

@ui.page('/login')
def login_page():
    # استفاده از ui.add_css به جای فایل خارجی
    ui.add_css('''
        body {
            background-image: linear-gradient(to top, #3311db, #4725e4, #5835ed, #6743f6, #7551ff);
            background-attachment: fixed;
            background-size: cover;
            color: white;
            overflow: hidden; /* غیرفعال کردن اسکرول */
        }
        .main-container {
            max-width: 1200px;
            margin: 0 auto;
            padding-left: 32px;
            padding-right: 32px;
            width: 100%;
        }
        .q-card {
            background-color: rgba(255, 255, 255, 0.95);
        }
        .footer-container {
            max-width: 1200px;
            margin: 0 auto;
            padding-left: 32px;
            padding-right: 32px;
            width: 100%;
            display: flex;
            justify-content: center;
        }
        .footer-row {
            display: flex;
            width: 100%;
            gap: 2px;
        }
        .footer-half {
            width: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .footer-menu {
            background-color: #4b2e83;
            padding: 5px 15px;
            border-radius: 5px;
        }
        .footer-menu a {
            color: white;
            margin: 0 10px;
            text-decoration: none;
            font-size: 14px;
        }
        .footer-text {
            color: white;
            font-size: 14px;
        }
        .footer {
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            background-color: #3311db;
            color: white;
            z-index: 100;
            padding: 10px 0;
        }
    ''')

    if not app_state["backend_ok"]:
        ui.label('❌ Backend is not reachable! Please check if Flask is running on http://127.0.0.1:5000').style('color:red')
        logger.error('Frontend could not connect to backend.')
        return

    with ui.element('div').classes('main-container'):
        with ui.row().classes('w-full h-screen items-center justify-center no-wrap'):
            with ui.column().classes('w-1/2 items-center justify-center'):
                with ui.card().style('height: 600px; width: 400px; padding: 20px;'):
                    ui.label('Sign In').style('color: black; font-size: 24px; text-align: center; margin-bottom: 10px;')
                    ui.label('Enter your username and password to sign in').style('text-align: center; margin-bottom: 20px; color: grey;')

                    ui.separator().style('margin-top: 20px; margin-bottom: 70px;')

                    global username, password
                    username = ui.input('Username*').props('outlined').classes('w-full')
                    password = ui.input('Password*', password=True).props('outlined').classes('w-full').on('keydown', lambda e: do_login() if e.args.get('key') == 'Enter' else None)

                    with ui.row().classes('w-full items-center justify-between'):
                        ui.checkbox('Keep me logged In').style('color: black')

                    ui.button('Sign In', on_click=do_login).props('color=primary').classes('w-full').style('margin-top: 10px; color: white;')

            with ui.column().classes('w-1/2 items-center justify-center'):
                ui.image('./public/img/auth/auth2.png').style('height: 800px; max-width: 1200px; width: 100%; object-fit: contain;')

    with ui.element('div').classes('footer'):
        with ui.element('div').classes('footer-container'):
            with ui.element('div').classes('footer-row'):
                with ui.element('div').classes('footer-half'):
                    ui.label('©2025 AI FIRE DETECTION. ALL RIGHTS RESERVED.').classes('footer-text')
                with ui.element('div').classes('footer-half'):
                    with ui.element('div').classes('footer-menu'):
                        for menu_item in ['Support', 'License', 'Terms of Use', 'Blog']:
                            ui.link(menu_item, '#').style('color: white; margin: 0 10px; text-decoration: none; font-size: 14px;')