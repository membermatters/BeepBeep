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
DEVICE_TYPE = DeviceType.DOOR_ROLLER
LCD_ENABLE = False
LOCK_REVERSED = False
RELAY_REVERSED = False
DOOR_SENSOR_REVERSED = True
DOOR_SENSOR_ENABLED = False
DOOR_SENSOR_TIMEOUT = 10  # seconds to wait for the door to open before locking again
FIXED_UNLOCK_DELAY = 10  # seconds to remain unlocked
