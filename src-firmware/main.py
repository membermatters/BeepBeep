import sys

sys.path.insert(0, "/micropython-i2c-lcd")
sys.path.insert(0, "/micropython_async_websocket_client")
sys.path.insert(0, "/urdm6300")

import asyncio
import json
import time

from machine import reset

import config
import models
import ulogging
import websocket_manager
import wifi
from hardware import Colour, hal
from models import DeviceType, DoorState, LockState
from swipe_cards import SwipeCards

ulogging.basicConfig(level=config.LOG_LEVEL)
logger = ulogging.getLogger("main")

# setup is starting
hal.set_rgb_led(Colour.SETUP)
hal.set_reader_buzzer_on()
hal.set_reader_led_on()
hal.lcd.print("Initialising...")
time.sleep(0.5)
hal.set_reader_buzzer_off()
hal.set_reader_led_off()

wifi.setup()

if config.DEVICE_TYPE in models.DOOR_TYPES:
    from hardware.door import Door

    door = Door(config.DEVICE_TYPE, hal)
    device = door


def load_swipe_cards() -> SwipeCards:
    """Load the card cache before starting async tasks.

    Return an empty cache if the file is missing or invalid; log load errors.
    """
    swipe_cards = SwipeCards()
    try:
        if swipe_cards.load():
            logger.info("Loaded %s saved tags from flash.", len(swipe_cards.cards))
    except Exception as e:  # noqa: BLE001
        logger.error("Could not load saved cards.")
        logger.error(e)
    return swipe_cards


async def main(swipe_cards: SwipeCards) -> None:
    """Run card handling, WiFi, WebSocket and status LED tasks concurrently.

    Share the persistent card cache with server sync handling.
    Serialize local and remote door commands with a shared async lock.
    Clear indicators on KeyboardInterrupt. Log other task failures, re-raising
    when CATCH_ALL_EXCEPTIONS is disabled; completed tasks are not restarted.
    """
    door_command_lock = asyncio.Lock()

    async def log_door_swipe(card_id: str, result: str, action: str) -> None:
        """Send a swipe outcome and requested door action to the portal.

        Results are "success", "denied" or "locked_out"; actions are "lock" or
        "unlock". Invalid values raise ValueError. Skip sending when no
        connection exists and log send errors without retrying.
        """
        commands = {
            "success": "log_access",
            "denied": "log_access_denied",
            "locked_out": "log_access_locked_out",
        }
        if result not in commands:
            raise ValueError("Unknown swipe result: " + result)
        if action not in ("lock", "unlock"):
            raise ValueError("Unknown swipe action: " + action)

        logger.info("Logging door swipe: result=%s, action=%s.", result, action)
        connection = websocket_manager.websocket
        if connection:
            try:
                await connection.send(
                    json.dumps(
                        {
                            "command": commands[result],
                            "card_id": card_id,
                            "action": action,
                        }
                    )
                )
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "Exception when logging door swipe: result=%s, action=%s.",
                    result,
                    action,
                )
                logger.error(e)

    async def flicker_status_led() -> None:
        """Turn the connected status LED off for 200 ms every three seconds.

        Restore it only if the same WebSocket connection remains open.
        """
        while True:
            await asyncio.sleep_ms(2800)
            connection = websocket_manager.websocket
            if connection and await connection.open():
                hal.set_status_led_off()
                await asyncio.sleep_ms(200)
                if (
                    websocket_manager.websocket is connection
                    and await connection.open()
                ):
                    hal.set_status_led_on()
            else:
                await asyncio.sleep_ms(200)

    async def process_websocket_messages() -> None:
        """Process JSON commands and update heartbeat, door and saved tag state.

        Ignore messages from replaced connections and log command errors.
        Close failed connections and request reconnection; propagate receive
        errors when CATCH_ALL_EXCEPTIONS is disabled.
        """
        while True:
            await asyncio.sleep(0.01)
            connection = websocket_manager.websocket
            try:
                if connection and await connection.open():
                    message = await connection.recv()
                    if message is None:
                        logger.debug(
                            "WebSocket %s: receive returned no message; closing.",
                            id(connection),
                        )
                        await websocket_manager.disconnect_websocket(connection)
                        continue
                    if websocket_manager.websocket is not connection:
                        logger.debug(
                            "Ignoring message from replaced WebSocket %s.",
                            id(connection),
                        )
                        continue
                    logger.debug("Got websocket packet:")
                    logger.debug(message)

                    try:
                        if isinstance(message, bytes):
                            message = message.decode("utf-8")
                        if not isinstance(message, str):
                            raise TypeError(
                                "Expected a text or bytes WebSocket message"
                            )
                        data = json.loads(message)

                        if data.get("authorised") is not None:
                            logger.info("Got authorisation packet.")
                            device.print_standby_message()

                        elif data.get("command") == "pong":
                            logger.debug(
                                "WebSocket pong received; %s ms since last one.",
                                time.ticks_diff(
                                    time.ticks_ms(), websocket_manager.last_pong
                                ),
                            )
                            websocket_manager.last_pong = time.ticks_ms()

                        elif data.get("command") == "ping":
                            logger.debug(
                                "WebSocket server ping received; sending pong."
                            )
                            await connection.send(json.dumps({"command": "pong"}))
                            logger.debug("WebSocket pong sent.")

                        elif data.get("command") == "reboot":
                            logger.warning("Rebooting device!")
                            await hal.play_action()
                            hal.set_rgb_led(Colour.RGB_OFF)
                            hal.set_reader_led_off()
                            hal.set_reader_buzzer_off()
                            hal.set_status_led_off()
                            hal.lcd.clear()
                            hal.lcd.print("Rebooting...")
                            reset()

                        elif data.get("command") == "update_device_locked_out":
                            locked_out = data.get("locked_out")
                            logger.info(f"Updating device locked out {locked_out}!")
                            if config.DEVICE_TYPE in models.DOOR_TYPES:
                                door.lock_state = LockState.LOCKED_OUT

                        elif data.get("command") == "bump":
                            if config.DEVICE_TYPE not in models.DOOR_TYPES:
                                logger.warning(
                                    f"Ignoring bump command - device type {config.DEVICE_TYPE} isn't a door!"
                                )
                            else:
                                logger.info("Bumping door!")
                                async with door_command_lock:
                                    await door.unlock_door()
                                    await asyncio.sleep(config.BUMP_DELAY)

                                    # don't close roller doors after a bump
                                    if config.DEVICE_TYPE == DeviceType.DOOR:
                                        await door.lock_door()

                        elif data.get("command") == "sync":
                            if swipe_cards.update(data.get("tags"), data.get("hash")):
                                logger.info(
                                    "Saved %s tags with hash: %s",
                                    len(swipe_cards.cards),
                                    swipe_cards.card_hash,
                                )
                            else:
                                logger.info("Tags hash unchanged, skipping save.")

                        elif data.get("command") == "unlock":
                            logger.info("Unlocking device from manual request!")
                            if config.DEVICE_TYPE in models.DOOR_TYPES:
                                async with door_command_lock:
                                    await door.unlock_door()

                        elif data.get("command") == "lock":
                            logger.info("Locking device from manual request!")
                            if config.DEVICE_TYPE in models.DOOR_TYPES:
                                async with door_command_lock:
                                    await door.lock_door()

                        else:
                            logger.warning("Unknown websocket packet!")
                            logger.warning(json.dumps(data))

                    except Exception as e:  # noqa: BLE001
                        logger.error("Error parsing JSON websocket packet!")
                        logger.error(str(e))
            except Exception as e:
                logger.error("WebSocket receive failed!")
                logger.error(str(e))
                if websocket_manager.websocket is connection:
                    logger.debug(
                        "WebSocket receive failure on active connection; requesting reconnect."
                    )
                    websocket_manager.reset_websocket.set()
                await websocket_manager.disconnect_websocket(connection)
                if not config.CATCH_ALL_EXCEPTIONS:
                    raise

    async def process_card_swipes() -> None:
        """Poll RFID cards and allow local door actions only for authorised cards.

        Feed the watchdog on each outer iteration. Check authorisation after
        acquiring the shared door lock, alert and log denied cards, and skip
        roller-door swipes while moving. Propagate failures to main().
        """
        while True:
            await asyncio.sleep(0.01)
            hal.feedWDT()

            if card := hal.rfid_reader.read_card():
                card = str(card)
                logger.info(f"Got a card: {card}")

                if config.BUZZ_ON_SWIPE:
                    await hal.play_card_read()

                async with door_command_lock:
                    if not swipe_cards.is_authorised(card):
                        action = (
                            "lock"
                            if config.DEVICE_TYPE == DeviceType.DOOR_ROLLER
                            and door.open_state == DoorState.OPEN
                            else "unlock"
                        )
                        logger.warning("Rejecting unauthorised card: %s", card)
                        await asyncio.gather(
                            log_door_swipe(card, "denied", action),
                            hal.play_alert(),
                        )
                        continue

                    if config.DEVICE_TYPE == DeviceType.DOOR_ROLLER:
                        if door.open_state == DoorState.CLOSED:
                            logger.info("Door is closed, opening...")
                            await asyncio.gather(
                                log_door_swipe(card, "success", "unlock"),
                                door.unlock_door(),
                            )  # start opening the door

                        elif door.open_state == DoorState.OPEN:
                            logger.info("Door is open, closing...")

                            await asyncio.gather(
                                log_door_swipe(card, "success", "lock"),
                                door.lock_door(),
                            )  # start closing the door

                        elif door.open_state == DoorState.CLOSING:
                            logger.info("Door is closing, skipping loop...")
                            continue

                        elif door.open_state == DoorState.OPENING:
                            logger.info("Door is opening, skipping loop...")
                            continue

                    elif config.DEVICE_TYPE == DeviceType.DOOR:
                        await asyncio.gather(
                            log_door_swipe(card, "success", "unlock"),
                            door.unlock_door(),
                        )  # start opening the door
                        await door.lock_door()

                    else:
                        logger.error(
                            f"Got a card swipe, but device type {config.DEVICE_TYPE} isn't supported yet!"
                        )

                # dedupe card reads; keep looping until we've cleared the buffer
                while hal.rfid_reader.read_card():
                    await asyncio.sleep(0.01)
                card = None

    logger.info("Starting main event loops...")
    hal.set_rgb_led(Colour.IDLE)
    device.print_standby_message()

    try:
        await asyncio.gather(
            process_card_swipes(),
            wifi.handle_wifi_check(websocket_manager.reset_websocket),
            flicker_status_led(),
            process_websocket_messages(),
            websocket_manager.run_websocket_heartbeat(device.print_standby_message),
        )
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


swipe_cards = load_swipe_cards()
asyncio.run(main(swipe_cards))
