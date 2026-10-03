"""Look: plain KDE.

The hub uses the system's Qt style and colours (Breeze on SKJ OS EZ, light or
dark as the user chose), so it looks like every other KDE app and theme icons
stay readable. No custom colours: only font sizes are set, in ui/widgets.py.
"""

# Breeze's "negative" text colour, readable on light and dark backgrounds
NEGATIVE = "#da4453"


def stylesheet() -> str:
    """Kept for callers; the hub ships no stylesheet."""
    return ""
