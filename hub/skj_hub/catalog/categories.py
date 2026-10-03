"""Plain-language app groups for browsing, mapped from freedesktop categories."""

from __future__ import annotations

# key -> freedesktop main categories (key "all" matches everything)
GROUPS: dict[str, tuple[str, ...]] = {
    "all": (),
    "games": ("Game",),
    "internet": ("Network",),
    "media": ("AudioVideo", "Audio", "Video"),
    "graphics": ("Graphics",),
    "office": ("Office",),
    "education": ("Education", "Science"),
    "tools": ("Utility",),
    "programming": ("Development",),
    "system": ("System",),
}


def in_group(categories: tuple[str, ...], group: str | None) -> bool:
    if not group or group == "all":
        return True
    wanted = GROUPS.get(group, ())
    return any(c in wanted for c in categories)
