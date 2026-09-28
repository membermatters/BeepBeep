"""WiFi setup, connection management, and background monitoring."""

import asyncio

import network
import ubinascii

import config
import ulogging
from hardware import Colour, hal

logger = ulogging.getLogger("wifi")
local_ip = None
local_mac = None


def setup() -> None:
    """Read the station MAC and configure the hostname and regulatory country."""
    global local_mac
    local_mac = ubinascii.hexlify(hal.sta_if.config("mac")).decode()
    hostname = "BeepBeep_" + local_mac
    logger.info("Setting hostname to: " + hostname)
    network.hostname(hostname)
    logger.debug("Setting WiFi country code to: " + config.WIFI_COUNTRY_CODE)
    network.country(config.WIFI_COUNTRY_CODE)


async def wifi_reset() -> None:
    """Disconnect and cycle the station interface, then apply configured TX power."""
    logger.info("Resetting Wi-Fi...")
    if hal.sta_if.isconnected():
        logger.debug("Already connected to WiFi, disconnecting first...")
        hal.sta_if.disconnect()
        await asyncio.sleep(0.5)

    hal.sta_if.active(False)
    await asyncio.sleep(0.5)
    hal.sta_if.active(True)
    if config.WIFI_TX_POWER:
        logger.debug(f"Setting WiFi Tx Power to {config.WIFI_TX_POWER}dBm")
        hal.sta_if.config(txpower=config.WIFI_TX_POWER)
    logger.info("Wi-Fi reset done.")

async def wifi_connect(reset_websocket: "asyncio.Event") -> bool:
    """Reset WiFi and wait for a connection while flashing the setup indicators.

    On success, update local_ip, request WebSocket reconnection and return True.
    Return False if connect() raises OSError or the final connection check fails.
    Waiting for the station to connect has no timeout.
    """
    global local_ip

    old_colour = hal.rgb_colour
    hal.set_status_led_on()
    hal.set_rgb_led(Colour.WIFI_SETUP)

    await wifi_reset()

    logger.info("Connecting To WiFi...")
    try:
        hal.sta_if.connect(config.WIFI_SSID, config.WIFI_PASS)
    except OSError as e:
        logger.error(e)
        return False

    # asynchronously toggle the LED while we're waiting for WiFi to connect
    hal.set_status_led_off()
    while not hal.sta_if.isconnected():
        hal.set_status_led_on()
        hal.set_rgb_led(Colour.WIFI_SETUP)
        await asyncio.sleep(0.25)
        hal.set_status_led_off()
        hal.set_rgb_led(Colour.IDLE)
        await asyncio.sleep(0.25)

    hal.set_reader_led_off()
    hal.set_status_led_off()
    hal.set_rgb_led(old_colour)

    if hal.sta_if.isconnected():
        hal.set_status_led_on()
        new_ip = hal.sta_if.ifconfig()[0]
        if new_ip != local_ip:
            local_ip = new_ip
            logger.info("New Local IP: " + local_ip)
        logger.info("WiFi connected; requesting WebSocket reconnect.")
        reset_websocket.set()  # trigger a websocket reconnect
        return True
    else:
        return False

async def handle_wifi_check(reset_websocket: "asyncio.Event") -> None:
    """Monitor WiFi once per second and reconnect when the station is offline.

    Pass reset_websocket to wifi_connect() so a new WiFi connection invalidates
    the old WebSocket. Connection errors outside its handled OSError propagate.
    """
    while True:
        if hal.sta_if.isconnected():
            await asyncio.sleep(1)
        else:
            logger.warning("WiFi disconnected, attempting to reconnect...")
            await wifi_connect(reset_websocket)
