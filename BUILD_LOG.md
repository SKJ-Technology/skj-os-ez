# Build log (local copy)

Primary log: Notion, SKJ Project Log, "SKJ OS EZ ISO Edition". This file is
the fallback in case Notion is unreachable; entries here are synced to Notion.

## Work log
- 2026-09-29: Repo set up. Vendored Fedora's kiwi descriptions (f44). Wrote skj-release, skj-logos (+ wallpaper, Plymouth theme, fastfetch config), artwork generator, kiwi profile SKJ-EZ-KDE-Live, build-rpms.sh / build-iso.sh / vm-test.sh. RPMs build; package set resolves (2208 pkgs, no Fedora branding packages).
- 2026-10-02: Local build abandoned (SELinux, see below). Builds move to GitHub Actions: .github/workflows/build-iso.yml (privileged fedora:44 container), green builds of main published as pre-releases by scripts/release.sh (ISO split into 1900M parts if needed, newest 5 kept). build-iso.sh: runs as root in the container, safe_rm refuses to delete while anything is mounted under build/, rm uses --one-file-system.

## Errors & fixes
- 2026-09-29: `dnf5 download` stopped at a GPG key prompt for a third-party repo (Cursor) -> use `--repo=fedora --repo=updates` (build-iso.sh does the same).
- 2026-09-29: dry-run resolve said "no match for skj-release" (no repodata, createrepo_c not installed) -> ran createrepo_c unpacked in a scratch dir; build-iso.sh installs it properly.
- 2026-09-29: vm-test.sh used a wrong VBoxManage subcommand (`enrollmssignedkeys`) -> correct name is `enrollmssignatures`; fixed before use.
- 2026-10-02: build-iso.sh stopped at `kiwi-ng --version` (prints 11.0.2 but exits 1, set -e) -> `kiwi-ng --version || true`.
- 2026-10-02: kiwi bootstrap failed: every %sysusers scriptlet exited 127. SELinux (Enforcing) on the host logged 10 AVC denials -> stop building on the host, build in a container on GitHub Actions.
- 2026-10-02: grub2-common %posttrans ran os-prober in the build root and saw the host disks (/dev bind-mounted). Read-only, host /boot untouched -> build-iso.sh now refuses rm -rf while anything is mounted under build/ and uses --one-file-system.
