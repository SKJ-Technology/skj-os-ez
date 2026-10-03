"""Snaps through snapd-glib, plus snapd's REST API for refresh holds (spec §4.4).

snapd checks polkit for changes; allow_interaction lets it show the password
prompt. snapd-glib has no "hold" call, so holding automatic refreshes (the
`snap refresh --hold` equivalent) talks to /run/snapd.socket directly.
"""

from __future__ import annotations

import json
import logging
import socket
from threading import Event

from skj_hub.backends.base import Backend, Progress, UpdateItem
from skj_hub.catalog.model import Offer, Source
from skj_hub.result import Problem, Result, classify

log = logging.getLogger(__name__)

SNAPD_SOCKET = "/run/snapd.socket"

# SnapdPublisherValidation: UNKNOWN=0, UNPROVEN=1, VERIFIED=2, STARRED=3
_VERIFIED = {2, 3}


def _snapd():
    import gi

    gi.require_version("Snapd", "2")
    from gi.repository import Snapd

    return Snapd


def _cancellable(cancel: Event):
    from gi.repository import Gio

    c = Gio.Cancellable()
    if cancel.is_set():
        c.cancel()
    return c


def hold_request_body(snaps: list[str] | None = None) -> bytes:
    """Body for POST /v2/snaps that holds auto-refresh forever (all snaps if None)."""
    body: dict = {"action": "hold", "time": "forever", "hold-level": "auto-refresh"}
    if snaps:
        body["snaps"] = snaps
    return json.dumps(body).encode()


def snapd_post(path: str, body: bytes, sock_path: str = SNAPD_SOCKET) -> tuple[int, dict]:
    """Minimal HTTP/1.1 POST over snapd's unix socket. Returns (status, json)."""
    req = (
        f"POST {path} HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n"
        f"X-Allow-Interaction: true\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n"
    ).encode() + body
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(120)
        s.connect(sock_path)
        s.sendall(req)
        data = b""
        while chunk := s.recv(65536):
            data += chunk
    head, _, payload = data.partition(b"\r\n\r\n")
    status = int(head.split(b" ", 2)[1])
    try:
        return status, json.loads(payload or b"{}")
    except ValueError:
        return status, {}


class SnapBackend(Backend):
    source = Source.SNAP

    def _client(self):
        c = _snapd().Client()
        c.set_allow_interaction(True)
        return c

    def available(self) -> bool:
        try:
            self._client().get_system_information_sync(None)
            return True
        except Exception as e:
            log.info("snapd not available: %s", e)
            return False

    def _offer(self, snap, installed: bool) -> Offer:
        return Offer(
            source=Source.SNAP,
            ref=snap.get_name(),
            app_id=None,
            name=snap.get_title() or snap.get_name(),
            summary=snap.get_summary() or "",
            version=snap.get_version() or "",
            developer_verified=int(snap.get_publisher_validation()) in _VERIFIED,
            installed=installed,
        )

    def _installed_names(self) -> set[str]:
        Snapd = _snapd()
        snaps = self._client().get_snaps_sync(Snapd.GetSnapsFlags.NONE, None, None)
        return {s.get_name() for s in snaps}

    def search(self, text: str) -> list[Offer]:
        try:
            Snapd = _snapd()
            snaps, _ = self._client().find_sync(Snapd.FindFlags.NONE, text, None)
            installed = self._installed_names()
            # only app snaps (not cores, bases, snapd itself); store results
            # have no apps list, so the type is the only filter
            return [
                self._offer(s, s.get_name() in installed)
                for s in snaps
                if s.get_snap_type() == Snapd.SnapType.APP
            ]
        except Exception as e:
            log.warning("snap search failed: %s", e)
            return []

    def installed(self) -> list[Offer]:
        try:
            Snapd = _snapd()
            snaps = self._client().get_snaps_sync(Snapd.GetSnapsFlags.NONE, None, None)
            return [self._offer(s, True) for s in snaps if s.get_snap_type() == Snapd.SnapType.APP]
        except Exception as e:
            log.warning("listing snaps failed: %s", e)
            return []

    def updates(self) -> list[UpdateItem]:
        try:
            snaps = self._client().find_refreshable_sync(None)
            return [
                UpdateItem(
                    Source.SNAP,
                    s.get_name(),
                    s.get_title() or s.get_name(),
                    "",
                    s.get_version() or "",
                    int(s.get_download_size() or 0),
                    False,
                )
                for s in snaps
            ]
        except Exception as e:
            log.warning("checking snap updates failed: %s", e)
            return []

    def _progress_cb(self, progress: Progress, status: str):
        def cb(_client, change, _deprecated, *_):
            try:
                tasks = change.get_tasks()
                done = sum(t.get_progress_done() for t in tasks)
                total = sum(t.get_progress_total() for t in tasks) or 1
                progress(int(100 * done / total), status)
            except Exception:
                pass

        return cb

    def install(self, offer: Offer, progress: Progress, cancel: Event) -> Result:
        try:
            Snapd = _snapd()
            self._client().install2_sync(
                Snapd.InstallFlags.NONE,
                offer.ref,
                None,
                None,
                self._progress_cb(progress, offer.name),
                None,
                _cancellable(cancel),
            )
            hold_auto_refresh([offer.ref])
            return Result.success()
        except Exception as e:
            return classify(e)

    def remove(self, offer: Offer, progress: Progress, cancel: Event) -> Result:
        try:
            Snapd = _snapd()
            self._client().remove2_sync(
                Snapd.RemoveFlags.NONE,
                offer.ref,
                self._progress_cb(progress, offer.name),
                None,
                _cancellable(cancel),
            )
            return Result.success()
        except Exception as e:
            return classify(e)

    def update(self, items: list[UpdateItem], progress: Progress, cancel: Event) -> Result:
        client = self._client()
        for i in items:
            if cancel.is_set():
                return Result(Problem.CANCELLED, "cancelled")
            try:
                client.refresh_sync(
                    i.ref, None, self._progress_cb(progress, i.name), None, _cancellable(cancel)
                )
            except Exception as e:
                return classify(e)
        return Result.success()


def hold_auto_refresh(snaps: list[str] | None = None) -> Result:
    """Stop snapd refreshing on its own; the hub refreshes snaps itself."""
    try:
        status, reply = snapd_post("/v2/snaps", hold_request_body(snaps))
        if status in (200, 202):
            return Result.success()
        return classify(reply.get("result", {}).get("message", f"snapd answered {status}"))
    except Exception as e:
        return classify(e)
