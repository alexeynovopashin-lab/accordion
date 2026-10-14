"""Measure the test chart after another program has processed it.

Usage: python3 -I tools/test_chart/measure_chart.py [--root DIR] [--out CSV] [--selfcheck] FILE_OR_DIR...
File names: cameraraw__<film>__<scanner>.tif -> program 'cameraraw', variant '<film>__<scanner>'.
Names without '__' (test_chart_srgb16.tif, pred__...) -> program = first part, variant = rest.
Reads 8/16-bit TIFF, uses the embedded ICC (matrix/TRC; none -> assumed sRGB, flagged),
takes the central 50 % of every patch (mean in linear light), converts to Lab D50.
Output columns: program, variant, id, group, name, L/a/b before (encoded in the source
file) and after, dL, dE00, dh_deg (hue shift, only where C_before >= 3), chroma_ratio.
--selfcheck: source file against the layout; exit 1 when max dE00 >= 0.5 (patches that
were gamut-mapped are compared with their encoded colour, intent shown separately).
"""
import argparse
import csv
import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import colorlib as cl

DEF_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MIN_C = 3.0   # below this chroma a hue shift / chroma ratio is not meaningful


def load_layout(root):
    with open(os.path.join(root, 'data/derived/test_chart_layout.csv')) as fh:
        return list(csv.DictReader(fh))


def read_image(path):
    with tifffile.TiffFile(path) as t:
        pg = t.pages[0]
        icc = pg.tags['InterColorProfile'].value if 'InterColorProfile' in pg.tags else None
        arr = pg.asarray()
    if arr.ndim == 3 and arr.shape[0] in (3, 4) and arr.shape[-1] not in (3, 4):
        arr = np.moveaxis(arr, 0, -1)
    arr = arr[..., :3]
    scale = 65535.0 if arr.dtype == np.uint16 else 255.0 if arr.dtype == np.uint8 else 1.0
    return arr.astype(np.float64) / scale, (bytes(icc) if icc is not None else None), arr.dtype


def srgb_profile():
    from PIL import ImageCms
    return ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()


def measure_file(path, layout, window=0.5):
    rgb, icc, dt = read_image(path)
    note = ''
    if icc is None:
        icc, note = srgb_profile(), 'no ICC, sRGB assumed'
    prof = cl.read_icc(icc)
    H, W = rgb.shape[:2]
    # layout was made for the original size; scale if the program resized the file
    sx = sy = 1.0
    ref_w, ref_h = int(layout[0]['img_w']), int(layout[0]['img_h'])
    if (W, H) != (ref_w, ref_h):
        sx, sy = W / ref_w, H / ref_h
        note = (note + '; ' if note else '') + 'size %dx%d != %dx%d, rects scaled' % (W, H, ref_w, ref_h)
    labs = []
    for r in layout:
        x, y, w, h = int(r['x']) * sx, int(r['y']) * sy, int(r['w']) * sx, int(r['h']) * sy
        m = (1 - window) / 2
        x0, x1 = int(round(x + w * m)), int(round(x + w * (1 - m)))
        y0, y1 = int(round(y + h * m)), int(round(y + h * (1 - m)))
        win = rgb[y0:y1, x0:x1].reshape(-1, 3)
        lin = np.stack([prof['trc'][c](win[:, c]) for c in range(3)], -1).mean(0)
        labs.append(cl.xyz_to_lab(lin @ prof['M'].T))
    return np.array(labs), dict(icc=prof['desc'], dtype=str(dt), note=note, size=(W, H))


def split_name(path):
    stem = os.path.splitext(os.path.basename(path))[0]
    parts = stem.split('__', 1)
    return parts[0], (parts[1] if len(parts) > 1 else '')


def rows_for(path, layout, labs):
    prog, var = split_name(path)
    before = np.array([[float(r['L_enc']), float(r['a_enc']), float(r['b_enc'])] for r in layout])
    de = cl.de2000(before, labs)
    c0, c1 = np.hypot(before[:, 1], before[:, 2]), np.hypot(labs[:, 1], labs[:, 2])
    h0, h1 = cl.hue_deg(before[:, 1], before[:, 2]), cl.hue_deg(labs[:, 1], labs[:, 2])
    out = []
    for i, r in enumerate(layout):
        ok = c0[i] >= MIN_C
        out.append([prog, var, r['id'], r['group'], r['name']]
                   + ['%.2f' % v for v in before[i]] + ['%.2f' % v for v in labs[i]]
                   + ['%.2f' % (labs[i, 0] - before[i, 0]), '%.2f' % de[i],
                      '%.1f' % cl.hue_diff(h0[i], h1[i]) if ok else '', '%.3f' % (c1[i] / c0[i]) if ok else ''])
    return out, de


HEAD = ['program', 'variant', 'id', 'group', 'name', 'L_before', 'a_before', 'b_before',
        'L_after', 'a_after', 'b_after', 'dL', 'dE00', 'dh_deg', 'chroma_ratio']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inputs', nargs='+')
    ap.add_argument('--root', default=DEF_ROOT)
    ap.add_argument('--out', default=None)
    ap.add_argument('--selfcheck', action='store_true')
    a = ap.parse_args()
    files = []
    for p in a.inputs:
        files += sorted(os.path.join(p, f) for f in os.listdir(p) if f.lower().endswith(('.tif', '.tiff'))) if os.path.isdir(p) else [p]
    layout = load_layout(a.root)
    allrows, status = [], 0
    for f in files:
        labs, info = measure_file(f, layout)
        rows, de = rows_for(f, layout, labs)
        allrows += rows
        print('%-44s icc=%s %s dE00 median %.2f p90 %.2f max %.2f %s' % (
            os.path.basename(f), info['icc'], info['dtype'], np.median(de), np.percentile(de, 90), de.max(), info['note']))
        if a.selfcheck:
            intent = np.array([[float(r['L_intent']), float(r['a_intent']), float(r['b_intent'])] for r in layout])
            mapped = np.array([r['gamut_mapped'] == '1' for r in layout])
            di = cl.de2000(intent, labs)
            print('  self-check vs encoded: max %.3f (limit 0.5) -> %s' % (de.max(), 'OK' if de.max() < 0.5 else 'FAIL'))
            print('  vs intent: in-gamut patches max %.3f; %d gamut-mapped patches median %.2f max %.2f'
                  % (di[~mapped].max(), mapped.sum(), np.median(di[mapped]), di[mapped].max()))
            status |= int(de.max() >= 0.5)
    if a.out:
        with open(a.out, 'w', newline='') as fh:
            w = csv.writer(fh)
            w.writerow(HEAD)
            w.writerows(allrows)
        print('wrote', a.out, len(allrows), 'rows')
    sys.exit(status)


if __name__ == '__main__':
    main()
