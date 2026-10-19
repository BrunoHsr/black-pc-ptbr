"""Piloto de teste: roda o port, acompanha o log e aperta os botoes quando cada tela aparece; ao abrir o video
pedido, tira prints nos tempos indicados (segundos desde a abertura do video).

uso: python piloto.py <pasta port> <VIDEO ex. 03_N> <legendas/xx.tsv | tempos separados por virgula> <saida_dir>
"""
import os, re, subprocess, sys, time

port, movie, when, out = sys.argv[1:5]
extra = sys.argv[5:]  # argumentos a mais para o black.exe (ex.: --wav arquivo.wav)
os.makedirs(out, exist_ok=True)
log = os.path.join(out, 'run.log')
pf = os.path.join(out, 'press.txt')
open(pf, 'w').close()
if os.path.exists(log):
    os.remove(log)

if when.endswith('.tsv'):
    times = []
    for line in open(when, encoding='utf-8'):
        if line.strip() and not line.startswith('#'):
            a, b, _ = line.split('\t', 2)
            times.append(round((float(a) + float(b)) / 2, 2))
else:
    times = [float(t) for t in when.split(',')]

# (texto esperado no log, botao, espera em s antes de apertar)
steps = [("ListenForPlayer", 'start', 1.5), ("C_N_US.xmv", 'a', 2.0), ("02_N.xmv", 'a', 2.0),
         ("StartMainMenu", 'a', 4.0), ("UpdateDificulty", 'a', 3.0)]
target = "videos\\%s.xmv" % movie

proc = subprocess.Popen([os.path.join(port, 'black.exe'), '--background', '--press-file', pf, '--log', log,
                         '--screenshot', out, '--shot-every', '100000', '--timeout', str(int(150 + max(times) + 60))] + extra)


def press(line):
    with open(pf, 'a') as f:
        f.write(line + '\n')


pos, k, t0, buf = 0, 0, None, ''
deadline = time.time() + 400
pending = []
while proc.poll() is None and time.time() < deadline:
    time.sleep(0.05)
    if os.path.exists(log):
        with open(log, 'r', encoding='utf-8', errors='replace') as f:
            f.seek(pos)
            buf += f.read()
            pos = f.tell()
        lines = buf.split('\n')
        buf = lines.pop()
        for l in lines:
            if t0 is None and target.lower() in l.lower() and 'NtCreateFile' in l:
                t0 = time.time()
                pending = sorted(times)
                print('video aberto; %d prints agendados' % len(pending), flush=True)
            elif t0 is None and k < len(steps) and steps[k][0] in l:
                trig, btn, wait = steps[k]
                print('%s -> %s' % (trig, btn), flush=True)
                time.sleep(wait)
                press(btn)
                k += 1
    if t0 is not None:
        while pending and time.time() - t0 >= pending[0]:
            press('shot:t%06.2f' % pending.pop(0))
        if not pending and time.time() - t0 > max(times) + 2:
            break
proc.terminate()
time.sleep(1)
print('fim; prints em', out)
