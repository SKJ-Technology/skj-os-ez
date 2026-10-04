"""Polish and English from day one (spec §5).

Plain words only: "Install", "Update everything", never "transaction" or
"repository". Technical words belong under "Details".
"""

from __future__ import annotations

import os

from skj_hub.result import Problem

STRINGS: dict[str, dict[str, str]] = {
    "app.title": {"en": "SKJ Hub", "pl": "SKJ Hub"},
    "nav.start": {"en": "Start", "pl": "Start"},
    "nav.apps": {"en": "Apps", "pl": "Aplikacje"},
    "nav.installed": {"en": "My apps", "pl": "Moje aplikacje"},
    "nav.updates": {"en": "Updates", "pl": "Aktualizacje"},
    "nav.help": {"en": "Help & safety", "pl": "Pomoc i bezpieczeństwo"},
    # start
    "start.hello": {"en": "Welcome to SKJ OS EZ", "pl": "Witaj w SKJ OS EZ"},
    "start.sub": {
        "en": "Everything you need is here: get apps, keep your PC up to date and find help.",
        "pl": "Wszystko w jednym miejscu: instaluj aplikacje, aktualizuj komputer i znajdź pomoc.",
    },
    "start.demo": {
        "en": "Demo mode: this is a small made-up list of apps, nothing is really installed.",
        "pl": "Tryb demo: to mała, przykładowa lista aplikacji, nic nie jest naprawdę instalowane.",
    },
    "start.find_apps": {"en": "Find apps", "pl": "Znajdź aplikacje"},
    "start.check_updates": {"en": "Check for updates", "pl": "Sprawdź aktualizacje"},
    "start.unsupported": {
        "en": "This system isn't fully supported yet. Only the parts that work are shown.",
        "pl": "Ten system nie jest jeszcze w pełni wspierany. Widzisz tylko to, co działa.",
    },
    # apps
    "apps.search": {
        "en": "Search for an app, e.g. Spotify or photo editor",
        "pl": "Szukaj aplikacji, np. Spotify albo edytor zdjęć",
    },
    "apps.hint": {
        "en": "Pick a group or type what you're looking for. We'll pick the best version for you.",
        "pl": "Wybierz grupę albo wpisz, czego szukasz. Najlepszą wersję wybierzemy za Ciebie.",
    },
    "apps.loading": {"en": "Loading apps…", "pl": "Wczytuję aplikacje…"},
    "apps.count": {"en": "({count} apps)", "pl": "(aplikacji: {count})"},
    "group.all": {"en": "All apps", "pl": "Wszystkie aplikacje"},
    "group.games": {"en": "Games", "pl": "Gry"},
    "group.internet": {"en": "Internet", "pl": "Internet"},
    "group.media": {"en": "Music & video", "pl": "Muzyka i wideo"},
    "group.graphics": {"en": "Photos & graphics", "pl": "Zdjęcia i grafika"},
    "group.office": {"en": "Office", "pl": "Biuro"},
    "group.education": {"en": "Learning & science", "pl": "Nauka"},
    "group.tools": {"en": "Tools", "pl": "Narzędzia"},
    "group.programming": {"en": "Programming", "pl": "Programowanie"},
    "group.system": {"en": "System", "pl": "System"},
    "apps.searching": {"en": "Searching…", "pl": "Szukam…"},
    "apps.none": {
        "en": "Nothing found. Try another word, e.g. 'music' or 'office'.",
        "pl": "Nic nie znaleziono. Spróbuj innego słowa, np. „muzyka” albo „biuro”.",
    },
    "apps.install": {"en": "Install", "pl": "Zainstaluj"},
    "apps.remove": {"en": "Remove", "pl": "Usuń"},
    "apps.installed": {"en": "Installed", "pl": "Zainstalowana"},
    "apps.other_versions": {"en": "Other versions", "pl": "Inne wersje"},
    "apps.from": {"en": "from {source}", "pl": "z {source}"},
    "apps.verified": {"en": "made by the app's developer", "pl": "od twórców aplikacji"},
    "apps.installing": {"en": "Installing {name}…", "pl": "Instaluję {name}…"},
    "apps.removing": {"en": "Removing {name}…", "pl": "Usuwam {name}…"},
    "apps.done_install": {"en": "{name} is installed.", "pl": "{name} jest zainstalowana."},
    "apps.done_remove": {"en": "{name} was removed.", "pl": "{name} została usunięta."},
    "apps.confirm_remove": {
        "en": "Remove {name}? Your own files (documents, photos) stay where they are.",
        "pl": "Usunąć {name}? Twoje pliki (dokumenty, zdjęcia) zostaną na miejscu.",
    },
    "installed.empty": {
        "en": "Apps you install from the hub show up here.",
        "pl": "Tu pojawią się aplikacje zainstalowane z huba.",
    },
    # sources (plain words)
    "source.distro": {"en": "SKJ OS (Fedora)", "pl": "SKJ OS (Fedora)"},
    "source.flatpak": {"en": "Flathub", "pl": "Flathub"},
    "source.snap": {"en": "Snap Store", "pl": "Snap Store"},
    # updates
    "updates.checking": {"en": "Checking for updates…", "pl": "Sprawdzam aktualizacje…"},
    "updates.none": {"en": "Your PC is up to date.", "pl": "Twój komputer jest aktualny."},
    "updates.some": {
        "en": "{count} updates are ready ({size}).",
        "pl": "Gotowe aktualizacje: {count} ({size}).",
    },
    "updates.why": {
        "en": "Updates fix problems and keep you safe. Your files are not touched.",
        "pl": "Aktualizacje naprawiają błędy i dbają o bezpieczeństwo. Twoje pliki są bezpieczne.",
    },
    "updates.button": {"en": "Update everything", "pl": "Zaktualizuj wszystko"},
    "updates.details": {
        "en": "Show what will be updated",
        "pl": "Pokaż, co zostanie zaktualizowane",
    },
    "updates.running": {
        "en": "Updating… you can keep using your PC.",
        "pl": "Aktualizuję… możesz dalej korzystać z komputera.",
    },
    "updates.done": {"en": "All done!", "pl": "Gotowe!"},
    "updates.restart_needed": {
        "en": "Restart your PC to finish. Save your work first. We never restart on our own.",
        "pl": "Uruchom komputer ponownie, aby dokończyć. Najpierw zapisz swoją pracę. "
        "Nigdy nie robimy tego sami.",
    },
    "updates.wait_driver": {
        "en": "Getting your graphics driver ready for the new system version… "
        "Please don't restart yet.",
        "pl": "Przygotowuję sterownik karty graficznej do nowej wersji systemu… "
        "Jeszcze nie uruchamiaj ponownie.",
    },
    "updates.restart_now": {"en": "Restart now", "pl": "Uruchom ponownie teraz"},
    "updates.later": {"en": "Later", "pl": "Później"},
    "updates.notify_title": {"en": "Updates are ready", "pl": "Aktualizacje są gotowe"},
    "updates.notify_body": {
        "en": "{count} updates for your PC. Open SKJ Hub to install them.",
        "pl": "Aktualizacje dla Twojego komputera: {count}. Otwórz SKJ Hub, aby je zainstalować.",
    },
    # common
    "common.cancel": {"en": "Cancel", "pl": "Anuluj"},
    "common.details": {"en": "Details", "pl": "Szczegóły"},
    "common.ok": {"en": "OK", "pl": "OK"},
    "common.try_again": {"en": "Try again", "pl": "Spróbuj ponownie"},
    # help (Notion: "don't be scared of commands" + safety)
    "help.title": {"en": "Help & safety", "pl": "Pomoc i bezpieczeństwo"},
    "help.commands_title": {"en": "Don't be scared of commands", "pl": "Nie bój się komend"},
    "help.commands": {
        "en": "If you can't find something in the hub, it's fine to run a command in the "
        "terminal. Just make sure you know what it does. If you don't, ask someone you "
        "trust or an AI to explain it before you run it.",
        "pl": "Jeśli czegoś nie ma w hubie, możesz uruchomić komendę w terminalu. "
        "Upewnij się tylko, że wiesz, co robi. Jeśli nie wiesz, poproś zaufaną osobę "
        "albo AI o wyjaśnienie, zanim ją uruchomisz.",
    },
    "help.flags_title": {"en": "Red flags: stop before running", "pl": "Uwaga: zatrzymaj się"},
    "help.flags": {
        "en": "• A website tells you to paste a command that downloads something and runs it "
        "(for example with 'curl … | sudo bash').\n"
        "• Someone you don't know asks for your password.\n"
        "• A command contains 'rm -rf /' or deletes things you didn't ask to delete.\n"
        "• You're told to turn off security features 'to make it work'.",
        "pl": "• Strona każe wkleić komendę, która coś pobiera i od razu uruchamia "
        "(np. 'curl … | sudo bash').\n"
        "• Ktoś obcy prosi o Twoje hasło.\n"
        "• Komenda zawiera 'rm -rf /' albo usuwa rzeczy, o które nie prosiłeś.\n"
        "• Każą Ci wyłączyć zabezpieczenia, „żeby zadziałało”.",
    },
    "help.report": {"en": "Report a problem", "pl": "Zgłoś problem"},
}

PROBLEMS: dict[Problem, dict[str, str]] = {
    Problem.CANCELLED: {
        "en": "Stopped. Nothing was changed.",
        "pl": "Zatrzymano. Nic nie zostało zmienione.",
    },
    Problem.NO_NETWORK: {
        "en": "No internet connection. Check your Wi-Fi or cable and try again.",
        "pl": "Brak internetu. Sprawdź Wi-Fi albo kabel i spróbuj ponownie.",
    },
    Problem.NO_SPACE: {
        "en": "Your disk is full. Remove some files or apps and try again.",
        "pl": "Dysk jest pełny. Usuń trochę plików albo aplikacji i spróbuj ponownie.",
    },
    Problem.CONFLICT: {
        "en": "This can't be installed right now because it clashes with something else. "
        "Try the other version below, or update everything first.",
        "pl": "Nie da się tego teraz zainstalować, bo koliduje z czymś innym. "
        "Wybierz inną wersję poniżej albo najpierw zaktualizuj wszystko.",
    },
    Problem.NOT_FOUND: {
        "en": "We couldn't find this anymore. Search again in a moment.",
        "pl": "Już tego nie znaleźliśmy. Wyszukaj ponownie za chwilę.",
    },
    Problem.SERVICE_DOWN: {
        "en": "A part of the system that installs apps isn't responding. Restart your PC "
        "and try again.",
        "pl": "Część systemu, która instaluje aplikacje, nie odpowiada. Uruchom komputer "
        "ponownie i spróbuj jeszcze raz.",
    },
    Problem.UNKNOWN: {
        "en": "Something went wrong. Try again; if it keeps happening, report a problem "
        "and include the details.",
        "pl": "Coś poszło nie tak. Spróbuj ponownie; jeśli to się powtarza, zgłoś problem "
        "i dołącz szczegóły.",
    },
}


def language(env: dict[str, str] | None = None) -> str:
    env = os.environ if env is None else env
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = env.get(var, "")
        if value:
            return "pl" if value.lower().startswith("pl") else "en"
    return "en"


_lang = language()


def set_language(lang: str) -> None:
    global _lang
    _lang = lang if lang in ("en", "pl") else "en"


def tr(key: str, **kw) -> str:
    entry = STRINGS.get(key)
    text = entry.get(_lang, entry["en"]) if entry else key
    return text.format(**kw) if kw else text


def problem_text(problem: Problem) -> str:
    entry = PROBLEMS.get(problem, PROBLEMS[Problem.UNKNOWN])
    return entry.get(_lang, entry["en"])


def human_size(size: int) -> str:
    units = ("B", "KB", "MB", "GB")
    value = float(size)
    for unit in units:
        if value < 1000 or unit == units[-1]:
            return f"{value:.0f} {unit}" if unit in ("B", "KB") else f"{value:.1f} {unit}"
        value /= 1000
    return f"{size} B"
