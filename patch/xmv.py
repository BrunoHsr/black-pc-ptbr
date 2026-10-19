"""Leitura e escrita de videos XMV do Xbox (so video WMV2, sem faixas de audio, como os do BLACK).

Layout (conferido com libavformat/xmv.c do ffmpeg e com os arquivos do jogo):
  cabecalho (36 bytes): u32 tamanho do pacote 1, u32 tamanho de cabecalho + pacote 0, u32 maior pacote, 'xobX',
             u32 versao, u32 largura, u32 altura, u32 duracao (ms), u16 n_audio (0), u16 0
  pacote:    u32 tamanho do proximo pacote, u32 video (bits 0-22 = bytes restantes do pacote, 23-30 = n de quadros,
             bit 31 = tem extradata), u32 duracao do pacote (ms), [4 bytes extradata WMV2], quadros, zeros ate
             fechar um multiplo de 4096 bytes a partir do inicio do arquivo
  quadro:    u32 (bits 0-16 = palavras - 1, bits 17-31 = duracao do quadro em ms), dados com as palavras de
             32 bits invertidas
"""
import struct

HDR = 36
ALIGN = 4096


class Frame:
    def __init__(self, dur, data):
        self.dur = dur        # ms
        self.data = data      # bitstream WMV2 (ordem normal)


class Packet:
    def __init__(self, frames=None, extradata=None, dur=0):
        self.frames = frames or []
        self.extradata = extradata
        self.dur = dur


def _swap_words(b):
    n = len(b) // 4
    return struct.pack('>%dI' % n, *struct.unpack('<%dI' % n, b))


def read(path):
    d = open(path, 'rb').read()
    first_next, first_size, max_size, magic, version, w, h, dur, n_audio, _ = struct.unpack_from('<III4sIIIIHH', d, 0)
    assert magic == b'xobX' and n_audio == 0, (magic, n_audio)
    packets = []
    pos, size = HDR, first_size - HDR
    while size:
        nxt, vid, pdur = struct.unpack_from('<III', d, pos)
        assert (vid & 0x7FFFFF) == size - 12, 'tamanho de pacote inesperado'
        p = Packet(dur=pdur)
        q = pos + 12
        if vid & 0x80000000:
            p.extradata = d[q:q + 4]
            q += 4
        for _ in range((vid >> 23) & 0xFF):
            fh = struct.unpack_from('<I', d, q)[0]
            fsize = (fh & 0x1FFFF) * 4 + 4
            p.frames.append(Frame(fh >> 17, _swap_words(d[q + 4:q + 4 + fsize])))
            q += 4 + fsize
        assert not any(d[q:pos + size]), 'enchimento nao zerado'
        packets.append(p)
        pos, size = pos + size, nxt
    return {'version': version, 'width': w, 'height': h, 'duration': dur, 'packets': packets}


def write(path, x):
    out = bytearray(HDR)
    starts, sizes = [], []
    for k, p in enumerate(x['packets']):
        body = bytearray()
        if p.extradata is not None:
            body += p.extradata
        for f in p.frames:
            assert len(f.data) % 4 == 0 and len(f.data) >= 4
            body += struct.pack('<I', (f.dur << 17) | (len(f.data) // 4 - 1)) + _swap_words(f.data)
        start = len(out)
        end = start + 12 + len(body)
        end = (end + ALIGN - 1) // ALIGN * ALIGN
        body += bytes(end - start - 12 - len(body))
        assert len(p.frames) < 256 and len(body) < (1 << 23)
        vid = len(body) | (len(p.frames) << 23) | (0x80000000 if p.extradata is not None else 0)
        out += struct.pack('<III', 0, vid, p.dur) + body
        starts.append(start)
        sizes.append(end - start)
    for k, s in enumerate(starts):
        struct.pack_into('<I', out, s, sizes[k + 1] if k + 1 < len(sizes) else 0)
    struct.pack_into('<III4sIIIIHH', out, 0, sizes[1] if len(sizes) > 1 else 0, HDR + sizes[0],
                     max([HDR + sizes[0]] + sizes[1:]), b'xobX', x['version'], x['width'], x['height'],
                     x['duration'], 0, 0)
    open(path, 'wb').write(out)
    return len(out)
