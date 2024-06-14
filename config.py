import ulogging


# TODO: uncomment the correct device below to import a default config. You
# can override any setting by specifying it again in this file.
from config.door import *

# from config.interlock import *

# from config.memberbucks import *

# =========================================================================
# =========================== Portal Settings =============================
# =========================================================================
# Which portal instance to connect to
# PORTAL_WS_URL = "ws://192.168.1.42:8080/api/ws/access" # local dev server
PORTAL_WS_URL = "wss://portal.example.com/ws/access"

# Access Control Device API key from portal
API_SECRET = "XXXXXXXX.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# =========================================================================
# ======================== WiFi Network Settings ==========================
# =========================================================================
WIFI_SSID = "Makerspace WiFi"
WIFI_PASS = "12345678"

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
