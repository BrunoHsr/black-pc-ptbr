"""Leitor minimo dos containers Apt do front end (export/frontend/*.bin), seguindo fe/apt.cpp do port."""
import struct

SIG = 0x09876543


def rd(b, o):
    return struct.unpack_from('<I', b, o)[0]


def container(data):
    count, base = rd(data, 8), rd(data, 12)
    regs = []
    for i in range(count):
        e = rd(data, base + 4 * i)
        name = rd(data, e); region = rd(data, e + 4)
        n = data[name:data.index(b'\0', name)].decode()
        regs.append((region, n))
    s = sorted(regs)
    out = {}
    for i, (r, n) in enumerate(s):
        end = s[i + 1][0] if i + 1 < len(s) else len(data)
        out[n] = (r, end)
    return [n for _, n in regs], out


class Movie:
    def __init__(self, region):
        self.r = region
        c, g = rd(region, 0x10), rd(region, 0x18)
        self.apt = region[0x80:c]
        self.cst = region[c:g] if g else region[c:]
        self.tail = region[g:] if g else b''
        self.main = rd(self.cst, 0x14)

    def characters(self):
        n, a = rd(self.apt, self.main + 20), rd(self.apt, self.main + 24)
        return [rd(self.apt, a + 4 * i) for i in range(n)]

    def str(self, off):
        if not off:
            return ''
        return self.apt[off:self.apt.index(b'\0', off)].decode('utf-8', 'replace')
