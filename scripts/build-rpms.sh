#!/bin/bash
# Build the SKJ branding RPMs (no root needed).
# Output: build/repo/*.rpm  (turned into a dnf repo by build-iso.sh)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOP="$ROOT/build/rpmbuild"
REPO="$ROOT/build/repo"

rm -rf "$TOP" "$REPO"
mkdir -p "$TOP" "$REPO"

# package name -> source directory
declare -A SRC=(
	[skj-release]="$ROOT/packaging/skj-release/src"
	[skj-logos]="$ROOT/packaging/skj-logos"
	[skj-hub]="$ROOT/hub"
)

for pkg in skj-release skj-logos skj-hub; do
	echo "==> building $pkg"
	rpmbuild -bb \
		--define "_topdir $TOP" \
		--define "_sourcedir ${SRC[$pkg]}" \
		"$ROOT/packaging/$pkg/$pkg.spec"
done

find "$TOP/RPMS" -name '*.rpm' -exec cp -t "$REPO" {} +
echo "==> RPMs in $REPO:"
ls -1 "$REPO"
