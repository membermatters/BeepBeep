import json
from machine import Pin
import socket
import network
import time

# third party modules
import slimdns
import uwebsockets.client

# our own modules
from leds import *
from urdm6300.urdm6300 import Rdm6300

FALLBACK_IP = "192.168.1.30"  # fallback IP in case mDNS fails
BUZZER_PIN = 32  # IO num, not pin num
BUZZER_ENABLE = True

led_ring = Leds()
led_ring.set_all(OFF)
rfid_reader = Rdm6300()
buzzer = Pin(BUZZER_PIN, Pin.OUT if BUZZER_ENABLE else Pin.IN)
buzzer.off()

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# mdns resolver stuff
local_addr = None
server = None


if not wlan.isconnected():
    print('connecting to network...')
    wlan.config(dhcp_hostname="MMController")
    wlan.connect('Bill Wi The Science Fi', '225261007622')
    while not wlan.isconnected():
        led_ring.run_single_wipe(BLUE)
        pass

    # mdns resolver stuff
    local_addr = wlan.ifconfig()[0]
    server = slimdns.SlimDNSServer(local_addr, "micropython")
    print('IP address:', local_addr)


def resolve_mdns(host):
    ip = server.resolve_mdns_address(host)

    if ip:
        print(slimdns.bytes_to_dotted_ip(ip))
        return slimdns.bytes_to_dotted_ip(ip)
    else:
        return None


# set to purple while we're connecting to the websocket
led_ring.set_all(PURPLE)

websocket = None
try:
    ip = resolve_mdns("membermatters.local")

    if not ip:
        ip = FALLBACK_IP

    websocket = uwebsockets.client.connect("ws://{}:8000/ws/access".format(ip))
    version_object = {"version": 1}
    websocket.send(json.dumps(version_object))
    led_ring.run_single_pulse(GREEN)

except:
    print("Couldn't connect to websocket!")
    led_ring.run_single_pulse(RED)

led_update = time.ticks_ms()
last_update = time.ticks_ms()
time.sleep(1)

led_ring.animate_idle()

print("Starting main loop...")
while True:
    if time.ticks_diff(time.ticks_ms(), led_update) >= 10:
        led_update = time.ticks_ms()
        led_ring.update_animation()

    if websocket:
        if time.ticks_ms() - last_update > 60000:
            print("sending time")
            last_update = time.ticks_ms()
            websocket.send(json.dumps({"time": time.ticks_ms() / 1000}))

        data = websocket.recv()
        if data:
            # TODO handle incoming websocket messages
            print(data)

    card = rfid_reader.read_card()

    if (card):
        # TODO handle a card scan
        print(card)
        buzzer.on()
        time.sleep(0.1)
        buzzer.off()
        led_ring.run_single_loop(BLUE)
        led_ring.pulse_speed = 10

        buzzer.on()
        time.sleep(0.05)
        buzzer.off()
        time.sleep(0.05)
        buzzer.on()
        time.sleep(0.05)
        buzzer.off()

        websocket.send(json.dumps({"card": card}))

        led_ring.run_single_pulse(GREEN)
        led_ring.animate_idle()

    card = None
