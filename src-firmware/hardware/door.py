"""Door control, sensor waits and roller-door contactor sequencing through a HAL."""

import asyncio
import time

import config
import ulogging
from hardware import HAL, Colour
from models import DeviceType, DoorState, LockState

logger = ulogging.getLogger("door")


class Door:
    """Control door outputs, position waits and feedback through a supplied HAL.

    Track commanded lock state separately from detected or assumed door position.
    Roller doors use the lock output to open and OUT_1 to close.
    """

    def __init__(self, door_type: str, hal: HAL) -> None:
        """Store a DeviceType door constant and the HAL instance to control.

        Initialize the tracked states to closed and locked without reading
        sensors or changing hardware outputs.
        """
        self.door_type = door_type
        self.hal = hal
        self.open_state = DoorState.CLOSED
        self.lock_state = LockState.LOCKED

    def print_standby_message(self) -> None:
        """Clear the LCD and display the swipe-to-unlock prompt and rocket graphic."""
        self.hal.lcd.clear()
        self.hal.lcd.print("Swipe To Unlock! ")
        self.hal.lcd.print_rocket()

    async def wait_until_open(self) -> bool | None:
        """Wait for an open door without changing the lock outputs.

        Set open_state to OPENING, then OPEN on detection and return True.
        On DOOR_SENSOR_TIMEOUT, set it to CLOSED and return False.
        For disabled sensors or roller doors, wait FIXED_UNLOCK_DELAY seconds,
        assume OPEN and return None. Yield to other tasks while waiting.
        """
        return await self._wait_until_state(True)

    async def wait_until_closed(self) -> bool | None:
        """Wait for a closed door without changing the lock outputs.

        Set open_state to CLOSING, then CLOSED on detection and return True.
        On DOOR_SENSOR_TIMEOUT, set it to OPEN and return False.
        For disabled sensors or roller doors, wait FIXED_UNLOCK_DELAY seconds,
        assume CLOSED and return None. Yield to other tasks while waiting.
        """
        return await self._wait_until_state(False)

    async def _wait_until_state(self, opened: bool) -> bool | None:
        """Wait for an open state when opened is True, otherwise a closed state.

        Poll the sensor every 0.1 seconds until DOOR_SENSOR_TIMEOUT. Ignore
        None readings. Return True on a match, or False on timeout and set
        open_state to the opposite of the target state.
        For disabled sensors or roller doors, use FIXED_UNLOCK_DELAY instead,
        set the assumed target state and return None.
        """
        target_state = DoorState.OPEN if opened else DoorState.CLOSED
        self.open_state = DoorState.OPENING if opened else DoorState.CLOSING

        if not config.DOOR_SENSOR_ENABLED or self.door_type == DeviceType.DOOR_ROLLER:
            logger.info(f"Waiting for door to be {target_state} for fixed delay of {config.FIXED_UNLOCK_DELAY} seconds...")
            await asyncio.sleep(config.FIXED_UNLOCK_DELAY)
            logger.info(f"Assuming door is {target_state} after fixed delay!")
            self.open_state = target_state
            return None

        wait_for = config.DOOR_SENSOR_TIMEOUT
        logger.info(f"Waiting for door to be {target_state} for {wait_for} seconds...")
        start_time = time.time()
        while time.time() - start_time < wait_for:
            sensor_state = self.hal.state.door_sensor
            if sensor_state is not None and sensor_state == opened:
                logger.info(f"Door is {target_state}!")
                self.open_state = target_state
                return True
            await asyncio.sleep(0.1)

        logger.info(f"Door did not become {target_state} before timeout!")
        self.open_state = DoorState.CLOSED if opened else DoorState.OPEN
        return False

    async def unlock_door(self) -> None:
        """Run unlock actuation and LED/LCD/sound feedback concurrently.

        Preserve the roller contactor interlock and release OPEN after the door
        wait completes. Feedback starts with the command; inspect open_state
        for the detected or assumed position after both functions finish.
        """
        logger.debug("Requesting door unlock from HAL...")

        async def actuate() -> None:
            """Apply unlock outputs, wait for opening and release roller OPEN."""
            if self.door_type == DeviceType.DOOR_ROLLER:
                self.hal.set_out_1_off() # make sure the close contactor is off before opening
                await asyncio.sleep(0.2)
            self.hal.set_lock_on() # turn on the open contactor
            self.lock_state = LockState.UNLOCKED
            await self.wait_until_open()
            if self.door_type == DeviceType.DOOR_ROLLER:
                self.hal.set_lock_off() # turn off the open contactor after the door is open

        async def show_feedback() -> None:
            """Show unlocked indicators and play the confirmation sound."""
            self.hal.set_rgb_led(Colour.UNLOCKED)
            self.hal.set_reader_led_on()
            self.hal.lcd.print("Door Unlocked!")
            logger.info("Door Unlocked!")

        await asyncio.gather(self.hal.play_ok(skip_led=True), actuate(), show_feedback())

    async def lock_door(self) -> None:
        """Run lock actuation and LED/LCD feedback concurrently after warnings.

        For rollers, disable OPEN and finish both warnings and the three-second
        delay before starting CLOSE or locked feedback. Release CLOSE after the
        closure wait. Inspect open_state for the detected or assumed position.
        """
        logger.debug("Requesting door lock from HAL...")

        # Finish the roller warning sequence before movement and locked feedback.
        if self.door_type == DeviceType.DOOR_ROLLER:
            self.hal.set_lock_off() # make sure the open contactor is off before closing
            self.hal.set_reader_buzzer_on()
            await asyncio.sleep(3)

        async def actuate() -> None:
            """Apply lock outputs, wait for closure and release roller CLOSE."""
            if self.door_type == DeviceType.DOOR_ROLLER:
                self.hal.set_out_1_on() # turn on the close contactor
            else:
                self.hal.set_lock_off()
            self.lock_state = LockState.LOCKED
            await self.wait_until_closed()
            if self.door_type == DeviceType.DOOR_ROLLER:
                self.hal.set_out_1_off() # turn off the close contactor after the door is closed

        async def show_feedback() -> None:
            """Show locked indicators and restore the standby LCD prompt."""
            if self.hal.rgb_colour == Colour.UNLOCKED:
                self.hal.set_rgb_led(Colour.IDLE)
            self.hal.set_reader_led_off()
            self.hal.lcd.print("Door Locked!")
            self.print_standby_message()
            logger.info("Door Locked!")

        await asyncio.gather(actuate(), show_feedback())
