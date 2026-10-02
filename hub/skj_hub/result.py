"""Outcome of anything that changes the system (spec §6).

Backends never raise into the UI. They return a Result with a Problem code;
the UI turns the code into one plain sentence in the user's language and
keeps the technical text for "Details".
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Problem(Enum):
    NONE = "none"
    CANCELLED = "cancelled"  # user closed the password prompt or pressed Cancel
    NO_NETWORK = "no-network"
    NO_SPACE = "no-space"
    CONFLICT = "conflict"  # packages that can't be installed together
    NOT_FOUND = "not-found"
    SERVICE_DOWN = "service-down"  # PackageKit / snapd / flatpak helper not answering
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Result:
    problem: Problem = Problem.NONE
    details: str = ""

    @property
    def ok(self) -> bool:
        return self.problem is Problem.NONE

    @classmethod
    def success(cls) -> Result:
        return cls()


# Lowercase fragments of error texts from PackageKit, libflatpak and snapd.
# Order matters: a dead service's error often also says "no such file".
_PATTERNS: list[tuple[Problem, tuple[str, ...]]] = [
    (
        Problem.SERVICE_DOWN,
        (
            "org.freedesktop.dbus.error.serviceunknown",
            "cannot communicate with server",
            "/run/snapd.socket",
            "packagekit is not running",
            "name has no owner",
        ),
    ),
    (
        Problem.CANCELLED,
        (
            "not authorized",
            "cancelled",
            "canceled",
            "dismissed",
            "authentication is required",
            "polkit",
        ),
    ),
    (Problem.NO_SPACE, ("no space left", "not enough space", "disk space", "enospc")),
    (
        Problem.NO_NETWORK,
        (
            "could not resolve",
            "network is unreachable",
            "no network",
            "failed to download",
            "timed out",
            "connection refused",
            "temporary failure in name resolution",
            "curl error",
        ),
    ),
    (
        Problem.CONFLICT,
        ("conflict", "nothing provides", "cannot install both", "depsolve", "dependency"),
    ),
    (Problem.NOT_FOUND, ("not found", "no such", "unknown package", "does not exist")),
]


def classify(error: BaseException | str) -> Result:
    """Map an error from any backend to a Result with a Problem code."""
    text = str(error)
    low = text.lower()
    for problem, fragments in _PATTERNS:
        if any(f in low for f in fragments):
            return Result(problem, text)
    return Result(Problem.UNKNOWN, text)
