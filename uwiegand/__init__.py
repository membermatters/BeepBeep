"""
uweigand.py - read card IDs from a wiegand card reader

(C) 2017 Paul Jimenez - released under LGPLv3+
(C) 2022 changes by Jaimyn Mayer - released under LGPLv3+
"""

from machine import Pin, Timer
import utime

CARD_MASK = 0b11111111111111110  # 16 ones
FACILITY_MASK = 0b1111111100000000000000000  # 8 ones

# Max pulse interval: 2ms
# pulse width: 50us


def zfl(s, width):
    # Thank-you kind person: https://stackoverflow.com/a/63274578
    # Pads the provided string with leading 0's to suit the specified 'chrs' length
    # Force # characters, fill with leading 0's
    return '{:0>{w}}'.format(s, w=width)


class Wiegand:
    def __init__(self, pin0, pin1, callback=None):
        """
        pin0 - the GPIO that goes high when a zero is sent by the reader
        pin1 - the GPIO that goes high when a one is sent by the reader
        callback - the function called (with two args: card ID and cardcount)
                   when a card is detected.  Note that micropython interrupt
                   implementation limitations apply to the callback!
        """
        self._pin0 = Pin(pin0, Pin.IN)
        self._pin1 = Pin(pin1, Pin.IN)
        self._callback = callback
        self._last_card = None
        self._next_card = 0
        self._bits = 0
        self._pin0.irq(trigger=Pin.IRQ_FALLING, handler=self._on_pin0)
        self._pin1.irq(trigger=Pin.IRQ_FALLING, handler=self._on_pin1)
        self._last_bit_read = None
        self._timer = Timer(-1)
        self._timer.init(period=50, mode=Timer.PERIODIC,
                         callback=self._cardcheck)
        self.cards_read = 0

    def _on_pin0(self, newstate): self._on_pin(0, newstate)
    def _on_pin1(self, newstate): self._on_pin(1, newstate)

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

    def get_last_card(self):
        last_card = self._get_card()
        facility_code = self._get_facility_code()
        card_uid = self._get_card_uid()

        if not last_card:
            return None

        self._last_card = None

        return {
            "card": last_card,
            "facility_code": facility_code,
            "card_uid": card_uid
        }

    def read_card(self):
        # compatible interface with our urdm6300 library
        last_card = self.get_last_card()
        if last_card:
            return last_card["card_uid"]
        else:
            return None

    def _get_card_uid(self):
        # I hate that I wrote this and it works
        # For card numbers that are very small (ie < 4096), it needs to be left padded / bit shifted properly.
        # TODO: undo this clusterfuck and use proper bit shifting
        if self._last_card is None:
            return None
        hex_facility = hex(self._get_facility_code())

        hex_card_number = hex(self._get_card())[2:]  # drop the 0x
        hex_card_number = zfl(hex_card_number, 4)  # left pad it

        return int(hex_facility + hex_card_number)

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

            if (self._callback):
                self._callback(self._get_card(),
                               self._get_facility_code(), self.cards_read, self._get_card_uid(), self._last_card)
