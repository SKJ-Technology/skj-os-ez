"""Small system probes and the user-initiated restart (spec §4.4)."""

from __future__ import annotations

import logging
import subprocess

from skj_hub.result import Result, classify
from skj_hub.updates.rules import DriverState

log = logging.getLogger(__name__)


def _run(cmd: list[str]) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return r.returncode, r.stdout
    except (OSError, subprocess.TimeoutExpired) as e:
        log.info("%s failed: %s", cmd[0], e)
        return 1, ""


def kmod_kernels(rpm_names: str) -> frozenset[str]:
    """Kernel versions from `rpm -qa --qf '%{NAME}\\n' 'kmod-nvidia-*'` output.

    akmods names the package kmod-nvidia-<kernel version>, e.g.
    kmod-nvidia-7.2.9-200.fc44.x86_64.
    """
    prefix = "kmod-nvidia-"
    return frozenset(
        line.strip()[len(prefix) :]
        for line in rpm_names.splitlines()
        if line.strip().startswith(prefix) and line.strip()[len(prefix) :][:1].isdigit()
    )


def akmods_building(active_state: str, akmods_process: bool) -> bool:
    """Is akmods building right now?

    akmods.service is oneshot + RemainAfterExit: after its boot run it stays
    "active" (sub-state exited) all day, so "active" means nothing. Only
    "activating" (running now) or a live akmods process count.
    """
    return active_state.strip() == "activating" or akmods_process


def driver_state() -> DriverState | None:
    """NVIDIA akmod status on Fedora; None when there's no akmod driver."""
    code, _ = _run(["rpm", "-q", "akmod-nvidia"])
    if code != 0:
        return None
    _, names = _run(["rpm", "-qa", "--qf", "%{NAME}\n", "kmod-nvidia-*"])
    _, state = _run(["systemctl", "show", "-p", "ActiveState", "--value", "akmods.service"])
    code, _ = _run(["pgrep", "-x", "akmods|akmodsbuild"])
    return DriverState(True, kmod_kernels(names), akmods_building(state, code == 0))


def restart() -> Result:
    """Ask logind to restart, only ever after the user pressed 'Restart now'."""
    try:
        from gi.repository import Gio, GLib

        bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        bus.call_sync(
            "org.freedesktop.login1",
            "/org/freedesktop/login1",
            "org.freedesktop.login1.Manager",
            "Reboot",
            GLib.Variant("(b)", (True,)),  # interactive: polkit may ask
            None,
            Gio.DBusCallFlags.NONE,
            -1,
            None,
        )
        return Result.success()
    except Exception as e:
        return classify(e)
