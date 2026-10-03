"""The one interface every app source implements (spec §4).

Backends are called from worker threads (never the UI thread) and must not
raise: system-changing calls return a Result, queries return [] on failure
and log why.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from threading import Event

from skj_hub.catalog.model import Offer, Source
from skj_hub.result import Result

# progress(percent or None for "busy", short status text)
Progress = Callable[[int | None, str], None]


def no_progress(percent: int | None, status: str) -> None:
    pass


@dataclass(frozen=True)
class UpdateItem:
    source: Source
    ref: str
    name: str
    old_version: str
    new_version: str
    download_size: int = 0
    needs_restart: bool = False


class Backend(ABC):
    source: Source

    @abstractmethod
    def available(self) -> bool:
        """True when the service behind this source answers."""

    @abstractmethod
    def search(self, text: str) -> list[Offer]: ...

    def browse(self, group: str | None) -> list[Offer]:
        """Every app this source can list (group: see catalog/categories.py).

        Sources that can't list their whole catalog (the Snap Store) return [].
        """
        return []

    @abstractmethod
    def installed(self) -> list[Offer]: ...

    @abstractmethod
    def updates(self) -> list[UpdateItem]: ...

    @abstractmethod
    def install(self, offer: Offer, progress: Progress, cancel: Event) -> Result: ...

    @abstractmethod
    def remove(self, offer: Offer, progress: Progress, cancel: Event) -> Result: ...

    @abstractmethod
    def update(self, items: list[UpdateItem], progress: Progress, cancel: Event) -> Result: ...
