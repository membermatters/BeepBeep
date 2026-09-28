"""Shared device types and door states for configuration and hardware control."""


class DeviceType:
    """String constants representing supported device types on MicroPython."""

    DOOR = "door"  # Active signal unlocks the door (e.g. a door strike).
    DOOR_REVERSED = "door_reversed"  # Active signal locks the door (e.g. a mag lock).
    DOOR_ROLLER = "door_roller"  # Active signal toggles a roller door.
    INTERLOCK = "interlock"
    MEMBERBUCKS = "memberbucks"


DOOR_TYPES = (DeviceType.DOOR, DeviceType.DOOR_ROLLER)


class DoorState:
    """Door position and movement states tracked by the door controller."""

    OPEN = "open"
    CLOSED = "closed"
    OPENING = "opening"
    CLOSING = "closing"


class LockState:
    """Commanded lock states; these do not confirm the physical door position."""

    LOCKED = "locked"
    UNLOCKED = "unlocked"
    LOCKED_OUT = "locked_out"
