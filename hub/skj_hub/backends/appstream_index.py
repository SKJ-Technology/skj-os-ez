"""App metadata for distro packages and Flatpaks, from AppStream (spec §4.2).

AppStream's pool holds Fedora's catalog (appstream-data, origin "fedora")
and the Flatpak remotes' catalogs (origin "flatpak"), with names already in
the user's language and Flathub's verification flag. The distro and Flatpak
backends search here and only use PackageKit / libflatpak to act.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

from skj_hub.catalog.model import Kind, Offer, Source

log = logging.getLogger(__name__)

# AppStream component kinds we show (AsComponentKind values)
DESKTOP_APP = 2
CONSOLE_APP = 3
_SHOWN = {DESKTOP_APP: Kind.APP, CONSOLE_APP: Kind.SYSTEM}

VERIFIED_KEY = "flathub::verification::verified"


@dataclass(frozen=True)
class ComponentInfo:
    """The few fields of an AsComponent the hub needs (keeps mapping testable)."""

    app_id: str
    kind: int
    name: str
    summary: str
    origin: str
    pkgnames: tuple[str, ...]
    flatpak_refs: tuple[str, ...]
    verified: bool
    icon: str | None = None


def to_offers(
    info: ComponentInfo, installed_pkgs: set[str], installed_refs: set[str]
) -> list[Offer]:
    kind = _SHOWN.get(info.kind)
    if kind is None:
        return []
    offers = []
    if info.pkgnames:
        pkg = info.pkgnames[0]
        offers.append(
            Offer(
                source=Source.DISTRO,
                ref=pkg,
                app_id=info.app_id,
                name=info.name,
                summary=info.summary,
                version="",
                developer_verified=False,
                installed=pkg in installed_pkgs,
                kind=kind,
                icon=info.icon,
            )
        )
    for ref in info.flatpak_refs:
        if not ref.startswith("app/"):
            continue
        offers.append(
            Offer(
                source=Source.FLATPAK,
                ref=ref,
                app_id=info.app_id,
                name=info.name,
                summary=info.summary,
                version="",
                developer_verified=info.verified,
                installed=ref in installed_refs,
                kind=kind,
                icon=info.icon,
            )
        )
    return offers


def _info(comp) -> ComponentInfo:  # AsComponent -> ComponentInfo
    from gi.repository import AppStream as AS

    refs = tuple(b.get_id() for b in comp.get_bundles() if b.get_kind() == AS.BundleKind.FLATPAK)
    icon = None
    for i in comp.get_icons() or []:
        if i.get_kind() in (AS.IconKind.STOCK, AS.IconKind.CACHED, AS.IconKind.LOCAL):
            icon = i.get_name() if i.get_kind() == AS.IconKind.STOCK else i.get_filename()
            if icon:
                break
    return ComponentInfo(
        app_id=comp.get_id(),
        kind=int(comp.get_kind()),
        name=comp.get_name() or comp.get_id(),
        summary=comp.get_summary() or "",
        origin=comp.get_origin() or "",
        pkgnames=tuple(comp.get_pkgnames() or ()),
        flatpak_refs=refs,
        verified=comp.get_custom_value(VERIFIED_KEY) == "true",
        icon=icon,
    )


class AppStreamIndex:
    """Loads the AppStream pool once (about 1.5 s) and searches it."""

    def __init__(self):
        self._pool = None
        self._lock = threading.Lock()

    def _load(self):
        with self._lock:
            if self._pool is None:
                import gi

                gi.require_version("AppStream", "1.0")
                from gi.repository import AppStream as AS

                pool = AS.Pool()
                try:
                    pool.load(None)
                except Exception as e:  # a broken catalog file must not kill the store
                    log.warning("AppStream pool loaded with errors: %s", e)
                self._pool = pool
        return self._pool

    def search(self, text: str, source: Source) -> list[ComponentInfo]:
        pool = self._load()
        found = []
        for comp in pool.search(text).as_array():
            info = _info(comp)
            if source is Source.DISTRO and info.pkgnames:
                found.append(info)
            elif source is Source.FLATPAK and info.flatpak_refs:
                found.append(info)
        return found

    def by_pkgnames(self, names: set[str]) -> list[ComponentInfo]:
        pool = self._load()
        return [
            i
            for i in (_info(c) for c in pool.get_components().as_array())
            if i.pkgnames and i.pkgnames[0] in names
        ]

    def by_flatpak_refs(self, refs: set[str]) -> list[ComponentInfo]:
        pool = self._load()
        return [
            i
            for i in (_info(c) for c in pool.get_components().as_array())
            if any(r in refs for r in i.flatpak_refs)
        ]
