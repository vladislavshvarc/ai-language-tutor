#!/bin/sh
# Install the speech engines ONCE, into this folder (script/.env/), not into the session's home:
# the Claude workspace starts with an empty home every session, but the languages folder is kept,
# so after the first run every session (and every git pull) just uses what is here.
#
#   sh script/text-to-voice/setup_engines.sh        # fast engines: Supertonic, Kokoro (+ scipy)
#   sh script/text-to-voice/setup_engines.sh all    # + Chatterbox (dialogues)
#
# Already installed -> prints "ready" and exits in under a second, so it is safe to run every session.
# Packages come from wheels/<name>/ when that offline copy exists, otherwise from PyPI (pinned versions
# for Chatterbox in requirements/). An install cut short by the shell's time limit is resumed by
# running the same command again. Models are downloaded separately (setup/download_models.sh).
D=$(cd "$(dirname "$0")" && pwd)
E=$(dirname "$D")/.env
PY=${PYTHON:-python3}
mkdir -p "$E"
TAG=$($PY -c 'import sys,platform;print("py%d.%d-%s"%(sys.version_info[0],sys.version_info[1],platform.machine()))')
want="fast"; [ "$*" = "all" ] && want="fast chatterbox"; [ -n "$*" ] && [ "$*" != "all" ] && want="$*"

ready() { for d in "$E/$1"-*; do [ -f "$d/.ok" ] && [ "$(cat "$d/.ok")" = "$TAG" ] && { echo "$d"; return 0; }; done; return 1; }
workdir() {  # an unfinished install for this python, or a new folder
  for d in "$E/$1"-*; do [ -d "$d" ] && [ ! -f "$d/.ok" ] && [ "$(cat "$d/.tag" 2>/dev/null)" = "$TAG" ] && { echo "$d"; return; }; done
  n=1; while [ -e "$E/$1-$n" ]; do n=$((n+1)); done; mkdir -p "$E/$1-$n"; echo "$TAG" > "$E/$1-$n/.tag"; echo "$E/$1-$n"; }
src() { [ -d "$D/wheels/$1" ] && echo "--no-index --find-links $D/wheels/$1"; }
step() {  # dir name args... : run once, remember it
  [ -f "$1/.$2" ] && return 0; d=$1; s=$2; shift 2
  $PY -m pip install -q --disable-pip-version-check --target "$d" "$@" > "$d/.log" 2>&1 || { grep -v "already exists" "$d/.log" | tail -3; return 1; }
  touch "$d/.$s"; }

for e in $want; do
  if r=$(ready "$e"); then echo "$e: ready ($r)"; continue; fi
  T=$(workdir "$e"); echo "$e: installing into $T ..."
  case $e in
    fast)
      step "$T" s1 $(src fast) supertonic kokoro-onnx soundfile scipy || { echo "$e: FAILED"; continue; } ;;
    chatterbox)
      [ -s "$D/models/chatterbox/t3_mtl23ls_v2.safetensors" ] || echo "$e: model files missing - run setup/download_models.sh chatterbox"
      Q=$D/requirements
      step "$T" s1 $(src chatterbox) --no-deps torch==2.6.0 &&
      grep -v '^torch==' "$Q/chatterbox.txt" > "$T/.rest.txt" &&
      step "$T" s2 $(src chatterbox) --no-deps -r "$T/.rest.txt" &&
      step "$T" s3 $(src chatterbox) --no-deps -r "$Q/chatterbox-nodeps.txt" || { echo "$e: FAILED"; continue; } ;;
    *) echo "unknown engine: $e (fast, chatterbox)"; continue ;;
  esac
  probe="import supertonic, kokoro_onnx, soundfile, scipy.signal"; [ "$e" = chatterbox ] && probe="import torch, chatterbox.mtl_tts"
  if PYTHONPATH="$T" $PY -c "$probe" >/dev/null 2>&1; then echo "$TAG" > "$T/.ok"; echo "$e: ready ($T)"; else echo "$e: installed but the import test failed - run again"; fi
done
