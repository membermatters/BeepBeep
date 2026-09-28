from lcd_i2c import LCD

try:
    from typing import TYPE_CHECKING
except ImportError:  # MicroPython does not provide typing.
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from machine import I2C


class LcdScreen:
    """Wrap the I2C LCD, making display operations no-ops when unconfigured."""
    lcd_driver = None
    i2c_address = None
    columns = 16
    rows = 2
    _CUSTOM_CHARS = [
        (0, list([0x04, 0x0E, 0x0E, 0x0E, 0x1F, 0x11, 0x04, 0x0E])),
    ]

    def __init__(
        self, i2c: "I2C | None", i2c_address: "int | None" = None,
        columns: int = 16, rows: int = 2,
    ) -> None:
        """Initialize an addressed LCD and its rocket glyph, or disable output.

        A truthy address requires an I2C bus. Without an address, no hardware
        driver is created and subsequent display calls do nothing.
        """
        self.columns = columns
        self.rows = rows
        self.i2c_address = i2c_address

        self.lcd_driver = (
            LCD(
                addr=self.i2c_address, cols=self.columns, rows=self.rows, i2c=i2c
            )
            if i2c_address
            else None
        )

        if self.lcd_driver:
            self.lcd_driver.begin()

            for character in self._CUSTOM_CHARS:
                self.lcd_driver.create_char(character[0], character[1])

                # for some reason you need to print a custom character at least once before it actually renders
                self.lcd_driver.print(chr(character[0]))
                self.clear()

    def print(self, text: str) -> None:
        """Write text at the current cursor position when the LCD is enabled."""
        if self.lcd_driver:
            self.lcd_driver.print(text)

    def print_rocket(self) -> None:
        """Write the custom rocket glyph at the current cursor position."""
        self.print(chr(0))

    def backlight(self) -> None:
        """Turn on the backlight when the LCD is enabled."""
        if self.lcd_driver:
            self.lcd_driver.backlight()

    def no_backlight(self) -> None:
        """Turn off the backlight when the LCD is enabled."""
        if self.lcd_driver:
            self.lcd_driver.no_backlight()

    def cursor(self) -> None:
        """Show the cursor when the LCD is enabled."""
        if self.lcd_driver:
            self.lcd_driver.cursor()

    def no_cursor(self) -> None:
        """Hide the cursor when the LCD is enabled."""
        if self.lcd_driver:
            self.lcd_driver.no_cursor()

    def blink(self) -> None:
        """Enable cursor blinking when the LCD is enabled."""
        if self.lcd_driver:
            self.lcd_driver.blink()

    def no_blink(self) -> None:
        """Disable cursor blinking when the LCD is enabled."""
        if self.lcd_driver:
            self.lcd_driver.no_blink()

    def home(self) -> None:
        """Return the enabled LCD's cursor and display shift to their origin."""
        if self.lcd_driver:
            self.lcd_driver.home()

    def set_cursor(self, col: int, row: int) -> None:
        """Move the enabled LCD's cursor to a zero-based column and row."""
        if self.lcd_driver:
            self.lcd_driver.set_cursor(col, row)

    def reset_screen(self) -> None:
        """Hide the cursor, disable blinking and turn on the backlight."""
        if self.lcd_driver:
            self.no_blink()
            self.no_cursor()
            self.backlight()

    def clear(self) -> None:
        """Clear the enabled LCD and return its cursor to the origin."""
        if self.lcd_driver:
            self.lcd_driver.clear()
