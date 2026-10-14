"""Predict what the decoded Color Precision nonRAW tables do to the test chart.

Usage: python3 -I tools/test_chart/predict_decoder.py [--root DIR] [--space pp18|srgb] [--out DIR]
For each of the 8 nonRAW profiles (Portra 400, Pro 400H, Velvia 50, Gold pushed x Frontier,
Noritsu): sRGB 16-bit chart -> table space -> 32^3 RGB table (trilinear) -> sRGB 16-bit,
written as <out>/decoder-<space>__<film>__<scanner>.tif (film tokens Portra400, Pro400H, Velvia50, GoldPushed) with the sRGB ICC embedded.
Table space: pp18 = ProPhoto primaries (D50), plain 1.8 gamma (primaries 2 / gamma 2 as read
by tools/cp_demo; NOT yet checked against Adobe code or real Camera Raw output);
srgb = alternative hypothesis (sRGB primaries and curve), for step 6 of the test-chart plan.
Only the RGB table is applied: Portra 400 also carries HSL sliders and tone curves in the XMP
(not applied here); the other six profiles have only the table. Amount = 100 %.
Output is clipped to the sRGB gamut and quantised to 16 bit, as a Camera Raw export would be.
"""
import argparse
import os
import struct
import sys

import numpy as np
import tifffile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'cp_demo'))
import colorlib as cl
import crs_table
from measure_chart import read_image, srgb_profile

FILMS = ['Portra 400', 'Pro 400H', 'Velvia 50', 'Gold pushed']
SCANNERS = ['Frontier', 'Noritsu']
TOKEN = {'Portra 400': 'Portra400', 'Pro 400H': 'Pro400H', 'Velvia 50': 'Velvia50', 'Gold pushed': 'GoldPushed'}


def load_table(path):
    _, refs, tabs = crs_table.read_xmp(path)
    d = crs_table.decode_table(tabs[refs['RGBTable']])
    btt, ver, dims, n = struct.unpack('<4I', d[:16])
    assert (btt, ver, dims) == (1, 1, 3)
    v = np.frombuffer(d[16:16 + n ** 3 * 6], '<i2').astype(float).reshape(n, n, n, 3)   # [r][g][b][ch]
    idx = np.arange(n) * 65535.0 / (n - 1)
    ident = np.stack(np.meshgrid(idx, idx, idx, indexing='ij'), -1)
    prim, gam, gamut = struct.unpack('<3I', d[16 + n ** 3 * 6:16 + n ** 3 * 6 + 12])
    return (ident + v) / 65535.0, (prim, gam, gamut)


def trilinear(lut, rgb):
    n = lut.shape[0]
    p = np.clip(rgb, 0, 1) * (n - 1)
    i = np.minimum(p.astype(int), n - 2)
    f = p - i
    out = np.zeros_like(rgb)
    for dr in (0, 1):
        for dg in (0, 1):
            for db in (0, 1):
                w = (f[..., 0] if dr else 1 - f[..., 0]) * (f[..., 1] if dg else 1 - f[..., 1]) * (f[..., 2] if db else 1 - f[..., 2])
                out += w[..., None] * lut[i[..., 0] + dr, i[..., 1] + dg, i[..., 2] + db]
    return out


def space(name):
    if name == 'pp18':
        return (cl.M_PP_INV, cl.M_PP, lambda x: np.sign(x) * np.abs(x) ** 1.8, lambda x: np.sign(x) * np.abs(x) ** (1 / 1.8))
    return (cl.M_S_INV, cl.M_S, cl.srgb_dec, cl.srgb_enc)


def run(img_srgb, lut, spc):
    to_xyz, from_xyz, dec, enc = spc
    xyz = cl.srgb_dec(img_srgb) @ cl.M_S_INV.T
    t_in = enc(np.clip(xyz @ from_xyz.T, 0, 1))
    t_out = trilinear(lut, t_in)
    xyz2 = dec(np.clip(t_out, 0, 1)) @ to_xyz.T
    lin = xyz2 @ cl.M_S.T
    clipped = np.mean(np.any((lin < -1e-4) | (lin > 1 + 1e-4), -1))
    return np.clip(cl.srgb_enc(np.clip(lin, 0, 1)), 0, 1), clipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=os.path.abspath(os.path.join(HERE, '..', '..')))
    ap.add_argument('--space', default='pp18', choices=['pp18', 'srgb'])
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    out_dir = a.out or os.path.join(a.root, 'data/work/test_chart_pred', a.space)
    os.makedirs(out_dir, exist_ok=True)
    src = os.path.join(a.root, 'data/derived/test_chart_srgb16.tif')
    img, icc, _ = read_image(src)
    assert cl.read_icc(icc)['desc'].lower().find('srgb') >= 0
    prof_dir = os.path.join(a.root, 'data/raw/cp_demo/Profiles/Color Precision Demo - nonRAW')
    icc_out = srgb_profile()
    for fm in FILMS:
        for sc in SCANNERS:
            lut, meta = load_table(os.path.join(prof_dir, '%s +0EV %s.xmp' % (fm, sc)))
            out, clipped = run(img, lut, space(a.space))
            name = 'decoder-%s__%s__%s.tif' % (a.space, TOKEN[fm], sc)
            tifffile.imwrite(os.path.join(out_dir, name), np.round(out * 65535).astype(np.uint16), photometric='rgb',
                             compression='zlib', extratags=[(34675, 'B', len(icc_out), icc_out, True)])
            print('%-34s table prim/gamma/gamut=%s  pixels outside sRGB before clip: %.1f%%' % (name, meta, clipped * 100))


if __name__ == '__main__':
    main()
