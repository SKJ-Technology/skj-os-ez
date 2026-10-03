"""What the hub is running on: base, desktop, image-based or not (spec §4.1)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Base(Enum):
    FEDORA = "fedora"
    UBUNTU = "ubuntu"
    BAZZITE = "bazzite"
    UNKNOWN = "unknown"


# Phase 1 supports Fedora KDE; other combinations start but only show what works.
_SUPPORTED = {(Base.FEDORA, "kde")}


@dataclass(frozen=True)
class Platform:
    base: Base
    desktop: str  # "kde", "gnome", ... or "unknown"
    version: str
    image_based: bool

    @property
    def supported(self) -> bool:
        return (self.base, self.desktop) in _SUPPORTED and not self.image_based


def parse_os_release(text: str) -> dict[str, str]:
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key] = value.strip().strip('"').strip("'")
    return values


def _base(values: dict[str, str]) -> Base:
    ids = [values.get("ID", "")] + values.get("ID_LIKE", "").split()
    if "bazzite" in ids[:1]:
        return Base.BAZZITE
    for i in ids:
        if i == "fedora":
            return Base.FEDORA
        if i in ("ubuntu", "debian"):
            return Base.UBUNTU
    return Base.UNKNOWN


def _desktop(env: dict[str, str]) -> str:
    names = env.get("XDG_CURRENT_DESKTOP", "").lower().split(":")
    for known in ("kde", "gnome", "xfce", "cinnamon", "lxqt", "budgie"):
        if known in names:
            return known
    return "unknown"


def detect(
    os_release: str | None = None,
    env: dict[str, str] | None = None,
    image_based: bool | None = None,
) -> Platform:
    if os_release is None:
        for path in ("/etc/os-release", "/usr/lib/os-release"):
            try:
                os_release = Path(path).read_text()
                break
            except OSError:
                continue
        else:
            os_release = ""
    if env is None:
        env = dict(os.environ)
    if image_based is None:
        image_based = Path("/run/ostree-booted").exists()

    values = parse_os_release(os_release)
    return Platform(
        base=_base(values),
        desktop=_desktop(env),
        version=values.get("VERSION_ID", ""),
        image_based=image_based,
    )
