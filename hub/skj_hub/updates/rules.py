"""When the hub may offer a restart (spec §4.4).

The hub never restarts on its own. It only *offers* "Restart now", and not
before the NVIDIA driver is ready for the new kernel: on Fedora, akmods
builds kmod-nvidia after a kernel update, and restarting before it finishes
leaves the user on the fallback driver (lesson from 2026-09-29).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RestartState(Enum):
    NOT_NEEDED = "not-needed"
    READY = "ready"  # offer "Restart now" / "Later"
    WAIT_FOR_DRIVER = "wait-for-driver"  # show "Getting your graphics driver ready..."


@dataclass(frozen=True)
class DriverState:
    """What the system says about the NVIDIA driver."""

    akmod_nvidia_installed: bool
    built_for: frozenset[str]  # kernel versions that have kmod-nvidia-<kver>
    akmods_running: bool


def restart_state(
    needs_restart: bool, new_kernels: list[str], driver: DriverState | None
) -> RestartState:
    if not needs_restart:
        return RestartState.NOT_NEEDED
    if driver is None or not driver.akmod_nvidia_installed or not new_kernels:
        return RestartState.READY
    if driver.akmods_running:
        return RestartState.WAIT_FOR_DRIVER
    if all(k in driver.built_for for k in new_kernels):
        return RestartState.READY
    return RestartState.WAIT_FOR_DRIVER
