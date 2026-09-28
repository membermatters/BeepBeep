import asyncio
import time

import network
from machine import I2C, WDT, Pin
from neopixel import NeoPixel

import config
import ulogging
from ulcdscreen import LcdScreen

logger = ulogging.getLogger("hardware")


class Colour:
    # WS2812 uses GRB instead of RGB!
    RGB_OFF = (0, 0, 0)
    RGB_WHITE = (255, 255, 255)
    RGB_RED = (0, 255, 0)
    RGB_GREEN = (255, 0, 0)
    RGB_BLUE = (0, 0, 255)
    RGB_YELLOW = (255, 255, 0)
    RGB_PURPLE = (0, 130, 130)
    RGB_PINK = (0, 200, 50)

    SETUP = RGB_PURPLE
    IDLE = RGB_BLUE
    WIFI_SETUP = RGB_YELLOW
    UNLOCKED = RGB_GREEN
    ALERT = RGB_RED
    ALERT_OK = RGB_GREEN


class HardwareState:
    """Expose live logical input states for a HAL instance."""

    def __init__(self, hal: "HAL") -> None:
        """Keep the HAL whose input pins are read by these properties."""
        self._hal = hal

    @property
    def door_sensor(self) -> bool | None:
        """Read the door sensor state, respecting DOOR_SENSOR_REVERSED.

        Return None if the pin is unconfigured; otherwise return a bool.
        """
        pin = self._hal.door_sensor_pin
        if pin is None:
            return None
        value = bool(pin.value())
        return not value if config.DOOR_SENSOR_REVERSED else value

    @property
    def in_1(self) -> bool | None:
        """Read the IN_1 state, respecting IN_1_REVERSED.

        Return None if the pin is unconfigured; otherwise return a bool.
        """
        pin = self._hal.in_1_pin
        if pin is None:
            return None
        value = bool(pin.value())
        return not value if config.IN_1_REVERSED else value

    @property
    def aux_1(self) -> bool | None:
        """Read the AUX_1 state, respecting AUX_1_REVERSED.

        Return None if the pin is unconfigured; otherwise return a bool.
        """
        pin = self._hal.aux_1_pin
        if pin is None:
            return None
        value = bool(pin.value())
        return not value if config.AUX_1_REVERSED else value

    @property
    def aux_2(self) -> bool | None:
        """Read the AUX_2 state, respecting AUX_2_REVERSED.

        Return None if the pin is unconfigured; otherwise return a bool.
        """
        pin = self._hal.aux_2_pin
        if pin is None:
            return None
        value = bool(pin.value())
        return not value if config.AUX_2_REVERSED else value


class HAL:
    """Hardware Abstraction Layer (HAL) for hardware control operations."""

    def __init__(self) -> None:
        """Initialize the watchdog, network interface, LCD, pins and RFID reader."""
        ulogging.basicConfig(level=config.LOG_LEVEL)

        self.wdt = None

        if config.ENABLE_WDT:
            logger.warning("Press CTRL+C to stop WDT starting in 3...")
            time.sleep(1)
            logger.warning("2...")
            time.sleep(1)
            logger.warning("1...")
            time.sleep(1)
            self.wdt = WDT(timeout=config.FIXED_UNLOCK_DELAY * 2000 + 5000)

        self.sta_if = network.WLAN(network.STA_IF)

        self.i2c = None
        self.i2c_devices = []
        self.lcd = LcdScreen(self.i2c, i2c_address=None)

        if config.SDA_PIN and config.SCL_PIN:
            self.i2c = I2C(0, scl=Pin(config.SCL_PIN), sda=Pin(config.SDA_PIN), freq=400000)

            for device in self.i2c.scan():
                self.i2c_devices.append(device)
                logger.debug(
                    f"Found i2c device. Decimal address: {device} | Hex address: {hex(device)}"
                )

        if config.LCD_ENABLE and config.LCD_ADDR in self.i2c_devices:
            logger.debug(f"Found LCD at i2c address {config.LCD_ADDR}. Initializing...")
            self.lcd = LcdScreen(
                self.i2c,
                i2c_address=config.LCD_ADDR,
                columns=config.LCD_COLS,
                rows=config.LCD_ROWS,
            )
            logger.debug("LCD initialized successfully.")

        elif config.LCD_ENABLE:
            # initialise without i2c address, and it will silently skip all writes to the i2c bus
            logger.error("LCD not found on i2c bus but it's configured!")

        self.reader_buzzer_pin: None | Pin = None
        self.reader_led_pin: None | Pin = None
        self.lock_pin: None | Pin = None
        self.relay_pin: None | Pin = None
        self.door_sensor_pin: None | Pin = None
        self.status_led_pin: None | Pin = None
        self.in_1_pin: None | Pin = None
        self.out_1_pin: None | Pin = None
        self.aux_1_pin: None | Pin = None
        self.aux_2_pin: None | Pin = None
        self.rgb_led_pin: None | NeoPixel = None

        if config.READER_BUZZER_PIN:
            self.reader_buzzer_pin = Pin(config.READER_BUZZER_PIN, Pin.OUT)

        if config.READER_LED_PIN:
            self.reader_led_pin = Pin(config.READER_LED_PIN, Pin.OUT)

        if config.LOCK_PIN:
            self.lock_pin = Pin(config.LOCK_PIN, Pin.OUT, value=config.LOCK_REVERSED)

        if config.RELAY_PIN:
            self.relay_pin = Pin(config.RELAY_PIN, Pin.OUT, value=config.RELAY_REVERSED)

        if config.DOOR_SENSOR_PIN:
            self.door_sensor_pin = Pin(config.DOOR_SENSOR_PIN, Pin.IN)

        if config.STATUS_LED_PIN:
            self.status_led_pin = Pin(config.STATUS_LED_PIN, Pin.OUT)

        if config.IN_1_PIN:
            self.in_1_pin = Pin(config.IN_1_PIN, Pin.IN)

        if config.OUT_1_PIN:
            self.out_1_pin = Pin(config.OUT_1_PIN, Pin.OUT, value=config.OUT_1_REVERSED)

        if config.AUX_1_PIN:
            self.aux_1_pin = Pin(config.AUX_1_PIN, Pin.IN, pull=Pin.PULL_DOWN)

        if config.AUX_2_PIN:
            self.aux_2_pin = Pin(config.AUX_2_PIN, Pin.IN, pull=Pin.PULL_DOWN)

        if config.RGB_LED_PIN:
            self.rgb_led_pin = NeoPixel(
                Pin(config.RGB_LED_PIN, Pin.OUT), config.RGB_LED_COUNT
            )  # create NeoPixel driver
            self.set_rgb_led(Colour.IDLE)  # set all pixels to blue (standby)

        self.rgb_colour = Colour.IDLE
        self.state = HardwareState(self)

        if config.WIEGAND_ENABLED:
            import uwiegand

            self.rfid_reader = uwiegand.Wiegand(
                config.WIEGAND_ZERO,
                config.WIEGAND_ONE,
                uid_32bit_mode=config.UID_32BIT_MODE,
                timer_id=config.WIEGAND_TIMER_ID,
            )
        else:
            from urdm6300 import Rdm6300

            self.rfid_reader = Rdm6300(rx=config.UART_RX_PIN, tx=config.UART_TX_PIN)

        logger.debug("HAL initialized successfully.")

    def feedWDT(self) -> None:
        """Feed the watchdog when it is enabled and initialized."""
        if config.ENABLE_WDT and self.wdt:
            logger.debug("Feeding watchdog timer.")
            self.wdt.feed()

    def set_status_led_on(self) -> None:
        """Turn on the status LED if its pin is configured."""
        if self.status_led_pin:
            self.status_led_pin.on()

    def set_status_led_off(self) -> None:
        """Turn off the status LED if its pin is configured."""
        if self.status_led_pin:
            self.status_led_pin.off()

    def set_rgb_led(self, colour: tuple[int, int, int]) -> None:
        """Set all configured RGB LEDs to a three-channel colour tuple.

        Use hardware.Colour.X constants."""
        if config.RGB_LED_PIN and self.rgb_led_pin:
            logger.debug(f"Setting RGB LED to {colour}")
            for x in range(config.RGB_LED_COUNT):
                self.rgb_led_pin[x] = colour
            self.rgb_led_pin.write()
            self.rgb_colour = colour
    
    @staticmethod
    def colorwheel(pos: float) -> tuple[int, int, int]:
        """Return a three-channel colour tuple for a wheel position from 0 to 255.

        Positions outside this range return (0, 0, 0)."""
        if pos < 0 or pos > 255:
            return (0, 0, 0)
        if pos < 85:
            value = (int(255 - pos * 3), int(pos * 3), 0)
            return value
        if pos < 170:
            pos -= 85
            value = (0, int(255 - pos * 3), int(pos * 3))
            return value
        pos -= 170
        value = (int(pos * 3), 0, int(255 - pos * 3))
        return value

    def set_rgb_led_colourwheel(self) -> None:
        """Set the RGB LEDs to the colour wheel position derived from uptime."""
        self.set_rgb_led(self.colorwheel(((time.ticks_ms() / 1000) * 100) % 255))

    def set_lock_on(self) -> None:
        """Drive the configured lock pin on, respecting LOCK_REVERSED."""
        if self.lock_pin:
            if config.LOCK_REVERSED:
                self.lock_pin.on()
            else:
                self.lock_pin.off()

    def set_lock_off(self) -> None:
        """Drive the configured lock pin off, respecting LOCK_REVERSED."""
        if self.lock_pin:
            if config.LOCK_REVERSED:
                self.lock_pin.off()
            else:
                self.lock_pin.on()

    def set_reader_led_on(self) -> None:
        """Turn on the configured reader LED, respecting READER_LED_REVERSED."""
        if config.READER_LED_PIN and self.reader_led_pin:
            if config.READER_LED_REVERSED:
                self.reader_led_pin.off()
            else:
                self.reader_led_pin.on()

    def set_reader_led_off(self) -> None:
        """Turn off the configured reader LED, respecting READER_LED_REVERSED."""
        if config.READER_LED_PIN and self.reader_led_pin:
            if config.READER_LED_REVERSED:
                self.reader_led_pin.on()
            else:
                self.reader_led_pin.off()

    def set_reader_buzzer_on(self) -> None:
        """Turn on the configured buzzer if enabled, respecting BUZZER_REVERSED."""
        if config.BUZZER_ENABLED and self.reader_buzzer_pin:
            if config.BUZZER_REVERSED:
                self.reader_buzzer_pin.off()
            else:
                self.reader_buzzer_pin.on()

    def set_reader_buzzer_off(self) -> None:
        """Turn off the configured buzzer, respecting BUZZER_REVERSED."""
        if self.reader_buzzer_pin:
            if config.BUZZER_REVERSED:
                self.reader_buzzer_pin.on()
            else:
                self.reader_buzzer_pin.off()

    async def play_alert(self, times: int = 2) -> None:
        """Play times alert beeps with LED flashes, defaulting to two.

        Each flash lasts 0.3 seconds, with a 0.3-second gap between flashes.
        Restore the RGB LEDs to self.rgb_colour after each flash and leave
        the reader LED and buzzer off. Non-positive times do nothing.
        """
        old_rgb_colour = self.rgb_colour

        for i in range(times):
            self.set_reader_buzzer_on()
            self.set_reader_led_on()
            self.set_rgb_led(Colour.ALERT)
            await asyncio.sleep(0.3)

            self.set_reader_buzzer_off()
            self.set_reader_led_off()
            self.set_rgb_led(old_rgb_colour)

            if i < times - 1:
                await asyncio.sleep(0.3)

    async def play_ok(self, short: bool = False, skip_led: bool = False) -> None:
        """Play a confirmation beep for one second, or half a second if short.

        Unless skip_led is set, light the reader LED and show Colour.ALERT_OK,
        then turn the reader LED off and restore the previous RGB colour.
        Yield to other tasks during the delay.
        """
        old_rgb_colour = self.rgb_colour
        self.set_reader_buzzer_on()
        if not skip_led:
            self.set_reader_led_on()
            self.set_rgb_led(Colour.ALERT_OK)
    
        await asyncio.sleep(0.5 if short else 1)

        self.set_reader_buzzer_off()
        if not skip_led:
            self.set_reader_led_off()
            self.set_rgb_led(old_rgb_colour)

    async def play_card_read(self) -> None:
        """Play a 0.5-second card-read beep, yielding during the delay."""
        await self.play_ok(short=True)

    async def play_action(self) -> None:
        """Play a beep for ACTION_BUZZ_DELAY seconds, yielding during the delay."""
        self.set_reader_buzzer_on()
        await asyncio.sleep(config.ACTION_BUZZ_DELAY)
        self.set_reader_buzzer_off()

    def set_relay_on(self) -> None:
        """Activate the configured relay, respecting RELAY_REVERSED."""
        if self.relay_pin:
            if config.RELAY_REVERSED:
                self.relay_pin.off()
            else:
                self.relay_pin.on()

    def set_relay_off(self) -> None:
        """Deactivate the configured relay, respecting RELAY_REVERSED."""
        if self.relay_pin:
            if config.RELAY_REVERSED:
                self.relay_pin.on()
            else:
                self.relay_pin.off()

    def set_out_1_on(self) -> None:
        """Activate the configured OUT_1 pin, respecting OUT_1_REVERSED."""
        if self.out_1_pin:
            if config.OUT_1_REVERSED:
                self.out_1_pin.off()
            else:
                self.out_1_pin.on()

    def set_out_1_off(self) -> None:
        """Deactivate the configured OUT_1 pin, respecting OUT_1_REVERSED."""
        if self.out_1_pin:
            if config.OUT_1_REVERSED:
                self.out_1_pin.on()
            else:
                self.out_1_pin.off()

# Share one board instance across firmware modules.
hal = HAL()
