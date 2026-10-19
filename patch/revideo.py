"""Recodifica um XMV do BLACK com legenda queimada, mantendo quadros, tempos e pacotes do original.

O ffmpeg nao devolve os quadros "pulados" de 8 bytes (P sem nenhum macrobloco); nessas posicoes o quadro anterior e
repetido, entao o video novo tem exatamente os mesmos quadros e duracoes do original.

uso: python revideo.py <original.xmv> <saida.xmv> [--ass legenda.ass] [--vf filtro] [--q 3]
"""
import argparse, os, struct, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xmv, avi

FONTS = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')  # Arial do proprio Windows


def ff_filter_path(p):
    # caminho para dentro de um filtro do ffmpeg: barras normais e ':' escapado
    return os.path.abspath(p).replace('\\', '/').replace(':', '\\:')


def xmv_extradata(wmv2):
    """Extradata WMV2 padrao (fps 5, bitrate 11, mspel, loop, abt, j_type, top_left, per_mb_rl, fatias 3 bits,
    big-endian) -> formato do XMV (u32 little-endian: bits 0-5 as mesmas flags, bits 6-8 fatias)."""
    v = int.from_bytes(wmv2[:4], 'big')
    flags = [(v >> (31 - 16 - i)) & 1 for i in range(6)]  # mspel, loop, abt, j_type, top_left, per_mb_rl
    slices = (v >> (31 - 24)) & 7
    out = sum(b << i for i, b in enumerate(flags)) | (slices << 6)
    return out.to_bytes(4, 'little')


def repacketize(frames, extradata, cap, duration):
    """Reagrupa os quadros em pacotes que nao passam de `cap` bytes (o maior pacote do original), para o
    player do Xbox nao precisar de mais memoria que no video original. Duracao do pacote como no original:
    floor(quadros * 1000 / 30), e o ultimo fecha na duracao total."""
    def t(i):
        return i * 1000 // 30

    def size(first, nbytes):
        head = xmv.HDR if first else 0
        return -(-(head + 12 + nbytes) // xmv.ALIGN) * xmv.ALIGN

    packets, cur, cur_bytes, start = [], [], 4, 0  # 4 = extradata do primeiro pacote
    for i, f in enumerate(frames):
        add = 4 + len(f.data)
        if cur and (size(not packets, cur_bytes + add) > cap or len(cur) == 255):
            packets.append(xmv.Packet(cur, extradata if not packets else None, t(start + len(cur)) - t(start)))
            start += len(cur)
            cur, cur_bytes = [], 0
        cur.append(f)
        cur_bytes += add
    packets.append(xmv.Packet(cur, extradata if not packets else None, duration - t(start)))
    return packets


def recode(src, dst, ass=None, vf=None, q=3):
    x = xmv.read(src)
    frames = [f for p in x['packets'] for f in p.frames]
    skip = [len(f.data) == 8 for f in frames]
    w, h = x['width'], x['height']
    fsize = w * h * 3 // 2

    filters = []
    if vf:
        filters.append(vf)
    if ass:
        filters.append("subtitles='%s':fontsdir='%s'" % (ff_filter_path(ass), ff_filter_path(FONTS)))
    tmp = tempfile.mkdtemp(prefix='revideo_')
    out_avi = os.path.join(tmp, 'v.avi')
    # setpts=N: carimbos sequenciais; com os do XMV (ms, as vezes repetidos) o muxer descartava quadros
    # (o rawvideo reclama de dts repetidos mesmo assim, sem perder quadros: a contagem abaixo confere)
    dec = subprocess.Popen(['ffmpeg', '-v', 'fatal', '-i', src, '-vf', 'setpts=N', '-f', 'rawvideo',
                            '-pix_fmt', 'yuv420p', '-fps_mode', 'passthrough', '-'], stdout=subprocess.PIPE)
    enc_cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'yuv420p', '-s', '%dx%d' % (w, h),
               '-r', '30', '-i', '-']
    if filters:
        enc_cmd += ['-vf', ','.join(filters)]
    enc_cmd += ['-c:v', 'wmv2', '-q:v', str(q), '-an', out_avi]
    enc = subprocess.Popen(enc_cmd, stdin=subprocess.PIPE)
    last, got = None, 0
    for s in skip:
        if not s or last is None:
            buf = dec.stdout.read(fsize)
            if len(buf) == fsize:
                last, got = buf, got + 1
        enc.stdin.write(last)
    rest = dec.stdout.read()
    enc.stdin.close()
    enc.wait(); dec.wait()
    expected = len(skip) - sum(skip[1:]) if skip and skip[0] else len(skip) - sum(skip)
    got += len(rest) // fsize
    if got != expected:
        raise SystemExit('decodificados %d quadros, esperados %d: os quadros sairiam fora de sincronia' % (got, expected))

    data, extra = avi.read(out_avi)
    assert len(data) == len(frames), (len(data), len(frames))
    for f, b in zip(frames, data):
        f.data = b + bytes(-len(b) % 4)
    cap = struct.unpack_from('<I', open(src, 'rb').read(12), 8)[0]
    x['packets'] = repacketize(frames, xmv_extradata(extra), cap, x['duration'])
    size = xmv.write(dst, x)
    os.remove(out_avi); os.rmdir(tmp)
    return len(frames), size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('dst')
    ap.add_argument('--ass'); ap.add_argument('--vf'); ap.add_argument('--q', type=int, default=3)
    a = ap.parse_args()
    n, size = recode(a.src, a.dst, a.ass, a.vf, a.q)
    print('%s: %d quadros, %.1f MB (original %.1f MB)' % (os.path.basename(a.dst), n, size / 1e6,
                                                          os.path.getsize(a.src) / 1e6))


if __name__ == '__main__':
    main()
