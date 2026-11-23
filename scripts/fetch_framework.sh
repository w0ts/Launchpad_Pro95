#!/usr/bin/env bash
# Fetch Ableton's _Framework (decompiled) into <dest>, for running the Launchpad_Pro95 tests
# outside Live.
#
#   scripts/fetch_framework.sh <dest>
#   ABLETON_FRAMEWORK_DIR=<dest> python -m pytest tests
#
# Source: the w0ts fork of gluon/AbletonLive11_MIDIRemoteScripts, branch
# fix-decompiled-framework (Live 11.2.11 sources with decompiler bugs fixed), offered
# upstream as https://github.com/gluon/AbletonLive11_MIDIRemoteScripts/pull/19.
# Pinned to a commit. Nothing from Ableton is committed to this repository.
# Idempotent: does nothing when <dest> already holds the pinned commit.
set -euo pipefail

if [ $# -ne 1 ]; then
	echo "usage: $0 <dest>" >&2
	exit 2
fi

DEST=$1
REPO=https://github.com/w0ts/AbletonLive11_MIDIRemoteScripts
SHA=272c3401c99a9881a2d6f66b2f62632886883c07   # fix-decompiled-framework

if [ -f "$DEST/.framework-stamp" ] && [ "$(cat "$DEST/.framework-stamp")" = "$SHA" ]; then
	echo "framework in $DEST is up to date"
	exit 0
fi

WORK=$(mktemp -d "${TMPDIR:-/tmp}/lppro95-framework.XXXXXX")
trap 'rm -rf "$WORK"' EXIT

git init -q "$WORK/src"
git -C "$WORK/src" fetch -q --depth 1 "$REPO" "$SHA"
git -C "$WORK/src" -c advice.detachedHead=false checkout -q FETCH_HEAD

OUT=$WORK/out
mkdir -p "$OUT/ableton/v2"
cp -R "$WORK/src/_Framework" "$WORK/src/_Generic" "$OUT/"
cp "$WORK/src/ableton/__init__.py" "$OUT/ableton/"
cp "$WORK/src/ableton/v2/__init__.py" "$OUT/ableton/v2/"
cp -R "$WORK/src/ableton/v2/base" "$OUT/ableton/v2/"

echo "$SHA" > "$OUT/.framework-stamp"
rm -rf "$DEST"
mkdir -p "$(dirname "$DEST")"
mv "$OUT" "$DEST"
echo "framework fetched into $DEST"
