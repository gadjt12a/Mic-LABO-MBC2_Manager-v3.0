#!/usr/bin/env bash
# Build the Mac package zip from a staging folder.
#
#   ./mac/make-mac-zip.sh --stage <dir> --zip <file> [--exec-pattern '*.command']
#
# ── Why this is three lines of zip on Linux and 80 of .NET on Windows ────────
#
# make-mac-zip.ps1 exists because of two Windows-only defects:
#
#   1. PowerShell 5.1's Compress-Archive writes BACKSLASH path separators into
#      the zip. The spec (APPNOTE 4.4.17.1) requires forward slashes, and macOS
#      may extract such a tree as flat files literally named
#      "MBC2Dashboard\app\server.py" - leaving the .command unable to find
#      app/server.py. The shipped v4.0.1 Mac zip had this.
#   2. bsdtar writes forward slashes correctly but PADS the archive to a
#      10240-byte block boundary, leaving trailing zeros after the End of
#      Central Directory record, which strict readers reject.
#
# Neither applies to Info-ZIP's `zip`: it writes forward slashes, does not pad,
# and stores the Unix mode in the external attributes by itself, so the
# launcher arrives executable without any of the .NET entry-building the
# PowerShell version has to do.
#
# ── But the SELF-CHECK is kept, and that is the point ────────────────────────
#
# The valuable half of the original is not the zip building, it is reading the
# archive back and failing the build rather than someone's Mac. "zip does the
# right thing" is exactly the sort of assumption that was wrong on Windows for
# several releases, so it is verified here too, by a reader that does not share
# any code with the writer.
#
# Linux counterpart of make-mac-zip.ps1, added 2026-10-17.
set -uo pipefail

STAGE=''
ZIP_PATH=''
EXEC_PATTERN='*.command'

usage() { sed -n '2,4p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

while [ $# -gt 0 ]; do
    case "$1" in
        --stage|-StageDir)        STAGE="${2:-}"; shift 2 ;;
        --zip|-ZipPath)           ZIP_PATH="${2:-}"; shift 2 ;;
        --exec-pattern|-ExecPattern) EXEC_PATTERN="${2:-}"; shift 2 ;;
        -h|--help)                usage 0 ;;
        *) printf 'Unknown option: %s\n' "$1" >&2; usage 1 ;;
    esac
done

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

[ -n "$STAGE" ]    || die "--stage is required"
[ -n "$ZIP_PATH" ] || die "--zip is required"
[ -d "$STAGE" ]    || die "staging directory does not exist: $STAGE"
command -v zip >/dev/null 2>&1 || die "zip not found. sudo dnf install zip"

STAGE=$(cd "$STAGE" && pwd)

# An absolute path before the cd below, or the zip lands inside the staging
# tree -- and then the archive contains itself, which is only noticed later.
case "$ZIP_PATH" in
    /*) ;;
    *) ZIP_PATH="$(pwd)/$ZIP_PATH" ;;
esac
mkdir -p "$(dirname "$ZIP_PATH")"
rm -f "$ZIP_PATH"

# ── Set the execute bits in the staging tree, not in the archive ─────────────
# zip stores whatever mode the file has, so the mode is set here and the
# archive follows. 755 on the launcher, 644 on everything else: a staging tree
# copied out of a Windows checkout can arrive with everything 777, and a Mac
# package where every .py is executable is untidy at best.
find "$STAGE" -type f -exec chmod 644 {} +
# -print to confirm something matched; the self-check below would catch it
# anyway, but the message is clearer here.
matched=$(find "$STAGE" -type f -name "$EXEC_PATTERN" -print -exec chmod 755 {} + | wc -l)
[ "$matched" -gt 0 ] || die "no file matching $EXEC_PATTERN in $STAGE -- the launcher would ship non-executable"

# ── Build ────────────────────────────────────────────────────────────────────
# -r recurse, -q quiet, -X drop the extra platform attributes that would
# otherwise carry a Windows-ish layer alongside the Unix mode.
# cd into the stage so paths are relative to it rather than absolute.
( cd "$STAGE" && zip -r -q -X "$ZIP_PATH" . ) || die "zip failed"

# ── Verify by reading it back ────────────────────────────────────────────────
# python's zipfile, which shares no code with Info-ZIP. A build that silently
# produces an unusable Mac zip is the failure this script exists to prevent.
python3 - "$ZIP_PATH" "$EXEC_PATTERN" <<'PYEOF'
import fnmatch
import sys
import zipfile

path, pattern = sys.argv[1], sys.argv[2]
MODE_EXEC = 0o100755
MODE_FILE = 0o100644

with zipfile.ZipFile(path) as z:
    entries = z.infolist()
    bad = [e.filename for e in entries if '\\' in e.filename]
    execs = [e for e in entries
             if fnmatch.fnmatch(e.filename.rsplit('/', 1)[-1], pattern)]

    if not entries:
        print('  ZIP CHECK FAILED - archive is empty')
        sys.exit(1)
    if bad:
        print(f'  ZIP CHECK FAILED - {len(bad)} entries use backslashes')
        for b in bad[:5]:
            print(f'    {b}')
        sys.exit(1)
    if not execs:
        print(f'  ZIP CHECK FAILED - no {pattern} entry found')
        sys.exit(1)

    for e in execs:
        mode = e.external_attr >> 16
        if mode != MODE_EXEC:
            print(f'  ZIP CHECK FAILED - {e.filename} is mode {mode:o}, want {MODE_EXEC:o}')
            sys.exit(1)

    # The original did not check this, and it is the same class of defect: a
    # .command with CRLF endings fails on macOS with a "bad interpreter"
    # message that names the shell rather than the line endings.
    for e in execs:
        if b'\r\n' in z.read(e.filename):
            print(f'  ZIP CHECK FAILED - {e.filename} has CRLF line endings')
            sys.exit(1)

    # Trailing bytes after the End of Central Directory record - the bsdtar
    # padding defect from the header. Info-ZIP does not do it; checked anyway,
    # because that is the point of a self-check.
    with open(path, 'rb') as fh:
        blob = fh.read()
    eocd = blob.rfind(b'PK\x05\x06')
    if eocd == -1:
        print('  ZIP CHECK FAILED - no End of Central Directory record')
        sys.exit(1)
    comment_len = int.from_bytes(blob[eocd + 20:eocd + 22], 'little')
    expected_end = eocd + 22 + comment_len
    if expected_end != len(blob):
        print(f'  ZIP CHECK FAILED - {len(blob) - expected_end} trailing bytes after EOCD')
        sys.exit(1)

    print(f'  Zip check OK - {len(entries)} entries, forward slashes, '
          f'{len(execs)} executable, no padding')
PYEOF
rc=$?
[ "$rc" -eq 0 ] || exit "$rc"
exit 0
