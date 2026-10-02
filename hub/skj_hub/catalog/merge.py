"""Group offers into one App per app, and pick the source a beginner gets.

Rules (spec §4.2, Notion "one entry per app, source picked automatically"):
  1. a source the app is already installed from stays the default;
  2. a developer-verified offer (Flathub verified, Snap verified publisher)
     beats an unverified one;
  3. otherwise apps prefer Flatpak, then the distro package, then Snap;
     system tools prefer the distro package.
"""

from __future__ import annotations

import json
from importlib import resources

from skj_hub.catalog.model import App, Kind, Offer, Source

_APP_ORDER = {Source.FLATPAK: 0, Source.DISTRO: 1, Source.SNAP: 2}
_SYSTEM_ORDER = {Source.DISTRO: 0, Source.FLATPAK: 1, Source.SNAP: 2}


def pick_default(offers: list[Offer]) -> Offer:
    if not offers:
        raise ValueError("an app needs at least one offer")

    def rank(o: Offer) -> tuple[int, int, int]:
        order = _SYSTEM_ORDER if o.kind is Kind.SYSTEM else _APP_ORDER
        return (not o.installed, not o.developer_verified, order[o.source])

    return min(offers, key=rank)


def load_app_map() -> dict[str, str]:
    """Snap name -> AppStream id, for snaps AppStream can't link by itself."""
    text = resources.files("skj_hub.catalog").joinpath("app-map.json").read_text()
    return {k: v for k, v in json.loads(text).items() if not k.startswith("_")}


def _norm_id(app_id: str) -> str:
    app_id = app_id.lower()
    return app_id[: -len(".desktop")] if app_id.endswith(".desktop") else app_id


def group_offers(offers: list[Offer], app_map: dict[str, str] | None = None) -> list[App]:
    if app_map is None:
        app_map = load_app_map()
    app_map = {k.lower(): _norm_id(v) for k, v in app_map.items()}

    apps: dict[str, App] = {}
    by_name: dict[str, str] = {}  # lowercase display name -> key
    unlinked: list[Offer] = []

    for o in offers:
        if o.app_id:
            key = _norm_id(o.app_id)
            apps.setdefault(key, App(key)).offers.append(o)
            by_name.setdefault(o.name.lower(), key)
        else:
            unlinked.append(o)

    for o in unlinked:
        key = app_map.get(o.name.lower()) or by_name.get(o.name.lower())
        if key is None:
            key = f"{o.source.value}:{o.name.lower()}"
        apps.setdefault(key, App(key)).offers.append(o)

    return list(apps.values())
