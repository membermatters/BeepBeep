import config
import time
import ulogging
import urequests
from machine import WDT, Pin, I2C
from neopixel import NeoPixel
from ulcdscreen import LcdScreen

ulogging.basicConfig(level=config.LOG_LEVEL)
logger = ulogging.getLogger("hardware")

wdt = None

if config.ENABLE_WDT:
    logger.warn("Press CTRL+C to stop the WDT starting...")
    time.sleep(3)
    wdt = WDT(timeout=config.FIXED_UNLOCK_DELAY * 2000 + 5000)


def feedWDT():
    if config.ENABLE_WDT and wdt:
        wdt.feed()


DEVICE_TYPE = config.DEVICE_TYPE

# setup i2c and lcd
i2c = None
i2c_devices = []
lcd = None

if config.SDA_PIN and config.SCL_PIN:
    i2c = I2C(0, scl=Pin(config.SCL_PIN), sda=Pin(config.SDA_PIN), freq=400000)

    for device in i2c.scan():
        i2c_devices.append(device)
        logger.debug(
            f"Found i2c device. Decimal address: {device} | Hexa address: {hex(device)}"
        )

if config.LCD_ENABLE and config.LCD_ADDR in i2c_devices:
    lcd = LcdScreen(
        i2c,
        i2c_address=config.LCD_ADDR,
        columns=config.LCD_COLS,
        rows=config.LCD_ROWS,
    )

else:
    # initialise without i2c address, and it will silently skip all writes to the i2c bus
    logger.error("LCD not found on i2c bus but it's configured!")
    lcd = LcdScreen(i2c, i2c_address=None)

# setup other pins
buzzer = None
reader_led = None
lock_pin = None
relay_pin = None
door_sensor_pin = None
status_led_pin = None
in_1_pin = None
out_1_pin = None
aux_1_pin = None
aux_2_pin = None
rgb_led_pin = None

if config.READER_BUZZER_PIN:
    buzzer = Pin(config.READER_BUZZER_PIN, Pin.OUT)

if config.READER_LED_PIN:
    reader_led = Pin(config.READER_LED_PIN, Pin.OUT)

if config.LOCK_PIN:
    lock_pin = Pin(config.LOCK_PIN, Pin.OUT, value=config.LOCK_REVERSED)

if config.RELAY_PIN:
    relay_pin = Pin(config.RELAY_PIN, Pin.OUT, value=config.RELAY_REVERSED)

if config.DOOR_SENSOR_PIN:
    door_sensor_pin = Pin(config.DOOR_SENSOR_PIN, Pin.IN)

if config.STATUS_LED_PIN:
    status_led_pin = Pin(config.STATUS_LED_PIN, Pin.OUT)

if config.IN_1_PIN:
    in_1_pin = Pin(config.IN_1_PIN, Pin.IN)

if config.OUT_1_PIN:
    out_1_pin = Pin(config.OUT_1_PIN, Pin.OUT, value=config.OUT_1_REVERSED)

if config.AUX_1_PIN:
    aux_1_pin = Pin(config.AUX_1_PIN, Pin.IN, pull=Pin.PULL_DOWN)

if config.AUX_2_PIN:
    aux_2_pin = Pin(config.AUX_2_PIN, Pin.IN, pull=Pin.PULL_DOWN)

if config.RGB_LED_PIN:
    rgb_led_pin = NeoPixel(
        Pin(config.RGB_LED_PIN, Pin.OUT), config.RGB_LED_COUNT
    )  # create NeoPixel driver for 1 pixel


def status_led_on():
    if status_led_pin:
        status_led_pin.on()


def status_led_off():
    if status_led_pin:
        status_led_pin.off()


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
        logger.debug(f"Setting RGB LED to {colour}")
        for x in range(config.RGB_LED_COUNT):
            rgb_led_pin[x] = colour
        rgb_led_pin.write()


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
    if config.READER_LED_PIN:
        if config.READER_LED_REVERSED:
            reader_led.off()
        else:
            reader_led.on()

    if lcd:
        lcd.no_backlight()


def led_off():
    if config.READER_LED_PIN:
        if config.READER_LED_REVERSED:
            reader_led.on()
        else:
            reader_led.off()

    if lcd:
        lcd.backlight()


def buzzer_on():
    if config.BUZZER_ENABLED:
        if config.BUZZER_REVERSED:
            buzzer.off()
        else:
            buzzer.on()


def buzzer_off():
    if buzzer:
        if config.BUZZER_REVERSED:
            buzzer.on()
        else:
            buzzer.off()


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


def buzz_ok(flash_led=True):
    buzzer_on()
    if flash_led:
        led_on()
        rgb_led_set(RGB_GREEN)

    time.sleep(1)

    if flash_led:
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


def interlock_session_started():
    rgb_led_set(RGB_GREEN)
    led_on()
    buzz_action()


def interlock_session_ended():
    rgb_led_set(RGB_BLUE)
    led_off()
    # buzz_action()


tasmota_base_url = f"http://{config.TASMOTA_HOST}/cm?user={config.TASMOTA_USER}&password={config.TASMOTA_PASSWORD}&cmnd="


def reset_interlock_power_usage() -> bool:
    if config.TASMOTA_HOST:
        logger.debug("Resetting power usage from remote interlock!")
        r = urequests.get(
            tasmota_base_url + "Backlog%20EnergyToday%200%3B%20EnergyTotal%200%3B"
        )
        return True


def interlock_power_control(status: bool) -> bool:
    if status:
        if config.TASMOTA_HOST:
            logger.info("Trying to turn ON remote interlock!")
            r = urequests.get(tasmota_base_url + f"Power%20On")
            return True

        else:
            unlock()
            return True

    else:
        if config.TASMOTA_HOST:
            logger.info("Trying to turn OFF remote interlock!")
            r = urequests.get(tasmota_base_url + f"Power%20Off")
            return True

        else:
            lock()
            return True


def get_interlock_power_usage() -> float | None:
    if config.TASMOTA_HOST:
        logger.debug("Getting power usage from remote interlock!")
        r = urequests.get(tasmota_base_url + "EnergyTotal")
        return float(r.json()["EnergyTotal"]["Total"])
    else:
        None


def relay_on():
    if config.RELAY_REVERSED:
        relay_pin.off()
    else:
        relay_pin.on()


def relay_off():
    if config.RELAY_REVERSED:
        relay_pin.on()
    else:
        relay_pin.off()


def out_1_on():
    if config.OUT_1_REVERSED:
        out_1_pin.off()
    else:
        out_1_pin.on()


def out_1_off():
    if config.RELAY_REVERSED:
        relay_pin.on()
    else:
        relay_pin.off()


def get_door_sensor_state():
    if config.DOOR_SENSOR_REVERSED:
        return not door_sensor_pin.value()
    else:
        return door_sensor_pin.value()


def get_in_1_state():
    if config.IN_1_REVERSED:
        return not in_1_pin.value()
    else:
        return in_1_pin.value()


def get_aux_1_state():
    if config.AUX_1_REVERSED:
        return not aux_1_pin.value()
    else:
        return aux_1_pin.value()


def get_aux_2_state():
    if config.AUX_2_REVERSED:
        return not aux_2_pin.value()
    else:
        return aux_2_pin.value()


def vend_product():
    rgb_led_set(RGB_GREEN)
    led_on()
    if config.BUZZ_ON_SWIPE:
        buzz_action()

    if config.VEND_MODE == "toggle":
        # TODO: timeout after 60 seconds and refund the money
        # currently we will wait forever for the accept coins signal to go low
        # even if a drink is never vended.
        relay_on()
        unlock()
        start_time = time.time()
        while time.time() - start_time < config.VEND_TOGGLE_TIME:
            time.sleep(0.1)
            feedWDT()
        relay_off()
        lock()
    elif config.VEND_MODE == "hold":
        relay_on()
        unlock()
        time.sleep(1)

        # once the vend relay is on, we need to wait for the accept coins (door sensor)
        # signal to go low before we can turn it off again
        while get_in_1_state():
            time.sleep(0.1)
        relay_off()
        lock()

    rgb_led_set(RGB_BLUE)
    led_off()
