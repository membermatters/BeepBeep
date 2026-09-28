"""WebSocket connection setup, cleanup, heartbeats, and reconnection."""

import asyncio
import json
import time

from async_websocket_client import AsyncWebsocketClient

import config
import ulogging
import wifi
from hardware import Colour, hal
from models import DeviceType

try:
    from typing import TYPE_CHECKING
except ImportError:  # MicroPython does not provide typing.
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable

logger = ulogging.getLogger("websocket_manager")
websocket = None
last_pong = time.ticks_ms()
reset_websocket = asyncio.Event()


async def disconnect_websocket(connection: "AsyncWebsocketClient | None") -> None:
    """Close a connection, clearing shared state only if it is still active.

    Passing None clears the status LED only when no active connection exists.
    Closing an older connection leaves its replacement untouched.
    """
    global websocket
    if connection is not None:
        logger.debug(
            "Closing WebSocket connection %s (active=%s).",
            id(connection), websocket is connection,
        )
    if websocket is connection:
        websocket = None
        hal.set_status_led_off()
    if connection is not None:
        await connection.close()
        logger.debug("WebSocket connection %s closed.", id(connection))

async def connect_websocket() -> None:
    """Replace the WebSocket and send authentication and the current IP address.

    If WiFi is offline, reconnect it and defer the WebSocket to a later call.
    Bound the handshake to ten seconds and clean up failed connection attempts.
    A ready connection means authentication was sent, not yet acknowledged.
    """
    global websocket, last_pong

    if not hal.sta_if.isconnected():
        logger.warning("Tried to setup websocket but WiFi is not connected...")
        await wifi.wifi_connect(reset_websocket)
        return

    device_type = config.DEVICE_TYPE
    if device_type == DeviceType.DOOR_ROLLER:
        device_type = "door"

    WS_URL = f"{config.PORTAL_WS_URL}/{device_type}/{wifi.local_mac}"

    logger.debug("Preparing WebSocket connection; closing any previous connection.")
    await disconnect_websocket(websocket)
    reset_websocket.clear()
    connection = AsyncWebsocketClient()
    started_at = time.ticks_ms()
    stage = "handshake"
    try:
        logger.info("Connecting to websocket...")
        logger.debug("WS_URL: " + WS_URL)
        hal.set_status_led_off()
        hal.lcd.clear()
        hal.lcd.print("Connecting WS")
        logger.debug("WebSocket %s: starting handshake (timeout=10s).", id(connection))
        await asyncio.wait_for(connection.handshake(WS_URL), 10)
        logger.debug(
            "WebSocket %s: handshake completed after %s ms.",
            id(connection), time.ticks_diff(time.ticks_ms(), started_at),
        )
        logger.info("Connected to websocket...")

        stage = "authentication send"
        logger.debug("WebSocket %s: sending authentication request.", id(connection))
        auth_packet = {
            "command": "authenticate",
            "secret_key": config.API_SECRET,
        }
        await connection.send(json.dumps(auth_packet))
        logger.debug("WebSocket authentication request sent; awaiting server response.")

        stage = "IP address send"
        ip_packet = {"command": "ip_address", "ip_address": wifi.local_ip}
        await connection.send(json.dumps(ip_packet))
        logger.debug("WebSocket IP address announcement sent.")
        websocket = connection
        last_pong = time.ticks_ms()
        hal.set_status_led_on()
        logger.debug(
            "WebSocket %s: connection ready after %s ms; heartbeat timer reset.",
            id(connection), time.ticks_diff(time.ticks_ms(), started_at),
        )

    except Exception as e:  # noqa: BLE001
        logger.debug(
            "WebSocket %s: connection failed during %s after %s ms: %r",
            id(connection), stage, time.ticks_diff(time.ticks_ms(), started_at), e,
        )
        await disconnect_websocket(connection)
        logger.error("Couldn't connect to websocket!")
        logger.error(e)
        hal.lcd.clear()
        hal.lcd.print("WS Connect Fail")
        hal.set_status_led_off()


async def run_websocket_heartbeat(print_standby_message: "Callable[[], None]") -> None:
    """Send JSON pings and check reconnection needs every CRON_PERIOD ms.

    Close connections on WiFi loss, reset requests or three periods without a
    pong. Call the synchronous display callback on heartbeat timeout. Log loop
    errors and continue only when CATCH_ALL_EXCEPTIONS is enabled.
    """
    global last_pong
    while True:
        await asyncio.sleep_ms(config.CRON_PERIOD)
        try:
            if reset_websocket.is_set() or not hal.sta_if.isconnected():
                logger.debug(
                    "WebSocket cleanup: reconnect_requested=%s, wifi_connected=%s.",
                    reset_websocket.is_set(), hal.sta_if.isconnected(),
                )
                await disconnect_websocket(websocket)
                reset_websocket.clear()
            if not hal.sta_if.isconnected():
                logger.debug("Skipping WebSocket reconnect while WiFi is disconnected.")
                continue

            # if we've missed at least 3 consecutive pongs, then reconnect
            if time.ticks_diff(time.ticks_ms(), last_pong) > config.CRON_PERIOD * 3:
                logger.debug(
                    "WebSocket heartbeat expired: elapsed=%s ms, timeout=%s ms.",
                    time.ticks_diff(time.ticks_ms(), last_pong), config.CRON_PERIOD * 3,
                )
                await disconnect_websocket(websocket)
                logger.debug("Websocket not open (pong timeout), trying to reconnect.")
                print_standby_message()

                # Restart the heartbeat timeout window after requesting a reconnect.
                last_pong = time.ticks_ms()

            if websocket and await websocket.open():
                connection = websocket
                try:
                    logger.debug("WebSocket %s: sending heartbeat ping.", id(connection))
                    await connection.send(json.dumps({"command": "ping"}))
                    logger.debug("WebSocket heartbeat ping sent.")
                except Exception as e:  # noqa: BLE001
                    logger.debug("WebSocket heartbeat send failed; closing before next reconnect attempt: %r", e)
                    await disconnect_websocket(connection)
                    logger.error("Websocket not open, trying to reconnect.")
                    logger.error(e)
                    hal.set_status_led_off()
                    continue

            else:
                logger.debug(
                    "WebSocket reconnect needed: connection_present=%s.",
                    websocket is not None,
                )
                logger.info("Websocket not open, trying to reconnect.")
                await connect_websocket()

        except KeyboardInterrupt:
            # turn off the LED and buzzer in case they were left on
            hal.set_reader_led_off()
            hal.set_rgb_led(Colour.RGB_WHITE)
            hal.set_reader_buzzer_off()
            hal.set_status_led_off()
            hal.lcd.clear()
            hal.lcd.print("KeybInt Stopped.")

            raise

        except Exception as e:
            if config.CATCH_ALL_EXCEPTIONS:
                logger.error(
                    "excepted, but config.CATCH_ALL_EXCEPTIONS is enabled so ignoring :("
                )
                logger.error(e)
            else:
                logger.error(
                    "excepted, but config.CATCH_ALL_EXCEPTIONS is disabled so throwing :o"
                )
                logger.error(e)
                hal.lcd.clear()
                hal.lcd.print("Error Stopped.")
                # turn off the LED and buzzer in case they were left on
                hal.set_reader_led_off()
                hal.set_rgb_led(Colour.RGB_WHITE)
                hal.set_reader_buzzer_off()
                raise
