"""Troca a traducao de indices ja existentes nos .tsv: python settr.py (le pares indice<TAB>texto da entrada padrao)."""
import glob, os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'traducao', 'pt')
new = {}
for line in sys.stdin.read().splitlines():
    if line.strip():
        i, _, t = line.partition('\t'); new[int(i)] = t
for path in sorted(glob.glob(os.path.join(ROOT, '*.tsv'))):
    lines = open(path, encoding='utf-8').read().splitlines()
    changed = False
    for k, l in enumerate(lines):
        i, sep, _ = l.partition('\t')
        if sep and i.isdigit() and int(i) in new:
            lines[k] = '%s\t%s' % (i, new.pop(int(i))); changed = True
    if changed:
        open(path, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
for i, t in new.items():
    print('indice %d nao existe em nenhum .tsv' % i)
