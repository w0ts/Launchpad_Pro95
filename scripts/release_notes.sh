#!/usr/bin/env bash
# Print the CHANGELOG.md section of one release (without its heading), for the GitHub release notes.
#
#   scripts/release_notes.sh <version>
#
# The section starts at "## [<version>]" (optionally followed by " - <date>") and ends before the next "## "
# heading. Fails when the section is missing or empty. Used by .github/workflows/release.yml.
set -euo pipefail

if [ $# -ne 1 ] || [ -z "$1" ]; then
	echo "usage: $0 <version>" >&2
	exit 2
fi
VERSION="$1"
CHANGELOG="$(cd "$(dirname "$0")/.." && pwd)/CHANGELOG.md"

if [ ! -f "$CHANGELOG" ]; then
	echo "error: $CHANGELOG not found" >&2
	exit 1
fi

NOTES="$(awk -v heading="## [$VERSION]" '
	index($0, "## ") == 1 {
		if (found) exit
		rest = substr($0, length(heading) + 1)
		if (substr($0, 1, length(heading)) == heading && (rest == "" || rest ~ /^ - /)) { found = 1; next }
	}
	found { print }
' "$CHANGELOG")"

# Drop blank lines at both ends.
NOTES="$(printf '%s\n' "$NOTES" | sed -e '/./,$!d' | awk '{ lines[NR] = $0 } /./ { last = NR } END { for (i = 1; i <= last; i++) print lines[i] }')"

if [ -z "$NOTES" ]; then
	echo "error: CHANGELOG.md has no section '## [$VERSION]' (or it is empty)." >&2
	echo "Rename '## [Unreleased]' to '## [$VERSION] - $(date +%Y-%m-%d)' and commit before tagging." >&2
	exit 1
fi
printf '%s\n' "$NOTES"
