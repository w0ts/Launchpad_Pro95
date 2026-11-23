#!/usr/bin/env bash
# Build the release zip: <outdir>/Launchpad_Pro95.zip, with one top folder Launchpad_Pro95/ holding only what
# Live needs (the script's .py files at the repository root, LICENSE, README.md, CHANGELOG.md).
#
#   scripts/build_release.sh <version> <outdir>
#
# Only files tracked by git are packed (no __pycache__, .DS_Store or local leftovers). The zip is deterministic:
# sorted entries, fixed timestamps and permissions, so the same commit always gives the same bytes.
# Used by .github/workflows/release.yml.
set -euo pipefail

NAME="Launchpad_Pro95"
EXTRA_FILES=(LICENSE README.md CHANGELOG.md)

if [ $# -ne 2 ]; then
	echo "usage: $0 <version> <outdir>" >&2
	exit 2
fi
VERSION="$1"
OUTDIR="$2"
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([-.+][0-9A-Za-z.-]+)?$ ]]; then
	echo "error: version '$VERSION' is not like 1.2.3" >&2
	exit 2
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# The script's modules: tracked *.py files directly at the repository root (not tests/, scripts/, site/).
FILES=()
while IFS= read -r f; do
	FILES+=("$f")
done < <(git ls-files -- '*.py' | grep -v '/' | LC_ALL=C sort)
if [ ${#FILES[@]} -eq 0 ] || [ ! -f __init__.py ]; then
	echo "error: no script files found at $REPO_ROOT" >&2
	exit 1
fi
for f in "${EXTRA_FILES[@]}"; do
	if [ ! -f "$f" ]; then
		echo "error: $f is missing" >&2
		exit 1
	fi
	FILES+=("$f")
done

mkdir -p "$OUTDIR"
ZIP="$(cd "$OUTDIR" && pwd)/$NAME.zip"
rm -f "$ZIP"

python3 - "$ZIP" "$NAME" "${FILES[@]}" <<'PY'
import sys
import zipfile

zip_path, top, *files = sys.argv[1:]
stamp = (2000, 1, 1, 0, 0, 0)  # fixed: the same sources always give the same zip


def entry(name, mode):
    info = zipfile.ZipInfo(name, date_time=stamp)
    info.create_system = 3  # unix, so the permissions below are kept
    info.external_attr = mode << 16
    return info


with zipfile.ZipFile(zip_path, "w") as zf:
    dir_info = entry(top + "/", 0o40755)
    dir_info.external_attr |= 0x10  # MS-DOS directory flag
    zf.writestr(dir_info, b"")
    for name in sorted(files):
        with open(name, "rb") as fh:
            data = fh.read()
        info = entry(f"{top}/{name}", 0o100644)
        info.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(info, data, compresslevel=9)
PY

echo "built $ZIP ($NAME $VERSION, ${#FILES[@]} files)"
