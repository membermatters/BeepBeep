# General Device Config
DEVICE_TYPE = "door"  # "door", "interlock" or "memberbucks"
LOCK_REVERSED = False
LED_REVERSED = True
BUZZER_ENABLED = True
BUZZ_ON_SWIPE = False  # send a short buzz when a card is swiped
UNLOCK_DELAY = 5  # seconds to remain unlocked
ACTION_BUZZ_DELAY = 2  # seconds to buzz for an action (unlock, lock, etc)

# Remote Interlock Config
TASMOTA_HOST = None  # "192.168.2.61" # set to the IP of the TASMOTA switching device to enable remote control
TASMOTA_USER = "admin"
TASMOTA_PASSWORD = "admin"

# Pin Configuration
BUZZER_PIN = 26  # IO num, not pin num
LED_PIN = None  # 27  # IO num, not pin num
RGB_LED_PIN = 27  # IO num, not pin num - optional, but recommended for interlocks
RGB_LED_COUNT = 30  # number of LEDs in the strip
LOCK_PIN = 13  # IO num, not pin num

# Wiegand Config
WIEGAND_ENABLED = True
WIEGAND_ZERO = 21
WIEGAND_ONE = 22

# Set True for full 32bit mifare UIDs or False for 24bit mifare UIDs
UID_32BIT_MODE = True

# Which portal instance to connect to
PORTAL_WS_URL = "wss://portal.brisbanemaker.space/ws/access"

# WiFi and Access Control Device API key from portal
API_SECRET = "X"
WIFI_SSID = "example"
WIFI_PASS = "example"

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

# WiFi Tx Power
TX_POWER = 8.5

# ESP timer ID. For ESP32 use -1 virtual timer (if supported), or 0 for hw timer
TIMER_ID = -1
