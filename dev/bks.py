"""Audio em streaming do BLACK: sound/streams/<nome>.ssh (indice) + <nome>.bks (dados).

.ssh: cabecalho de 0x20 bytes (+0x16 = numero de faixas), depois 8 bytes por faixa:
u16 setor inicial, u16 tamanho em setores (setor = 2048 bytes), u32 taxa (32000).
Cada faixa: blocos de 0x4000 bytes alternando entre os canais; cada bloco tem 862 quadros EA-XAS v0
(0x13 bytes, 32 amostras) e 6 bytes de enchimento.

uso: python bks.py <pasta streams> <nome> <saida_dir> [canais=2]   -> <nome>_<faixa>.wav para cada faixa
"""
import os, struct, sys, wave
import numpy as np

SECTOR = 0x800
BLOCK = 0x4000
FRAME = 0x13
FRAMES_PER_BLOCK = BLOCK // FRAME  # 862
COEFS = np.array([[0.0, 0.0], [240.0, 0.0], [460.0, -208.0], [392.0, -220.0]] + [[0.0, 0.0]] * 12)


def tracks(ssh_path):
    h = open(ssh_path, 'rb').read()
    n = h[0x16]
    out = []
    for i in range(n):
        start, size, rate = struct.unpack_from('<HHI', h, 0x20 + 8 * i)
        out.append((start * SECTOR, size * SECTOR, rate))
    return out


def decode_frames(frames):
    """frames: array (N, 19) uint8 -> int16 (N*32) mono, EA-XAS v0 (cada quadro e independente)."""
    hdr = frames[:, 0].astype(np.uint32) | (frames[:, 1].astype(np.uint32) << 8) | \
        (frames[:, 2].astype(np.uint32) << 16) | (frames[:, 3].astype(np.uint32) << 24)
    c = COEFS[hdr & 0x0F]
    hist2 = ((hdr & 0xFFF0).astype(np.int32) ^ 0x8000) - 0x8000
    hist1 = (((hdr >> 16) & 0xFFF0).astype(np.int32) ^ 0x8000) - 0x8000
    shift = ((hdr >> 16) & 0x0F).astype(np.int32)
    out = np.empty((len(frames), 32), np.int32)
    out[:, 0], out[:, 1] = hist2, hist1
    h1, h2 = hist1.astype(np.float64), hist2.astype(np.float64)
    nib = frames[:, 4:]
    for i in range(30):
        b = nib[:, i // 2].astype(np.int32)
        v = (b & 0x0F) if i & 1 else (b >> 4)
        v = np.where(v >= 8, v - 16, v)
        s = (v << (20 - shift)).astype(np.float64) + h1 * c[:, 0] + h2 * c[:, 1]
        s = np.clip((np.floor(s).astype(np.int64) + 128) >> 8, -32768, 32767)
        out[:, 2 + i] = s
        h2, h1 = h1, s.astype(np.float64)
    return out.reshape(-1).astype(np.int16)


def decode_track(data, channels=2):
    nblocks = len(data) // BLOCK
    blocks = np.frombuffer(data[:nblocks * BLOCK], np.uint8).reshape(nblocks, BLOCK)
    frames = blocks[:, :FRAMES_PER_BLOCK * FRAME].reshape(nblocks, FRAMES_PER_BLOCK, FRAME)
    pcm = decode_frames(frames.reshape(-1, FRAME)).reshape(nblocks, FRAMES_PER_BLOCK * 32)
    nblocks -= nblocks % channels
    chans = [pcm[c:nblocks:channels].reshape(-1) for c in range(channels)]
    return np.stack(chans, axis=1)


def write_wav(path, pcm, rate):
    with wave.open(path, 'wb') as w:
        w.setnchannels(pcm.shape[1])
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.astype('<i2').tobytes())


if __name__ == '__main__':
    folder, name, outdir = sys.argv[1:4]
    ch = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(folder, name + '.bks'), 'rb') as f:
        for i, (off, size, rate) in enumerate(tracks(os.path.join(folder, name + '.ssh'))):
            f.seek(off)
            pcm = decode_track(f.read(size), ch)
            p = os.path.join(outdir, '%s_%d.wav' % (name, i))
            write_wav(p, pcm, rate)
            print('%s faixa %d: %.1f s' % (name, i, len(pcm) / rate))
