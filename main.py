import json
from machine import Pin, PWM
import socket
import usocket
from uselect import select
import network
import time
import urequests

# our own modules
from leds import *
from urdm6300.urdm6300 import Rdm6300
import config

BUZZER_PIN = 32  # IO num, not pin num
LOCK_PIN = 13  # IO num, not pin num
BUZZER_ENABLE = True
UNLOCK_DELAY = 5  # seconds to remain unlocked

# setup LED ring
led_ring = Leds()
led_ring.set_all(OFF)

# setup RFID
rfid_reader = Rdm6300()

# setup buzzer
buzzer = PWM(Pin(BUZZER_PIN), freq=400, duty=0)

# setup lock output
lock = Pin(LOCK_PIN, Pin.OUT)
lock.off()

# setup wifi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

authorised_rfid_tags = list()  # hold our in memory cache of authorised tags
local_ip = None  # store our local IP address
local_mac = wlan.config('mac')  # store our mac address

if not wlan.isconnected():
    print('connecting to network...')
    wlan.config(dhcp_hostname="MMController")
    wlan.connect(config.WIFI_SSID, config.WIFI_PASS)
    while not wlan.isconnected():
        led_ring.run_single_wipe(BLUE)
        pass

    local_ip = wlan.ifconfig()[0]
    print('Local IP:', local_ip)
    print('Local MAC:', local_mac)

# set to purple while we're connecting to the websocket
led_ring.set_all(PURPLE)

websocket = None
sock = None
led_update = time.ticks_ms()
last_update = time.ticks_ms()
time.sleep(1)


def setup_websocket_connection():
    global websocket, led_ring
    # try:
    #     websocket = uwebsockets.client.connect(config.PORTAL_WS_URL)
    #     version_object = {"version": 1}
    #     websocket.send(json.dumps(version_object))
    #     led_ring.run_single_pulse(GREEN)

    # except:
    #     print("Couldn't connect to websocket!")
    #     led_ring.run_single_pulse(RED)


def setup_http_server():
    global sock

    try:
        # setup our HTTP server
        sock = usocket.socket()

        # s.setsockopt(usocket.SOL_SOCKET, usocket.SO_REUSEADDR, 1)
        sock.bind(socket.getaddrinfo('0.0.0.0', 80)[0][-1])
        sock.listen(2)
        return True
    except Exception as e:
        print("Got exception when setting up HTTP server")
        print(e)
        return False


def client_response(conn):
    response = """
            {"success": true}
            """

    conn.send('HTTP/1.1 200 OK\n')
    conn.send('Content-Type: application/json\n')
    conn.send('Connection: close\n\n')
    conn.sendall(response)
    conn.close()


def sync_rfid():
    global authorised_rfid_tags
    print("Syncing tags!!")
    response = urequests.get(
        config.PORTAL_URL + '/api/door/' + str(local_mac) + '/authorised/?secret=' + config.API_SECRET)

    json_data = response.json()

    if json_data.get("authorised_tags"):
        authorised_rfid_tags = json_data.get("authorised_tags")
        print(authorised_rfid_tags)

    print("Syncing tags done!!")


def log_rfid(card_id):
    print("Logging access!!")

    try:
        urequests.get(
            config.PORTAL_URL + '/api/door/' + str(local_mac) + '/check/' + card_id + "/?secret=" + config.API_SECRET)
    except:
        pass


def swipe_success():
    lock.on()
    buzzer.duty(512)
    buzzer.freq(400)
    time.sleep(0.1)
    buzzer.freq(1000)
    time.sleep(0.3)
    buzzer.duty(0)
    buzzer.freq(400)

    led_ring.run_single_pulse(GREEN, fadein=True)
    time.sleep(UNLOCK_DELAY)
    led_ring.run_single_pulse(GREEN, fadeout=True)
    lock.off()


# try to set up the http server
if not setup_http_server():
    print("FAILED to setup http server on startup :(")

sync_rfid()
last_rfid_sync = time.ticks_ms()

print("Starting main loop...")
while True:
    try:
        # every 10 minutes sync RFID
        if time.ticks_diff(time.ticks_ms(), last_rfid_sync) >= 600000:
            last_rfid_sync = time.ticks_ms()
            sync_rfid()

        # every 10ms update the animation
        if time.ticks_diff(time.ticks_ms(), led_update) >= 10:
            led_update = time.ticks_ms()
            led_ring.update_animation()

        # if we have a websocket connection
        if websocket:
            if time.ticks_diff(time.ticks_ms(), last_update) > 60000:
                print("sending time")
                last_update = time.ticks_ms()
                websocket.send(json.dumps({"time": time.ticks_ms() / 1000}))

            data = websocket.recv()
            if data:
                # TODO handle incoming websocket messages
                print(data)

        r, w, err = select((sock,), (), (), 1)
        if r:
            for readable in r:
                conn, addr = sock.accept()
                request = str(conn.recv(1024))
                client_response(conn)
                if request.find('/bump?secret=' + config.API_SECRET):
                    swipe_success()
                    break

        # try to read a card
        card = rfid_reader.read_card()

        # if we got a valid card read
        if (card):
            print("got a card: " + str(card))

            buzzer.duty(512)
            time.sleep(0.1)
            buzzer.duty(0)

            if str(card) in authorised_rfid_tags:
                swipe_success()

            else:
                led_ring.set_all(BLUE)
                sync_rfid()
                if card in authorised_rfid_tags:
                    swipe_success()
                else:
                    buzzer.duty(512)
                    buzzer.freq(1000)
                    time.sleep(0.05)
                    buzzer.duty(0)
                    time.sleep(0.05)
                    buzzer.freq(200)
                    buzzer.duty(512)
                    time.sleep(0.05)
                    buzzer.duty(0)
                    led_ring.run_single_pulse(RED)

            log_rfid(card)

            # dedupe card reads; keep looping until we've cleared the buffer
            while True:
                if not rfid_reader.read_card():
                    break

        card = None
    except:
        continue
