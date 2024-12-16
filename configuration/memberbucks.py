from configuration.base import *

# =========================================================================
# ============================== WARNING! =================================
# =========================================================================
# Do not change this file to make configuration changes. This is a base
# config file used for the other config files. Copy configsetting.example.py
# to configsetting.py and make your changes there.

# =========================================================================
# ========================== General Settings =============================
# =========================================================================
DEVICE_TYPE = "memberbucks"  # "door", "interlock" or "memberbucks"
LOCK_REVERSED = False
RELAY_REVERSED = False

# =========================================================================
# ========================== Vending Settings =============================
# =========================================================================
VEND_PRICE = 250  # price in cents to debit an account
# None, "hold" or "toggle" - None disable, hold until the accept coins signal is ready, toggle will hold for VEND_TOGGLE_TIME (s)
VEND_MODE = "hold"
VEND_TOGGLE_TIME = 1
