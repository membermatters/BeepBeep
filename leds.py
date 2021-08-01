import machine, neopixel, time

GREEN = (0, 100, 0)
RED = (100, 0, 0)
BLUE = (0, 0, 100)
YELLOW = (100, 50, 0)
PURPLE = (100, 0, 100)
ORANGE = (100, 100, 0)
OFF = (0, 0, 0)


class Leds:
    neopixel = None

    def __init__(self, pin=16, number=12):
        """[Initialise the LED driver]
        Args:
            pin ([type]): [The pin to drive the addressable LEDs from.]
            number ([type]): [The number of LEDs connected.]
        """
        self.pin = pin
        self.number = number

        self.leds = neopixel.NeoPixel(machine.Pin(self.pin), self.number)
        self.clear()

    def clear(self):
        """[Set every LED to off.]"""
        for i in range(self.number):
            self.leds[i] = OFF
        self.leds.write()

    def set_all(self, colour):
        """[Set every LED to the specified RGB colour.]
        Args:
            r ([integer]): [Red value 0-255]
            g ([integer]): [Green value 0-255]
            b ([integer]): [Blue value 0-255]
        """
        r, g, b = colour[0], colour[1], colour[2]

        for i in range(self.number):
            self.leds[i] = (r, g, b)
        self.leds.write()

    def set_channel(self, channel, colour, write=True):
        """[Set the channel's LED to the specified RGB colour.]
        Args:
            channel ([integer]): [The channel to set]
            r ([tuple]): [Red, green and blue values 0-255 (r, g, b)]
        """
        channel = int(channel)
        self.leds[channel] = colour
        if write:
            self.write()

    def write(self):
        self.leds.write()