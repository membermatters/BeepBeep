# General Device Config
DEVICE_TYPE = "interlock"  # "door", "interlock" or "memberbucks"
LOCK_REVERSED = False
LED_REVERSED = True
BUZZER_ENABLED = True
BUZZ_ON_SWIPE = False  # send a short buzz when a card is swiped
UNLOCK_DELAY = 5  # seconds to remain unlocked
ACTION_BUZZ_DELAY = 2  # seconds to buzz for an action (unlock, lock, etc)

# Remote Interlock Config
TASMOTA_HOST = None  # "192.168.2.61"  # set to the IP of the TASMOTA switching device to enable remote control
TASMOTA_USER = "admin"
TASMOTA_PASSWORD = "admin"

# Pin Configuration
BUZZER_PIN = 26  # IO num, not pin num
LED_PIN = None  # 27  # IO num, not pin num
RGB_LED_PIN = 16  # IO num, not pin num - optional, but recommended for interlocks
RGB_LED_COUNT = 30  # number of LEDs in the strip
LOCK_PIN = 13  # IO num, not pin num
SDA_PIN = 21  # IO num, not pin num
SCL_PIN = 22  # IO num, not pin num

# LCD Config
LCD_ADDR = 0x27  # I2C address of LCD display
LCD_COLS = 16  # number of columns on the LCD display
LCD_ROWS = 2  # number of rows on the LCD display

# Wiegand Config
WIEGAND_ENABLED = True
WIEGAND_ZERO = 27
WIEGAND_ONE = 14

# Set True for full 32bit mifare UIDs or False for 24bit mifare UIDs
UID_32BIT_MODE = True

# Which portal instance to connect to
# PORTAL_WS_URL = "ws://192.168.1.174:8080/api/ws/access"
# PORTAL_WS_URL = "ws://10.0.0.130:8080/api/ws/access"
PORTAL_WS_URL = "wss://portal.brisbanemaker.space/ws/access"

# WiFi and Access Control Device API key from portal
# API_SECRET = "7ioWPv23.fZRez6dtkclffdMD3mIjUMndN0Wr6zbA"  # dev
API_SECRET = "secure_api_secret"  # prd
WIFI_SSID = "cool_name"
WIFI_PASS = "secure_password"

# You probably shouldn't mess with these!

# Enables the backup HTTP server.
ENABLE_BACKUP_HTTP_SERVER = False

# Enables the micropython WebREPL feature.
# The password is the first 8 characters (or less) of API_SECRET.
ENABLE_WEBREPL = False

# Enables the hardware watchdog timer.
ENABLE_WDT = False

# Ignore exceptions and continue the event loop
CATCH_ALL_EXCEPTIONS = True

# WiFi Tx Power - set to None for max power
TX_POWER = None

# ESP timer ID. For ESP32 use -1 virtual timer (if supported), or 0 for hw timer
TIMER_ID = -1
