"""Le e grava language/strings/MainUS.bin do BLACK (Xbox).

Formato: u32 magic 0x586A0308, u32 (desconhecido, mantido), u32 n, u32 off_tabela (16);
n offsets u32 crescentes; cada entrada = u32 chave (hash do nome) + texto UTF-8 terminado em NUL,
alinhado a 4 bytes (menos a ultima).
"""
import struct


def read(path):
    d = open(path, 'rb').read()
    magic, word, n, toff = struct.unpack_from('<IIII', d, 0)
    assert magic == 0x586A0308, hex(magic)
    offs = struct.unpack_from('<%dI' % n, d, toff)
    entries = []
    for o in offs:
        key = struct.unpack_from('<I', d, o)[0]
        end = d.index(b'\0', o + 4)
        entries.append((key, d[o + 4:end]))
    return word, entries


def write(path, word, entries):
    n = len(entries)
    toff = 16
    body = bytearray()
    offs = []
    base = toff + 4 * n
    for i, (key, text) in enumerate(entries):
        assert b'\0' not in text
        offs.append(base + len(body))
        body += struct.pack('<I', key) + text + b'\0'
        if i != n - 1:
            while len(body) % 4:
                body += b'\0'
    out = struct.pack('<IIII', 0x586A0308, word, n, toff) + struct.pack('<%dI' % n, *offs) + bytes(body)
    open(path, 'wb').write(out)
    return len(out)
