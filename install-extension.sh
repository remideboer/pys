#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if command -v python >/dev/null 2>&1; then
  python -m transpiler install extension "$@"
elif command -v python3 >/dev/null 2>&1; then
  python3 -m transpiler install extension "$@"
else
  echo "python / python3 not found on PATH" >&2
  exit 1
fi
