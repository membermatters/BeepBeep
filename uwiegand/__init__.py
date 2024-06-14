"""
uweigand.py - read card IDs from a wiegand card reader

(C) 2017, 2022 Paul Jimenez - released under LGPLv3+
(C) 2022 changes by Jaimyn Mayer - released under LGPLv3+
(C) 2023 changes by Scott Picton - released under LGPLv3+
"""

from machine import Pin, Timer
import utime

# The common Wiegand standard use 26 bits
CARD_MASK = 0b0_00000000_00000000_11111111_11111111_0  # lower two bytes (16 bits)
FACILITY_MASK = (
    0b0_00000000_11111111_00000000_00000000_0  # third lower byte only (8 bits)
)

# Mifare standard (13.56Mhz cards) typically use 32 bits
MIFARE_24_MASK = (
    0b0_00000000_11111111_11111111_11111111_0  # lower three bytes (24 bits)
)
MIFARE_MASK = 0b0_11111111_11111111_11111111_11111111_0  # all 4 bytes (32 bits)

# Max pulse interval: 2ms
# pulse width: 50us


class Wiegand:
    def __init__(self, pin0, pin1, callback=None, timer_id=-1, uid_32bit_mode=False):
        """
        pin0 - the GPIO that goes high when a zero is sent by the reader
        pin1 - the GPIO that goes high when a one is sent by the reader
        callback - the function called (with two args: card ID and cardcount)
                   when a card is detected.  Note that micropython interrupt
                   implementation limitations apply to the callback!
        timer_id - the Timer ID to use for periodic callbacks
        uid_32bit_mode - if True read_card() returns full 32bit mifare code, otherwise
                         if False read_card() returns only 24bit mifare code
        """
        self._pin0 = Pin(pin0, Pin.IN, Pin.PULL_UP)
        self._pin1 = Pin(pin1, Pin.IN, Pin.PULL_UP)
        self._callback = callback
        self._last_card = None
        self._next_card = 0
        self._bits = 0
        self._pin0.irq(trigger=Pin.IRQ_FALLING, handler=self._on_pin0)
        self._pin1.irq(trigger=Pin.IRQ_FALLING, handler=self._on_pin1)
        self._last_bit_read = None
        self._timer = Timer(timer_id)
        self._timer.init(period=50, mode=Timer.PERIODIC, callback=self._cardcheck)
        self.cards_read = 0
        self._uid_32bit_mode = uid_32bit_mode

    def _on_pin0(self, newstate):
        self._on_pin(0, newstate)

    def _on_pin1(self, newstate):
        self._on_pin(1, newstate)

    def _on_pin(self, is_one, newstate):
        now = utime.ticks_ms()

        self._last_bit_read = now
        self._next_card <<= 1
        if is_one:
            self._next_card |= 1
        self._bits += 1

    def _get_card(self):
        if self._last_card is None:
            return None
        return (self._last_card & CARD_MASK) >> 1

    def read_card(self):
        # compatible interface with our urdm6300 library
        if self._last_card is None:
            return None

        card_uid = self._get_card_uid()

        self._last_card = None

        return card_uid

    def _get_card_uid(self):
        if self._last_card is None:
            return None
        if self._uid_32bit_mode:
            return (self._last_card & MIFARE_24_MASK) >> 1
        else:
            return (self._last_card & MIFARE_MASK) >> 1

    def _get_facility_code(self):
        if self._last_card is None:
            return None
        # Specific to standard 26bit wiegand
        return (self._last_card & FACILITY_MASK) >> 17

    def _cardcheck(self, t):
        if self._last_bit_read is None:
            return
        now = utime.ticks_ms()
        if now - self._last_bit_read > 100:
            # too slow - new start!
            self._last_bit_read = None
            self._last_card = self._next_card
            self._next_card = 0
            self._bits = 0
            self.cards_read += 1

            if self._callback:
                self._callback(
                    self._get_card(),
                    self._get_facility_code(),
                    self.cards_read,
                    self._get_card_uid(),
                    self._last_card,
                )
