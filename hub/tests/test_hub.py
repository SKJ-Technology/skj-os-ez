from skj_hub.backends.base import UpdateItem
from skj_hub.backends.fake import FakeBackend, demo_backends
from skj_hub.catalog.model import Source
from skj_hub.hub import Hub, new_kernels
from skj_hub.platform import Base, Platform
from skj_hub.result import Problem

FEDORA_KDE = Platform(Base.FEDORA, "kde", "44", False)


def hub(backends=None):
    return Hub(backends or demo_backends(), FEDORA_KDE)


def test_search_groups_sources_into_one_app():
    apps = hub().search("gimp")
    assert len(apps) == 1
    assert {o.source for o in apps[0].offers} == {Source.DISTRO, Source.FLATPAK}
    assert apps[0].default.source is Source.FLATPAK  # verified on Flathub


def test_spotify_defaults_to_verified_snap():
    [spotify] = hub().search("spotify")
    assert spotify.default.source is Source.SNAP


def test_short_search_returns_nothing():
    assert hub().search(" g ") == []


def test_unavailable_backend_is_skipped():
    backends = demo_backends()
    backends[2].is_available = False  # snap
    [spotify] = hub(backends).search("spotify")
    assert spotify.default.source is Source.FLATPAK


def test_install_uses_default_source_and_marks_installed():
    h = hub()
    [gimp] = h.search("gimp")
    assert h.install(gimp).ok
    flatpak = h.backend_for(Source.FLATPAK)
    assert flatpak.calls == [("install", "app/org.gimp.GIMP/x86_64/stable")]
    assert h.search("gimp")[0].installed


def test_remove_uses_installed_source():
    h = hub()
    [firefox] = h.search("firefox")
    assert h.remove(firefox).ok
    assert h.backend_for(Source.DISTRO).calls == [("remove", "firefox")]


def test_remove_not_installed():
    h = hub()
    [vlc] = h.search("vlc")
    assert h.remove(vlc).problem is Problem.NOT_FOUND


def test_installed_apps():
    names = [a.name for a in hub().installed_apps()]
    assert names == ["Firefox", "Kdenlive"]


def test_update_plan_and_apply():
    h = hub()
    plan = h.update_plan()
    assert plan.count == 3
    assert plan.needs_restart
    assert h.apply(plan).ok
    assert h.update_plan().empty


def test_apply_stops_at_first_problem():
    backends = demo_backends()
    backends[0].fail_with = Problem.NO_NETWORK  # distro fails first
    h = hub(backends)
    r = h.apply(h.update_plan())
    assert r.problem is Problem.NO_NETWORK
    assert backends[1].calls == []  # flatpak never ran


def test_new_kernels_from_packagekit_ids():
    items = [
        UpdateItem(
            Source.DISTRO,
            "kernel-core;7.2.9-200.fc44;x86_64;updates",
            "kernel-core",
            "",
            "7.2.9-200.fc44",
            0,
            True,
        ),
        UpdateItem(
            Source.DISTRO, "firefox;156.0.2-1.fc44;x86_64;updates", "firefox", "", "", 0, False
        ),
        UpdateItem(Source.FLATPAK, "app/x", "kernel", "", "", 0, False),
    ]
    assert new_kernels(items) == ["7.2.9-200.fc44.x86_64"]


def test_fake_backend_search_matches_summary():
    b = FakeBackend(Source.DISTRO, demo_backends()[0]._offers.values())
    assert [o.ref for o in b.search("photos")] == ["gimp"]


def test_browse_all_lists_every_app_once_a_to_z():
    names = [a.name for a in hub().browse()]
    assert names == sorted(names, key=str.lower)
    assert names.count("GIMP") == 1  # distro + flatpak grouped
    assert "htop" not in names  # command-line tools aren't listed
    assert "SuperTuxKart" in names


def test_browse_group():
    assert [a.name for a in hub().browse("games")] == ["SuperTuxKart"]
    assert {a.name for a in hub().browse("media")} == {"Kdenlive", "Spotify", "VLC"}


def test_browse_unknown_group_is_empty():
    assert hub().browse("nope") == []


def test_browse_adds_known_official_snaps():
    # Spotify: Flathub build is unofficial, the snap is verified -> Snap,
    # in the browse list too (not only in search).
    spotify = next(a for a in hub().browse("media") if a.name == "Spotify")
    assert spotify.default.source is Source.SNAP


def test_browse_asks_snap_store_only_once_per_app():
    backends = demo_backends()
    h = hub(backends)
    seen = []
    real_search = backends[2].search
    backends[2].search = lambda text: seen.append(text) or real_search(text)
    h.browse()
    h.browse()
    assert seen == ["spotify"]
