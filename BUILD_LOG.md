# Build log (local copy)

Primary log: Notion, SKJ Project Log, "SKJ OS EZ ISO Edition". This file is
the fallback in case Notion is unreachable; entries here are synced to Notion.

## Work log
- 2026-09-29: Repo set up. Vendored Fedora's kiwi descriptions (f44). Wrote skj-release, skj-logos (+ wallpaper, Plymouth theme, fastfetch config), artwork generator, kiwi profile SKJ-EZ-KDE-Live, build-rpms.sh / build-iso.sh / vm-test.sh. RPMs build; package set resolves (2208 pkgs, no Fedora branding packages).

## Errors & fixes
- 2026-09-29: `dnf5 download` stopped at a GPG key prompt for a third-party repo (Cursor) -> use `--repo=fedora --repo=updates` (build-iso.sh does the same).
- 2026-09-29: dry-run resolve said "no match for skj-release" (no repodata, createrepo_c not installed) -> ran createrepo_c unpacked in a scratch dir; build-iso.sh installs it properly.
- 2026-09-29: vm-test.sh used a wrong VBoxManage subcommand (`enrollmssignedkeys`) -> correct name is `enrollmssignatures`; fixed before use.
