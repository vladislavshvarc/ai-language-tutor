#!/bin/sh
# Install the text-to-speech engines for this session (the Claude workspace VM starts empty every session).
#   sh script/text-to-voice/setup_engines.sh            # fast engines: Supertonic, Kokoro (from PyPI)
#   sh script/text-to-voice/setup_engines.sh all        # + Chatterbox in its own virtual env
# Chatterbox needs its own library versions, so it gets a virtual env in $HOME/.venvs/chatterbox
# (outside the languages folder). Its packages come from wheels/chatterbox/ when that folder exists
# (an offline copy, Linux aarch64 / Python 3.10), otherwise from PyPI with the pinned versions in
# requirements/. The models themselves are downloaded once with setup/download_models.sh.
D=$(cd "$(dirname "$0")" && pwd)
want="$*"; [ "$want" = "all" ] && want="chatterbox"
pip install --user -q supertonic kokoro-onnx soundfile && echo "fast engines: ok"
for e in $want; do
  case $e in
    chatterbox)
      V=$HOME/.venvs/$e; W=$D/wheels/$e; Q=$D/requirements
      if [ -x "$V/bin/python" ] && "$V/bin/python" -c "import torch, chatterbox" 2>/dev/null; then echo "$e: already set up"; continue; fi
      [ -s "$D/models/chatterbox/t3_mtl23ls_v2.safetensors" ] || echo "$e: model files missing - run setup/download_models.sh chatterbox first"
      python3 -m venv "$V" || { echo "$e: FAILED (python3 -m venv)"; continue; }
      if [ -d "$W" ]; then SRC="--no-index --find-links $W"; else SRC=""; fi
      "$V/bin/pip" install -q $SRC --upgrade pip setuptools wheel &&
      "$V/bin/pip" install -q $SRC -r "$Q/$e.txt" &&
      "$V/bin/pip" install -q $SRC --no-deps -r "$Q/$e-nodeps.txt" &&
      echo "$e: ok ($V)" || echo "$e: FAILED" ;;
    *) echo "unknown engine: $e (available: chatterbox)" ;;
  esac
done
