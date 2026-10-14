#!/bin/sh
# Download the speech models into script/ (they are not in git: ~4 GB).
# Plain curl, so it runs in macOS Terminal as well as in Linux - the model files are the same
# on every platform. If huggingface.co is blocked where you run it, run it on your Mac instead.
#
#   sh setup/download_models.sh            # everything (~4.1 GB)
#   sh setup/download_models.sh fast       # Supertonic + Kokoro + whisper only (~1 GB, no Chatterbox)
#   sh setup/download_models.sh chatterbox # one part: supertonic | kokoro | chatterbox | whisper
#
# Already-downloaded files are skipped (re-run after an interrupted download: partial files are
# downloaded as *.part and only renamed when complete).
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
TTV="$ROOT/script/text-to-voice/models"
STT="$ROOT/script/voice-to-text/models"
HF=${HF_ENDPOINT:-https://huggingface.co}
want="$*"; [ -z "$want" ] && want="supertonic kokoro chatterbox whisper"; [ "$want" = "fast" ] && want="supertonic kokoro whisper"

get() { # url dest
  [ -s "$2" ] && { echo "  ok   $(basename "$2")"; return; }
  mkdir -p "$(dirname "$2")"; echo "  get  $(basename "$2")"
  curl -fL --retry 3 -C - -o "$2.part" "$1" && mv "$2.part" "$2"
}

for part in $want; do
  case $part in
    supertonic) echo "Supertonic 3 (0.4 GB, Open RAIL-M) - fast voices for words and sentences"
      R="$HF/Supertone/supertonic-3/resolve/main"
      for f in LICENSE config.json onnx/duration_predictor.onnx onnx/text_encoder.onnx onnx/tts.json \
               onnx/unicode_indexer.json onnx/vector_estimator.onnx onnx/vocoder.onnx \
               voice_styles/F1.json voice_styles/F2.json voice_styles/F3.json voice_styles/F4.json voice_styles/F5.json \
               voice_styles/M1.json voice_styles/M2.json voice_styles/M3.json voice_styles/M4.json voice_styles/M5.json; do
        get "$R/$f" "$TTV/supertonic-3/$f"; done ;;
    kokoro) echo "Kokoro-82M int8 (0.1 GB, Apache-2.0) - one more French voice"
      R=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
      get "$R/kokoro-v1.0.int8.onnx" "$TTV/kokoro-v1.0.int8.onnx"
      get "$R/voices-v1.0.bin" "$TTV/voices-v1.0.bin" ;;
    chatterbox) echo "Chatterbox Multilingual (3.1 GB, MIT) - the natural dialogue voices"
      R="$HF/ResembleAI/chatterbox/resolve/main"
      for f in t3_mtl23ls_v2.safetensors s3gen.pt ve.pt grapheme_mtl_merged_expanded_v1.json Cangjie5_TC.json conds.pt; do
        get "$R/$f" "$TTV/chatterbox/$f"; done ;;
    whisper) echo "whisper.cpp 'small' model (0.5 GB, MIT) - transcribes voice messages"
      get "$HF/ggerganov/whisper.cpp/resolve/main/ggml-small.bin" "$STT/ggml-small.bin" ;;
    *) echo "unknown part: $part (supertonic | kokoro | chatterbox | whisper | fast)"; exit 1 ;;
  esac
done
echo "Done. Next, in the session that makes the audio: sh script/text-to-voice/setup_engines.sh all && sh setup/build_whisper.sh"
