"""Exercise the firmware swipe loop without importing hardware startup code."""

import ast
import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src-firmware"))

from models import DeviceType, DoorState
from swipe_cards import SwipeCards


class StopReading(Exception):
    """End a mocked RFID stream so the infinite firmware loop can be tested."""
    pass


class CardAuthorisationTests(unittest.IsolatedAsyncioTestCase):
    """Check that only authorised cards can invoke local door actions."""

    async def exercise(
        self, device_type: str, state: str, cards: list[str], revoke_on_lock: bool = False,
    ) -> tuple[SimpleNamespace, AsyncMock, SimpleNamespace]:
        """Run one mocked swipe and return the door, audit logger and HAL mocks."""
        source = ast.parse(
            (Path(__file__).resolve().parents[1] / "src-firmware/main.py").read_text()
        )
        function = next(
            node for node in ast.walk(source)
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "process_card_swipes"
        )
        cache = SwipeCards()
        cache.cards = cards
        cache.card_hash = "123"  # Metadata must never authorise a swipe.
        hal = SimpleNamespace(
            rfid_reader=SimpleNamespace(read_card=Mock(side_effect=[123, None, StopReading()])),
            feedWDT=Mock(), play_card_read=AsyncMock(), play_alert=AsyncMock(),
        )
        door = SimpleNamespace(
            open_state=state, unlock_door=AsyncMock(), lock_door=AsyncMock(),
        )
        log = AsyncMock()

        class CommandLock:
            """Simulate lock acquisition with optional intervening card revocation."""

            async def __aenter__(self) -> None:
                """Revoke the card at lock acquisition when requested by the test."""
                if revoke_on_lock:
                    cache.cards = []

            async def __aexit__(self, *args: object) -> bool:
                """Propagate any exception from the simulated critical section."""
                return False

        namespace = dict(
            asyncio=SimpleNamespace(sleep=AsyncMock(), gather=asyncio.gather),
            config=SimpleNamespace(DEVICE_TYPE=device_type, BUZZ_ON_SWIPE=False),
            DeviceType=DeviceType, DoorState=DoorState, swipe_cards=cache,
            hal=hal, door=door, door_command_lock=CommandLock(),
            log_door_swipe=log, logger=Mock(),
        )
        exec(compile(ast.Module(body=[function], type_ignores=[]), "main.py", "exec"), namespace)
        with self.assertRaises(StopReading):
            await namespace["process_card_swipes"]()
        return door, log, hal

    async def test_unknown_and_empty_cache_deny_all_door_actions(self) -> None:
        """Reject unknown IDs, including IDs matching metadata, on both door types."""
        for cards in ([], ["other"]):
            for device_type, state, action in (
                (DeviceType.DOOR, DoorState.CLOSED, "unlock"),
                (DeviceType.DOOR_ROLLER, DoorState.CLOSED, "unlock"),
                (DeviceType.DOOR_ROLLER, DoorState.OPEN, "lock"),
            ):
                with self.subTest(cards=cards, device=device_type, state=state):
                    door, log, hal = await self.exercise(device_type, state, cards)
                    door.unlock_door.assert_not_awaited()
                    door.lock_door.assert_not_awaited()
                    log.assert_awaited_once_with("123", "denied", action)
                    hal.play_alert.assert_awaited_once()

    async def test_authorised_cards_keep_existing_door_actions(self) -> None:
        """Keep the existing strike cycle and roller open/close behavior."""
        for device_type, state, unlocks, locks in (
            (DeviceType.DOOR, DoorState.CLOSED, 1, 1),
            (DeviceType.DOOR_ROLLER, DoorState.CLOSED, 1, 0),
            (DeviceType.DOOR_ROLLER, DoorState.OPEN, 0, 1),
        ):
            with self.subTest(device=device_type, state=state):
                door, log, hal = await self.exercise(device_type, state, ["123"])
                self.assertEqual(door.unlock_door.await_count, unlocks)
                self.assertEqual(door.lock_door.await_count, locks)
                log.assert_awaited_once_with("123", "success", "unlock" if unlocks else "lock")
                hal.play_alert.assert_not_awaited()

    async def test_card_revoked_while_waiting_for_lock_is_denied(self) -> None:
        """Check the current authorisation list after the door lock is acquired."""
        door, log, _ = await self.exercise(
            DeviceType.DOOR, DoorState.CLOSED, ["123"], revoke_on_lock=True,
        )
        door.unlock_door.assert_not_awaited()
        door.lock_door.assert_not_awaited()
        log.assert_awaited_once_with("123", "denied", "unlock")


if __name__ == "__main__":
    unittest.main()
