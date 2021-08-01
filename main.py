from leds import *
import time

LED_DATA_PIN = 16
NUMBER_LEDS = 12
ANIMATION_DELAY = 75

LEDS = Leds(pin=LED_DATA_PIN, number=NUMBER_LEDS)

while True:
    for x in range(NUMBER_LEDS):
        LEDS.set_channel(x, RED)
        time.sleep_ms(ANIMATION_DELAY)
        LEDS.clear()
    for x in range(NUMBER_LEDS):
        LEDS.set_channel(x, BLUE)
        time.sleep_ms(ANIMATION_DELAY)
        LEDS.clear()
    for x in range(NUMBER_LEDS):
        LEDS.set_channel(x, PURPLE)
        time.sleep_ms(ANIMATION_DELAY)
        LEDS.clear()
    for x in range(NUMBER_LEDS):
        LEDS.set_channel(x, GREEN)
        time.sleep_ms(ANIMATION_DELAY)
        LEDS.clear()
    for x in range(NUMBER_LEDS):
        LEDS.set_channel(x, YELLOW)
        time.sleep_ms(ANIMATION_DELAY)
        LEDS.clear()

    for x in range(2):
        for x in range(NUMBER_LEDS):
            LEDS.set_channel(x, RED)
            time.sleep_ms(ANIMATION_DELAY)

        for x in range(NUMBER_LEDS):
            LEDS.set_channel(x, OFF)
            time.sleep_ms(ANIMATION_DELAY)

    for x in range(2):
        for x in range(50, 200):
            LEDS.set_all((0, x, 0))
            time.sleep_ms(1)

        for x in reversed(range(50, 200)):
            LEDS.set_all((0, x, 0))
            time.sleep_ms(1)