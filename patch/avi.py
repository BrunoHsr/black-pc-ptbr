"""Extrai quadros e extradata de um AVI (RIFF) com video WMV2 gerado pelo ffmpeg."""
import struct


def read(path):
    d = open(path, 'rb').read()
    frames, extra = [], None

    def walk(pos, end):
        nonlocal extra
        while pos + 8 <= end:
            cid, size = d[pos:pos + 4], struct.unpack_from('<I', d, pos + 4)[0]
            body = pos + 8
            if cid in (b'RIFF', b'LIST'):
                walk(body + 4, body + size)
            elif cid == b'strf' and extra is None:
                bih = struct.unpack_from('<I', d, body)[0]   # biSize
                extra = d[body + bih: body + size] if size > bih else d[body + 40: body + size]
            elif cid[2:] in (b'dc', b'db'):
                frames.append(d[body:body + size])
            pos = body + size + (size & 1)
    walk(0, len(d))
    return frames, extra
