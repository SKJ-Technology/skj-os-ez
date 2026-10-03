"""Distro packages through PackageKit: dnf5 on Fedora, apt on Ubuntu (spec §3).

PackageKit asks polkit itself, so the hub runs as the user and the system
shows its normal password prompt.
"""

from __future__ import annotations

import logging
from threading import Event

from skj_hub.backends.appstream_index import AppStreamIndex, to_offers
from skj_hub.backends.base import Backend, Progress, UpdateItem
from skj_hub.catalog.model import Offer, Source
from skj_hub.result import Problem, Result, classify

log = logging.getLogger(__name__)

# Updates to these need a restart even when PackageKit doesn't say so.
RESTART_PACKAGES = {
    "kernel",
    "kernel-core",
    "kernel-modules",
    "glibc",
    "systemd",
    "dbus-broker",
    "linux-firmware",
}


def _pk():
    import gi

    gi.require_version("PackageKitGlib", "1.0")
    from gi.repository import PackageKitGlib as PK

    return PK


def _trusted() -> int:
    # Transaction flags are a bitfield: pass the converted value, not the enum.
    return _pk().transaction_flag_bitfield_from_string("only-trusted")


def _cancellable(cancel: Event):
    from gi.repository import Gio

    c = Gio.Cancellable()
    if cancel.is_set():
        c.cancel()
    return c


class PackageKitBackend(Backend):
    source = Source.DISTRO

    def __init__(self, index: AppStreamIndex):
        self.index = index

    # --- queries ----------------------------------------------------------------

    def available(self) -> bool:
        try:
            PK = _pk()
            PK.Control().get_properties(None)
            return True
        except Exception as e:
            log.info("PackageKit not available: %s", e)
            return False

    def _installed_names(self) -> set[str]:
        PK = _pk()
        client = PK.Client()
        res = client.get_packages(
            PK.filter_bitfield_from_string("installed"), None, lambda *a: None, None
        )
        return {p.get_name() for p in res.get_package_array()}

    def search(self, text: str) -> list[Offer]:
        try:
            infos = self.index.search(text, Source.DISTRO)
            installed = self._installed_names() if infos else set()
            return [o for i in infos for o in to_offers(i, installed, set())]
        except Exception as e:
            log.warning("distro search failed: %s", e)
            return []

    def browse(self, group: str | None) -> list[Offer]:
        try:
            infos = self.index.browse(Source.DISTRO, group)
            installed = self._installed_names() if infos else set()
            return [o for i in infos for o in to_offers(i, installed, set())]
        except Exception as e:
            log.warning("listing distro apps failed: %s", e)
            return []

    def installed(self) -> list[Offer]:
        try:
            names = self._installed_names()
            return [o for i in self.index.by_pkgnames(names) for o in to_offers(i, names, set())]
        except Exception as e:
            log.warning("listing installed packages failed: %s", e)
            return []

    def updates(self) -> list[UpdateItem]:
        try:
            PK = _pk()
            client = PK.Client()
            res = client.get_updates(
                PK.filter_bitfield_from_string("none"), None, lambda *a: None, None
            )
            pkgs = res.get_package_array()
            restart_ids = self._restart_ids(client, [p.get_id() for p in pkgs])
            return [
                UpdateItem(
                    source=Source.DISTRO,
                    ref=p.get_id(),
                    name=p.get_name(),
                    old_version="",
                    new_version=p.get_version(),
                    download_size=0,
                    needs_restart=p.get_id() in restart_ids or p.get_name() in RESTART_PACKAGES,
                )
                for p in pkgs
            ]
        except Exception as e:
            log.warning("checking distro updates failed: %s", e)
            return []

    def _restart_ids(self, client, ids: list[str]) -> set[str]:
        if not ids:
            return set()
        PK = _pk()
        try:
            res = client.get_update_detail(ids, None, lambda *a: None, None)
        except Exception as e:
            log.info("no update details: %s", e)
            return set()
        wanted = {PK.RestartEnum.SYSTEM, PK.RestartEnum.SECURITY_SYSTEM}
        return {
            d.get_package_id() for d in res.get_update_detail_array() if d.get_restart() in wanted
        }

    # --- actions ----------------------------------------------------------------

    def _progress_cb(self, progress: Progress, status: str):
        def cb(prog, kind, *_):
            try:
                pct = prog.get_percentage()
                progress(pct if 0 <= pct <= 100 else None, status)
            except Exception:
                pass

        return cb

    def _resolve(self, name: str, installed: bool) -> list[str]:
        PK = _pk()
        flt = "installed" if installed else "newest;~installed;arch"
        res = (
            _pk()
            .Client()
            .resolve(PK.filter_bitfield_from_string(flt), [name], None, lambda *a: None, None)
        )
        return [p.get_id() for p in res.get_package_array()]

    def install(self, offer: Offer, progress: Progress, cancel: Event) -> Result:
        PK = _pk()
        try:
            ids = self._resolve(offer.ref, installed=False)
            if not ids:
                return Result(Problem.NOT_FOUND, f"no installable package named {offer.ref}")
            PK.Client().install_packages(
                _trusted(),
                ids[:1],
                _cancellable(cancel),
                self._progress_cb(progress, offer.name),
                None,
            )
            return Result.success()
        except Exception as e:
            return classify(e)

    def remove(self, offer: Offer, progress: Progress, cancel: Event) -> Result:
        PK = _pk()
        try:
            ids = self._resolve(offer.ref, installed=True)
            if not ids:
                return Result(Problem.NOT_FOUND, f"{offer.ref} is not installed")
            # allow_deps=False: never take other programs with it; autoremove
            # cleans up what only this app needed.
            PK.Client().remove_packages(
                0,
                ids,
                False,
                True,
                _cancellable(cancel),
                self._progress_cb(progress, offer.name),
                None,
            )
            return Result.success()
        except Exception as e:
            return classify(e)

    def update(self, items: list[UpdateItem], progress: Progress, cancel: Event) -> Result:
        if not items:
            return Result.success()
        PK = _pk()
        try:
            PK.Client().update_packages(
                _trusted(),
                [i.ref for i in items],
                _cancellable(cancel),
                self._progress_cb(progress, "system"),
                None,
            )
            return Result.success()
        except Exception as e:
            return classify(e)
