"""Junta prints num mosaico: python sheet.py <pasta> <saida.png> [colunas] [largura_miniatura]"""
import sys, glob, os
from PIL import Image, ImageDraw
files = sorted(glob.glob(os.path.join(sys.argv[1], '*.png')))
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 4
tw = int(sys.argv[4]) if len(sys.argv) > 4 else 480
ims = [Image.open(f) for f in files]
th = round(tw * ims[0].height / ims[0].width)
rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (cols * tw, rows * th), 'black')
d = ImageDraw.Draw(sheet)
for k, (f, im) in enumerate(zip(files, ims)):
    x, y = (k % cols) * tw, (k // cols) * th
    sheet.paste(im.convert('RGB').resize((tw, th)), (x, y))
    d.text((x + 4, y + 4), os.path.basename(f)[6:11], fill='yellow')
sheet.save(sys.argv[2])
