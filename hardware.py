import config
import time
from machine import Pin, PWM
from neopixel import NeoPixel

DEVICE_TYPE = config.DEVICE_TYPE

# setup pins
buzzer = PWM(Pin(config.BUZZER_PIN), freq=400, duty=0)
lock_pin = Pin(config.LOCK_PIN, Pin.OUT, value=config.LOCK_REVERSED)
led = Pin(config.LED_PIN, Pin.OUT)
rgb_led = NeoPixel(
    Pin(config.RGB_LED_PIN, Pin.OUT), 1
)  # create NeoPixel driver for 1 pixel

RGB_OFF = (0, 0, 0)
RGB_WHITE = (255, 255, 255)
RGB_RED = (255, 0, 0)
RGB_GREEN = (0, 255, 0)
RGB_BLUE = (0, 0, 255)
RGB_YELLOW = (255, 255, 0)


def rgb_led_set(colour):
    rgb_led[0] = colour
    rgb_led.write()


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
    if config.LED_REVERSED:
        led.off()
    else:
        led.on()


def led_off():
    if config.LED_REVERSED:
        led.on()
    else:
        led.off()


def buzzer_on():
    if config.BUZZER_ENABLED:
        buzzer.duty(0)


def buzzer_off():
    if config.BUZZER_ENABLED:
        buzzer.duty(1023)


def buzz_alert():
    buzzer_on()
    led_on()
    rgb_led_set(RGB_RED)
    time.sleep(0.2)

    buzzer_off()
    led_off()
    rgb_led_set(RGB_BLUE)
    time.sleep(0.2)

    buzzer_on()
    led_on()
    rgb_led_set(RGB_RED)
    time.sleep(0.2)

    buzzer_off()
    led_off()
    rgb_led_set(RGB_BLUE)


def buzz_ok():
    buzzer_on()
    led_on()
    rgb_led_set(RGB_GREEN)

    time.sleep(1)

    led_off()
    rgb_led_set(RGB_BLUE)
    buzzer_off()


def buzz_card_read():
    buzzer.duty(512)
    time.sleep(0.1)
    buzzer.duty(0)


def led_ok():
    led_on()
    rgb_led_set(RGB_GREEN)

    time.sleep(1)

    led_off()
    rgb_led_set(RGB_OFF)
