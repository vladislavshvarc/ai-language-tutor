# Background sounds for listening exercises

Used by `../../ambience.py` (and `tts.py --ambience <scene>`). Each scene folder holds ~60 s recordings that are looped and crossfaded under a dialogue; `_events/` holds short sounds dropped in at random moments.

| Scene | Recordings | Source |
|---|---|---|
| metro, metro_station, bus, tram, airport, street (pedestrian), traffic, park, square, mall | 3 per scene, mostly recorded in **Paris** (others: Helsinki, London, Barcelona...) | TUT Urban Acoustic Scenes 2018, development set (Tampere University; Mesaros, Heittola, Virtanen). Free for non-commercial / research use. Mirror used: huggingface.co/datasets/wetdog/TUT-urban-acoustic-scenes-2018-development-16bit |
| most scenes (cafe, restaurant, train_station, office, kitchen, river, car + extra metro, bus, park, square, traffic) | DEMAND noise database (Thiemann, Ito, Vincent 2013), recorded in France; 2 × 75 s per environment, channel 1 | CC BY-SA 3.0 - zenodo.org/records/1227121 |
| cafe (also) | 3 synthetic beds: unintelligible French chatter from 9 overlapping TTS voices + cups and spoons (`make_cafe.py`) | made here; the dataset has no café scene |
| _events/birds, bells, laughing, pouring, car_horn, footsteps | 40 short clips each | ESC-50 (Karol J. Piczak), clips from freesound.org, CC BY-NC 3.0; per-clip sources in `_events/sources.json` |

Personal study only - don't publish lessons that contain these recordings commercially.

## Freesound recordings (75 s from the middle of each preview; credit the authors if you share lessons)

| Scene | Recording | Author | Licence |
|---|---|---|---|
| airplane | [Airplane cabin ambience / atmosphere Airbus A330-300](https://freesound.org/people/FillSoko/sounds/456092/) | FillSoko | CC0 |
| airport | [airport Munich terminal busy activity movement +kid start.flac](https://freesound.org/people/kyles/sounds/404963/) | kyles | CC0 |
| airport | [airport Dorval calm waiting area at gate carpeted low ceiling +baby.flac](https://freesound.org/people/kyles/sounds/450686/) | kyles | CC0 |
| beach | [Beach - Waves & People](https://freesound.org/people/Liljendal/sounds/442641/) | Liljendal | CC0 |
| beach | [PorthcurnoBeach6.wav](https://freesound.org/people/innov8ting/sounds/439682/) | innov8ting | CC BY 4.0 |
| bus | [Bus Interior ; music, traffic, doors open and close.wav](https://freesound.org/people/The_Runner_01/sounds/580637/) | The_Runner_01 | CC0 |
| cafe | [Café parisien ambiance Paris.wav](https://freesound.org/people/beman87/sounds/162853/) | beman87 | CC BY 3.0 |
| cafe | [Small Restaurant atmosphere.wav](https://freesound.org/people/Berwitz/sounds/263584/) | Berwitz | CC0 |
| cafe | [Ambient sound inside cafe bar.aif](https://freesound.org/people/4team/sounds/214995/) | 4team | CC0 |
| cafe | [MS STEREO Coffee Shop, 6 People, low chatter, refrigerator, barista movement 1.WAV](https://freesound.org/people/AwenAudio/sounds/403065/) | AwenAudio | CC0 |
| hotel | [Hotel lobby - large open plan.wav](https://freesound.org/people/soundmary/sounds/117618/) | soundmary | CC0 |
| market | [market square 006 200513_0176.wav](https://freesound.org/people/klankbeeld/sounds/543445/) | klankbeeld | CC BY 4.0 |
| market | [Street_market_1.aif](https://freesound.org/people/susiq12/sounds/333652/) | susiq12 | CC BY 3.0 |
| metro | [metro, Warszawa, 2017, Centrum station ambience, trains Inspiro and 81 (Russian) entering and taking off, passengers, doors and signals, Poland.wav](https://freesound.org/people/be_a_hero_not_a_patriot/sounds/430982/) | be_a_hero_not_a_patriot | CC0 |
| metro | [Inside NYC Subway Train 1.WAV](https://freesound.org/people/georgisound/sounds/466174/) | georgisound | CC0 |
| metro_station | [metro, Warszawa, 2017, Centrum station ambience, no trains, many people, kids, Poland.wav](https://freesound.org/people/be_a_hero_not_a_patriot/sounds/430984/) | be_a_hero_not_a_patriot | CC0 |
| metro_station | [On_subway_station.wav](https://freesound.org/people/cornodrig/sounds/77362/) | cornodrig | CC BY 4.0 |
| park | [When the city park wakes up.wav](https://freesound.org/people/dibko/sounds/625628/) | dibko | CC BY 4.0 |
| park | [City Park - All sounds of the park.wav](https://freesound.org/people/dibko/sounds/624123/) | dibko | CC BY 4.0 |
| park | [20250504 - 02 - H4n - Maribor - City park with fountain](https://freesound.org/people/dibko/sounds/803614/) | dibko | CC BY 4.0 |
| park | [church-bell city-park Zuiderpark s-Hertogenbosch Netherlands 0901 am 250729_1184](https://freesound.org/people/klankbeeld/sounds/850139/) | klankbeeld | CC BY 4.0 |
| rain | [city far thunder rain wind traffiic 506 pm 250913_0014](https://freesound.org/people/klankbeeld/sounds/826578/) | klankbeeld | CC BY 4.0 |
| restaurant | [ambience - restaurant.WAV](https://freesound.org/people/soundtracvkradio/sounds/394678/) | soundtracvkradio | CC0 |
| restaurant | [Restaurant ambience, Clachan Inn, Dryden, Scotland.  August 27, 2022.  2040 hours.](https://freesound.org/people/Robert.Crosley/sounds/730021/) | Robert.Crosley | CC BY 4.0 |
| shop | [Inside Bakery, Shop Ambience, Day, London, 2OA - Spatial Audio](https://freesound.org/people/VizAion/sounds/802509/) | VizAion | CC0 |
| square | [Leipzig market square old town hall bell sound effect](https://freesound.org/people/Garuda1982/sounds/565600/) | Garuda1982 | CC BY 4.0 |
| street | [HOW A FRENCH CITY SOUNDS V2](https://freesound.org/people/FreeToUseSounds/sounds/394331/) | FreeToUseSounds | CC BY 3.0 |
| street | [Rue Rivoli Paris 2.wav](https://freesound.org/people/bruno.auzet/sounds/527750/) | bruno.auzet | CC0 |
| street | [traffic medium busy street boulevard Jean Talon heavy trucks XY Montreal, Canada.flac](https://freesound.org/people/kyles/sounds/452523/) | kyles | CC0 |
| supermarket | [Grocery Store Ambience Checkout Line](https://freesound.org/people/deleted_user_7146007/sounds/383718/) | deleted_user_7146007 | CC0 |
| traffic | [City parking lot ambience with cars passing by, restaurant hum, bird singing, wind in foliage, man voice and whistle](https://freesound.org/people/felix.blume/sounds/690473/) | felix.blume | CC0 |
| train | [train at station interior.wav](https://freesound.org/people/theplax/sounds/613873/) | theplax | CC BY 4.0 |
| train | [Inside a train in Buenos Aires (regional train inside the city)](https://freesound.org/people/felix.blume/sounds/165606/) | felix.blume | CC0 |
| train_station | [Train Passing by in the Train Station](https://freesound.org/people/bassimat/sounds/833570/) | bassimat | CC0 |
| train_station | [Railway station Pragersko - Freight train.wav](https://freesound.org/people/dibko/sounds/631994/) | dibko | CC BY 4.0 |
| tram | [Tram Train Entering and Interior Ambience.wav](https://freesound.org/people/The_Runner_01/sounds/580641/) | The_Runner_01 | CC0 |

Recordings are cut from Freesound's 128 kbps previews (the API key in `script/.freesound_api_key` is only used to search and fetch previews). Every bed was checked with whisper: beds where clear speech could be followed were dropped.

Not used yet: BBC Sound Effects (downloads work, but its search service `sound-effects-api.bbcrewind.co.uk` is not in the allowed domains), Internet Archive (domain not reachable), Stable Audio Open Small (needs a Hugging Face account/token).

Add a scene: put mono recordings (OGG/FLAC/WAV, 30-120 s, no clear speech in the learner's language) into a new folder and add it to `SCENES` in `ambience.py`.
