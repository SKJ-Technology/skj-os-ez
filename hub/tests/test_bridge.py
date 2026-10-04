"""The Kirigami UI's Python side, on the fake backend (spec §7)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import pytest  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402

from skj_hub import i18n  # noqa: E402
from skj_hub.backends.fake import demo_backends  # noqa: E402
from skj_hub.hub import Hub  # noqa: E402
from skj_hub.platform import Base, Platform  # noqa: E402
from skj_hub.result import Problem, Result  # noqa: E402
from skj_hub.ui.bridge import AppsModel, Bridge  # noqa: E402
from skj_hub.updates.rules import DriverState  # noqa: E402

FEDORA_KDE = Platform(Base.FEDORA, "kde", "44", False)
ROLE = {name: Qt.UserRole + i for i, name in enumerate(AppsModel.ROLES)}


@pytest.fixture(autouse=True)
def english():
    i18n.set_language("en")


@pytest.fixture
def bridge(qapp):
    restarts = []

    def restart():
        restarts.append(True)
        return Result.success()

    backends = demo_backends()
    b = Bridge(Hub(backends, FEDORA_KDE), lambda: None, restart)
    b.restarts, b.backends = restarts, backends
    yield b
    b.jobs.wait(5000)


def row(model, name):
    for r in range(model.rowCount()):
        if model.data(model.index(r), ROLE["name"]) == name:
            return r
    raise AssertionError(f"{name} not in the list")


def get(model, r, role):
    return model.data(model.index(r), ROLE[role])


def test_browse_lists_all_apps_a_to_z(bridge, qtbot):
    apps = bridge.apps
    apps.refresh("", "all")
    qtbot.waitUntil(lambda: apps.model.count >= 5, timeout=5000)
    names = [get(apps.model, r, "name") for r in range(apps.model.count)]
    assert names == sorted(names, key=str.lower)
    assert "SuperTuxKart" in names
    assert "apps)" in apps.message and not apps.loading


def test_group_filter(bridge, qtbot):
    bridge.apps.refresh("", "games")
    qtbot.waitUntil(lambda: bridge.apps.model.count == 1, timeout=5000)
    assert get(bridge.apps.model, 0, "name") == "SuperTuxKart"


def test_search_and_install(bridge, qtbot):
    apps, model = bridge.apps, bridge.apps.model
    apps.refresh("gimp", "all")
    qtbot.waitUntil(lambda: model.count == 1 and not apps.loading, timeout=5000)
    assert "Flathub" in get(model, 0, "source")
    assert get(model, 0, "others") == ["from SKJ OS (Fedora)"]
    model.install(0)
    qtbot.waitUntil(lambda: get(model, 0, "installed"), timeout=5000)
    assert get(model, 0, "status") == "GIMP is installed."
    assert not get(model, 0, "busy")
    assert get(model, 0, "others") == []  # installed: no other versions offered
    assert ("install", "app/org.gimp.GIMP/x86_64/stable") in bridge.backends[1].calls


def test_install_from_another_source(bridge, qtbot):
    model = bridge.apps.model
    bridge.apps.refresh("gimp", "all")
    qtbot.waitUntil(lambda: model.count == 1, timeout=5000)
    model.installFrom(0, 0)  # the Fedora package instead of Flathub
    qtbot.waitUntil(lambda: get(model, 0, "installed"), timeout=5000)
    assert ("install", "gimp") in bridge.backends[0].calls
    assert bridge.backends[1].calls == []


def test_search_nothing_found(bridge, qtbot):
    bridge.apps.refresh("zzzzzz", "all")
    qtbot.waitUntil(lambda: bridge.apps.message.startswith("Nothing found"), timeout=5000)
    assert bridge.apps.model.count == 0


def test_install_problem_is_plain_text(bridge, qtbot):
    bridge.backends[1].fail_with = Problem.NO_NETWORK
    model = bridge.apps.model
    bridge.apps.refresh("gimp", "all")
    qtbot.waitUntil(lambda: model.count == 1, timeout=5000)
    model.install(0)
    qtbot.waitUntil(lambda: get(model, 0, "problem") != "", timeout=5000)
    assert get(model, 0, "problem").startswith("No internet")
    assert get(model, 0, "details") == "fake install failed"
    assert not get(model, 0, "installed") and not get(model, 0, "busy")


def test_installed_list_and_remove(bridge, qtbot):
    inst, model = bridge.installed, bridge.installed.model
    inst.reload()
    qtbot.waitUntil(lambda: model.count == 2, timeout=5000)
    r = row(model, "Firefox")
    model.remove(r)
    qtbot.waitUntil(lambda: not get(model, r, "installed"), timeout=5000)
    assert get(model, r, "status") == "Firefox was removed."
    assert ("remove", "firefox") in bridge.backends[0].calls


def test_update_everything_then_offer_restart(bridge, qtbot):
    up = bridge.updates
    up.check()
    qtbot.waitUntil(lambda: up.state == "ready", timeout=5000)
    assert "3 updates" in up.summary and "kernel-core" in up.details
    up.apply()
    qtbot.waitUntil(lambda: up.state == "done", timeout=5000)
    assert up.summary == "All done!"
    assert up.restartState == "ready"
    assert bridge.restarts == []  # never restarts on its own
    up.restartNow()
    assert bridge.restarts == [True]


def test_restart_waits_for_nvidia_driver(bridge, qtbot):
    up = bridge.updates
    up.driver_probe = lambda: DriverState(True, frozenset(), True)  # akmods building
    up.check()
    qtbot.waitUntil(lambda: up.state == "ready", timeout=5000)
    up.apply()
    qtbot.waitUntil(lambda: up.state == "done", timeout=5000)
    assert up.restartState == "wait"
    up.restartNow()  # ignored while the driver is building
    assert bridge.restarts == []
    up.later()
    assert up.restartState == "none"


def test_update_problem_is_shown(bridge, qtbot):
    bridge.backends[0].fail_with = Problem.NO_SPACE
    up = bridge.updates
    up.check()
    qtbot.waitUntil(lambda: up.state == "ready", timeout=5000)
    up.apply()
    qtbot.waitUntil(lambda: up.problem != "", timeout=5000)
    assert up.problem.startswith("Your disk is full")
    assert up.restartState == "none"


def test_strings_follow_language(qapp):
    i18n.set_language("pl")
    b = Bridge(Hub(demo_backends(), FEDORA_KDE), lambda: None, Result.success)
    assert b.strings["updates.button"] == "Zaktualizuj wszystko"
    assert {"key": "games", "label": "Gry"} in b.groups
    b.jobs.wait(5000)


def test_qml_loads_and_every_page_opens(qapp, qtbot):
    """The real Kirigami window loads without QML errors and shows each page."""
    pytest.importorskip("PySide6.QtQuick")
    from skj_hub.ui import qmlapp

    hub = Hub(demo_backends(), FEDORA_KDE)
    problems = []
    engine, bridge, window = qmlapp.load(hub, lambda: None, Result.success)
    if window is None:
        pytest.skip("Kirigami (org.kde.kirigami) is not installed here")
    engine.warnings.connect(
        lambda ws: problems.extend(w.toString() for w in ws if qmlapp._NOISE not in w.toString())
    )
    for page in qmlapp.PAGES:
        window.showPage(page)
        qtbot.wait(300)
        assert window.property("currentPage") == page
    qtbot.waitUntil(lambda: bridge.apps.model.count >= 5, timeout=5000)
    bridge.jobs.wait(5000)
    qmlapp.shutdown(engine)
    assert problems == []
