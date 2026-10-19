"""Aplica (ou remove) a traducao PT-BR do BLACK na copia do jogo usada pelo port de PC.

Nada do jogo vem neste repositorio: os arquivos traduzidos sao gerados a partir dos SEUS arquivos originais.
Os originais ficam guardados em <pasta do BLACK>\\traducao-ptbr-backup e voltam com --restaurar.

uso: python aplicar.py [pasta do BLACK (a que tem game\\default.xbe) ou a propria pasta game]
     python aplicar.py --restaurar [pasta]
"""
import hashlib, os, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

XBE_NTSC_U = 'df2739c372d254a90aeeccf5971d12097f22d89fbb90db021fda96dd4deb68f6'
# arquivos que a traducao troca, com o sha256 do original (disco NTSC-U)
ORIGINAIS = {
    'language/strings/MainUS.bin': 'b23eeb4ad86a72894b40e7239d0ea8842e5a6bc05936a936401b608070e8c7bb',
    'language/fonts/Big.bin': '119ede7ec211ddebde76b46e4dcbea86e486f1b13549fc1fe58ecb5ed59611c5',
    'language/fonts/Small.bin': 'f194f96f9389ba7f4cb126ac02e2f619f27df0339ab97df6fe7a740e5a1fca35',
    'videos/03_n.xmv': '0ea5e82a6c438e9866af3cc588cdc2fc86938242683e2da8de97e353a4d5574c',
    'videos/05_n.xmv': '012d30d3da4bc11f66cfee155c297d7c5d8175955da3c8d83126240412f59f4e',
    'videos/07_n.xmv': 'dec07afe87f7a9147c293c1a197d83cbef78140ea370c7a6e5962c63a7ee34ec',
    'videos/09_n.xmv': 'a857c9c45dc88d9b63a52792beb711738a5fa30dfe62f5375c63b372a562cc0e',
    'videos/11_n.xmv': 'f79236a81e228d6b238df424caa1e5c7268e70b885cca3c8706a878c49f3d799',
    'videos/13_n.xmv': '1579d4e1416898630bac47aa25d04ef6681a59acc22eeea4a807071bdedcd153',
    'videos/15_n.xmv': '1cf9ced4459f44aca54be8505a1b82515fe0d058ff9d054c3588ef16a0257a22',
    'videos/17_n.xmv': '39ce7e5a1007c0b6c72de88f8d61a6da37a01e837246044d9f06115a63cd8886',
    'videos/18_n.xmv': '210db11d234240720e106ebd954885b346650987898e2bbaea56889c5a9c7d8e',
}
BACKUP = 'traducao-ptbr-backup'


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def real(game, rel):
    """Caminho do arquivo no disco ignorando maiusculas (o disco tem 03_n.xmv, o jogo pede 03_N.xmv)."""
    cur = game
    for part in rel.split('/'):
        names = {n.lower(): n for n in os.listdir(cur)} if os.path.isdir(cur) else {}
        cur = os.path.join(cur, names.get(part.lower(), part))
    return cur


def find_game(arg):
    cands = [arg] if arg else [os.getcwd(), os.path.join(HERE, '..', '..')]
    for c in cands:
        c = os.path.abspath(c.strip('"'))
        for g in (c, os.path.join(c, 'game'), os.path.join(os.path.dirname(c), 'game')):
            if os.path.isfile(os.path.join(g, 'default.xbe')):
                return g
    return None


def ask_game():
    print('Arraste aqui a pasta do BLACK (a que tem a pasta "game") e aperte Enter:')
    return input('> ').strip()


def check_tools():
    try:
        import PIL  # noqa: F401
    except ImportError:
        raise SystemExit('Falta o Pillow. Instale com:  python -m pip install pillow')
    try:
        enc = subprocess.run(['ffmpeg', '-hide_banner', '-encoders'], capture_output=True, text=True).stdout
        flt = subprocess.run(['ffmpeg', '-hide_banner', '-filters'], capture_output=True, text=True).stdout
    except FileNotFoundError:
        raise SystemExit('Falta o ffmpeg no PATH. Instale com:  winget install Gyan.FFmpeg  (e abra um terminal novo)')
    if ' wmv2 ' not in enc or ' subtitles ' not in flt:
        raise SystemExit('Este ffmpeg nao tem o encoder wmv2 ou o filtro subtitles (libass). Use um build completo, '
                         'por exemplo:  winget install Gyan.FFmpeg')


def restore(game, backup):
    if not os.path.isdir(backup):
        raise SystemExit('Nao achei o backup em %s; nada a restaurar.' % backup)
    for rel, h in ORIGINAIS.items():
        src = os.path.join(backup, *rel.split('/'))
        if not os.path.isfile(src) or sha256(src) != h:
            raise SystemExit('Backup incompleto ou alterado: %s' % src)
    for rel in ORIGINAIS:
        shutil.copy2(os.path.join(backup, *rel.split('/')), real(game, rel))
    print('Originais restaurados. O backup continua em %s (pode apagar).' % backup)


def apply(game, backup):
    import build_strings, fontpatch, legendas
    check_tools()

    # 1. originais: do backup, se ja existe; senao, conferir e guardar os do jogo
    if os.path.isdir(backup):
        print('Usando os originais guardados em %s' % backup)
    else:
        bad = [rel for rel, h in ORIGINAIS.items() if sha256(real(game, rel)) != h]
        if bad:
            raise SystemExit('Estes arquivos nao sao os originais do BLACK NTSC-U (ja modificados?):\n  ' +
                             '\n  '.join(bad) + '\nRestaure-os do seu disco antes de aplicar a traducao.')
        for rel in ORIGINAIS:
            dst = os.path.join(backup, *rel.split('/'))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(real(game, rel), dst)
        print('Originais guardados em %s' % backup)

    def orig(rel):
        return os.path.join(backup, *rel.split('/'))

    tmp = tempfile.mkdtemp(prefix='black-ptbr-')
    try:
        # 2. textos e fontes
        n = build_strings.build(orig('language/strings/MainUS.bin'), os.path.join(tmp, 'MainUS.bin'))
        print('Textos: %d traduzidos' % n)
        for f in ('Small.bin', 'Big.bin'):
            fontpatch.patch(orig('language/fonts/' + f), os.path.join(tmp, f))
        print('Fontes: Ã/ã e Õ/õ acrescentados')
        # 3. videos com legenda
        vids = [rel for rel in ORIGINAIS if rel.startswith('videos/')]
        for k, rel in enumerate(vids, 1):
            name = os.path.basename(rel)[:-4]
            t = time.time()
            legendas.build(name, orig(rel), os.path.join(tmp, name + '.xmv'))
            print('Video %d/%d: %s legendado (%.0f s)' % (k, len(vids), name, time.time() - t))
        # 4. tudo pronto: copiar para o jogo
        shutil.copy2(os.path.join(tmp, 'MainUS.bin'), real(game, 'language/strings/MainUS.bin'))
        for f in ('Small.bin', 'Big.bin'):
            shutil.copy2(os.path.join(tmp, f), real(game, 'language/fonts/' + f))
        for rel in vids:
            shutil.copy2(os.path.join(tmp, os.path.basename(rel)), real(game, rel))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print('\nPronto! Traducao aplicada em %s' % game)
    print('Para voltar ao original:  aplicar.bat --restaurar  (ou python aplicar.py --restaurar)')


def main():
    args = [a for a in sys.argv[1:] if a != '--restaurar']
    restaurar = '--restaurar' in sys.argv[1:]
    game = find_game(args[0] if args else None)
    if not game:
        game = find_game(ask_game())
    if not game:
        raise SystemExit('Nao achei game\\default.xbe nessa pasta.')
    xbe = sha256(os.path.join(game, 'default.xbe'))
    if xbe != XBE_NTSC_U:
        raise SystemExit('Este default.xbe nao e o do BLACK NTSC-U suportado pelo port.')
    backup = os.path.join(os.path.dirname(os.path.abspath(game)), BACKUP)
    print('Jogo: %s' % game)
    restore(game, backup) if restaurar else apply(game, backup)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
