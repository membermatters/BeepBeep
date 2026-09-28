"""Host-side checks for card persistence, sync and authorisation."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src-firmware"))

from swipe_cards import SwipeCards


class SwipeCardsTests(unittest.TestCase):
    """Check card-cache persistence, hash comparisons and failure recovery."""

    def setUp(self) -> None:
        """Create an isolated cache path whose parent directory does not yet exist."""
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "data" / "tags.json"
        self.cards = SwipeCards(str(self.path))

    def test_missing_cache_authorises_nothing(self) -> None:
        """Keep cards and metadata empty when there is no saved file."""
        self.assertFalse(self.cards.load())
        self.assertFalse(self.cards.is_authorised("123"))
        self.assertIsNone(self.cards.card_hash)
        self.assertIsNone(self.cards.last_updated)

    def test_round_trip_and_authorisation_exclude_metadata(self) -> None:
        """Restore cards and metadata while authorising only exact card IDs."""
        with patch("swipe_cards.time.time", return_value=1000):
            self.assertTrue(self.cards.update(["123", "0042"], "hash-1"))
        restored = SwipeCards(str(self.path))
        self.assertTrue(restored.load())
        self.assertEqual(restored.cards, ["123", "0042"])
        self.assertEqual(restored.card_hash, "hash-1")
        self.assertEqual(restored.last_updated, 1000)
        self.assertTrue(restored.is_authorised(123))
        self.assertTrue(restored.is_authorised("0042"))
        self.assertFalse(restored.is_authorised("42"))
        self.assertFalse(restored.is_authorised("hash-1"))
        self.assertFalse(restored.is_authorised(1000))

    def test_matching_hash_skips_write_and_timestamp(self) -> None:
        """Treat equal server hashes as unchanged even if supplied cards differ."""
        self.cards.update(["123"], "hash-1")
        before = self.path.read_bytes()
        timestamp = self.cards.last_updated
        with patch.object(self.cards, "_save") as save:
            self.assertFalse(self.cards.update(["456"], "hash-1"))
            save.assert_not_called()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.cards.cards, ["123"])
        self.assertEqual(self.cards.last_updated, timestamp)

    def test_new_hash_replaces_cards_and_allows_empty_list(self) -> None:
        """Persist a changed hash, new timestamp and an empty authorisation list."""
        self.cards.update(["123"], "hash-1")
        with patch("swipe_cards.time.time", return_value=2000):
            self.assertTrue(self.cards.update([], "hash-2"))
        self.assertFalse(self.cards.is_authorised("123"))
        self.assertEqual(json.loads(self.path.read_text()), {
            "cards": [], "hash": "hash-2", "last_updated": 2000,
        })

    def test_failed_replace_preserves_disk_and_memory_for_retry(self) -> None:
        """Keep the old cache on rename failure and accept a later retry."""
        self.cards.update(["123"], "hash-1")
        before = self.path.read_bytes()
        timestamp = self.cards.last_updated
        with patch("swipe_cards.os.rename", side_effect=OSError("write failed")):
            with self.assertRaises(OSError):
                self.cards.update(["456"], "hash-2")
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.cards.cards, ["123"])
        self.assertEqual(self.cards.card_hash, "hash-1")
        self.assertEqual(self.cards.last_updated, timestamp)
        self.assertFalse(Path(str(self.path) + ".tmp").exists())
        self.assertTrue(self.cards.update(["456"], "hash-2"))

    def test_invalid_updates_and_files_do_not_change_state(self) -> None:
        """Reject malformed input while retaining the last valid in-memory cache."""
        self.cards.update(["123"], "hash-1")
        for tags, card_hash in ((None, "hash-2"), ([123], "hash-2"), (["123"], None)):
            with self.assertRaises(TypeError):
                self.cards.update(tags, card_hash)
        for contents, error in (
            ('{', ValueError),
            ('[]', TypeError),
            ('{"cards": [], "hash": "h", "last_updated": null}', TypeError),
        ):
            self.path.write_text(contents)
            with self.assertRaises(error):
                self.cards.load()
            self.assertEqual(self.cards.cards, ["123"])
            self.assertEqual(self.cards.card_hash, "hash-1")


if __name__ == "__main__":
    unittest.main()
