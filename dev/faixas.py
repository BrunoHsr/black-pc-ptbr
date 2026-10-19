"""Empilha a faixa inferior (legenda) de cada print: python faixas.py <pasta> <saida.png> [frac_inicio=0.84]"""
import sys, glob, os
from PIL import Image, ImageDraw
files = sorted(f for f in glob.glob(os.path.join(sys.argv[1], 't*.png')))
frac = float(sys.argv[3]) if len(sys.argv) > 3 else 0.84
strips = []
for f in files:
    im = Image.open(f).convert('RGB')
    W, H = im.size
    s = im.crop((0, int(H * frac), W, H)).resize((W // 2, int(H * (1 - frac)) // 2))
    d = ImageDraw.Draw(s)
    d.text((4, 2), os.path.basename(f)[1:-4], fill='yellow')
    strips.append(s)
out = Image.new('RGB', (strips[0].width, sum(s.height for s in strips)))
y = 0
for s in strips:
    out.paste(s, (0, y)); y += s.height
out.save(sys.argv[2])
