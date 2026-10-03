"""Tell the user when updates are waiting (spec §4.4).

Replaces Discover's notifier (Discover is removed from the ISO). Run by a
systemd user timer (`skj-hub --notify`): checks once, shows one desktop
notification if there are updates, and opens the hub's Updates page when
the user clicks it. No window, no tray icon, nothing installed by itself.
"""

from __future__ import annotations

import logging
import subprocess
import sys

from skj_hub.i18n import tr

log = logging.getLogger(__name__)

WAIT_FOR_CLICK_SECONDS = 15 * 60


def notify(count: int) -> None:
    from gi.repository import Gio, GLib

    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    reply = bus.call_sync(
        "org.freedesktop.Notifications",
        "/org/freedesktop/Notifications",
        "org.freedesktop.Notifications",
        "Notify",
        GLib.Variant(
            "(susssasa{sv}i)",
            (
                tr("app.title"),
                0,
                "system-software-update",
                tr("updates.notify_title"),
                tr("updates.notify_body", count=count),
                ["default", tr("nav.updates")],
                {"desktop-entry": GLib.Variant("s", "skj-hub")},
                -1,
            ),
        ),
        GLib.VariantType("(u)"),
        Gio.DBusCallFlags.NONE,
        -1,
        None,
    )
    note_id = reply.unpack()[0]
    loop = GLib.MainLoop()

    def on_signal(_conn, _sender, _path, _iface, signal, params):
        args = params.unpack()
        if args[0] != note_id:
            return
        if signal == "ActionInvoked":
            subprocess.Popen([sys.executable, "-m", "skj_hub", "--page", "updates"])
        loop.quit()

    for name in ("ActionInvoked", "NotificationClosed"):
        bus.signal_subscribe(
            "org.freedesktop.Notifications",
            "org.freedesktop.Notifications",
            name,
            "/org/freedesktop/Notifications",
            None,
            Gio.DBusSignalFlags.NONE,
            on_signal,
        )
    GLib.timeout_add_seconds(WAIT_FOR_CLICK_SECONDS, loop.quit)
    loop.run()


def run(hub) -> int:
    plan = hub.update_plan()
    log.info("notifier: %d updates", plan.count)
    if not plan.empty:
        try:
            notify(plan.count)
        except Exception as e:
            log.warning("could not show notification: %s", e)
            return 1
    return 0
