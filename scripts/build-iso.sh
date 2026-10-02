#!/bin/bash
# Build the SKJ OS EZ ISO Edition (KDE Plasma) live/install ISO with kiwi,
# Fedora's official live-ISO build tool.
#
# Normally run by GitHub Actions (.github/workflows/build-iso.yml) as root
# inside a privileged fedora:44 container. Do not run it on a desktop with
# SELinux enforcing: it blocks kiwi's %sysusers scriptlets.
#
# Manual run (root, e.g. in a fedora:44 container), after ./scripts/build-rpms.sh:
#   ./scripts/build-iso.sh 2>&1 | tee build.log
#
# Env: MIN_FREE_GB (default 40) - free space required under build/.
#
# What it does (and nothing else):
#   1. installs the build tools from the Fedora repos (kiwi, createrepo_c, ...)
#   2. makes a dnf repo out of build/repo/*.rpm           -> build/iso-repo/
#   3. runs kiwi with profile SKJ-EZ-KDE-Live             -> build/kiwi/
#   4. copies the ISO + checksum to out/ and gives them to you
# It never reboots and only deletes its own work dirs inside this project
# (build/iso-repo and build/kiwi), and refuses to even do that while anything
# is mounted under build/ (kiwi bind-mounts /dev, /proc, /sys into its root).

set -Eeuo pipefail

# Ctrl+C must stop the whole script, not just the current command.
trap 'echo; echo "!! interrupted - stopping"; exit 130' INT TERM
trap 'echo "!! FAILED at line $LINENO: $BASH_COMMAND (exit $?)"' ERR

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROFILE="SKJ-EZ-KDE-Live"
KIWI_FILE="SKJ-OS-EZ.kiwi"
RPM_DIR="$ROOT/build/repo"
ISO_REPO="$ROOT/build/iso-repo"
TARGET="$ROOT/build/kiwi"
OUT="$ROOT/out"
OWNER="${SUDO_USER:-}"
MIN_FREE_GB="${MIN_FREE_GB:-40}"

step() { echo; echo "==> [$(date '+%F %T')] $*"; }

# Delete one of our work dirs under build/. Refuses while anything is mounted
# under build/ (a crashed kiwi run can leave the host's /dev bind-mounted in
# its root), and never crosses into another filesystem.
safe_rm() {
	local dir="$1" mounts
	case "$dir" in
		"$ROOT"/build/?*) ;;
		*) echo "safe_rm: refusing to delete $dir (not under $ROOT/build/)" >&2; exit 1 ;;
	esac
	mounts=$(findmnt -rn -o TARGET | awk -v p="$ROOT/build/" 'index($0, p) == 1')
	if [ -n "$mounts" ]; then
		echo "Refusing to delete $dir - still mounted under $ROOT/build/:" >&2
		echo "$mounts" >&2
		echo "Unmount these first (umount -R), then rerun." >&2
		exit 1
	fi
	rm -rf --one-file-system "$dir"
}

if [ "$(id -u)" -ne 0 ]; then
	echo "Run this as root (in a fedora:44 container): $0 2>&1 | tee build.log" >&2
	exit 1
fi

step "SKJ OS EZ ISO build starting in $ROOT"
echo "kernel: $(uname -r)   host: $(. /etc/os-release; echo "$PRETTY_NAME")"

# --- sanity checks ------------------------------------------------------------
shopt -s nullglob
rpms=("$RPM_DIR"/*.rpm)
shopt -u nullglob
if [ ${#rpms[@]} -eq 0 ]; then
	echo "No RPMs in $RPM_DIR - run ./scripts/build-rpms.sh (as your user) first." >&2
	exit 1
fi
for p in skj-release skj-logos skj-backgrounds-kde plymouth-theme-skj skj-fastfetch-config; do
	ls "$RPM_DIR"/$p-[0-9]*.noarch.rpm >/dev/null
done

mkdir -p "$ROOT/build"
free_gb=$(df -BG --output=avail "$ROOT/build" | tail -1 | tr -dc '0-9')
echo "free space on build disk: ${free_gb} GB"
if [ "$free_gb" -lt "$MIN_FREE_GB" ]; then
	echo "Need at least $MIN_FREE_GB GB free for the build." >&2
	exit 1
fi

# --- 1. build tools -----------------------------------------------------------
step "Installing build tools (Fedora repos only)"
# --repo limits dnf to Fedora's own repos, so third-party repos on this
# machine are not touched. No system upgrade, no reboot.
dnf5 install -y --repo=fedora --repo=updates \
	kiwi-cli kiwi-systemdeps distribution-gpg-keys createrepo_c erofs-utils xorriso
kiwi-ng --version || true

# --- 2. local repo with the SKJ packages ----------------------------------------
step "Creating local repo with the SKJ packages"
safe_rm "$ISO_REPO"
mkdir -p "$ISO_REPO"
cp -v "${rpms[@]}" "$ISO_REPO"/
createrepo_c "$ISO_REPO"

# --- 3. kiwi build ------------------------------------------------------------
step "Building the ISO with kiwi (profile $PROFILE) - this takes a while"
safe_rm "$TARGET"
mkdir -p "$TARGET"
cd "$ROOT/kiwi"
kiwi-ng --type=iso --profile="$PROFILE" --kiwi-file="$KIWI_FILE" \
	--logfile "$ROOT/build/kiwi.log" \
	system build \
	--description "$ROOT/kiwi" \
	--target-dir "$TARGET" \
	--add-repo "dir://$ISO_REPO,rpm-md,skj-local,1,false,false"

# --- 4. result ----------------------------------------------------------------
step "Collecting the result"
shopt -s nullglob
isos=("$TARGET"/*.iso)
shopt -u nullglob
if [ ${#isos[@]} -ne 1 ]; then
	echo "Expected one ISO in $TARGET, found ${#isos[@]}" >&2
	ls -la "$TARGET" >&2
	exit 1
fi
mkdir -p "$OUT"
stamp=$(date +%Y%m%d-%H%M)
iso="$OUT/SKJ-OS-EZ-KDE-44-x86_64-$stamp.iso"
cp -v "${isos[0]}" "$iso"
(cd "$OUT" && sha256sum "$(basename "$iso")" > "$(basename "$iso").sha256")
cp "$TARGET"/*.packages "$OUT/SKJ-OS-EZ-KDE-44-x86_64-$stamp.packages" 2>/dev/null || true

if [ -n "$OWNER" ]; then
	chown -R "$OWNER:$(id -gn "$OWNER")" "$OUT" "$ROOT/build/kiwi.log"
fi

step "Done"
ls -lh "$OUT"
cat "$iso.sha256"
