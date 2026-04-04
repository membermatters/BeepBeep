import ulogging

# =========================================================================
# ============================== WARNING! =================================
# =========================================================================
# Do not change this file to make configuration changes. This is the
# example config file and won't affect anything. Copy config.example.py to
# config.py and make your changes there.


# TODO: uncomment the correct device below to import a default config. You
# can override any setting by specifying it again in this file.
from configuration.door import *

# from configuration.interlock import *

# from configuration.memberbucks import *

# =========================================================================
# =========================== Portal Settings =============================
# =========================================================================
# Which portal instance to connect to
# PORTAL_WS_URL = "ws://192.168.1.174:8080/api/ws/access"
PORTAL_WS_URL = "wss://portal.brisbanemaker.space/ws/access"

# Access Control Device API key from portal
# API_SECRET = "DNUql8l8.8jl4VZDBU3TiQTteMpzIjQw2WzuQIDJl"  # dev
API_SECRET = "DQWvSFI8.oKg3sJbbz3TchNB1CdCcwPp3yrLWg5JS"  # prd

# =========================================================================
# ======================== WiFi Network Settings ==========================
# =========================================================================
WIFI_SSID = "bmsiot"
WIFI_PASS = "444422224444"

# =========================================================================
# ========================== Buzzer Settings ==============================
# =========================================================================
BUZZER_ENABLED = True
BUZZ_ON_SWIPE = True  # send a short buzz when a card is swiped

# =========================================================================
# ========================= Development Settings ==========================
# =========================================================================
# Enables the hardware watchdog timer to reset the ESP if software crashes.
ENABLE_WDT = True  # You definitely want this on in production!

# Ignore unhandled exceptions and continue the event loop.
CATCH_ALL_EXCEPTIONS = True  # You definitely want this on in production!

# Log level for debug messages
LOG_LEVEL = ulogging.WARNING  # You can increase this to e.g. DEBUG or INFO
