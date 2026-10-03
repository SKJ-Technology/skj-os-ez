"""UI smoke tests on the fake backend, headless (spec §7)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

from skj_hub import i18n  # noqa: E402
from skj_hub.backends.fake import demo_backends  # noqa: E402
from skj_hub.hub import Hub  # noqa: E402
from skj_hub.platform import Base, Platform  # noqa: E402
from skj_hub.result import Problem, Result  # noqa: E402
from skj_hub.updates.rules import DriverState  # noqa: E402

FEDORA_KDE = Platform(Base.FEDORA, "kde", "44", False)


@pytest.fixture(autouse=True)
def english():
    i18n.set_language("en")


@pytest.fixture
def window(qtbot):
    from skj_hub.ui.theme import stylesheet
    from skj_hub.ui.window import MainWindow

    restarts = []

    def restart():
        restarts.append(True)
        return Result.success()

    backends = demo_backends()
    w = MainWindow(Hub(backends, FEDORA_KDE), lambda: None, restart)
    w.setStyleSheet(stylesheet())
    w.restarts = restarts
    w.backends = backends
    qtbot.addWidget(w)
    w.show()
    yield w
    w.jobs.wait(5000)


def test_start_page_shows_updates(window, qtbot):
    qtbot.waitUntil(lambda: "updates are ready" in window.start.updates.text(), timeout=5000)
    assert not window.start.note.isVisible()  # Fedora KDE is supported


def test_search_and_install(window, qtbot):
    window.show_page("apps")
    window.apps.search.setText("gimp")
    qtbot.waitUntil(lambda: len(window.apps.results.cards) == 1, timeout=5000)
    card = window.apps.results.cards[0]
    assert "Flathub" in card.source.text()
    assert card.main_button.text() == "Install"
    card.main_button.click()
    qtbot.waitUntil(lambda: card.main_button.isEnabled(), timeout=5000)
    assert card.status.text() == "GIMP is installed."
    assert card.main_button.text() == "Remove"
    assert ("install", "app/org.gimp.GIMP/x86_64/stable") in window.backends[1].calls


def test_search_nothing_found(window, qtbot):
    window.show_page("apps")
    window.apps.search.setText("zzzzzz")
    qtbot.waitUntil(lambda: window.apps.state.text().startswith("Nothing found"), timeout=5000)
    assert window.apps.results.cards == []


def test_install_problem_is_plain_text(window, qtbot):
    window.backends[1].fail_with = Problem.NO_NETWORK
    window.show_page("apps")
    window.apps.search.setText("gimp")
    qtbot.waitUntil(lambda: len(window.apps.results.cards) == 1, timeout=5000)
    card = window.apps.results.cards[0]
    card.main_button.click()
    qtbot.waitUntil(lambda: card.problem.isVisible(), timeout=5000)
    assert card.problem.text.text().startswith("No internet")
    assert card.main_button.text() == "Install"


def test_update_everything_then_offer_restart(window, qtbot):
    window.show_page("updates")
    page = window.updates
    qtbot.waitUntil(lambda: page.go.isVisible(), timeout=5000)
    assert "3 updates" in page.status.text()
    page.go.click()
    qtbot.waitUntil(lambda: page.restart_box.isVisible(), timeout=5000)
    assert page.status.text() == "All done!"
    assert page.restart_now.isEnabled()
    assert window.restarts == []  # never restarts on its own
    page.restart_now.click()
    assert window.restarts == [True]


def test_restart_waits_for_nvidia_driver(window, qtbot):
    page = window.updates
    page.driver_probe = lambda: DriverState(True, frozenset(), True)  # akmods building
    window.show_page("updates")
    qtbot.waitUntil(lambda: page.go.isVisible(), timeout=5000)
    page.go.click()
    qtbot.waitUntil(lambda: page.restart_box.isVisible(), timeout=5000)
    assert "graphics driver" in page.restart_text.text()
    assert not page.restart_now.isEnabled()


def test_help_page(window):
    window.show_page("help")
    assert window.stack.currentWidget() is window.help


def test_polish_ui(qtbot):
    from skj_hub.ui.window import MainWindow

    i18n.set_language("pl")
    w = MainWindow(Hub(demo_backends(), FEDORA_KDE), lambda: None, Result.success)
    qtbot.addWidget(w)
    assert w.nav.item(1).text() == "Aplikacje"
    assert w.updates.go.text() == "Zaktualizuj wszystko"
    w.jobs.wait(5000)


def test_apps_page_lists_all_apps_without_searching(window, qtbot):
    window.show_page("apps")
    qtbot.waitUntil(lambda: len(window.apps.results.cards) >= 5, timeout=5000)
    names = [c.app.name for c in window.apps.results.cards]
    assert names == sorted(names, key=str.lower)
    assert "SuperTuxKart" in names


def test_apps_page_group_filter(window, qtbot):
    window.show_page("apps")
    page = window.apps
    page.group.setCurrentIndex(page.group.findData("games"))
    qtbot.waitUntil(
        lambda: [c.app.name for c in page.results.cards] == ["SuperTuxKart"], timeout=5000
    )


def test_show_more_pages_long_lists(window, qtbot):
    from skj_hub.catalog.model import App, Offer, Source

    apps = [
        App(f"a{i}", [Offer(Source.FLATPAK, f"r{i}", f"a{i}", f"App {i:03}", "", "1")])
        for i in range(95)
    ]
    lst = window.apps.results
    lst.show_apps(apps)
    assert len(lst.cards) == 40 and lst.more.isVisibleTo(lst)
    lst.more.click()
    lst.more.click()
    assert len(lst.cards) == 95 and not lst.more.isVisibleTo(lst)


def test_sidebar_has_no_horizontal_scrollbar(window):
    from PySide6.QtCore import Qt

    assert window.nav.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff


def test_no_custom_stylesheet(window):
    from skj_hub.ui.theme import stylesheet

    assert stylesheet() == ""  # standard KDE look: system style and colours
