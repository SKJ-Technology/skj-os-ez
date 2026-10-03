"""The hub's brain, without any UI: talks to all backends at once (spec §4).

The Qt UI calls this from worker threads; tests call it directly with fake
backends.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from skj_hub.backends.base import Backend, Progress, UpdateItem, no_progress
from skj_hub.catalog.merge import group_offers, load_app_map
from skj_hub.catalog.model import App, Offer, Source
from skj_hub.platform import Platform, detect
from skj_hub.result import Problem, Result
from skj_hub.updates.plan import UpdatePlan

log = logging.getLogger(__name__)


class Hub:
    def __init__(self, backends: list[Backend], platform: Platform | None = None):
        self.platform = platform or detect()
        self._all = backends
        self._available: list[Backend] | None = None
        self.demo = False  # True with --fake: the UI says it's demo data
        self._snap_cache: dict[str, list[Offer]] = {}

    @property
    def backends(self) -> list[Backend]:
        if self._available is None:
            self._available = [b for b in self._all if b.available()]
            log.info("sources: %s", [b.source.value for b in self._available])
        return self._available

    def backend_for(self, source: Source) -> Backend | None:
        return next((b for b in self.backends if b.source is source), None)

    def _gather(self, call) -> list:
        with ThreadPoolExecutor(max_workers=max(1, len(self.backends))) as pool:
            parts = list(pool.map(call, self.backends))
        return [x for part in parts for x in part]

    # --- apps -------------------------------------------------------------------

    def search(self, text: str) -> list[App]:
        text = text.strip()
        if len(text) < 2:
            return []
        apps = group_offers(self._gather(lambda b: b.search(text)))
        # installed first, then names starting with the search text, then A-Z
        t = text.lower()
        return sorted(
            apps, key=lambda a: (not a.installed, not a.name.lower().startswith(t), a.name.lower())
        )

    def browse(self, group: str | None = None) -> list[App]:
        """All apps (or one group), A-Z.

        The Snap Store can't be listed in full, so snaps only join for the
        apps in app-map.json (e.g. Spotify): otherwise browsing would offer
        the unofficial Flathub build where search offers the official snap.
        """
        offers = self._gather(lambda b: b.browse(group))
        offers += self._known_snaps({o.app_id.lower() for o in offers if o.app_id})
        return sorted(group_offers(offers), key=lambda a: a.name.lower())

    def _known_snaps(self, app_ids: set[str]) -> list[Offer]:
        snap = self.backend_for(Source.SNAP)
        if snap is None:
            return []
        names = [n for n, app_id in load_app_map().items() if app_id.lower() in app_ids]
        missing = [n for n in names if n not in self._snap_cache]
        if missing:
            with ThreadPoolExecutor(max_workers=min(8, len(missing))) as pool:
                for name, found in zip(missing, pool.map(snap.search, missing), strict=True):
                    self._snap_cache[name] = [o for o in found if o.ref == name]
        return [o for n in names for o in self._snap_cache[n]]

    def installed_apps(self) -> list[App]:
        apps = group_offers(self._gather(lambda b: b.installed()))
        return sorted(apps, key=lambda a: a.name.lower())

    def install(
        self,
        app: App,
        progress: Progress = no_progress,
        cancel: Event | None = None,
        offer: Offer | None = None,
    ) -> Result:
        offer = offer or app.default
        backend = self.backend_for(offer.source)
        if backend is None:
            return Result(Problem.SERVICE_DOWN, f"{offer.source.value} is not available")
        return backend.install(offer, progress, cancel or Event())

    def remove(
        self, app: App, progress: Progress = no_progress, cancel: Event | None = None
    ) -> Result:
        for offer in app.offers:
            if offer.installed:
                backend = self.backend_for(offer.source)
                if backend is None:
                    return Result(Problem.SERVICE_DOWN, f"{offer.source.value} is not available")
                return backend.remove(offer, progress, cancel or Event())
        return Result(Problem.NOT_FOUND, f"{app.name} is not installed")

    # --- updates ------------------------------------------------------------------

    def update_plan(self) -> UpdatePlan:
        return UpdatePlan.build(self._gather(lambda b: b.updates()))

    def apply(
        self, plan: UpdatePlan, progress: Progress = no_progress, cancel: Event | None = None
    ) -> Result:
        """Run the plan step by step; stop at the first problem."""
        cancel = cancel or Event()
        for source, items in plan.steps:
            backend = self.backend_for(source)
            if backend is None:
                continue
            r = backend.update(list(items), progress, cancel)
            if not r.ok:
                return r
        return Result.success()


def new_kernels(items: list[UpdateItem]) -> list[str]:
    """Kernel versions an update plan installs (for the NVIDIA restart rule)."""
    out = []
    for i in items:
        if i.source is Source.DISTRO and i.name in ("kernel", "kernel-core"):
            # PackageKit id: name;version;arch;repo -> "7.2.9-200.fc44.x86_64"
            parts = i.ref.split(";")
            if len(parts) >= 3 and parts[1]:
                out.append(f"{parts[1].split(':')[-1]}.{parts[2]}")
    return sorted(set(out))


def real_backends() -> list[Backend]:
    from skj_hub.backends.appstream_index import AppStreamIndex
    from skj_hub.backends.flatpak import FlatpakBackend
    from skj_hub.backends.packagekit import PackageKitBackend
    from skj_hub.backends.snap import SnapBackend

    index = AppStreamIndex()
    return [PackageKitBackend(index), FlatpakBackend(index), SnapBackend()]
