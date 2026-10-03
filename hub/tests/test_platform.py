from skj_hub.platform import Base, detect

SKJ_EZ = """NAME="SKJ OS EZ ISO Edition"
ID=skj-os-ez
ID_LIKE=fedora
VERSION_ID=44
VARIANT_ID=kde
"""

UBUNTU = """NAME="Ubuntu"
ID=ubuntu
ID_LIKE=debian
VERSION_ID="26.04"
"""

BAZZITE = """NAME="Bazzite"
ID=bazzite
ID_LIKE="fedora"
VERSION_ID=44
VARIANT_ID=bazzite-nvidia
"""


def test_skj_ez_on_fedora_kde():
    p = detect(os_release=SKJ_EZ, env={"XDG_CURRENT_DESKTOP": "KDE"}, image_based=False)
    assert p.base is Base.FEDORA
    assert p.desktop == "kde"
    assert p.version == "44"
    assert not p.image_based
    assert p.supported


def test_ubuntu_gnome_is_detected_but_not_supported_yet():
    p = detect(os_release=UBUNTU, env={"XDG_CURRENT_DESKTOP": "ubuntu:GNOME"}, image_based=False)
    assert p.base is Base.UBUNTU
    assert p.desktop == "gnome"
    assert not p.supported


def test_bazzite_is_its_own_base_and_image_based():
    p = detect(os_release=BAZZITE, env={"XDG_CURRENT_DESKTOP": "KDE"}, image_based=True)
    assert p.base is Base.BAZZITE
    assert p.image_based
    assert not p.supported


def test_unknown_system():
    p = detect(os_release="ID=arch\n", env={}, image_based=False)
    assert p.base is Base.UNKNOWN
    assert p.desktop == "unknown"
    assert not p.supported


def test_quoted_values_and_comments():
    p = detect(os_release='# c\nID="skj-os-ez"\nID_LIKE="fedora"\n', env={}, image_based=False)
    assert p.base is Base.FEDORA
