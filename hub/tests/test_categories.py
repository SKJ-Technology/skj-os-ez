from skj_hub import i18n
from skj_hub.catalog.categories import GROUPS, in_group


def test_all_matches_everything():
    assert in_group((), None)
    assert in_group(("Game",), "all")


def test_group_matches_freedesktop_categories():
    assert in_group(("Game", "ArcadeGame"), "games")
    assert in_group(("Audio", "Player"), "media")
    assert not in_group(("Office",), "games")


def test_every_group_has_a_name_in_both_languages():
    for key in GROUPS:
        assert set(i18n.STRINGS[f"group.{key}"]) == {"en", "pl"}
