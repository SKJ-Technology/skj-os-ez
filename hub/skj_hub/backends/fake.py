"""In-memory backend for tests, screenshots and UI work without root (spec §4).

Start the hub with SKJ_HUB_FAKE=1 to use it instead of the real sources.
"""

from __future__ import annotations

from dataclasses import replace
from threading import Event

from skj_hub.backends.base import Backend, Progress, UpdateItem
from skj_hub.catalog.model import Kind, Offer, Source
from skj_hub.result import Problem, Result


class FakeBackend(Backend):
    def __init__(
        self,
        source: Source,
        offers: list[Offer] | None = None,
        updates: list[UpdateItem] | None = None,
        fail_with: Problem | None = None,
        is_available: bool = True,
    ):
        self.source = source
        self._offers = {o.ref: o for o in offers or []}
        self._updates = list(updates or [])
        self.fail_with = fail_with
        self.is_available = is_available
        self.calls: list[tuple[str, str]] = []

    def available(self) -> bool:
        return self.is_available

    def search(self, text: str) -> list[Offer]:
        t = text.lower()
        return [o for o in self._offers.values() if t in o.name.lower() or t in o.summary.lower()]

    def installed(self) -> list[Offer]:
        return [o for o in self._offers.values() if o.installed]

    def updates(self) -> list[UpdateItem]:
        return list(self._updates)

    def _run(self, what: str, ref: str, progress: Progress, cancel: Event) -> Result:
        self.calls.append((what, ref))
        for pct in (0, 50, 100):
            if cancel.is_set():
                return Result(Problem.CANCELLED, "cancelled")
            progress(pct, what)
        if self.fail_with:
            return Result(self.fail_with, f"fake {what} failed")
        return Result.success()

    def install(self, offer: Offer, progress: Progress, cancel: Event) -> Result:
        r = self._run("install", offer.ref, progress, cancel)
        if r.ok:
            self._offers[offer.ref] = replace(offer, installed=True)
        return r

    def remove(self, offer: Offer, progress: Progress, cancel: Event) -> Result:
        r = self._run("remove", offer.ref, progress, cancel)
        if r.ok and offer.ref in self._offers:
            self._offers[offer.ref] = replace(offer, installed=False)
        return r

    def update(self, items: list[UpdateItem], progress: Progress, cancel: Event) -> Result:
        r = self._run("update", ",".join(i.ref for i in items), progress, cancel)
        if r.ok:
            done = {i.ref for i in items}
            self._updates = [u for u in self._updates if u.ref not in done]
        return r


def demo_backends() -> list[FakeBackend]:
    """A small believable catalog for running the UI without a real system."""

    def o(source, ref, name, summary, app_id=None, verified=False, installed=False, kind=Kind.APP):
        return Offer(source, ref, app_id, name, summary, "1.0", verified, installed, kind)

    distro = FakeBackend(
        Source.DISTRO,
        [
            o(Source.DISTRO, "gimp", "GIMP", "Edit photos and pictures", "org.gimp.GIMP"),
            o(Source.DISTRO, "vlc", "VLC", "Play any video or music", "org.videolan.VLC"),
            o(
                Source.DISTRO,
                "firefox",
                "Firefox",
                "Browse the web",
                "org.mozilla.firefox",
                installed=True,
            ),
            o(Source.DISTRO, "htop", "htop", "See what's using your PC", "htop", kind=Kind.SYSTEM),
        ],
        [
            UpdateItem(
                Source.DISTRO,
                "kernel-core;7.2.9-200.fc44;x86_64;updates",
                "kernel-core",
                "7.2.8",
                "7.2.9",
                90_000_000,
                True,
            ),
            UpdateItem(Source.DISTRO, "firefox", "Firefox", "156.0.1", "156.0.2", 80_000_000),
        ],
    )
    flatpak = FakeBackend(
        Source.FLATPAK,
        [
            o(
                Source.FLATPAK,
                "app/org.gimp.GIMP/x86_64/stable",
                "GIMP",
                "Edit photos and pictures",
                "org.gimp.GIMP",
                verified=True,
            ),
            o(
                Source.FLATPAK,
                "app/com.spotify.Client/x86_64/stable",
                "Spotify",
                "Music for everyone",
                "com.spotify.Client",
            ),
        ],
        [
            UpdateItem(
                Source.FLATPAK,
                "app/org.kde.kdenlive/x86_64/stable",
                "Kdenlive",
                "25.08",
                "25.12",
                120_000_000,
            )
        ],
    )
    snap = FakeBackend(
        Source.SNAP,
        [o(Source.SNAP, "spotify", "spotify", "Music for everyone", verified=True)],
    )
    return [distro, flatpak, snap]
