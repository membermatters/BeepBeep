"""Persist the authorised card list and its server-supplied sync metadata."""

import errno
import json
import os
import time


class SwipeCards:
    """Manage a JSON card cache using synchronous MicroPython file operations."""

    def __init__(self, path: str = "data/tags.json") -> None:
        """Start with no authorised cards; call load() to restore saved state."""
        self.path = path
        self.cards = []
        self.card_hash = None
        self.last_updated = None

    @staticmethod
    def _validate(cards: list[str], card_hash: str) -> None:
        """Raise TypeError unless the hash and every item in the list are strings."""
        if not isinstance(card_hash, str):
            raise TypeError("Card hash must be a string")
        if not isinstance(cards, list) or any(not isinstance(card, str) for card in cards):
            raise TypeError("Cards must be a list of strings")

    def load(self) -> bool:
        """Restore cards, hash and timestamp; return False if no file exists.

        Invalid files raise an exception and leave the current state unchanged.
        """
        try:
            with open(self.path) as cards_file:
                data = json.load(cards_file)
        except OSError as error:
            if error.args[0] == errno.ENOENT:
                return False
            raise

        if not isinstance(data, dict):
            raise TypeError("Saved cards must be a JSON object")
        cards = data["cards"]
        card_hash = data["hash"]
        last_updated = data["last_updated"]
        self._validate(cards, card_hash)
        if type(last_updated) is not int:
            raise TypeError("Last updated time must be an integer")

        self.cards = cards
        self.card_hash = card_hash
        self.last_updated = last_updated
        return True

    def _save(self, cards: list[str], card_hash: str, last_updated: int) -> None:
        """Create the immediate parent directory and replace the cache via a temp file.

        Parent ancestors must already exist. Remove the temporary file on failure
        when possible, and propagate the write or rename error.
        """
        if "/" in self.path:
            parent = self.path.rsplit("/", 1)[0]
            if parent:
                try:
                    os.mkdir(parent)
                except OSError as error:
                    if error.args[0] != errno.EEXIST:
                        raise

        temporary_path = self.path + ".tmp"
        try:
            with open(temporary_path, "w") as cards_file:
                json.dump(
                    {"cards": cards, "hash": card_hash, "last_updated": last_updated},
                    cards_file,
                )
            os.rename(temporary_path, self.path)
        except Exception:
            try:
                os.remove(temporary_path)
            except OSError:
                pass
            raise

    def update(self, cards: list[str], card_hash: str) -> bool:
        """Save a changed server hash and card list, returning whether it changed.

        Matching hashes skip both the write and timestamp update. The timestamp
        uses the device clock's time.time(), whose accuracy depends on RTC setup.
        A failed save leaves the current in-memory cards and metadata unchanged.
        The hash is supplied by the server, not calculated from the card list.
        """
        self._validate(cards, card_hash)
        if self.card_hash == card_hash:
            return False

        cards = list(cards)
        last_updated = int(time.time())
        self._save(cards, card_hash, last_updated)
        self.cards = cards
        self.card_hash = card_hash
        self.last_updated = last_updated
        return True

    def is_authorised(self, card_id: "str | int") -> bool:
        """Check a reader's card ID against the card list, excluding metadata."""
        return str(card_id) in self.cards
