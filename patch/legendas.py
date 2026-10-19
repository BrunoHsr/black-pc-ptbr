"""Gera as legendas .ass a partir de legendas/*.tsv e queima nos videos.

uso: python legendas.py <pasta videos originais> <pasta saida> [video ...]      (sem lista = todos os .tsv)
"""
import glob, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import revideo

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

# Video 640x480 com faixas pretas (imagem nas linhas ~67-414). O port mostra o quadro inteiro esticado para 16:9,
# entao a legenda fica na faixa de baixo e e comprimida na horizontal (ScaleX 75) para parecer normal em widescreen.
HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 640
PlayResY: 480
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Fala,Arial,23,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,75,100,0,0,1,1.6,0.8,2,20,20,8,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

MIN_DUR = 0.9     # s na tela no minimo
EXTRA = 0.25      # s a mais depois do fim da fala, se der
GAP = 0.04


def ts(t):
    cs = int(round(t * 100))
    return '%d:%02d:%02d.%02d' % (cs // 360000, cs // 6000 % 60, cs // 100 % 60, cs % 100)


def load(path):
    cues = []
    for n, line in enumerate(open(path, encoding='utf-8'), 1):
        line = line.rstrip('\r\n')  # o git no Windows pode entregar o .tsv com CRLF
        if not line.strip() or line.startswith('#'):
            continue
        a, b, text = line.split('\t', 2)
        a, b = float(a), float(b)
        if b <= a:
            raise SystemExit('%s:%d: fim antes do inicio' % (path, n))
        cues.append([a, b, text])
    cues.sort()
    for i, c in enumerate(cues):
        nxt = cues[i + 1][0] - GAP if i + 1 < len(cues) else 1e9
        c[1] = min(max(c[1] + EXTRA, c[0] + MIN_DUR), max(nxt, c[1]))
        if i + 1 < len(cues) and c[1] > cues[i + 1][0]:
            print('aviso: %s sobrepoe a seguinte em %.2f s' % (c[2][:30], c[1] - cues[i + 1][0]))
    return cues


def to_ass(cues, path):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(HEADER)
        for a, b, text in cues:
            f.write('Dialogue: 0,%s,%s,Fala,,0,0,0,,%s\n' % (ts(a), ts(b), text))


def names():
    return [os.path.basename(p)[:-4] for p in sorted(glob.glob(os.path.join(ROOT, 'legendas', '*.tsv')))]


def build(name, src, dst):
    """Queima legendas/<name>.tsv no video src, gravando dst. Devolve (quadros, bytes)."""
    cues = load(os.path.join(ROOT, 'legendas', name + '.tsv'))
    fd, ass = tempfile.mkstemp(suffix='.ass', prefix=name + '_')
    os.close(fd)
    try:
        to_ass(cues, ass)
        return revideo.recode(src, dst, ass=ass, q=3)
    finally:
        os.remove(ass)


def main():
    src_dir, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for n in sys.argv[3:] or names():
        frames, size = build(n, os.path.join(src_dir, n + '.xmv'), os.path.join(out, n + '.xmv'))
        print('%s.xmv: %d quadros, %.1f MB' % (n, frames, size / 1e6))


if __name__ == '__main__':
    main()
