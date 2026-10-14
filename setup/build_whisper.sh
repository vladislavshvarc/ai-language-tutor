#!/bin/sh
# Build whisper.cpp's whisper-cli for THIS machine (the Claude desktop workspace VM is Linux; a Mac
# build won't run there and vice versa). Needs git, a C/C++ compiler and cmake (installed with pip if
# missing). The source is built outside the languages folder; only the binary is copied in.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
DEST="$ROOT/script/voice-to-text/whisper.cpp/build/bin"
B=${WHISPER_BUILD_DIR:-$HOME/wbuild}
command -v cmake >/dev/null 2>&1 || { pip install --user -q cmake && PATH="$HOME/.local/bin:$PATH"; }
[ -d "$B/whisper.cpp" ] || git clone --depth 1 https://github.com/ggml-org/whisper.cpp "$B/whisper.cpp"
cd "$B/whisper.cpp"
cmake -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DGGML_NATIVE=OFF -DWHISPER_BUILD_TESTS=OFF
cmake --build build -j4 --target whisper-cli
mkdir -p "$DEST" && cp build/bin/whisper-cli "$DEST/"
echo "Built: $DEST/whisper-cli  (check: python3 $ROOT/script/stt.py --check)"
