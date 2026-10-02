# SKJ OS EZ ISO Edition (KDE Plasma)

Beginner edition of SKJ OS, based on Fedora Linux 44. This repo builds a
bootable live/install ISO with SKJ branding. The hub app is not included yet.

## Layout

| Path | What |
|---|---|
| `kiwi/` | Fedora's official kiwi image descriptions (f44, see `kiwi/UPSTREAM`) plus the SKJ files: `SKJ-OS-EZ.kiwi`, `teams/skj-ez.xml`, `components/skj-liveinstall.xml`, `grub-x86-skj.cfg.iso-template`, SKJ block at the end of `config.sh` |
| `packaging/skj-release/` | `skj-release`: os-release (`ID=skj-os-ez`, `ID_LIKE=fedora`, `VERSION_ID=44`), presets, dnf defaults, Anaconda profile. Replaces `fedora-release*` |
| `packaging/skj-logos/` | `skj-logos` (replaces `fedora-logos`), `skj-backgrounds-kde` (wallpaper), `plymouth-theme-skj` (boot splash), `skj-fastfetch-config` (`/etc/xdg/fastfetch/config.jsonc`) |
| `artwork/generate.py` | Generates all logos/wallpaper into `packaging/skj-logos/assets/` |
| `scripts/build-rpms.sh` | Builds the SKJ RPMs into `build/repo/` (no root) |
| `scripts/build-iso.sh` | Installs kiwi, builds the ISO into `out/` (root, in a fedora:44 container) |
| `scripts/release.sh` | Publishes a built ISO as a GitHub pre-release (CI only) |
| `.github/workflows/build-iso.yml` | CI: builds the ISO on every PR and push to `main`; green `main` builds become pre-releases |
| `scripts/vm-test.sh` | VirtualBox test VM (EFI + Secure Boot, 8 GB, 4 CPUs, 60 GB) |

## Build

ISOs are built by GitHub Actions (`.github/workflows/build-iso.yml`) inside a
privileged `fedora:44` container: on every pull request, every push to `main`
and on demand (Actions → Build ISO → Run workflow). Local builds on a desktop
are not supported: SELinux blocks kiwi's `%sysusers` scriptlets.

Every green build of `main` becomes a pre-release named
`build-YYYYMMDD-<short sha>` under
[Releases](https://github.com/SKJ-Technology/skj-os-ez/releases); the newest
5 are kept. An ISO of 1900 MiB or more is split into parts (GitHub's
per-file limit is 2 GiB); the release notes say how to join them and check
the SHA-256.

Test a downloaded ISO in VirtualBox:

```bash
./scripts/vm-test.sh create && ./scripts/vm-test.sh start
```

To regenerate the artwork: `pip install fonttools` (e.g. in a venv) and run
`python3 artwork/generate.py` (needs ImageMagick and the Comfortaa font).

SKJ OS EZ is based on Fedora but is not Fedora and is not endorsed by the
Fedora Project.
