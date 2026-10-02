import string

import pytest

from skj_hub import i18n
from skj_hub.result import Problem


def test_every_string_has_polish_and_english():
    for key, entry in i18n.STRINGS.items():
        assert set(entry) == {"en", "pl"}, key
        assert entry["en"].strip() and entry["pl"].strip(), key


def test_placeholders_match_between_languages():
    def fields(text):
        return {f for _, f, _, _ in string.Formatter().parse(text) if f}

    for key, entry in i18n.STRINGS.items():
        assert fields(entry["en"]) == fields(entry["pl"]), key


def test_every_problem_has_a_message():
    for p in Problem:
        if p is Problem.NONE:
            continue
        assert set(i18n.PROBLEMS[p]) == {"en", "pl"}, p


@pytest.mark.parametrize(
    "env, lang",
    [
        ({"LANG": "pl_PL.UTF-8"}, "pl"),
        ({"LANG": "en_US.UTF-8"}, "en"),
        ({"LANGUAGE": "pl", "LANG": "en_US.UTF-8"}, "pl"),
        ({}, "en"),
    ],
)
def test_language_from_env(env, lang):
    assert i18n.language(env) == lang


def test_tr_and_fallback():
    i18n.set_language("pl")
    assert i18n.tr("updates.button") == "Zaktualizuj wszystko"
    assert i18n.tr("apps.installing", name="GIMP") == "Instaluję GIMP…"
    assert i18n.tr("no.such.key") == "no.such.key"
    i18n.set_language("en")
    assert i18n.problem_text(Problem.NO_NETWORK).startswith("No internet")


def test_no_jargon_in_user_texts():
    banned = ("transaction", "repository", "dependency", "dependencies", "package manager")
    for key, entry in i18n.STRINGS.items():
        assert not any(b in entry["en"].lower() for b in banned), key


@pytest.mark.parametrize(
    "size, text",
    [(500, "500 B"), (12_000, "12 KB"), (340_000_000, "340.0 MB"), (3_400_000_000, "3.4 GB")],
)
def test_human_size(size, text):
    assert i18n.human_size(size) == text
