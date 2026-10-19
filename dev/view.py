"""Lista os textos de um MainUS.bin (indice<TAB>texto, quebras e icones escapados), para traduzir.
uso: python view.py <MainUS.bin original> <saida.txt>"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'patch'))
import strtab


def esc(s):
    out = []
    for ch in s:
        o = ord(ch)
        if ch == '\r': out.append(r'\r')
        elif ch == '\n': out.append(r'\n')
        elif 0xE000 <= o <= 0xF8FF: out.append('<%04X>' % o)
        else: out.append(ch)
    return ''.join(out)


_, entries = strtab.read(sys.argv[1])
with open(sys.argv[2], 'w', encoding='utf-8', newline='\n') as f:
    for i, (_, t) in enumerate(entries):
        f.write('%d\t%s\n' % (i, esc(t.decode('utf-8'))))
