# cafe.py <out.flac> <seed> [seconds] - synthetic café ambience: French babble from many TTS voices + cups/spoons
import sys, os, random, subprocess, numpy as np, soundfile as sf
sys.path.insert(0, os.path.expanduser("~/mnt/Languages/script")); import tts as T
out, seed = sys.argv[1], int(sys.argv[2]); dur = float(sys.argv[3]) if len(sys.argv) > 3 else 60
rnd = random.Random(seed); SR = 24000
lines = """Tu as vu le match hier soir ? | Oui, c'était incroyable, surtout la fin. | Je prends un café allongé, s'il vous plaît. | On se retrouve à quelle heure demain ? | Elle a trouvé un nouvel appartement près du canal. | Il fait vraiment froid ce matin. | Tu veux partager un dessert ? | J'ai oublié mon parapluie au bureau. | Les enfants sont partis en vacances chez leurs grands-parents. | Ce restaurant est toujours plein le samedi. | Tu as lu ce livre ? Il est génial. | Mon train a eu vingt minutes de retard. | On pourrait aller au cinéma ce week-end. | Je ne sais pas encore, je dois réfléchir. | Ils ont ouvert une boulangerie au coin de la rue. | Attends, je regarde sur mon téléphone. | C'est combien, l'addition ? | Je travaille à la maison le mercredi. | Ma sœur arrive de Lyon ce soir. | Franchement, je préfère le thé. | Tu connais un bon médecin dans le quartier ? | On a visité le musée dimanche dernier. | Il y avait beaucoup de monde au marché. | Je dois rendre ce dossier avant vendredi. | Ah bon ? Je ne savais pas ! | Ça fait longtemps qu'on ne s'est pas vus. | Tu veux un croissant ou un pain au chocolat ? | Le serveur est très sympa ici. | Nous partons en Bretagne au mois d'août. | Je cherche un cadeau pour l'anniversaire de mon père. | Il faut réserver une table pour huit personnes. | Mon chat dort toute la journée. | On prend le métro ou on marche ? | Je suis complètement d'accord avec toi. | Elle parle trois langues, c'est impressionnant. | J'ai commencé le yoga le mois dernier.""".split(" | ")
cast = [v for v in T.cast_for("fr", ("supertonic", "kokoro"))]
tmp = "/tmp/cafe_seg.wav"
def say(text, voice):
    T.synth_local(voice, text, "fr", False, tmp)
    a, sr = sf.read(tmp, dtype="float32")
    if a.ndim > 1: a = a.mean(1)
    if sr != SR:
        import scipy.signal as ss; a = ss.resample_poly(a, SR, sr).astype(np.float32)
    return a / (np.abs(a).max() + 1e-6)
N = int(dur * SR); mix = np.zeros(N + SR * 5, np.float32)
streams = 9
for s in range(streams):
    v = rnd.choice(cast); g = 10 ** (rnd.uniform(-16, -7) / 20); t = rnd.uniform(0, 2.5)
    while t < dur:
        a = say(rnd.choice(lines), v if rnd.random() < 0.8 else rnd.choice(cast))
        i = int(t * SR); mix[i:i + len(a)] += g * a[: len(mix) - i]; t += len(a) / SR + rnd.uniform(0.2, 1.5)
# cups / spoons: short inharmonic decaying partials
t = rnd.uniform(0.5, 2)
while t < dur:
    L = int(SR * rnd.uniform(0.15, 0.4)); x = np.arange(L) / SR; f0 = rnd.uniform(1800, 4200)
    tone = sum(np.sin(2 * np.pi * f0 * k * x) / (i + 1) for i, k in enumerate((1, 2.76, 5.40, 8.93)))
    c = (tone * np.exp(-x * rnd.uniform(18, 35))).astype(np.float32) * 10 ** (rnd.uniform(-24, -14) / 20)
    i = int(t * SR); mix[i:i + L] += c[: len(mix) - i]; t += rnd.uniform(1.0, 5.0)
mix = mix[:N]
f = int(SR * 0.5); mix[:f] *= np.linspace(0, 1, f); mix[-f:] *= np.linspace(1, 0, f)
sf.write("/tmp/cafe_raw.wav", mix, SR)
# push it into a room: soften highs, add a little reverb, normalise loudness
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "/tmp/cafe_raw.wav", "-af",
                "lowpass=f=5000,aecho=0.8:0.6:60|110:0.25|0.15,loudnorm=I=-28:TP=-3:LRA=11", "-ar", "24000", out], check=True)
print(out)
