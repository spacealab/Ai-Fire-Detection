from nicegui import ui
from home import login_page
from dashboard.dashboard import home_page

# اضافه کردن یک مسیر اصلی که به داشبورد هدایت می‌شود
@ui.page('/')
def redirect_to_dashboard():
    # هدایت مستقیم به داشبورد
    ui.navigate.to('/home')

# اجرای اپلیکیشن
ui.run(title='Fire Detection Dashboard', port=8080, reload=True)