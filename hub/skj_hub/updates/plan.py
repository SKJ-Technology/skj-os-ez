"""One update plan over every source (spec §4.4)."""

from __future__ import annotations

from dataclasses import dataclass, field

from skj_hub.backends.base import UpdateItem
from skj_hub.catalog.model import Source

# Distro packages first (they may need a restart), then Flatpak, then Snap.
ORDER = (Source.DISTRO, Source.FLATPAK, Source.SNAP)


@dataclass(frozen=True)
class UpdatePlan:
    steps: tuple[tuple[Source, tuple[UpdateItem, ...]], ...] = field(default_factory=tuple)

    @classmethod
    def build(cls, items: list[UpdateItem]) -> UpdatePlan:
        steps = []
        for source in ORDER:
            group = tuple(sorted((i for i in items if i.source is source), key=lambda i: i.name))
            if group:
                steps.append((source, group))
        return cls(tuple(steps))

    @property
    def items(self) -> list[UpdateItem]:
        return [i for _, group in self.steps for i in group]

    @property
    def count(self) -> int:
        return len(self.items)

    @property
    def download_size(self) -> int:
        return sum(i.download_size for i in self.items)

    @property
    def needs_restart(self) -> bool:
        return any(i.needs_restart for i in self.items)

    @property
    def empty(self) -> bool:
        return not self.steps
