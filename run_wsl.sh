#!/usr/bin/env bash
set -euo pipefail
task_project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
task_python="${HOME}/physicalai-genesis-final/.venv/bin/python"
if [[ ! -x "${task_python}" ]]; then
  echo "Genesis environment not found. See README.md for setup." >&2
  exit 1
fi
export LD_LIBRARY_PATH="/usr/lib/wsl/lib:${LD_LIBRARY_PATH:-}"
cd -- "${task_project_dir}"
exec "${task_python}" run_demo.py "$@"
