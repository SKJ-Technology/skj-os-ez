# SKJ Hub — design

Status: **in use** — written 2026-10-02 while Jakub was away; on 2026-10-03 he
reviewed the first build, answered §9 question 5, and said to merge so the hub
can be tested in the VM. §9 lists what is decided and what is still a default.
Source of truth for the product: Notion "SKJ OS ISO EZ Edition" (Daily App
Ideas). This spec turns it into a build plan for the hub. Anything marked
**[assumption]** is my call and needs a yes/no from Jakub; everything else
is a decision already recorded in Notion or in this session.

## 1. What the hub is

The one app a beginner needs on SKJ OS EZ: app store, updates and settings
in one place, in plain language, Polish and English from day one.

Decided (Notion / Jakub):
- Hub v1 = everything in the Notion plan; later work is bug fixes and new ideas.
- It **is** the settings app (replaces the desktop's own), not a launcher.
- Its own app store replaces KDE Discover (Discover is removed from the ISO, PR #6).
- App sources: Flatpak, dnf, apt (Ubuntu base), Snap on every base.
- One entry per app; the source is picked automatically, preferring the
  developer-verified source (so Spotify → Snap).
- One update button for everything (dnf/apt/bootc + Flatpak + Snap). The hub
  handles Snap refreshes itself (`snap refresh --hold`), Fedora's yearly major
  upgrade, and on Fedora + NVIDIA it must not reboot before akmods finishes.
  **It never reboots on its own.**
- Rollback is optional (opt-in): Snapper + boot-menu rollback on Fedora,
  Timeshift on Ubuntu, built in on Bazzite; one "Undo last update" button.
- Works on every base (Fedora, Ubuntu, Bazzite) and every desktop: it detects
  what it runs on and switches mode. Shared settings (Wi-Fi, sound, Bluetooth,
  power, printers, date/time) work everywhere; look, displays, shortcuts and
  panels are per desktop.
- No built-in AI help, no built-in remote help.
- Optional safety extra: ClamGuard (needs generic defaults first).
- "Don't be scared of commands" message + red flags, in the help/safety page.

## 2. Scope split

"Everything in Notion" is several independent products. Each gets its own
spec → plan → build cycle, in this order:

| # | Project | Depends on |
|---|---|---|
| A | **Hub, phase 1**: shell, platform detection, app store, updates, update notifier — Fedora KDE | — |
| B | Hub, phase 2: settings (shared + KDE) — replaces System Settings | A |
| C | Hub, phase 3: rollback (opt-in), safety page, ClamGuard integration | A |
| D | Hub on other bases/desktops: Ubuntu (apt, Timeshift), Bazzite (bootc), GNOME etc. | A–C |
| E | Installer work (Anaconda web UI): step explanations, BitLocker screen, dual-boot slider, NVIDIA/MOK walkthrough | — |
| F | Windows companion (.exe) | E |
| G | Docs, wiki, videos | A–F |

This spec designs the hub as a whole (A–D) and details **phase 1 (A)**.
E, F and G get their own specs.

## 3. Technology

- **UI: QML + Kirigami** (`hub/skj_hub/qml/`), loaded by PySide6. QML only
  binds to the Python bridge (`ui/bridge.py`: app list models, update state)
  and never touches a backend.
- **Python 3 + PySide6 (Qt 6).** [assumption] Same stack as ClamGuard, which
  Jakub already wrote; Qt fits KDE; available on every base.
- System access through the same libraries KDE Discover uses, via PyGObject:
  - **PackageKit** (`PackageKitGlib`) for distro packages. On Fedora 44 it uses
    the dnf5 backend; on Ubuntu the apt backend, so one code path covers both.
  - **libflatpak** (`Flatpak`) for Flatpak.
  - **snapd-glib** (`Snapd`) for Snap.
  - **AppStream** (`AppStream`) for app names, icons, descriptions, screenshots.
  - Later: libnm (Wi-Fi), BlueZ, timedated/localed, UPower etc. over D-Bus.
  Verified on Jakub's PC on 2026-10-02: all typelibs present; PackageKit
  resolves packages, Flatpak lists the fedora + flathub remotes, snapd finds
  Spotify with publisher validation "verified" — all without root.
- **No privileged helper of our own in phase 1.** PackageKit, Flatpak's system
  helper and snapd all ask polkit, so the hub runs as the user and the system
  shows the normal password prompt. An own helper is added only if a later
  phase needs something no existing service offers.
- Code lives in this repo under `hub/` [assumption: monorepo, so ISO and hub
  change together and one CI shows both]. Packaged as the `skj-hub` RPM by
  `build-rpms.sh`.

## 4. Architecture

```
hub/
  skj_hub/
    app.py            # QApplication, main window, page registry
    platform.py       # what am I running on (base, desktop, immutable?)
    jobs.py           # background jobs: progress, cancel, result
    log.py            # ~/.local/state/skj-hub/hub.log
    i18n/             # Qt translations: pl, en
    catalog/
      model.py        # App, Offer (one app from one source), Source enum
      merge.py        # group offers into one App; pick the default source
      app-map.json    # known identities AppStream can't link (e.g. spotify snap)
    backends/
      base.py         # Backend interface (search, details, install, remove,
                      #   installed, updates, update)
      packagekit.py
      flatpak.py
      snap.py
      fake.py         # in-memory backend for tests and UI work
    updates/
      plan.py         # one update plan over all backends, ordering, reboot need
      rules.py        # never auto-reboot, wait for akmods, snap hold
      notifier.py     # tray/notification when updates are waiting
    ui/
      theme.py        # colours from the SKJ palette, big-button style
      pages/start.py, apps.py, app_detail.py, updates.py, help.py
  tests/
```

Units talk only through the interfaces in `backends/base.py`,
`catalog/model.py` and `jobs.py`. The UI never imports a backend directly;
it gets them from `platform.py`, so tests and screenshots run on the fake
backend.

### 4.1 Platform detection (`platform.py`)
Reads `/etc/os-release` (`ID`, `ID_LIKE`, `VARIANT_ID`), `XDG_CURRENT_DESKTOP`,
and checks for `bootc`/`rpm-ostree` (image-based). Returns a `Platform` with
`base` (fedora | ubuntu | bazzite), `desktop` (kde | gnome | …), `image_based`
(bool) and the list of available backends (a backend is available when its
service answers, e.g. snapd socket present). Phase 1 supports Fedora KDE;
on anything else the hub starts and shows only what works.

### 4.2 Catalog: one entry per app
- **Offers** come from each backend: AppStream metadata for distro packages
  (Fedora's `appstream-data`) and Flatpak remotes; snapd's store search for Snap.
- **Grouping**: offers with the same AppStream component ID are one app. Snaps
  have no AppStream ID, so they join by `app-map.json` (curated, small) and
  then by exact name match on the desktop file / snap name.
- **Default source** (Notion: prefer the developer-verified source):
  1. offers whose publisher is the app's developer: Flathub "verified",
     Snap publisher validation verified/starred;
  2. among those, or if none: Flatpak, then distro package, then Snap
     [assumption: Flatpak first for sandboxing and same version everywhere;
     distro package first for system tools, i.e. AppStream type
     `console-application`, `driver`, `firmware`, `addon`].
  The app page still lists the other sources under "Other versions" for
  people who care; beginners never have to choose.
- Already-installed apps keep the source they were installed from.
- **Browsing** (Jakub's review, 2026-10-03): with an empty search box the Apps
  page lists every desktop app, A-Z (one scrolling list), with a group
  picker in plain words (Games, Internet, Music & video, Photos & graphics,
  Office, Learning & science, Tools, Programming, System) mapped from
  freedesktop categories. The list comes from AppStream (about 3,900 apps in
  3 s on Jakub's PC). The Snap Store can't be listed in full, so snaps join
  the list only for the apps in `app-map.json`; that keeps Spotify on the
  official snap when browsing, same as in search.
  Later: order by popularity / a "Recommended" group instead of plain A-Z.

### 4.3 Jobs
Every install/remove/update runs as a `Job` on a worker thread (GI sync calls,
never on the UI thread). A job reports progress (0–100 or "busy"), a short
plain-language status ("Downloading Spotify…"), and ends with a `Result`
(ok | cancelled | failed + user message + technical details). Only one
system-changing job runs at a time per backend; the rest queue and are
visible in a small "Working on…" list.

### 4.4 Updates (`updates/`)
- **One button** builds an `UpdatePlan` from all backends: distro packages,
  Flatpaks, Snaps. The page shows a single summary ("12 updates, about 340 MB")
  with details on request.
- Order: distro packages first (they may need a restart), then Flatpak, then Snap.
- **Snap**: on first start the hub holds automatic refreshes for all snaps
  (the `snap refresh --hold` equivalent), so Snap doesn't refresh behind the
  user's back; the hub refreshes snaps as part of the plan. snapd-glib has no
  hold call (checked 2026-10-02), so this one call goes to snapd's REST API on
  `/run/snapd.socket` (polkit-authorised like the rest of snapd).
- **Restart**: if any update needs a restart (kernel, glibc, systemd, desktop),
  the hub says so and offers "Restart now" / "Later". It never restarts on its
  own. Distro updates that need a restart use PackageKit offline updates
  (applied during the next restart), like Discover did.
- **NVIDIA (Fedora)**: before offering "Restart now" after a kernel update,
  the hub waits until akmods has built the module for the new kernel
  (`kmod-nvidia-<new kernel>` installed, `akmods` service finished) and shows
  "Getting your graphics driver ready…". Lesson from 2026-09-29.
- **Fedora major upgrade** (once a year): when the next release is available
  and stable, the Updates page shows a separate card with plain-language
  explanation; it uses PackageKit's system upgrade (`upgrade_system` exists in
  PackageKit-glib and in the dnf5 backend, checked 2026-10-02; to be tested
  end to end in a VM before relying on it). Never automatic.
- **Notifier**: a small background part (autostarted, no window) checks once a
  day and on network-up, and shows a desktop notification when updates are
  waiting. It replaces Discover's notifier, which went with Discover.

### 4.5 Settings (phase 2, outline)
Shared pages built on system services (identical on every desktop): Wi-Fi and
network (NetworkManager), sound (PipeWire via WirePlumber), Bluetooth (BlueZ),
power (UPower + power-profiles-daemon), printers (CUPS), date/time and
language (timedated, localed), users (accountsservice). KDE pages: look,
displays (kscreen), shortcuts, panels — via KDE's own config/D-Bus. Once the
settings pages cover what beginners need, System Settings is hidden from the
menu on SKJ OS EZ (not removed: KDE modules still use parts of it).

Decided by Jakub (2026-10-03): hide it, and the hub's settings area says in
plain words that these are the basic settings, and that the full KDE System
Settings exist for more advanced users, with a button that opens them.

### 4.6 Rollback and safety (phase 3, outline)
Opt-in switch "Let me undo updates": Fedora → Snapper snapshots before each
update + grub-btrfs boot entries; one "Undo last update" button. Ubuntu →
Timeshift. Bazzite → its built-in rollback. Safety page: the Notion "don't be
scared of commands" text, red flags, optional ClamGuard (with generic defaults).

## 5. Beginner UX rules
- Big, obvious buttons; one main action per screen.
- Plain words: "Install", "Remove", "Update everything", never "transaction",
  "repository", "dependency". Technical terms only under "Details".
- Every step says what it's doing and why.
- Polish + English from day one (Qt translations; follows the system language).
- Errors: one sentence what happened, one sentence what to do, "Details" for
  the log. Never a raw traceback.
- Look: a real KDE app (Jakub, 2026-10-04: "make it use some library that
  actual KDE apps use"). The window is written in QML with **Kirigami**, the
  framework Discover and System Settings use, with KDE's Qt Quick style
  (`org.kde.desktop`): global drawer for navigation, page toolbar, search
  field, inline messages, prompt dialogs. Colours and icons come from the
  user's colour scheme. History: v0.1 had a custom dark Qt Widgets theme
  (Breeze's dark icons were invisible on it), then plain Qt Widgets with the
  Breeze style (worked, but still didn't look like a KDE app).
  SKJ colours appear only in the letter tile for apps without an icon.

## 6. Error handling
- Backends never raise into the UI: every call returns a `Result`; exceptions
  are caught at the backend boundary, logged with details, and mapped to a
  plain message (no network, not enough space, cancelled at password prompt,
  package conflict, service not running).
- A backend that isn't available (e.g. snapd not running) is hidden, not an
  error; the app page says "Not available on this system" for that source.
- Long jobs survive the window closing: the notifier keeps running and reports
  the result.

## 7. Testing
- **Unit tests (pytest)** for everything that isn't Qt or a system service:
  platform detection (fixture os-release files), catalog grouping and source
  picking, update plan ordering and restart rules, result/error mapping —
  all against `backends/fake.py`.
- **UI smoke tests** (pytest-qt, `QT_QPA_PLATFORM=offscreen`): every page opens
  on the fake backend, main flows (search → install → done; update all)
  complete.
- **Backend integration tests**, read-only (search, details, list installed,
  list updates) against real PackageKit/Flatpak/Snap: run locally and in the
  VM, not in CI (no system services in the CI container).
- **VM checklist** per release: install an app from each source, update
  everything, restart prompt, notifier.
- CI: a new `hub` workflow runs ruff + pytest on every PR that touches `hub/`
  (fast, minutes). The ISO workflow keeps running on every PR.

## 8. Packaging and ISO
- `packaging/skj-hub/skj-hub.spec` → `skj-hub` RPM (noarch, Requires:
  python3-pyside6, python3-gobject, PackageKit-glib, flatpak-libs, snapd-glib,
  appstream). Built by `build-rpms.sh` like the other SKJ packages.
- Added to the ISO (kiwi `skj-ez.xml`) **only after Jakub has reviewed the
  hub in a VM** — until then it is built and tested but not shipped.
- With the hub, the ISO also needs: `snapd` + `/snap` symlink (Notion: Snap on
  every base), Flathub enabled (Fedora already ships the flathub remote, seen
  on Jakub's PC), the hub pinned in the taskbar where Discover was.

## 9. Questions for Jakub: status
1. Python + PySide6 — **default in use** (not explicitly confirmed). (§3)
2. Hub code in this repo under `hub/` — **default in use** (not explicitly
   confirmed). (§3)
3. Default-source tie-break: Flatpak first for apps, distro first for system
   tools — **default in use** (not explicitly confirmed). (§4.2)
4. Name in the menu: "SKJ Hub" in both languages — **default in use** (not
   explicitly confirmed).
5. KDE System Settings in phase 2 — **decided 2026-10-03**: hide it from the
   menu; the hub's settings say they are the basic ones and point to the KDE
   settings for advanced users. (§4.5)

## 10. Known gaps after phase 1
- The hub is not pinned in the taskbar where Discover was (Plasma's default
  launchers are compiled into the task manager; needs a layout change).
- Real install / remove / update is untested until the first VM run.
- Browse order is A-Z, not by popularity.
