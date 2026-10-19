"""Fontes bitmap do BLACK (language/fonts/Big.bin e Small.bin).

Layout: '4.1v', u32 tam_cabecalho (inicio do recurso de textura), 6 floats, tabela de 129 u32 em 0x1C
(offset do registro de cada codigo 0..128), registros de glifo (40 bytes cada, 1..3 por codigo),
recurso D3D Xbox (20 bytes) em tam_cabecalho, textura DXT3 em tam_cabecalho + 0x80.
"""
import struct, io
from PIL import Image

NCODES = 129


def load(path):
    d = bytearray(open(path, 'rb').read())
    hdr = struct.unpack_from('<I', d, 4)[0]
    fmt = struct.unpack_from('<I', d, hdr + 12)[0]
    w = 1 << ((fmt >> 20) & 15)
    h = 1 << ((fmt >> 24) & 15)
    return d, hdr, w, h


def texture(d, hdr, w, h):
    data = bytes(d[hdr + 0x80: hdr + 0x80 + w * h])
    dds = bytearray(128)
    dds[0:4] = b'DDS '
    struct.pack_into('<IIIIIII', dds, 4, 124, 0x1007 | 0x80000, h, w, w * h, 0, 1)
    struct.pack_into('<II4s', dds, 76, 32, 4, b'DXT3')
    struct.pack_into('<I', dds, 108, 0x1000)
    return Image.open(io.BytesIO(bytes(dds) + data)).convert('RGBA')


def records(d):
    tab = struct.unpack_from('<%dI' % NCODES, d, 0x1C)
    hdr = struct.unpack_from('<I', d, 4)[0]
    starts = sorted(set(tab)) + [hdr]
    out = {}
    for c, o in enumerate(tab):
        end = starts[starts.index(o) + 1]
        out[c] = [struct.unpack_from('<7fI2I', d, p) for p in range(o, end, 40)]
    return tab, out
