# boot.py -- run on boot-up
import config
import webrepl

if config.ENABLE_WEBREPL:
    webrepl.start(password=config.API_SECRET[:9])
