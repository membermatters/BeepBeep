import ulogging

# =========================================================================
# ============================== WARNING! =================================
# =========================================================================
# Do not change this file to make configuration changes. This is a base
# config file used for the other config files. Copy configsetting.example.py
# to configsetting.py and make your changes there.


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
# ========================== General Settings =============================
# =========================================================================
DEVICE_TYPE = "door"  # "door", "interlock" or "memberbucks"
LOCK_REVERSED = False
READER_LED_REVERSED = True
RELAY_REVERSED = False
DOOR_SENSOR_REVERSED = True
DOOR_SENSOR_ENABLED = True
DOOR_SENSOR_TIMEOUT = 5  # seconds to wait for the door to open before locking again
DOOR_OPEN_ALARM_TIMEOUT = None  # seconds to wait for the door to close before alarming
OUT_1_REVERSED = False
IN_1_REVERSED = True
AUX_1_REVERSED = False
AUX_2_REVERSED = False
FIXED_UNLOCK_DELAY = 7  # seconds to remain unlocked
RGB_LED_COUNT = 1  # number of LEDs in the strip
WIEGAND_ENABLED = True

# =========================================================================
# ========================== Buzzer Settings ==============================
# =========================================================================
BUZZER_ENABLED = True
BUZZER_REVERSED = True
BUZZ_ON_SWIPE = True  # send a short buzz when a card is swiped
ACTION_BUZZ_DELAY = 2  # seconds to buzz for an action (unlock, lock, etc)

# =========================================================================
# ====================== Remote Interlock Settings ========================
# =========================================================================
TASMOTA_HOST = None  # "192.168.2.61"  # set to None or the IP of the TASMOTA switching device to enable remote control
TASMOTA_USER = "admin"
TASMOTA_PASSWORD = "admin"

# =========================================================================
# ========================== Vending Settings =============================
# =========================================================================
VEND_PRICE = 250  # price in cents to debit an account
# None, "hold" or "toggle" - None disable, hold until the accept coins signal is ready, toggle will hold for VEND_TOGGLE_TIME (s)
VEND_MODE = None
VEND_TOGGLE_TIME = 1

# =========================================================================
# ============================ LCD Settings ===============================
# =========================================================================
LCD_ENABLE = True  # set to False to disable the LCD
LCD_ADDR = 0x27  # I2C address of LCD display
LCD_COLS = 16  # number of columns on the LCD display
LCD_ROWS = 2  # number of rows on the LCD display

# =========================================================================
# ========================== Pin Configuration ============================
# =========================================================================
AUX_1_PIN = 2  # IO num, not pin num
AUX_2_PIN = 1  # IO num, not pin num

RGB_LED_PIN = 37  # Recommended for interlocks
STATUS_LED_PIN = 38  # On board status LED

READER_LED_PIN = 5  # IO num, not pin num
READER_BUZZER_PIN = 4  # IO num, not pin num
RELAY_PIN = 36  # IO num, not pin num
LOCK_PIN = 14  # IO num, not pin num
DOOR_SENSOR_PIN = 12  # IO num, not pin num

OUT_1_PIN = 35  # IO num, not pin num
IN_1_PIN = 13  # IO num, not pin num

SDA_PIN = 48  # IO num, not pin num
SCL_PIN = 47  # IO num, not pin num

UART_RX_PIN = 16  # IO num, not pin num - used if WIEGAND_ENABLED is False
UART_TX_PIN = 15  # IO num, not pin num - used if WIEGAND_ENABLED is False

WIEGAND_ZERO = 7
WIEGAND_ONE = 6

# =========================================================================
# ========================= Development Settings ==========================
# =========================================================================
# Enables the hardware watchdog timer.
ENABLE_WDT = False

# Ignore exceptions and continue the event loop
CATCH_ALL_EXCEPTIONS = False

# Log level for debug messages
LOG_LEVEL = ulogging.INFO

# Enables the micropython WebREPL feature.
# The password is the first 8 characters (or less) of API_SECRET.
ENABLE_WEBREPL = False

# =========================================================================
# ====================== BE CAREFUL ADJUSTING THESE! ======================
# =========================================================================
# Enables the backup HTTP server. May be less secure and impact reliability.
ENABLE_BACKUP_HTTP_SERVER = False

# Set True for full 32bit mifare UIDs or False for 24bit mifare UIDs
UID_32BIT_MODE = True

# WiFi Tx Power - set to None for max power
WIFI_TX_POWER = None

# two-letter ISO 3166-1 Alpha-2 country code to be used for radio compliance
WIFI_COUNTRY_CODE = "AU"

# ESP timer ID. For ESP32 use -1 virtual timer (if supported), or 0 for hw timer
WIEGAND_TIMER_ID = 0

# every 10 seconds run cron tasks
CRON_PERIOD = 10 * 1000
