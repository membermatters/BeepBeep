import os
import uwiegand
import network
import config
import ulogging
from urdm6300.urdm6300 import Rdm6300
import time
from machine import WDT, reset
import ubinascii
import json
import uwebsockets.client
import uselect
import hardware
import httpserver
import urequests

ulogging.basicConfig(level=ulogging.INFO)
logger = ulogging.getLogger("main")

wdt = None

if config.ENABLE_WDT:
    hardware.buzzer_off()
    logger.warn("Press CTRL+C to stop the WDT starting...")
    time.sleep(3)
    wdt = WDT(timeout=config.UNLOCK_DELAY * 1000 + 5000)


def feedWDT():
    if config.ENABLE_WDT and wdt:
        wdt.feed()


INTERLOCK_SESSION = {
    "session_id": None,  # any value == on, None == off
    "total_kwh": 0,
}
STATE = {"locked_out": False, "tag_hash": ""}


def file_or_dir_exists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False


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
        if not file_or_dir_exists("state.json"):
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


# setup is starting
hardware.buzz_alert()
get_state()  # grab the state from the flash

# setup RFID
if config.WIEGAND_ENABLED:
    # setup wiegand reader
    rfid_reader = uwiegand.Wiegand(
        config.WIEGAND_ZERO, config.WIEGAND_ONE, uid_32bit_mode=config.UID_32BIT_MODE
    )
else:
    rfid_reader = Rdm6300()


try:
    # create it if it doesn't exist
    if not file_or_dir_exists("tags.json"):
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


# setup wifi
wlan = network.WLAN(network.STA_IF)
local_ip = None  # store our local IP address
local_mac = ubinascii.hexlify(wlan.config("mac")).decode()  # store our mac address

wlan.active(True)
wlan.config(dhcp_hostname="MM_Controller_" + local_mac, txpower=config.TX_POWER)

wlan_connecting_start = time.ticks_ms()
led_toggle_last_update = time.ticks_ms()
led_toggle_last_state = False

if not wlan.isconnected():
    logger.info("connecting to network...")
    wlan.connect(config.WIFI_SSID, config.WIFI_PASS)
    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), wlan_connecting_start) > 30000:
            logger.warn("Took too long to wait for WiFi!")
            logger.warn(
                "The ESP32 should continue trying to connect in the background."
            )
            hardware.led_off()
            break

        if time.ticks_diff(time.ticks_ms(), led_toggle_last_update) > 250:
            feedWDT()
            led_toggle_last_update = time.ticks_ms()

            if led_toggle_last_state:
                hardware.led_off()
                led_toggle_last_state = False

            else:
                hardware.led_on()
                led_toggle_last_state = True

    hardware.led_off()

    local_ip = wlan.ifconfig()[0]
    logger.info("Local IP: " + local_ip)
    logger.info("Local MAC: " + local_mac)


websocket = None
led_update = time.ticks_ms()
ten_second_cron_update = time.ticks_ms()
last_pong = None

DEVICE_SERIAL = local_mac
WS_URL = f"{config.PORTAL_WS_URL}/{config.DEVICE_TYPE}/{DEVICE_SERIAL}"


def setup_websocket_connection():
    global websocket, led_ring, last_pong
    try:
        logger.info("setting up websocket")
        logger.info("WS_URL: " + WS_URL)
        websocket = uwebsockets.client.connect(WS_URL)
        last_pong = time.ticks_ms()

        auth_packet = {"command": "authenticate", "secret_key": config.API_SECRET}
        websocket.send(json.dumps(auth_packet))

        ip_packet = {"command": "ip_address", "ip_address": local_ip}
        websocket.send(json.dumps(ip_packet))

        hardware.led_ok()

    except Exception as e:
        logger.error("Couldn't connect to websocket!")
        logger.error(str(e))

        hardware.led_off()


def save_tags(new_tags):
    global authorised_rfid_tags
    logger.info("Syncing tags!!")

    try:
        authorised_rfid_tags = new_tags
        logger.info("Got %s tags!", len(authorised_rfid_tags))
        # save the tags to flash
        with open("tags.json", "w") as new_tags:
            json.dump(authorised_rfid_tags, new_tags)
            logger.debug("saved tags to flash")

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
        pass


def interlock_session_started():
    hardware.rgb_led_set(hardware.RGB_GREEN)
    hardware.buzz_ok()


def interlock_session_ended():
    hardware.rgb_led_set(hardware.RGB_BLUE)
    hardware.buzz_ok()


def interlock_power_control(status: bool):
    tasmota_base_url = f"http://{config.TASMOTA_HOST}/cm?user={config.TASMOTA_USER}&password={config.TASMOTA_PASSWORD}&cmnd=Power%20"

    if status:
        if config.TASMOTA_HOST:
            r = urequests.get(tasmota_base_url + "On")
            hardware.rgb_led_set(hardware.RGB_GREEN)
            return True

        else:
            hardware.unlock()
            hardware.rgb_led_set(hardware.RGB_GREEN)
            return True

    else:
        if config.TASMOTA_HOST:
            r = urequests.get(tasmota_base_url + "Off")
            logger.warn("Pretending to turn OFF interlock!")
            hardware.rgb_led_set(hardware.RGB_BLUE)
            return True

        else:
            hardware.lock()
            hardware.rgb_led_set(hardware.RGB_BLUE)
            return True


def door_swipe_success():
    # TODO: add support for a contact sensor to make locking logic more robust
    logger.warn("Unlocking!")
    hardware.unlock()
    hardware.rgb_led_set(hardware.RGB_GREEN)
    hardware.buzz_ok()
    time.sleep(config.UNLOCK_DELAY)
    hardware.lock()
    hardware.rgb_led_set(hardware.RGB_BLUE)
    logger.warn("Locking!")


def door_swipe_denied():
    hardware.buzz_alert()


def handle_swipe_door(card: str):
    hardware.buzz_card_read()

    if card in authorised_rfid_tags:
        if STATE["locked_out"]:
            try:
                log_door_swipe(card, locked_out=True)
            except:
                pass
            door_swipe_denied()

        else:
            # if there's an issue logging the swipe, open the door anyway
            try:
                log_door_swipe(card)
            except:
                pass
            door_swipe_success()

    else:
        try:
            log_door_swipe(card, rejected=True)
        except:
            pass
        door_swipe_denied()


def handle_swipe_interlock(card: str):
    current_session_id = INTERLOCK_SESSION.get("session_id")
    current_session_kwh = INTERLOCK_SESSION.get("total_kwh")

    # request a new interlock session
    if current_session_id is None:
        interlock_packet = {
            "command": "interlock_session_start",
            "card_id": card,
        }
        try:
            websocket.send(json.dumps(interlock_packet))
        except:
            hardware.buzz_alert()
        hardware.buzz_card_read()

    # turn off the interlock if it was manually turned on by the system
    elif current_session_id == "system":
        interlock_packet = {"command": "interlock_off"}

        try:
            websocket.send(json.dumps(interlock_packet))
        except:
            hardware.buzz_alert()

        hardware.buzz_card_read()
        interlock_power_control(False)

    # end the current interlock session
    else:
        interlock_packet = {
            "command": "interlock_session_end",
            "session_id": current_session_id,
            "session_kwh": current_session_kwh,
            "card_id": card,
        }
        try:
            INTERLOCK_SESSION["session_id"] = None
            INTERLOCK_SESSION["total_kwh"] = 0
            websocket.send(json.dumps(interlock_packet))
        except:
            hardware.buzz_alert()

        hardware.buzz_card_read()
        interlock_power_control(False)


def handle_swipe_memberbucks(card: str):
    pass


if config.ENABLE_BACKUP_HTTP_SERVER:
    # try to set up the http server
    if not httpserver.setup_http_server():
        logger.error("FAILED to setup http server on startup :(")
    else:
        poll = uselect.poll()
        poll.register(httpserver.sock, uselect.POLLIN)
else:
    logger.warning("Backup http server disabled!")

last_rfid_sync = time.ticks_ms()

setup_websocket_connection()

logger.info("Starting main loop...")

while True:
    feedWDT()
    try:
        # every 15 minutes sync RFID
        if time.ticks_diff(time.ticks_ms(), last_rfid_sync) >= 15 * 60 * 1000:
            last_rfid_sync = time.ticks_ms()
            websocket.send(json.dumps({"command": "sync"}))

        # every 10 seconds run cron tasks
        cron_period = 10 * 1000

        if time.ticks_diff(time.ticks_ms(), ten_second_cron_update) > cron_period:
            ten_second_cron_update = time.ticks_ms()

            if websocket and websocket.open:
                logger.debug("sending ping")

                # if we've missed at least 3 consecutive pongs, then reconnect
                if time.ticks_diff(time.ticks_ms(), last_pong) > cron_period * 4:
                    websocket = None
                    logger.info(
                        "Websocket not open (pong timeout), trying to reconnect."
                    )
                    setup_websocket_connection()
                    # skip the rest of this event loop
                    continue

                try:
                    websocket.send(json.dumps({"command": "ping"}))
                except:
                    websocket = None
                    setup_websocket_connection()
                    # skip the rest of this event loop
                    continue

                if INTERLOCK_SESSION.get("session_id") is not None:
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
            data = websocket.recv()
            if data:
                logger.info("Got websocket packet:")
                logger.info(data)

                try:
                    data = json.loads(data)

                    if data.get("authorised") is not None:
                        logger.info(str(data))

                    if data.get("command") == "pong":
                        last_pong = time.ticks_ms()

                    if data.get("command") == "reboot":
                        logger.warn("Rebooting device!")
                        hardware.buzz_alert()
                        reset()

                    if data.get("command") == "bump" and config.DEVICE_TYPE == "door":
                        logger.info("Bumping Door!")
                        door_swipe_success()

                    if data.get("command") == "sync":
                        tags_hash_new = data.get("hash")
                        tags_hash_current = STATE.get("tag_hash")

                        if tags_hash_new != tags_hash_current:
                            save_tags(data.get("tags"))
                            STATE["tag_hash"] = tags_hash_new
                            save_state(STATE)
                            logger.info("Saved tags with hash: " + tags_hash_new)
                        else:
                            logger.info("Tags hash unchanged, skipping save.")

                    if data.get("command") == "interlock_on":
                        if interlock_power_control(True):
                            INTERLOCK_SESSION[
                                "session_id"
                            ] = "system"  # special state - manually turned on by the system
                            interlock_session_started()
                            hardware.rgb_led_set(hardware.RGB_GREEN)

                        else:
                            logger.warn("Interlock power control failed!")
                            hardware.buzz_alert()

                    if data.get("command") == "interlock_off":
                        logger.info("Turning off interlock and ending session!")

                        INTERLOCK_SESSION["session_id"] = None
                        INTERLOCK_SESSION["total_kwh"] = 0

                        if interlock_power_control(False):
                            interlock_session_ended()
                            hardware.rgb_led_set(hardware.RGB_BLUE)

                        else:
                            logger.warn("Interlock power control failed!")
                            hardware.buzz_alert()

                    if data.get("command") == "interlock_session_start":
                        logger.info("Turning on interlock from new session!")

                        INTERLOCK_SESSION["session_id"] = data.get("session_id")
                        INTERLOCK_SESSION["total_kwh"] = 0

                        if interlock_power_control(True):
                            interlock_session_started()
                            hardware.rgb_led_set(hardware.RGB_GREEN)

                        else:
                            logger.warn("Interlock power control failed!")
                            hardware.buzz_alert()

                    if data.get("command") == "interlock_session_rejected":
                        logger.info("Interlock session request failed!")
                        hardware.buzz_alert()

                except Exception as e:
                    logger.error("Error parsing JSON websocket packet!")
                    logger.error(str(e))

        if config.ENABLE_BACKUP_HTTP_SERVER:
            # backup http server for manually bumping a door from the local network
            for event in poll.poll(1):
                conn, addr = httpserver.sock.accept()
                request = str(conn.recv(2048))
                logger.info("got http request!")
                logger.info(request)
                httpserver.client_response(conn)
                if "/bump?secret=" + config.API_SECRET in request:
                    logger.info("got authenticated bump request")
                    door_swipe_success()
                    break

        # try to read a card
        card = rfid_reader.read_card()

        if card:
            card = str(card)
            logger.info("got a card: " + card)

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
            card = None

    except KeyboardInterrupt as e:
        # turn off the LED and buzzer in case they were left on
        hardware.led_off()
        hardware.buzzer_off()

        raise e

    except Exception as e:
        # turn off the LED and buzzer in case they were left on
        hardware.led_off()
        hardware.buzzer_off()

        if config.CATCH_ALL_EXCEPTIONS:
            print(
                "excepted, but config.CATCH_ALL_EXCEPTIONS is enabled so ignoring :( "
            )
            print(e)
            continue
        else:
            raise e
