from skj_hub.catalog.merge import group_offers, pick_default
from skj_hub.catalog.model import Kind, Offer, Source


def offer(source, name, app_id=None, verified=False, installed=False, kind=Kind.APP, ref=None):
    return Offer(
        source=source,
        ref=ref or f"{source.value}:{name}",
        app_id=app_id,
        name=name,
        summary="",
        version="1",
        developer_verified=verified,
        installed=installed,
        kind=kind,
    )


# --- default source -------------------------------------------------------------


def test_developer_verified_source_wins():
    # Notion: Spotify's official package is the Snap, the Flathub one isn't
    # made by Spotify -> Snap.
    flathub = offer(Source.FLATPAK, "Spotify", "com.spotify.Client", verified=False)
    snap = offer(Source.SNAP, "spotify", verified=True)
    assert pick_default([flathub, snap]) is snap


def test_flatpak_before_distro_for_apps_when_both_verified_or_not():
    distro = offer(Source.DISTRO, "GIMP", "org.gimp.GIMP")
    flatpak = offer(Source.FLATPAK, "GIMP", "org.gimp.GIMP")
    snap = offer(Source.SNAP, "gimp")
    assert pick_default([snap, distro, flatpak]) is flatpak


def test_distro_first_for_system_tools():
    distro = offer(Source.DISTRO, "htop", "htop", kind=Kind.SYSTEM)
    flatpak = offer(Source.FLATPAK, "htop", "htop", kind=Kind.SYSTEM)
    assert pick_default([flatpak, distro]) is distro


def test_installed_source_is_kept():
    distro = offer(Source.DISTRO, "Firefox", "org.mozilla.firefox", installed=True)
    flatpak = offer(Source.FLATPAK, "Firefox", "org.mozilla.firefox", verified=True)
    assert pick_default([flatpak, distro]) is distro


def test_pick_default_needs_offers():
    try:
        pick_default([])
    except ValueError:
        return
    raise AssertionError("expected ValueError")


# --- grouping ---------------------------------------------------------------------


def test_same_appstream_id_is_one_app():
    apps = group_offers(
        [
            offer(Source.DISTRO, "GIMP", "org.gimp.GIMP"),
            offer(Source.FLATPAK, "GIMP", "org.gimp.GIMP.desktop"),
        ]
    )
    assert len(apps) == 1
    assert {o.source for o in apps[0].offers} == {Source.DISTRO, Source.FLATPAK}


def test_snap_joins_through_app_map():
    apps = group_offers(
        [
            offer(Source.FLATPAK, "Spotify", "com.spotify.Client"),
            offer(Source.SNAP, "spotify", verified=True),
        ],
        app_map={"spotify": "com.spotify.Client"},
    )
    assert len(apps) == 1
    assert apps[0].default.source is Source.SNAP


def test_snap_joins_by_exact_name_when_not_mapped():
    apps = group_offers(
        [
            offer(Source.DISTRO, "VLC", "org.videolan.VLC"),
            offer(Source.SNAP, "vlc"),
        ],
        app_map={},
    )
    assert len(apps) == 1


def test_unrelated_apps_stay_separate():
    apps = group_offers(
        [
            offer(Source.DISTRO, "GIMP", "org.gimp.GIMP"),
            offer(Source.SNAP, "spotify"),
        ],
        app_map={},
    )
    assert sorted(a.name for a in apps) == ["GIMP", "spotify"]


def test_app_name_comes_from_default_offer():
    apps = group_offers(
        [
            offer(Source.FLATPAK, "Spotify", "com.spotify.Client"),
            offer(Source.SNAP, "spotify", verified=True),
        ],
        app_map={"spotify": "com.spotify.Client"},
    )
    # the default is the snap, but the friendlier AppStream name is kept
    assert apps[0].name == "Spotify"


def test_bundled_app_map_has_spotify():
    from skj_hub.catalog.merge import load_app_map

    assert load_app_map()["spotify"] == "com.spotify.Client"
