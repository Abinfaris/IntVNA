#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "$(uname -s)" != "Darwin" ]]; then echo 'Run on macOS';exit 1;fi
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
"$PYTHON_BIN" -m venv .build-venv
source .build-venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
if [[ ! -d vendor/nanovna-saver ]]; then
  mkdir -p vendor
  git clone --depth 1 --branch v0.7.3 https://github.com/NanoVNA-Saver/nanovna-saver.git vendor/nanovna-saver
fi
(cd vendor/nanovna-saver && python -m pip install -e . && PYTHONPATH=src python -m tools.ui_compile)
PYTHONPATH="$PWD/src:$PWD/vendor/nanovna-saver/src" python -c "import intvna; from intvna import IntVNA; print('IntVNA measurement module import OK')"
python -m PyInstaller --noconfirm --clean --onedir --windowed \
  --name IntVNA --osx-bundle-identifier com.intsensing.intvna \
  --paths "$PWD/src" --paths "$PWD/vendor/nanovna-saver/src" \
  --collect-all NanoVNASaver --collect-submodules PySide6 \
  --copy-metadata nanovnasaver src/intvna_app.py
mkdir -p releases
ditto -c -k --keepParent dist/IntVNA.app "releases/IntVNA-macOS-$(uname -m)-beta.zip"
echo "Created releases/IntVNA-macOS-$(uname -m)-beta.zip"
