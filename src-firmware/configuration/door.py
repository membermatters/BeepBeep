from configuration.base import *
from models import DeviceType

# =========================================================================
# ============================== WARNING! =================================
# =========================================================================
# Do not change this file to make configuration changes. This is a base
# config file used for the other config files. Copy config.example.py
# to config.py and make your changes there.

# =========================================================================
# ========================== General Settings =============================
# =========================================================================
DEVICE_TYPE = DeviceType.DOOR
LCD_ENABLE = False
LOCK_REVERSED = False
RELAY_REVERSED = False
DOOR_SENSOR_REVERSED = True
DOOR_SENSOR_ENABLED = True
DOOR_SENSOR_TIMEOUT = 5  # seconds to wait for the door to open before locking again
IN_1_REVERSED = True
FIXED_UNLOCK_DELAY = 7  # seconds to remain unlocked
