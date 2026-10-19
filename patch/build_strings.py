"""Monta o MainUS.bin traduzido a partir do MainUS.bin original do jogo + traducao/pt/*.tsv.

Cada linha dos .tsv: <indice><TAB><texto>. No texto: \\r e \\n viram quebra de linha, <F01E> vira o icone de botao
U+F01E. Indice ausente = fica o texto original. Confere que %s/%d/%1..., icones e quebras batem com o original.

uso: python build_strings.py <MainUS.bin original> <saida MainUS.bin>
"""
import glob, os, re, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import strtab

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
PH = re.compile(r'%(?:\d+|[-+ #0]*\d*(?:\.\d+)?[sdifcxXu%])')
ICON = re.compile(r'[-]')
COUNT = 1724  # textos no MainUS.bin do BLACK NTSC-U


def unesc(s):
    s = s.replace('\\r', '\r').replace('\\n', '\n')
    return re.sub(r'<(F[0-9A-F]{3})>', lambda m: chr(int(m.group(1), 16)), s)


def load_pt():
    pt = {}
    for path in sorted(glob.glob(os.path.join(ROOT, 'traducao', 'pt', '*.tsv'))):
        for n, line in enumerate(open(path, encoding='utf-8'), 1):
            line = line.rstrip('\r\n')  # o git no Windows pode entregar o .tsv com CRLF
            if not line.strip() or line.startswith('#'):
                continue
            i, _, text = line.partition('\t')
            i = int(i)
            if i in pt:
                raise SystemExit('%s:%d: indice %d repetido' % (path, n, i))
            pt[i] = (unesc(text), path, n)
    return pt


def check(en, pt):
    errs = []
    a, b = PH.findall(en), PH.findall(pt)
    numbered = all(re.fullmatch(r'%\d+', x) for x in a)
    if (Counter(a) != Counter(b)) if numbered else (a != b):
        errs.append('marcadores %s -> %s' % (a, b))
    if Counter(ICON.findall(en)) != Counter(ICON.findall(pt)):
        errs.append('icones de botao diferentes')
    return errs


def build(src, out):
    word, entries = strtab.read(src)
    if len(entries) != COUNT:
        raise SystemExit('%s tem %d textos, esperado %d (outra versao do jogo?)' % (src, len(entries), COUNT))
    pt = load_pt()
    bad = 0
    new = []
    for i, (key, raw) in enumerate(entries):
        text = raw.decode('utf-8')
        if i in pt:
            t, path, n = pt[i]
            errs = check(text, t)
            if errs:
                bad += 1
                print('%s:%d [%d] %s\n   en: %r\n   pt: %r' % (os.path.basename(path), n, i, '; '.join(errs), text, t))
            text = t
        new.append((key, text.encode('utf-8')))
    if bad:
        raise SystemExit('%d erro(s); nada gravado' % bad)
    strtab.write(out, word, new)
    return len(pt)


if __name__ == '__main__':
    n = build(sys.argv[1], sys.argv[2])
    print('%d de %d textos traduzidos -> %s' % (n, COUNT, sys.argv[2]))
