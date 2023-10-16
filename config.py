# General Device Config
DEVICE_TYPE = "interlock"  # "door", "interlock" or "memberbucks"
INTERLOCK_REMOTE_IP = "192.168.1.61"  # set to the IP of the TASMOTA switching device if remote control is enabled
LOCK_REVERSED = False
LED_REVERSED = True
BUZZER_ENABLED = True
UNLOCK_DELAY = 5  # seconds to remain unlocked

# Pin Configuration
BUZZER_PIN = 26  # IO num, not pin num
LED_PIN = 27  # IO num, not pin num
RGB_LED_PIN = 25  # IO num, not pin num - only used by interlock devices
LOCK_PIN = 14  # IO num, not pin num

# Wiegand Config
WIEGAND_ENABLED = True
WIEGAND_ZERO = 22
WIEGAND_ONE = 21

# Set True for full 32bit mifare UIDs or False for 24bit mifare UIDs
UID_32BIT_MODE = True

# Which portal instance to connect to
PORTAL_WS_URL = "ws://192.168.1.174:8080/api/ws/access"

# WiFi and Access Control Device API key from portal
API_SECRET = "7ioWPv23.fZRez6dtkclffdMD3mIjUMndN0Wr6zbA"
WIFI_SSID = "Bill Wi The Science Fi"
WIFI_PASS = "225261007622"

# You probably shouldn't mess with these!

# Enables the backup HTTP server.
ENABLE_BACKUP_HTTP_SERVER = False

# Enables the micropython WebREPL feature.
# The password is the first 8 characters (or less) of API_SECRET.
ENABLE_WEBREPL = False

# Enables the hardware watchdog timer.
ENABLE_WDT = False

# WiFi Tx Power
TX_POWER = 8.5

# ESP timer ID. For ESP32 use -1 virtual timer (if supported), or 0 for hw timer
TIMER_ID = -1
