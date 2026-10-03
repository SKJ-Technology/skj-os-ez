"""Flatpak apps through libflatpak, system installation (spec §3).

Changes to the system installation go through flatpak's system helper,
which asks polkit.
"""

from __future__ import annotations

import logging
from threading import Event

from skj_hub.backends.appstream_index import AppStreamIndex, to_offers
from skj_hub.backends.base import Backend, Progress, UpdateItem
from skj_hub.catalog.model import Offer, Source
from skj_hub.result import Problem, Result, classify

log = logging.getLogger(__name__)


def _fp():
    import gi

    gi.require_version("Flatpak", "1.0")
    from gi.repository import Flatpak

    return Flatpak


def _cancellable(cancel: Event):
    from gi.repository import Gio

    c = Gio.Cancellable()
    if cancel.is_set():
        c.cancel()
    return c


class FlatpakBackend(Backend):
    source = Source.FLATPAK

    def __init__(self, index: AppStreamIndex):
        self.index = index

    def _installation(self):
        return _fp().Installation.new_system(None)

    def available(self) -> bool:
        try:
            self._installation()
            return True
        except Exception as e:
            log.info("Flatpak not available: %s", e)
            return False

    def _installed_refs(self) -> dict[str, object]:
        Flatpak = _fp()
        refs = self._installation().list_installed_refs_by_kind(Flatpak.RefKind.APP, None)
        return {r.format_ref(): r for r in refs}

    def search(self, text: str) -> list[Offer]:
        try:
            infos = self.index.search(text, Source.FLATPAK)
            installed = set(self._installed_refs()) if infos else set()
            return [o for i in infos for o in to_offers(i, set(), installed)]
        except Exception as e:
            log.warning("flatpak search failed: %s", e)
            return []

    def browse(self, group: str | None) -> list[Offer]:
        try:
            infos = self.index.browse(Source.FLATPAK, group)
            installed = set(self._installed_refs()) if infos else set()
            return [o for i in infos for o in to_offers(i, set(), installed)]
        except Exception as e:
            log.warning("listing flatpaks failed: %s", e)
            return []

    def installed(self) -> list[Offer]:
        try:
            refs = set(self._installed_refs())
            return [o for i in self.index.by_flatpak_refs(refs) for o in to_offers(i, set(), refs)]
        except Exception as e:
            log.warning("listing flatpaks failed: %s", e)
            return []

    def updates(self) -> list[UpdateItem]:
        try:
            inst = self._installation()
            return [
                UpdateItem(
                    source=Source.FLATPAK,
                    ref=r.format_ref(),
                    name=r.get_appdata_name() or r.get_name(),
                    old_version=r.get_appdata_version() or "",
                    new_version="",
                    download_size=0,
                    needs_restart=False,
                )
                for r in inst.list_installed_refs_for_update(None)
            ]
        except Exception as e:
            log.warning("checking flatpak updates failed: %s", e)
            return []

    # --- actions ----------------------------------------------------------------

    def _run(self, fill, progress: Progress, status: str, cancel: Event) -> Result:
        Flatpak = _fp()
        try:
            tx = Flatpak.Transaction.new_for_installation(self._installation(), None)
            fill(tx)

            def on_new_operation(_tx, _op, op_progress):
                op_progress.connect("changed", lambda p: progress(p.get_progress(), status))

            tx.connect("new-operation", on_new_operation)
            tx.run(_cancellable(cancel))
            return Result.success()
        except Exception as e:
            return classify(e)

    def _remote_for(self, ref: str) -> str | None:
        inst = self._installation()
        for remote in inst.list_remotes(None):
            if remote.get_disabled():
                continue
            try:
                inst.fetch_remote_ref_sync(
                    remote.get_name(),
                    _fp().RefKind.APP,
                    ref.split("/")[1],
                    ref.split("/")[2],
                    ref.split("/")[3],
                    None,
                )
                return remote.get_name()
            except Exception:
                continue
        return None

    def install(self, offer: Offer, progress: Progress, cancel: Event) -> Result:
        remote = self._remote_for(offer.ref)
        if remote is None:
            return Result(Problem.NOT_FOUND, f"no remote has {offer.ref}")
        return self._run(
            lambda tx: tx.add_install(remote, offer.ref, None), progress, offer.name, cancel
        )

    def remove(self, offer: Offer, progress: Progress, cancel: Event) -> Result:
        return self._run(lambda tx: tx.add_uninstall(offer.ref), progress, offer.name, cancel)

    def update(self, items: list[UpdateItem], progress: Progress, cancel: Event) -> Result:
        if not items:
            return Result.success()

        def fill(tx):
            for i in items:
                tx.add_update(i.ref, None, None)

        return self._run(fill, progress, "flatpak", cancel)
