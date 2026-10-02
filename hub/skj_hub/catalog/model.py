"""What the app store shows: one App made of Offers from different sources."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Source(Enum):
    DISTRO = "distro"  # dnf / apt through PackageKit
    FLATPAK = "flatpak"
    SNAP = "snap"


class Kind(Enum):
    APP = "app"  # something with a window
    SYSTEM = "system"  # command-line tools, drivers, firmware, add-ons


@dataclass(frozen=True)
class Offer:
    """One app from one source."""

    source: Source
    ref: str  # backend's own id: PackageKit package id, flatpak ref, snap name
    app_id: str | None  # AppStream component id, None for snaps
    name: str
    summary: str
    version: str
    developer_verified: bool = False
    installed: bool = False
    kind: Kind = Kind.APP
    icon: str | None = None
    download_size: int | None = None


@dataclass
class App:
    """One entry in the store: the same app from one or more sources."""

    key: str
    offers: list[Offer] = field(default_factory=list)

    @property
    def default(self) -> Offer:
        from skj_hub.catalog.merge import pick_default

        return pick_default(self.offers)

    @property
    def name(self) -> str:
        # AppStream names are the friendly ones ("Spotify", not "spotify")
        for o in self.offers:
            if o.app_id:
                return o.name
        return self.default.name

    @property
    def installed(self) -> bool:
        return any(o.installed for o in self.offers)
