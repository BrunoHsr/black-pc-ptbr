"""Mede a defasagem video x audio de uma execucao do piloto (prints + --wav).
uso: python sincronia.py <video.xmv> <faixa.wav> <pasta prints> <audio gravado.wav> <VIDEO ex. 03_N>"""
import numpy as np, re, wave, sys, os, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xmv
from PIL import Image
vid, track, shots, rec, movie = sys.argv[1:6]
x = xmv.read(vid); fr = [f for p in x['packets'] for f in p.frames]
nonskip = [i for i, f in enumerate(fr) if len(f.data) > 8 or i == 0]
raw = subprocess.run(['ffmpeg', '-v', 'quiet', '-i', vid, '-vf', 'setpts=N,scale=160:120', '-fps_mode', 'passthrough',
                      '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True).stdout
a = np.frombuffer(raw, np.uint8).reshape(-1, 120, 160).astype(np.float32)
idx = nonskip if len(a) == len(nonskip) else list(range(len(a)))
print('quadros decodificados', len(a), 'nao-pulados', len(nonskip), 'total', len(fr))
log = open(os.path.join(shots, 'run.log'), encoding='utf-8', errors='replace').read()
open_t = float(re.search(r'^\s*([\d.]+) .*videos.%s.xmv' % movie, log, re.M | re.I).group(1))
saved = {m.group(2): float(m.group(1)) for m in re.finditer(r'^\s*([\d.]+) .*screenshot .*?(t[\d.]+)\.png: saved', log, re.M)}
end_t = float(re.findall(r'^\s*([\d.]+) ', log, re.M)[-1])
w = wave.open(rec); r = w.getframerate()
wav = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, w.getnchannels()).mean(1)
t5 = wave.open(track); tr = np.frombuffer(t5.readframes(t5.getnframes()), np.int16).reshape(-1, t5.getnchannels()).mean(1)
def env(sig, rate):
    n = int(rate / 100); m = len(sig) // n
    return np.abs(sig[:m * n]).reshape(m, n).mean(1)
ew, et = env(wav, r), env(tr, t5.getframerate())
ewn = (ew - ew.mean()) / (ew.std() + 1e-9)
def locate(tt, span=6):
    seg = et[int(tt * 100):int((tt + span) * 100)]
    seg = (seg - seg.mean()) / (seg.std() + 1e-9)
    return np.correlate(ewn, seg, 'valid').argmax() / 100.0
anchors = [(tt, locate(tt)) for tt in np.arange(10, len(et) / 100 - 8, 10)]
print('faixa->wav (tempo na faixa, deslocamento):', [(round(tt), round(wt - tt, 2)) for tt, wt in anchors])
W0 = np.median([wt - tt for tt, wt in anchors])
c = end_t - len(wav) / r
print('faixa comeca no log em ~%.2f (video aberto em %.2f)' % (W0 + c, open_t))
print('print  t_video_aberto  pos_video  pos_audio  video-audio')
for name, L in sorted(saved.items(), key=lambda kv: kv[1]):
    s = np.asarray(Image.open(os.path.join(shots, name + '.png')).convert('L').resize((160, 120))).astype(np.float32)
    d = ((a - s) ** 2).mean((1, 2)); k = int(d.argmin())
    V = idx[k] / 30.0; A = L - (W0 + c)
    print('%s  %6.2f  %6.2f  %6.2f  %+.2f' % (name, L - open_t, V, A, V - A))
