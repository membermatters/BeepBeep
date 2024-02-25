import network
import config
import ulogging
import time
from machine import reset
import ubinascii
import json
import uwebsockets.client
import hardware
import utils
import gc

if config.ENABLE_BACKUP_HTTP_SERVER:
    import httpserver

ulogging.basicConfig(level=ulogging.INFO)
logger = ulogging.getLogger("main")

hardware.buzzer_off()
hardware.rgb_led_set(hardware.RGB_OFF)
hardware.led_off()

# setup is starting
hardware.rgb_led_set(hardware.RGB_PURPLE)
hardware.alert(rgb_return_colour=hardware.RGB_PURPLE)
hardware.lcd.print("Initialising...")


INTERLOCK_SESSION = {
    "session_id": None,  # any value == on, None == off
    "total_kwh": 0,
}
STATE = {"locked_out": False, "tag_hash": ""}


def save_state(state):
    global STATE
    logger.info("Saving STATE!!")

    STATE = state  # update the in memory state

    try:
        # save the state to flash
        with open("state.json", "w") as state_file:
            json.dump(state, state_file)
            logger.debug("saved state to flash")
        return True

    except Exception as e:
        logger.error("Saving STATE FAILED! Exception:")
        logger.error(str(e))
        return False


def get_state():
    global STATE
    try:
        # create it if it doesn't exist
        if not utils.file_or_dir_exists("state.json"):
            with open("state.json", "w") as state_file:
                json.dump(STATE, state_file)

        with open("state.json") as state_file:
            STATE = json.load(state_file)
            if STATE:
                logger.info("Loaded saved STATE from flash.")
            return STATE

    except Exception as e:
        logger.error("Could not load saved STATE (unhandled error)")
        logger.error(str(e))
        return False


# setup RFID
if config.WIEGAND_ENABLED:
    # setup wiegand reader
    import uwiegand

    rfid_reader = uwiegand.Wiegand(
        config.WIEGAND_ZERO, config.WIEGAND_ONE, uid_32bit_mode=config.UID_32BIT_MODE
    )
else:
    from urdm6300.urdm6300 import Rdm6300

    rfid_reader = Rdm6300(rx=config.UART_RX_PIN, tx=config.UART_TX_PIN)


try:
    # create it if it doesn't exist
    if not utils.file_or_dir_exists("tags.json"):
        with open("tags.json", "w") as new_tags:
            json.dump([], new_tags)

        # if we have any saved tags, load them
    with open("tags.json") as tags:
        parsed_tags = json.load(tags)
        if parsed_tags:
            authorised_rfid_tags = parsed_tags
            logger.info("Loaded %s saved tags from flash.", len(authorised_rfid_tags))
except:
    logger.error("Could not load saved tags (unhandled error)")

get_state()  # grab the state from the flash

# setup wifi
hardware.lcd.clear()
hardware.lcd.print("Connecting WiFi")

sta_if = network.WLAN(network.STA_IF)
local_ip = None  # store our local IP address
local_mac = ubinascii.hexlify(sta_if.config("mac")).decode()  # store our mac address

hostname = "MM_Controller_" + local_mac
# network.hostname(hostname)

wlan_connecting_start = time.ticks_ms()
led_toggle_last_update = time.ticks_ms()
led_toggle_last_state = False

if not sta_if.isconnected():
    logger.info("Connecting To WiFi...")
    sta_if.active(True)
    if config.TX_POWER:
        sta_if.config(txpower=config.TX_POWER)
    sta_if.connect(config.WIFI_SSID, config.WIFI_PASS)

    while not sta_if.isconnected():
        if time.ticks_diff(time.ticks_ms(), wlan_connecting_start) > 10000:
            logger.warn("Took too long to wait for WiFi!")
            logger.warn(
                "The ESP32 should continue trying to connect in the background."
            )
            hardware.led_off()
            hardware.rgb_led_set(hardware.RGB_PURPLE)  # booting up colour
            break

        if time.ticks_diff(time.ticks_ms(), led_toggle_last_update) > 250:
            led_toggle_last_update = time.ticks_ms()
            hardware.feedWDT()

            if led_toggle_last_state:
                hardware.led_off()
                hardware.rgb_led_set(hardware.RGB_OFF)
                led_toggle_last_state = False

            else:
                hardware.led_on()
                hardware.rgb_led_set(hardware.RGB_PURPLE)
                led_toggle_last_state = True

    hardware.led_off()
    hardware.rgb_led_set(hardware.RGB_PURPLE)  # booting up colour

    local_ip = sta_if.ifconfig()[0]
    logger.info("Local IP: " + local_ip)
    logger.info("Local MAC: " + local_mac)


websocket = None
led_update = time.ticks_ms()
ten_second_cron_update = time.ticks_ms()
last_pong = None
last_rfid_sync = time.ticks_ms()


def setup_websocket_connection():
    global websocket, last_pong

    if not sta_if.isconnected():
        logger.warn("WiFi not connected...")
        return

    WS_URL = f"{config.PORTAL_WS_URL}/{config.DEVICE_TYPE}/{local_mac}"

    try:
        logger.info("connecting to websocket...")
        logger.info("WS_URL: " + WS_URL)
        hardware.lcd.clear()
        hardware.lcd.print("Connecting WS")
        websocket = uwebsockets.client.connect(WS_URL)
        last_pong = time.ticks_ms()

        auth_packet = {"command": "authenticate", "secret_key": config.API_SECRET}
        websocket.send(json.dumps(auth_packet))

        ip_packet = {"command": "ip_address", "ip_address": local_ip}
        websocket.send(json.dumps(ip_packet))

    except Exception as e:
        logger.error("Couldn't connect to websocket!")
        logger.error(str(e))
        hardware.lcd.clear()
        hardware.lcd.print("WS Connect Fail")


def save_tags(new_tags):
    global authorised_rfid_tags
    logger.info("Syncing tags!!")

    try:
        authorised_rfid_tags = new_tags
        logger.info("Got %s tags!", len(authorised_rfid_tags))
        # save the tags to flash
        with open("tags.json", "w") as tags_file:
            json.dump(authorised_rfid_tags, tags_file)
            logger.debug("Saved tags to flash")

        logger.debug("Syncing tags done!")

    except Exception as e:
        logger.error("Syncing tags FAILED! Exception:")
        logger.error(str(e))


def log_door_swipe(card_id, rejected=False, locked_out=False):
    logger.info("Logging door swipe!")

    try:
        if rejected:
            websocket.send(
                json.dumps({"command": "log_access_denied", "card_id": card_id})
            )
        elif locked_out:
            websocket.send(
                json.dumps({"command": "log_access_locked_out", "card_id": card_id})
            )
        else:
            websocket.send(json.dumps({"command": "log_access", "card_id": card_id}))
    except Exception as e:
        logger.warn("Exception when logging access!")
        logger.error(e)


def interlock_end_session():
    if (
        INTERLOCK_SESSION.get("session_id")
        and INTERLOCK_SESSION.get("session_id") != "system"
    ):
        print(INTERLOCK_SESSION.get("session_id"))
        try:
            interlock_packet = {
                "command": "interlock_session_end",
                "session_id": INTERLOCK_SESSION.get("session_id"),
                "session_kwh": INTERLOCK_SESSION.get("session_kwh"),
                "card_id": card,
            }
            websocket.send(json.dumps(interlock_packet))
        except:
            hardware.alert()

    INTERLOCK_SESSION["session_id"] = None
    INTERLOCK_SESSION["total_kwh"] = 0
    hardware.interlock_power_control(False)
    hardware.interlock_session_ended()


def handle_swipe_door(card: str):
    hardware.buzz_card_read()

    if card in authorised_rfid_tags:
        if STATE["locked_out"]:
            try:
                log_door_swipe(card, locked_out=True)
            except:
                pass
            hardware.door_swipe_denied()

        else:
            # if there's an issue logging the swipe, open the door anyway
            try:
                log_door_swipe(card)
            except:
                pass
            # TODO: check if door was manually unlocked and only unlock on a double swipe
            hardware.door_swipe_success()

    else:
        try:
            log_door_swipe(card, rejected=True)
        except:
            pass
        hardware.door_swipe_denied()


def handle_swipe_interlock(card: str):
    # request a new interlock session
    if INTERLOCK_SESSION.get("session_id") is None:
        interlock_packet = {
            "command": "interlock_session_start",
            "card_id": card,
        }
        try:
            websocket.send(json.dumps(interlock_packet))
        except:
            hardware.alert()

    # turn off the interlock if it was manually turned on by the system
    elif INTERLOCK_SESSION.get("session_id") == "system":
        interlock_packet = {"command": "interlock_off"}

        try:
            websocket.send(json.dumps(interlock_packet))
            interlock_end_session()
        except:
            hardware.alert()

    # end the current interlock session
    else:
        interlock_end_session()


def handle_swipe_memberbucks(card_id: str):
    # attempt to debit the card
    debit_packet = {
        "command": "debit",
        "card_id": card_id,
        "amount": config.VEND_PRICE / 100,
    }
    try:
        websocket.send(json.dumps(debit_packet))
        hardware.lcd.clear()
        hardware.lcd.print("Please Wait... ")
        hardware.lcd.blink()
    except:
        hardware.alert()


if config.ENABLE_BACKUP_HTTP_SERVER:
    import uselect

    # try to set up the http server
    if not httpserver.setup_http_server():
        logger.error("FAILED to setup http server on startup :(")
    else:
        poll = uselect.poll()
        poll.register(httpserver.sock, uselect.POLLIN)
else:
    logger.warning("Backup http server disabled!")

setup_websocket_connection()

logger.info("Starting main loop...")
hardware.led_on()
time.sleep(0.5)
hardware.led_off()
hardware.rgb_led_set(hardware.RGB_BLUE)


def print_device_standby_message():
    if config.DEVICE_TYPE in ["interlock", "door"]:
        hardware.lcd.clear()
        hardware.lcd.print("Swipe To Unlock! ")
        hardware.lcd.print_rocket()
    elif config.DEVICE_TYPE == "memberbucks":
        hardware.lcd.clear()
        hardware.lcd.print("Coming Soon! ")
        hardware.lcd.print_rocket()


last_card_id = None
print_device_standby_message()

while True:
    hardware.feedWDT()
    try:
        if card := rfid_reader.read_card():
            card = str(card)
            logger.info(f"got a card: {card}")

            if config.BUZZ_ON_SWIPE:
                hardware.buzz_card_read()

            if config.DEVICE_TYPE == "door":
                handle_swipe_door(card)

            if config.DEVICE_TYPE == "interlock":
                handle_swipe_interlock(card)

            if config.DEVICE_TYPE == "memberbucks":
                handle_swipe_memberbucks(card)

            # dedupe card reads; keep looping until we've cleared the buffer
            while True:
                if not rfid_reader.read_card():
                    break
            last_card_id = card
            card = None

        # every 10 seconds run cron tasks
        cron_period = 10 * 1000

        if time.ticks_diff(time.ticks_ms(), ten_second_cron_update) > cron_period:
            ten_second_cron_update = time.ticks_ms()
            gc.collect()

            # if we've missed at least 3 consecutive pongs, then reconnect
            if time.ticks_diff(time.ticks_ms(), last_pong) > cron_period * 4:
                websocket = None
                logger.info(
                    "Websocket not open (pong timeout), trying to reconnect."
                )
                setup_websocket_connection()
                print_device_standby_message()

                # this stops us trying to reconnect every 10 seconds and holding up the main loop
                last_pong = time.ticks_ms()

                # skip the rest of this event loop
                continue

            if websocket and websocket.open:
                try:
                    logger.debug("sending ping")
                    websocket.send(json.dumps({"command": "ping"}))
                except:
                    websocket = None
                    setup_websocket_connection()

                    # this stops us trying to reconnect every 10 seconds and holding up the main loop
                    last_pong = time.ticks_ms()

                    # skip the rest of this event loop
                    continue

                if (
                    INTERLOCK_SESSION.get("session_id") is not None
                    and INTERLOCK_SESSION.get("session_id") != "system"
                ):
                    logger.debug("Sending interlock session update")
                    interlock_packet = {
                        "command": "interlock_session_update",
                        "session_id": INTERLOCK_SESSION.get("session_id"),
                        "session_kwh": INTERLOCK_SESSION.get("session_kwh"),
                    }
                    try:
                        websocket.send(json.dumps(interlock_packet))
                    except:
                        continue

            else:
                logger.info("Websocket not open, trying to reconnect.")
                setup_websocket_connection()

        if websocket and websocket.open:
            if data := websocket.recv():
                logger.debug("Got websocket packet:")
                logger.debug(data)

                try:
                    data = json.loads(data)

                    if data.get("authorised") is not None:
                        logger.info("Got authorisation packet.")
                        print_device_standby_message()

                    elif data.get("command") == "pong":
                        last_pong = time.ticks_ms()

                    elif data.get("command") == "ping":
                        websocket.send(json.dumps({"command": "pong"}))

                    elif data.get("command") == "reboot":
                        logger.warn("Rebooting device!")
                        if config.DEVICE_TYPE == "interlock":
                            interlock_end_session()
                        else:
                            hardware.lock()
                            hardware.buzz_action()
                        hardware.rgb_led_set(hardware.RGB_OFF)
                        reset()

                    elif data.get("command") == "update_device_locked_out":
                        locked_out = data.get("locked_out")
                        logger.info(f"Updating device locked out {locked_out}!")
                        STATE["locked_out"] = locked_out
                        save_state(STATE)

                    elif data.get("command") == "bump" and config.DEVICE_TYPE == "door":
                        logger.info("Bumping Door!")
                        hardware.door_swipe_success()

                    elif data.get("command") == "sync":
                        tags_hash_new = data.get("hash")
                        tags_hash_current = STATE.get("tag_hash")

                        if tags_hash_new != tags_hash_current:
                            save_tags(data.get("tags"))
                            STATE["tag_hash"] = tags_hash_new
                            save_state(STATE)
                            logger.info(f"Saved tags with hash: {tags_hash_new}")
                        else:
                            logger.info("Tags hash unchanged, skipping save.")

                    elif data.get("command") == "unlock":
                        if config.DEVICE_TYPE == "interlock":
                            logger.info("Turning on interlock from manual request!")
                            if hardware.interlock_power_control(True):
                                INTERLOCK_SESSION[
                                    "session_id"
                                ] = "system"  # special state - manually turned on by the system
                                hardware.interlock_session_started()

                            elif config.DEVICE_TYPE == "door":
                                logger.warn("Interlock power control failed!")
                                hardware.alert()
                        else:
                            logger.info("Unlocking device from manual request!")
                            hardware.unlock()

                    elif data.get("command") == "lock":
                        if config.DEVICE_TYPE == "door":
                            logger.info("Locking device from manual request!")
                            hardware.lock()

                        elif config.DEVICE_TYPE == "interlock":
                            logger.info("Turning off interlock from manual request!")
                            interlock_end_session()
                    elif data.get("command") == "interlock_session_start":
                        if config.DEVICE_TYPE == "interlock":
                            logger.info("Turning on interlock from new session!")

                            INTERLOCK_SESSION["session_id"] = data.get("session_id")
                            INTERLOCK_SESSION["total_kwh"] = 0

                            if hardware.interlock_power_control(True):
                                hardware.interlock_session_started()

                            else:
                                logger.warn("Interlock power control failed!")
                                hardware.alert()

                    elif data.get("command") == "interlock_session_rejected":
                        if config.DEVICE_TYPE == "interlock":
                            logger.info("Interlock session request failed!")
                            hardware.alert()

                    elif data.get("command") == "interlock_session_update":
                        pass

                    elif data.get("command") == "debit":
                        hardware.lcd.reset_screen()
                        print(data)
                        success = data.get("success")
                        balance = data.get("balance")

                        balance = (
                            f"${str(round(float(balance) / 100, 2))}"
                            if balance
                            else "Unknown"
                        )
                        if success:
                            logger.info("Debit successful!")
                            hardware.lcd.clear()
                            hardware.lcd.print_rocket()
                            hardware.lcd.print(f" Success! {balance}")
                            hardware.buzz_action()
                            hardware.vend_product()
                            time.sleep(5)
                        else:
                            logger.info("Debit failed!")
                            hardware.lcd.clear()
                            hardware.lcd.print(f"Vend Declined :(Balance: {balance}")
                            hardware.lcd.no_backlight()
                            hardware.rgb_led_set(hardware.RGB_RED)
                            time.sleep(0.25)
                            hardware.lcd.backlight()
                            time.sleep(0.25)
                            hardware.lcd.no_backlight()
                            time.sleep(0.25)
                            hardware.lcd.backlight()
                            hardware.feedWDT()
                            time.sleep(5)
                            hardware.rgb_led_set(hardware.RGB_BLUE)
                        print_device_standby_message()
                    else:
                        logger.warn("Unknown websocket packet!")
                        logger.warn(json.dumps(data))

                except Exception as e:
                    logger.error("Error parsing JSON websocket packet!")
                    logger.error(str(e))

        if config.ENABLE_BACKUP_HTTP_SERVER:
            # backup http server for manually bumping a door from the local network
            for _ in poll.poll(1):
                conn, addr = httpserver.sock.accept()
                request = str(conn.recv(2048))
                hardware.rgb_led_set(hardware.RGB_PURPLE)
                logger.info("got http request!")
                logger.info(request)
                time.sleep(0.1)
                hardware.rgb_led_set(hardware.RGB_BLUE)
                httpserver.client_response(conn)
                if f"/bump?secret={config.API_SECRET}" in request:
                    logger.info("got authenticated bump request")
                    hardware.door_swipe_success()
                    break

    except KeyboardInterrupt as e:
        # turn off the LED and buzzer in case they were left on
        hardware.led_off()
        hardware.rgb_led_set(hardware.RGB_WHITE)
        hardware.buzzer_off()
        hardware.lcd.clear()
        hardware.lcd.print("KeybInt Stopped.")

        raise e

    except Exception as e:
        if config.CATCH_ALL_EXCEPTIONS:
            print(
                "excepted, but config.CATCH_ALL_EXCEPTIONS is enabled so ignoring :( "
            )
            print(e)
            continue
        else:
            hardware.lcd.clear()
            hardware.lcd.print("Error Stopped.")
            # turn off the LED and buzzer in case they were left on
            hardware.led_off()
            hardware.rgb_led_set(hardware.RGB_WHITE)
            hardware.buzzer_off()
            raise e
