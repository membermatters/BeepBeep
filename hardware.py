import config
import time
import ulogging
import urequests
from machine import WDT, Pin, I2C
from neopixel import NeoPixel
from ulcdscreen import LcdScreen

ulogging.basicConfig(level=ulogging.INFO)
logger = ulogging.getLogger("main")

wdt = None

if config.ENABLE_WDT:
    logger.warn("Press CTRL+C to stop the WDT starting...")
    time.sleep(3)
    wdt = WDT(timeout=config.UNLOCK_DELAY * 1000 + 5000)


def feedWDT():
    if config.ENABLE_WDT and wdt:
        wdt.feed()


DEVICE_TYPE = config.DEVICE_TYPE

# setup i2c and lcd
i2c = I2C(0, scl=Pin(config.SCL_PIN), sda=Pin(config.SDA_PIN), freq=400000)
i2c_devices = []
lcd = None

for device in i2c.scan():
    i2c_devices.append(device)
    logger.debug(
        f"Found i2c device. Decimal address: {device} | Hexa address: {hex(device)}"
    )

if config.LCD_ADDR in i2c_devices:
    lcd = LcdScreen(
        i2c, i2c_address=config.LCD_ADDR, columns=config.LCD_COLS, rows=config.LCD_ROWS
    )

else:
    # initialise without i2c address, and it will silently skip all writes to the i2c bus
    logger.error("LCD not found on i2c bus but it's configured!")
    lcd = LcdScreen(i2c, i2c_address=None)

# setup other pins
buzzer_pin = Pin(config.BUZZER_PIN, Pin.OUT)
lock_pin = Pin(config.LOCK_PIN, Pin.OUT, value=config.LOCK_REVERSED)
vend_pin = Pin(config.RELAY_PIN, Pin.OUT, value=config.VEND_REVERSED)
accept_coins_pin = Pin(config.ACCEPT_COINS_PIN, Pin.IN, pull=Pin.PULL_DOWN)
led = None
rgb_led = None

if config.LED_PIN:
    led = Pin(config.LED_PIN, Pin.OUT)

if config.RGB_LED_PIN:
    rgb_led = NeoPixel(
        Pin(config.RGB_LED_PIN, Pin.OUT), config.RGB_LED_COUNT
    )  # create NeoPixel driver for 1 pixel

# WS2812 uses GRB instead of RGB!
RGB_OFF = (0, 0, 0)
RGB_WHITE = (255, 255, 255)
RGB_RED = (0, 255, 0)
RGB_GREEN = (255, 0, 0)
RGB_BLUE = (0, 0, 255)
RGB_YELLOW = (255, 255, 0)
RGB_PURPLE = (0, 130, 130)
RGB_PINK = (0, 200, 50)


def rgb_led_set(colour):
    if config.RGB_LED_PIN:
        for x in range(config.RGB_LED_COUNT):
            rgb_led[x] = colour
        rgb_led.write()


def colorwheel(pos, p=False):
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if pos < 85:
        value = (int(255 - pos * 3), int(pos * 3), 0)
        if p:
            print(value)
        return value
    if pos < 170:
        pos -= 85
        value = (0, int(255 - pos * 3), int(pos * 3))
        if p:
            print(value)
        return value
    pos -= 170
    value = (int(pos * 3), 0, int(255 - pos * 3))
    if p:
        print(value)
    return value


def rgb_led_set_colourwheel():
    rgb_led_set(colorwheel(((time.ticks_ms() / 1000) * 100) % 255))


def lock():
    rgb_led_set(RGB_BLUE)  # blue is standby
    led_off()
    if config.LOCK_REVERSED:
        lock_pin.on()
    else:
        lock_pin.off()


def unlock():
    rgb_led_set(RGB_GREEN)  # green is unlocked
    led_on()
    if config.LOCK_REVERSED:
        lock_pin.off()
    else:
        lock_pin.on()


def led_on():
    if config.LED_PIN:
        if config.LED_REVERSED:
            led.off()
            if lcd:
                lcd.no_backlight()
        else:
            led.on()
            if lcd:
                lcd.backlight()


def led_off():
    if config.LED_PIN:
        if config.LED_REVERSED:
            led.on()
            if lcd:
                lcd.backlight()
        else:
            led.off()
            if lcd:
                lcd.no_backlight()


def buzzer_on():
    if config.BUZZER_ENABLED:
        buzzer_pin.on()


def buzzer_off():
    if config.BUZZER_ENABLED:
        buzzer_pin.off()


def alert(rgb_return_colour=RGB_BLUE):
    buzzer_on()
    led_on()
    rgb_led_set(RGB_RED)
    time.sleep(0.3)

    buzzer_off()
    led_off()
    rgb_led_set(rgb_return_colour)
    time.sleep(0.3)

    buzzer_on()
    led_on()
    rgb_led_set(RGB_RED)
    time.sleep(0.3)

    buzzer_off()
    led_off()
    rgb_led_set(rgb_return_colour)


def buzz_ok():
    buzzer_on()
    led_on()
    rgb_led_set(RGB_GREEN)

    time.sleep(1)

    led_off()
    rgb_led_set(RGB_BLUE)
    buzzer_off()


def buzz_card_read():
    buzzer_on()
    time.sleep(0.2)
    buzzer_off()


def buzz_action():
    buzzer_on()
    time.sleep(config.ACTION_BUZZ_DELAY)
    buzzer_off()


def door_swipe_success():
    # TODO: add support for a contact sensor to make locking logic more robust
    logger.warn("Unlocking!")
    unlock()
    rgb_led_set(RGB_GREEN)
    buzz_ok()
    time.sleep(config.ACTION_BUZZ_DELAY)
    lock()
    rgb_led_set(RGB_BLUE)
    logger.warn("Locking!")


def door_swipe_denied():
    alert()


def interlock_session_started():
    rgb_led_set(RGB_GREEN)
    led_on()
    buzz_action()


def interlock_session_ended():
    rgb_led_set(RGB_BLUE)
    led_off()
    # buzz_action()


def interlock_power_control(status: bool):
    tasmota_base_url = f"http://{config.TASMOTA_HOST}/cm?user={config.TASMOTA_USER}&password={config.TASMOTA_PASSWORD}&cmnd=Power%20"

    if status:
        if config.TASMOTA_HOST:
            logger.info("Trying to turn ON remote interlock!")
            r = urequests.get(tasmota_base_url + "On")
            return True

        else:
            unlock()
            return True

    else:
        if config.TASMOTA_HOST:
            logger.info("Trying to turn ON remote interlock!")
            r = urequests.get(tasmota_base_url + "Off")
            return True

        else:
            lock()
            return True


def vend_on():
    if config.VEND_REVERSED:
        vend_pin.off()
    else:
        vend_pin.on()


def vend_off():
    if config.VEND_REVERSED:
        vend_pin.on()
    else:
        vend_pin.off()


def accept_coins():
    if config.ACCEPT_COINS_REVERSED:
        return not accept_coins_pin.value()
    else:
        return accept_coins_pin.value()


def vend_product():
    rgb_led_set(RGB_GREEN)
    led_on()
    if config.BUZZ_ON_SWIPE:
        buzz_action()

    if config.VEND_MODE == "toggle":
        # TODO: timeout after 60 seconds and refund the money
        # currently we will wait forever for the accept coins signal to go low
        # even if a drink is never vended.
        vend_on()
        start_time = time.time()
        while time.time() - start_time < config.VEND_TOGGLE_TIME:
            time.sleep(0.1)
            feedWDT()
        vend_off()
    elif config.VEND_MODE == "hold":
        vend_on()
        time.sleep(1)

        # once the vend relay is on, we need to wait for the accept coins signal to go low
        # before we can turn it off again
        while accept_coins():
            time.sleep(0.1)
        vend_off()

    rgb_led_set(RGB_BLUE)
    led_off()
