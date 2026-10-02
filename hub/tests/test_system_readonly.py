"""Read-only checks against the real PackageKit, Flatpak and snapd (spec §7).

Never install, remove or update anything here. Off by default (CI has no
system services); run with SKJ_HUB_SYSTEM_TESTS=1 on a Fedora machine or VM.
"""

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("SKJ_HUB_SYSTEM_TESTS") != "1", reason="needs real system services"
)


@pytest.fixture(scope="module")
def index():
    from skj_hub.backends.appstream_index import AppStreamIndex

    return AppStreamIndex()


def test_packagekit_search_installed_updates(index):
    from skj_hub.backends.packagekit import PackageKitBackend

    b = PackageKitBackend(index)
    assert b.available()
    found = b.search("gimp")
    assert any(o.ref == "gimp" and o.app_id == "org.gimp.GIMP" for o in found)
    installed = b.installed()
    assert any(o.ref == "firefox" and o.installed for o in installed)
    assert isinstance(b.updates(), list)


def test_flatpak_search_and_updates(index):
    from skj_hub.backends.flatpak import FlatpakBackend

    b = FlatpakBackend(index)
    assert b.available()
    found = b.search("gimp")
    gimp = [o for o in found if o.ref.startswith("app/org.gimp.GIMP/")]
    assert gimp and gimp[0].developer_verified
    assert isinstance(b.installed(), list)
    assert isinstance(b.updates(), list)


def test_snap_search_finds_verified_spotify():
    from skj_hub.backends.snap import SnapBackend

    b = SnapBackend()
    if not b.available():
        pytest.skip("snapd not running")
    spotify = [o for o in b.search("spotify") if o.ref == "spotify"]
    assert spotify and spotify[0].developer_verified
    assert isinstance(b.updates(), list)
