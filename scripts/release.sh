#!/bin/bash
# Publish a built ISO as a GitHub pre-release. Run by
# .github/workflows/build-iso.yml after a green build of main, never for PRs.
#
#   scripts/release.sh <dir with the ISO> <empty staging dir>
#
# Needs: gh (GH_TOKEN with contents: write), GITHUB_REPOSITORY, GITHUB_SHA.
#
# GitHub rejects release files of 2 GiB or more. An ISO under 1900 MiB goes up
# as one file; a bigger one is split into 1900M parts (split -b 1900M -d) and
# the release notes say how to join them. SHA256SUMS is always attached.
# Only the newest 5 automatic pre-releases (build-YYYYMMDD-<sha>) are kept;
# older ones are deleted together with their tags.

set -Eeuo pipefail
trap 'echo "!! FAILED at line $LINENO: $BASH_COMMAND (exit $?)"' ERR

SRC_DIR="$1"
STAGE="$2"
REPO="${GITHUB_REPOSITORY:?}"
SHA="${GITHUB_SHA:?}"
KEEP=5
PART_SIZE="${PART_SIZE:-1900M}"      # env override only for testing
MAX_SINGLE=$(numfmt --from=iec "$PART_SIZE")
TAG="build-$(date -u +%Y%m%d)-${SHA:0:7}"
SERVER="${GITHUB_SERVER_URL:-https://github.com}"

step() { echo; echo "==> [$(date '+%F %T')] $*"; }

# PR descriptions and commit messages carry tool attribution lines
# ("🤖 Generated with [Claude Code](...)", "Co-Authored-By: ..."); keep them
# out of the release notes and squeeze the blank lines they leave behind.
# Only whole footer lines go: text that mentions the footer stays.
strip_attribution() {
	tr -d '\r' | sed -E \
		-e '/^[^[:alnum:]]*Generated with \[Claude Code\]\([^)]*\)[[:space:]]*$/d' \
		-e '/^Co-Authored-By:/Id' | cat -s
}

shopt -s nullglob
isos=("$SRC_DIR"/*.iso)
pkgs=("$SRC_DIR"/*.packages)
shopt -u nullglob
if [ ${#isos[@]} -ne 1 ]; then
	echo "Expected one ISO in $SRC_DIR, found ${#isos[@]}" >&2
	exit 1
fi
iso_path="${isos[0]}"
iso="$(basename "$iso_path")"
size=$(stat -c %s "$iso_path")
mkdir -p "$STAGE"

# --- files to upload ------------------------------------------------------------
step "Preparing $iso ($(numfmt --to=iec "$size"))"
files=()
if [ "$size" -lt "$MAX_SINGLE" ]; then
	echo "Under $PART_SIZE - uploading as one file"
	files+=("$iso_path")
	(cd "$SRC_DIR" && sha256sum "$iso") > "$STAGE/SHA256SUMS"
	parts=()
else
	echo "$PART_SIZE or more - splitting into $PART_SIZE parts"
	split -b "$PART_SIZE" -d "$iso_path" "$STAGE/$iso.part"
	(cd "$STAGE" && ls -1 "$iso".part*) > "$STAGE/parts.txt"
	mapfile -t parts < "$STAGE/parts.txt"
	for p in "${parts[@]}"; do files+=("$STAGE/$p"); done
	{
		(cd "$SRC_DIR" && sha256sum "$iso")
		(cd "$STAGE" && sha256sum "${parts[@]}")
	} > "$STAGE/SHA256SUMS"
fi
files+=("$STAGE/SHA256SUMS")
if [ ${#pkgs[@]} -gt 0 ]; then
	files+=("${pkgs[0]}")
fi
iso_sum=$(head -1 "$STAGE/SHA256SUMS" | cut -d' ' -f1)
cat "$STAGE/SHA256SUMS"

# --- release notes ----------------------------------------------------------------
step "Writing release notes"
pr_json=$(gh api "repos/$REPO/commits/$SHA/pulls" --jq '[.[] | select(.merged_at != null)][0] // empty')
notes="$STAGE/notes.md"
{
	echo "Automatic build of SKJ OS EZ ISO Edition (KDE Plasma), based on Fedora Linux 44."
	echo "Pre-release: untested, for testing in a VM."
	echo
	echo "Commit: $SERVER/$REPO/commit/$SHA"
	echo
	if [ -n "$pr_json" ]; then
		echo "## Changes: #$(jq -r .number <<<"$pr_json") $(jq -r .title <<<"$pr_json")"
		echo
		jq -r '.body // ""' <<<"$pr_json" | strip_attribution
	else
		echo "## Changes"
		echo
		gh api "repos/$REPO/commits/$SHA" --jq .commit.message | strip_attribution
	fi
	echo
	echo "## Download"
	echo
	if [ ${#parts[@]} -eq 0 ]; then
		echo "Download \`$iso\` and check it against \`SHA256SUMS\`:"
		echo
		echo '```sh'
		echo "sha256sum -c --ignore-missing SHA256SUMS"
		echo '```'
	else
		echo "The ISO is too big for one GitHub release file, so it comes in ${#parts[@]} parts."
		echo "Download all \`$iso.part*\` files and \`SHA256SUMS\` into one folder, then join them:"
		echo
		echo "**Linux / macOS**"
		echo
		echo '```sh'
		echo "cat ${parts[*]} > $iso"
		echo '```'
		echo
		echo "**Windows** (Command Prompt, in the download folder)"
		echo
		echo '```bat'
		echo "copy /b $(IFS=+; echo "${parts[*]}") $iso"
		echo '```'
		echo
		echo "Then check the joined ISO."
		echo
		echo "**Linux / macOS**"
		echo
		echo '```sh'
		echo "sha256sum -c --ignore-missing SHA256SUMS"
		echo '```'
		echo
		echo "**Windows**"
		echo
		echo '```bat'
		echo "certutil -hashfile $iso SHA256"
		echo '```'
	fi
	echo
	echo "Expected SHA-256 of \`$iso\`:"
	echo
	echo '```'
	echo "$iso_sum"
	echo '```'
	echo
	echo "SKJ OS EZ is based on Fedora but is not Fedora and is not endorsed by the Fedora Project."
} > "$notes"
cat "$notes"

# --- create the release -------------------------------------------------------------
# A rerun of the same commit on the same day replaces its own release.
if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
	step "Release $TAG already exists (workflow rerun) - replacing it"
	gh release delete "$TAG" --repo "$REPO" --cleanup-tag --yes
fi

# Upload into a draft and publish only when every file is there, so nobody
# sees a release with half the parts. A failed upload deletes the draft.
step "Creating draft pre-release $TAG"
gh release create "$TAG" --repo "$REPO" --target "$SHA" --draft --prerelease \
	--title "SKJ OS EZ KDE $TAG" --notes-file "$notes"
cleanup_draft() {
	echo "!! upload failed - deleting draft $TAG"
	gh release delete "$TAG" --repo "$REPO" --yes || true
}
trap cleanup_draft EXIT

for f in "${files[@]}"; do
	step "Uploading $(basename "$f") ($(numfmt --to=iec "$(stat -c %s "$f")"))"
	for attempt in 1 2 3; do
		if gh release upload "$TAG" --repo "$REPO" --clobber "$f"; then
			break
		fi
		if [ "$attempt" -eq 3 ]; then
			echo "Upload of $f failed 3 times" >&2
			exit 1
		fi
		echo "upload failed (attempt $attempt) - retrying in 30 s"
		sleep 30
	done
done

step "Publishing $TAG"
gh release edit "$TAG" --repo "$REPO" --draft=false --prerelease
trap - EXIT

# --- prune old automatic pre-releases -------------------------------------------------
step "Keeping the newest $KEEP automatic pre-releases"
old=$(gh release list --repo "$REPO" --limit 200 \
	--json tagName,isPrerelease,isDraft,createdAt \
	--jq "[.[] | select(.isPrerelease and (.isDraft | not)
		and (.tagName | test(\"^build-[0-9]{8}-[0-9a-f]{7,}\$\")))]
		| sort_by(.createdAt) | reverse | .[$KEEP:] | .[].tagName")
for t in $old; do
	echo "deleting $t"
	gh release delete "$t" --repo "$REPO" --cleanup-tag --yes
done

step "Done: $SERVER/$REPO/releases/tag/$TAG"
