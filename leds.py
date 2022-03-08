import machine
import neopixel
import time

GAMMA_CORRECTION = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1,
                    1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2,
                    2, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 5, 5, 5,
                    5, 6, 6, 6, 6, 7, 7, 7, 7, 8, 8, 8, 9, 9, 9, 10,
                    10, 10, 11, 11, 11, 12, 12, 13, 13, 13, 14, 14, 15, 15, 16, 16,
                    17, 17, 18, 18, 19, 19, 20, 20, 21, 21, 22, 22, 23, 24, 24, 25,
                    25, 26, 27, 27, 28, 29, 29, 30, 31, 32, 32, 33, 34, 35, 35, 36,
                    37, 38, 39, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 50,
                    51, 52, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 66, 67, 68,
                    69, 70, 72, 73, 74, 75, 77, 78, 79, 81, 82, 83, 85, 86, 87, 89,
                    90, 92, 93, 95, 96, 98, 99, 101, 102, 104, 105, 107, 109, 110, 112, 114,
                    115, 117, 119, 120, 122, 124, 126, 127, 129, 131, 133, 135, 137, 138, 140, 142,
                    144, 146, 148, 150, 152, 154, 156, 158, 160, 162, 164, 167, 169, 171, 173, 175,
                    177, 180, 182, 184, 186, 189, 191, 193, 196, 198, 200, 203, 205, 208, 210, 213,
                    215, 218, 220, 223, 225, 228, 231, 233, 236, 239, 241, 244, 247, 249, 252, 255)

GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
PURPLE = (GAMMA_CORRECTION[255], 0, GAMMA_CORRECTION[255])
YELLOW = (GAMMA_CORRECTION[200], GAMMA_CORRECTION[200], 0)
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
        self.number_leds = number
        self.loop_speed = 60  # in ms
        self.pulse_speed = 3
        self.min_pulse_brightness = 160
        self.animate_mode = ""
        self.animate_colour = ""
        self.animate_last_update = time.ticks_ms()
        self.animate_brightness = 0
        self.animate_position = 0
        self.animate_direction = 0

        self.leds = neopixel.NeoPixel(machine.Pin(self.pin), self.number_leds)
        self.clear()

    def clear(self):
        """[Set every LED to off.]"""
        for i in range(self.number_leds):
            self.leds[i] = OFF
        self.leds.write()

    def set_all(self, colour):
        """[Set every LED to the specified RGB colour.]
        Args:
            r ([integer]): [Red value 0-255]
            g ([integer]): [Green value 0-255]
            b ([integer]): [Blue value 0-255]
        """
        r, g, b = GAMMA_CORRECTION[colour[0]
                                   ], GAMMA_CORRECTION[colour[1]], GAMMA_CORRECTION[colour[2]]

        for i in range(self.number_leds):
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

    def run_single_loop(self, colour, times=1):
        """[Blocking single LED loop]

        Args:
            colour ([colour enum]): []
            times (int, optional): [number of times to loop]. Defaults to 1.
        """
        for i in range(times):
            for x in range(self.number_leds):
                self.clear()
                self.set_channel(x, colour)
                time.sleep_ms(self.loop_speed)
        self.clear()

    def run_single_wipe(self, colour, times=1):
        """[Blocking single LED wipe]

        Args:
            colour ([colour enum]): []
            times (int, optional): [number of times to loop]. Defaults to 1.
        """
        for i in range(times):
            for x in range(self.number_leds):
                self.set_channel(x, colour)
                time.sleep_ms(self.loop_speed)

            for x in range(self.number_leds):
                self.set_channel(x, OFF)
                time.sleep_ms(self.loop_speed)
        self.clear()

    def run_single_pulse(self, colour, times=1, fadein=False, fadeout=False):
        """[Blocking single LED pulse]

        Args:
            colour ([colour enum]): []
            times (int, optional): [number of times to loop]. Defaults to 1.
            fadein (bool, optional): only fade in
        """
        for i in range(times):
            range_list = list()
            if fadein:
                range_list += list(range(self.min_pulse_brightness, 255))

            if fadeout:
                range_list += list(reversed(range(self.min_pulse_brightness, 255)))

            for x in range_list:
                time.sleep_ms(self.pulse_speed)
                x = GAMMA_CORRECTION[x]
                self.set_all((x if colour == RED or colour == PURPLE or colour == YELLOW else 0, x if colour ==
                              GREEN or colour == YELLOW else 0, x if colour == BLUE or colour == PURPLE else 0))
        self.clear()

    def start_animation(self, animation, colour):
        """Starts a non blocking animation.

        Args:
            animation (string): The animation to start (from "loop", "wipe" and "pulse")
            colour (COLOUR): A colour defined in leds.py
        """
        self.animate_mode = animation
        self.animate_colour = colour

    def end_animation(self):
        """Stops the animation and reset default state values.
        """
        self.animate_mode = ""
        self.animate_colour = ""
        self.animate_last_update = time.ticks_ms()
        self.animate_brightness = 0
        self.animate_position = 0
        self.animate_direction = 0
        self.set_all(OFF)

    def update_animation(self):
        """Updates the LEDs based on the current animation state.
        """
        if self.animate_mode == "loop":
            # if it's time to update the animation
            if time.ticks_ms() - self.animate_last_update > self.loop_speed:
                self.animate_last_update = time.ticks_ms()

                if self.animate_position == 0:
                    self.set_channel(self.number_leds-1, OFF)
                else:
                    self.set_channel(self.animate_position - 1, OFF)

                if self.animate_position < self.number_leds:
                    self.set_channel(self.animate_position,
                                     self.animate_colour)

                self.animate_position += 1

                # loop back to 0 if we get to the end
                if self.animate_position == self.number_leds:
                    self.animate_position = 0

            return

        elif self.animate_mode == "wipe":
            # if it's time to update the animation
            if time.ticks_ms() - self.animate_last_update > self.loop_speed:
                self.animate_last_update = time.ticks_ms()

                if self.animate_direction == 0:
                    self.set_channel(self.animate_position,
                                     self.animate_colour)
                    self.animate_position += 1

                    if self.animate_position == self.number_leds:
                        self.animate_direction = 1
                        self.animate_position = 0

                else:
                    self.set_channel(self.animate_position, OFF)
                    self.animate_position += 1

                    if self.animate_position == self.number_leds:
                        self.animate_direction = 0
                        self.animate_position = 0

            return

        elif self.animate_mode == "pulse":
            # if it's time to update the animation
            if time.ticks_ms() - self.animate_last_update > self.pulse_speed:
                self.animate_last_update = time.ticks_ms()

                colour = self.animate_colour

                if (self.animate_brightness > 255):
                    self.animate_brightness = 255
                if (self.animate_brightness < self.min_pulse_brightness):
                    self.animate_brightness = self.min_pulse_brightness

                x = GAMMA_CORRECTION[self.animate_brightness]

                if self.animate_direction == 0:
                    self.set_all((x if colour == RED or colour == PURPLE or colour == YELLOW else 0, x if colour ==
                                  GREEN or colour == YELLOW else 0, self.animate_brightness if colour == BLUE or colour == PURPLE else 0))
                    self.animate_brightness += 1

                    if self.animate_brightness >= 255:
                        self.animate_direction = 1

                else:
                    self.set_all((x if colour == RED or colour == PURPLE or colour == YELLOW else 0, x if colour ==
                                  GREEN or colour == YELLOW else 0, self.animate_brightness if colour == BLUE or colour == PURPLE else 0))
                    self.animate_brightness -= 1

                    if self.animate_brightness <= self.min_pulse_brightness:
                        self.animate_direction = 0

            return

        else:
            self.end_animation()

    def animate_idle(self):
        """Starts the default slow blue pulse animation.
        """
        self.start_animation("pulse", BLUE)
        self.pulse_speed = 25
        self.min_pulse_brightness = 180

    def animate_defaults(self):
        """Sets the animation state back to default, but keeps the animation type/colour
        """
        self.loop_speed = 60  # in ms
        self.pulse_speed = 3
        self.min_pulse_brightness = 160
        self.animate_direction = 0
