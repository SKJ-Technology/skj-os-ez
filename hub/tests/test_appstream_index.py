from skj_hub.backends.appstream_index import (
    CONSOLE_APP,
    DESKTOP_APP,
    ComponentInfo,
    to_offers,
)
from skj_hub.catalog.model import Kind, Source

ADDON = 6


def info(**kw):
    base = dict(
        app_id="org.gimp.GIMP",
        kind=DESKTOP_APP,
        name="Edytor obrazów GIMP",
        summary="Tworzenie obrazów i edycja zdjęć",
        origin="fedora",
        pkgnames=(),
        flatpak_refs=(),
        verified=False,
    )
    base.update(kw)
    return ComponentInfo(**base)


def test_fedora_component_becomes_distro_offer():
    [o] = to_offers(info(pkgnames=("gimp",)), installed_pkgs=set(), installed_refs=set())
    assert o.source is Source.DISTRO
    assert o.ref == "gimp"
    assert o.app_id == "org.gimp.GIMP"
    assert o.name == "Edytor obrazów GIMP"  # localized name kept
    assert not o.installed


def test_flathub_component_keeps_verified_flag():
    [o] = to_offers(
        info(origin="flatpak", flatpak_refs=("app/org.gimp.GIMP/x86_64/stable",), verified=True),
        installed_pkgs=set(),
        installed_refs={"app/org.gimp.GIMP/x86_64/stable"},
    )
    assert o.source is Source.FLATPAK
    assert o.developer_verified
    assert o.installed


def test_addons_and_runtimes_are_hidden():
    assert to_offers(info(kind=ADDON, pkgnames=("gimp-data-extras",)), set(), set()) == []
    assert (
        to_offers(info(flatpak_refs=("runtime/org.gimp.GIMP.Manual/x86_64/2.10",)), set(), set())
        == []
    )


def test_console_app_is_system_kind():
    [o] = to_offers(info(kind=CONSOLE_APP, pkgnames=("htop",)), set(), set())
    assert o.kind is Kind.SYSTEM


def test_installed_distro_package():
    [o] = to_offers(info(pkgnames=("gimp",)), installed_pkgs={"gimp"}, installed_refs=set())
    assert o.installed
