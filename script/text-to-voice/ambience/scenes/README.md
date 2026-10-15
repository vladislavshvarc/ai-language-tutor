# Scene maps

One file per place. `ambience.py` / `tts.py --ambience <theme>` read them, so a lesson only names the
place and every detail comes from here. Edit a map to change how a place sounds; add a file to add a place.

| key | meaning |
|---|---|
| theme | the scene name (= file name) |
| leitmotif | folder with the base recordings (looped, crossfaded, real stereo) |
| loudness_db | how much louder than the level's SNR the base is (quiet or rumbling places need more) |
| highpass_hz | cut hum below this (office ventilation sounded like a metro) |
| room | `[rt60 s, wet]` reverb shared by all voices, or "outdoor" |
| layers | continuous sounds under the whole dialogue: `{"sound", "db"}` (rail clatter in a train) |
| sounds | short details: `{"sound": folder in _events/, "every": seconds - how often on average (also its share), "db": vs the base, "max_seconds", "signature": true - comes in every recording, early}` |
| max_per_minute | at most this many details start per minute |
| calm | `[min, max]` seconds of only the base after each detail (sometimes twice as long) |

Details never overlap and never repeat back to back; a detail that falls on a line is 5 dB quieter.
Sounds available: `ls ../_events` (credits in `../README.md`; `make_events.py` makes the whistle and
rail clatter, which no free dataset has).
