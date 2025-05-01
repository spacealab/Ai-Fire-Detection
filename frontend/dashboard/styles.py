# styles.py
STYLES = '''
body { 
    background-color: white; 
    color: black; 
    margin: 0;
    padding: 0;
    overflow: hidden;
}
.main-container {
    display: flex;
    width: 100%;
    height: 100vh;
    overflow: hidden;
}
.sidebar {
    width: 250px;
    min-width: 250px;
    background-color: #f8f8fc;
    height: 100vh;
    border-right: 3px solid #e0e0fa;
    display: flex;
    flex-direction: column;
    padding-top: 20px;
    position: fixed;
    left: 0;
    top: 0;
    overflow-y: auto;
    z-index: 100;
}
.sidebar-header {
    font-size: 20px;
    font-weight: normal;
    padding: 0 15px 20px 15px;
    border-bottom: 1px solid #eaeaea;
    margin-bottom: 20px;
    text-align: center;
    white-space: nowrap;
}
.bold {
    font-weight: bold;
}
.menu-item {
    display: flex;
    align-items: center;
    padding: 15px;
    margin: 5px 0;
    cursor: pointer;
    transition: all 0.3s;
    white-space: nowrap;
}
.menu-item.active {
    color: #3311db;
    background-color: rgba(51, 17, 219, 0.05);
}
.menu-item:not(.active) {
    color: #8a96a3;
}
.menu-item:hover:not(.active) {
    background-color: rgba(138, 150, 163, 0.05);
}
.menu-icon {
    font-size: 22px;
    margin-right: 15px;
    width: 25px;
    text-align: center;
    flex-shrink: 0;
}
.menu-text {
    font-size: 16px;
}
.content-wrapper {
    margin-left: 250px;
    width: calc(100% - 250px);
    height: 100vh;
    display: flex;
    flex-direction: column;
}
.content {
    padding: 25px;
    height: calc(100vh - 120px);
    overflow-y: auto;
}
.grid-container {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    grid-template-rows: repeat(2, auto);
    gap: 20px;
    height: 100%;
}
.grid-box {
    background-color: white;
    border-radius: 10px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    padding: 15px;
    display: flex;
    flex-direction: column;
    min-height: 200px;
}
.grid-box-title {
    font-size: 18px;
    font-weight: bold;
    margin-bottom: 15px;
    color: #333;
}
.footer {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background-color: #3311db;
    color: white;
    z-index: 90;
    padding: 10px 0;
    margin-left: 250px;
    width: calc(100% - 250px);
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
.map-container {
    position: relative;
    height: 320px;
    width: 100%;
}
.loading-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(255, 255, 255, 0.8);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 10;
    font-weight: bold;
    color: #333;
}

/* Dashboard Grid Layout CSS - Moved from dashboard.py */
.content .grid-container {
    /* Three columns - first column wider, Map and Camera-info columns same width */
    grid-template-columns: 1.5fr 0.75fr 0.75fr;
    /* Two rows with adjusted heights - first row 71%, second row 29% (except third column) */
    grid-template-rows: 2.45fr 1fr;
    /* Create 3x2 grid */
    display: grid;
    grid-template-areas: 
        "live-feed map right-column"
        "alerts stats right-column";
    /* Set specific gap between rows to exactly 20px */
    grid-row-gap: 20px;
    grid-column-gap: 20px;
    height: 100%;
}

/* Right column container that spans both rows */
.right-column-container {
    grid-area: right-column;
    display: flex;
    flex-direction: column;
    height: 100%;
    gap: 20px; /* Match the main grid gap */
}

/* Set equal heights for the boxes in right column */
.camera-area, .calendar-area {
    flex: 1; /* Equal flex distribution (50% each) */
    min-height: 0; /* Needed for flex to work properly */
}

/* Remove fixed heights and use relative heights instead */
.upper-box {
    height: 100%; /* Will be controlled by grid-template-rows */
}

.lower-box {
    height: 100%; /* Will be controlled by grid-template-rows */
}

/* Make the live feed match other boxes in top row */
.live-feed-box {
    height: 100% !important;
    margin-bottom: 0 !important; /* Ensure no extra margin */
}

/* Ensure no extra margin for alerts box */
.alerts-area {
    margin-top: 0 !important;
}

/* Define grid areas */
.live-feed-area { grid-area: live-feed; }
.alerts-area { grid-area: alerts; }
.map-area { grid-area: map; }
.stats-area { grid-area: stats; }
'''