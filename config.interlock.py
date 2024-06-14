from config.base import *

# =========================================================================
# ========================== General Settings =============================
# =========================================================================
DEVICE_TYPE = "interlock"  # "door", "interlock" or "memberbucks"
LOCK_REVERSED = False
RELAY_REVERSED = False
IN_1_REVERSED = True
FIXED_UNLOCK_DELAY = 7  # seconds to remain unlocked

# =========================================================================
# ====================== Remote Interlock Settings ========================
# =========================================================================
TASMOTA_HOST = None  # "192.168.2.61"  # set to None or the IP of the TASMOTA switching device to enable remote control
TASMOTA_USER = "admin"
TASMOTA_PASSWORD = "admin"
