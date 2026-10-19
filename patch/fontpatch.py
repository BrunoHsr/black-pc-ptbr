"""Acrescenta letras acentuadas que faltam nas fontes bitmap do BLACK (Small.bin / Big.bin).

Cada letra nova e montada com pecas da propria fonte: o corpo da letra base (A, O) e o til tirado do N com til.
Os registros entram no balde certo da tabela de hash ((codigo & 0x7F) + 1), o resto do arquivo e deslocado e a
textura DXT3 so tem reescritos os blocos 4x4 que estavam vazios.

uso: python fontpatch.py <pasta_fonts_original> <pasta_saida> [<pasta_previa>]
"""
import struct, sys, os
from PIL import Image
import font

START = 0x1C + 4 * font.NCODES
REC = 40

# letra nova -> (letra base, letra de onde vem o acento, letra base sem acento correspondente a doadora)
COMPOSE = {
    'Ã': ('A', 'Ñ', 'N'),
    'Õ': ('O', 'Ñ', 'N'),
}
LOWER = {'Ã': 'ã', 'Õ': 'õ'}


def parse(d):
    hdr = struct.unpack_from('<I', d, 4)[0]
    n = (hdr - START) // REC
    recs = [list(struct.unpack_from('<7fI2I', d, START + REC * i)) for i in range(n)]
    return hdr, recs


def bucket(cp):
    return (cp & 0x7F) + 1


def crop(tex, r, tw, th):
    x, y = round(r[0] * tw), round(r[1] * th)
    w, h = round(r[2] * tw), round(r[3] * th)
    return tex.crop((x, y, x + w, y + h))


def ink_box(img):
    a = img.getchannel('A')
    return a.getbbox()


def compose(tex, by, tw, th, new, base, donor, donor_base):
    rb, rd_, rdb = by[ord(base)], by[ord(donor)], by[ord(donor_base)]
    gb = crop(tex, rb, tw, th)
    gd = crop(tex, rd_, tw, th)
    acc_rows = round(rd_[3] * th) - round(rdb[3] * th)
    accent = gd.crop((0, 0, gd.width, acc_rows))
    abox = ink_box(accent)
    accent = accent.crop(abox)
    # centro horizontal: o do til no doador, relativo ao centro da tinta do doador sem acento
    bbox_b = ink_box(gb)
    cx_base = (bbox_b[0] + bbox_b[2]) / 2
    w = gb.width
    h = acc_rows + gb.height
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    out.paste(gb, (0, acc_rows))
    ax = round(cx_base - accent.width / 2)
    ax = max(0, min(w - accent.width, ax))
    out.alpha_composite(accent, (ax, abox[1]))
    rec = list(rb)
    rec[3] = h / th
    rec[5] = rb[5] - acc_rows / th
    rec[7] = ord(new)
    rec[8] = 0
    return out, rec


def block_empty(alpha, bx, by_):
    for y in range(by_ * 4, by_ * 4 + 4):
        for x in range(bx * 4, bx * 4 + 4):
            if alpha[x, y]:
                return False
    return True


def find_space(occ, tw, th, w, h):
    """Retangulo alinhado a blocos com 1 bloco de folga em volta, todo vazio; procura de baixo para cima, da direita."""
    bw, bh = (w + 2 + 3) // 4, (h + 2 + 3) // 4
    nbx, nby = tw // 4, th // 4
    for by_ in range(nby - bh - 1, 0, -1):
        for bx in range(nbx - bw - 1, 0, -1):
            if all(not occ[y][x] for y in range(by_ - 1, by_ + bh + 1) for x in range(bx - 1, bx + bw + 1)):
                for y in range(by_, by_ + bh):
                    for x in range(bx, bx + bw):
                        occ[y][x] = True
                return bx, by_, bw, bh
    raise RuntimeError('sem espaco na textura para %dx%d' % (w, h))


def dxt3_block(pixels):
    """16 pixels RGBA brancos -> bloco DXT3 (alfa explicito 4 bits, cor branca)."""
    alpha = 0
    for i, p in enumerate(pixels):
        alpha |= (min(15, (p[3] + 8) // 17)) << (4 * i)
    return struct.pack('<Q', alpha) + struct.pack('<HHI', 0xFFFF, 0xFFFF, 0)


def patch(src, dst, preview=None):
    d = bytearray(open(src, 'rb').read())
    hdr, recs = parse(d)
    _, _, tw, th = font.load(src)
    tex = font.texture(d, hdr, tw, th)
    texdata = bytearray(d[hdr + 0x80: hdr + 0x80 + tw * th])
    texhdr = bytes(d[hdr: hdr + 0x80])
    tail = bytes(d[hdr + 0x80 + tw * th:])
    by = {r[7]: r for r in recs if r[7]}

    alpha = tex.getchannel('A').load()
    occ = [[not block_empty(alpha, bx, by_) for bx in range(tw // 4)] for by_ in range(th // 4)]

    added = []
    for new, (base, donor, donor_base) in COMPOSE.items():
        if ord(new) in by:
            continue
        img, rec = compose(tex, by, tw, th, new, base, donor, donor_base)
        bx, by_, bw, bh = find_space(occ, tw, th, img.width, img.height)
        x0, y0 = bx * 4 + 1, by_ * 4 + 1
        canvas = Image.new('RGBA', (bw * 4, bh * 4), (255, 255, 255, 0))
        canvas.paste(img, (1, 1))
        tex.paste(canvas, (bx * 4, by_ * 4))
        cp = canvas.load()
        for j in range(bh):
            for i in range(bw):
                pix = [cp[i * 4 + x, j * 4 + y] for y in range(4) for x in range(4)]
                off = ((by_ + j) * (tw // 4) + (bx + i)) * 16
                texdata[off:off + 16] = dxt3_block(pix)
        rec[0], rec[1] = x0 / tw, y0 / th
        low = list(rec)
        low[7] = ord(LOWER[new])
        low[8] = 1
        added += [rec, low]
        # print('  %s/%s em (%d,%d) %dx%d' % (new, LOWER[new], x0, y0, img.width, img.height))

    # insere cada registro no fim do seu balde (ordem do arquivo = ordem dos baldes)
    for rec in added:
        b = bucket(rec[7])
        pos = None
        for i, r in enumerate(recs):
            if r[7] and bucket(r[7]) == b:
                pos = i + 1
        if pos is None:  # balde vazio: antes do primeiro balde maior
            pos = next(i for i, r in enumerate(recs) if not r[7] or bucket(r[7]) > b)
        recs.insert(pos, rec)

    # tabela: primeiro registro de cada balde; vazios apontam para o registro padrao (codigo 0)
    dflt = next(i for i, r in enumerate(recs) if r[7] == 0)
    first = {}
    for i, r in enumerate(recs):
        if r[7]:
            first.setdefault(bucket(r[7]), i)
    table = [START + REC * first.get(b, dflt) for b in range(font.NCODES)]

    body = b''.join(struct.pack('<7fI2I', *r) for r in recs)
    new_hdr = START + len(body)
    new_hdr = (new_hdr + 8 + 0x7F) & ~0x7F  # mesma folga minima do original, alinhado a 0x80
    out = bytearray(d[:0x1C])
    struct.pack_into('<I', out, 4, new_hdr)
    out += struct.pack('<%dI' % font.NCODES, *table) + body
    out += b'\0' * (new_hdr - len(out))
    out += texhdr + texdata + tail
    open(dst, 'wb').write(out)
    if preview:
        bg = Image.new('RGBA', tex.size, (40, 40, 60, 255))
        bg.alpha_composite(font.texture(out, new_hdr, tw, th))
        bg.resize((tw * 3, th * 3), Image.NEAREST).save(preview)
    return out


if __name__ == '__main__':
    src_dir, out_dir = sys.argv[1], sys.argv[2]
    prev_dir = sys.argv[3] if len(sys.argv) > 3 else None
    os.makedirs(out_dir, exist_ok=True)
    for fn in ('Small.bin', 'Big.bin'):
        print(fn)
        patch(os.path.join(src_dir, fn), os.path.join(out_dir, fn),
              os.path.join(prev_dir, fn.replace('.bin', '.png')) if prev_dir else None)
