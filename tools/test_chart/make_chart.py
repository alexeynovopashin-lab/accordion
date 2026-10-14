"""Build the test chart for measuring other programs' colour handling.

Usage: python3 -I tools/test_chart/make_chart.py [repo_root]
Writes data/derived/test_chart_srgb16.tif (16-bit RGB, sRGB ICC embedded, deflate) and
data/derived/test_chart_layout.csv (id, rect, intended and encoded Lab D50 / OkLab, group).

Groups (24 columns, one row per group; the wheel takes 6 rows):
  cc24    ColorChecker 24, Lab D50 averages of BabelColor (D. Pascale, "RGB coordinates of the
          Macbeth ColorChecker", 2006), same table as tools/cp_demo/measure.py
  grey21  neutral ramp, L* 0..100 step 5, a = b = 0
  skin24  Kosenko (docs/kosenko_notes.md, ch. 16): L 40/55/70/85 x (a,b) in
          (10,12) (15,16) (18,20) (20,17) (25,28) (-5,19)
  memory9 lips / sky / foliage: no independent source found; these are ColorChecker patches
          (moderate red ~ lips, blue sky, foliage) at L-12, +0, +12 with the same a, b.
          The +0 copy repeats a cc24 patch at another position (position check).
  wheel144  OkLab hue 0..345 step 15 (24) x L 0.45/0.65/0.85 x C 0.05/0.10; chroma is cut
          at the sRGB gamut edge (constant OkLab L and h), flag gamut_mapped
Out-of-gamut targets (Lab D50 beyond sRGB) are chroma-reduced at constant L and hue; 'intent'
columns keep the wanted colour, 'encoded' columns the colour actually in the file.
Field: neutral 18 % grey (linear Y = 0.18, sRGB code 0.4614).
"""
import csv
import os
import sys

import numpy as np
import tifffile
from PIL import Image, ImageCms, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import colorlib as cl

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

CC = [('dark skin', 37.986, 13.555, 14.059), ('light skin', 65.711, 18.13, 17.81),
      ('blue sky', 49.927, -4.88, -21.925), ('foliage', 43.139, -13.095, 21.905),
      ('blue flower', 55.112, 8.844, -25.399), ('bluish green', 70.719, -33.397, -0.199),
      ('orange', 62.661, 36.067, 57.096), ('purplish blue', 40.02, 10.41, -45.964),
      ('moderate red', 51.124, 48.239, 16.248), ('purple', 30.325, 22.976, -21.587),
      ('yellow green', 72.532, -23.709, 57.255), ('orange yellow', 71.941, 19.363, 67.857),
      ('blue', 28.778, 14.179, -50.297), ('green', 55.261, -38.342, 31.37),
      ('red', 42.101, 53.378, 28.19), ('yellow', 81.733, 4.039, 79.819),
      ('magenta', 51.935, 49.986, -14.574), ('cyan', 51.038, -28.631, -28.638),
      ('white 9.5', 96.539, -0.425, 1.186), ('neutral 8', 81.257, -0.638, -0.335),
      ('neutral 6.5', 66.766, -0.734, -0.504), ('neutral 5', 50.867, -0.153, -0.27),
      ('neutral 3.5', 35.656, -0.421, -1.231), ('black 2', 20.461, -0.079, -0.973)]
SKIN_AB = [(10, 12), (15, 16), (18, 20), (20, 17), (25, 28), (-5, 19)]
SKIN_L = [40, 55, 70, 85]
WHEEL_L = [0.45, 0.65, 0.85]
WHEEL_C = [0.05, 0.10]

COLS, PATCH, CELL_W, ROW_H = 24, 72, 88, 104
MARGIN_X, MARGIN_Y, HEADER_H = 40, 70, 26
FIELD_Y = 0.18


def lab_patch(name, group, source, lab):
    rgb, lab_enc, mapped = cl.lab_to_rgb_mapped(lab)
    return dict(name=name, group=group, source=source, lab_int=np.array(lab, float), rgb=rgb, mapped=mapped)


def build_patches():
    P = []
    for n, L, a, b in CC:
        P.append(lab_patch(n, 'cc24', 'BabelColor avg (Pascale 2006)', (L, a, b)))
    for s in range(21):
        P.append(lab_patch('grey L%d' % (s * 5), 'grey21', 'ramp L* step 5', (s * 5, 0, 0)))
    for L in SKIN_L:
        for a, b in SKIN_AB:
            P.append(lab_patch('skin L%d a%d b%d' % (L, a, b), 'skin24', 'Kosenko ch.16 (docs/kosenko_notes.md)', (L, a, b)))
    for obj, cc_name in (('lips', 'moderate red'), ('sky', 'blue sky'), ('foliage', 'foliage')):
        _, L, a, b = next(c for c in CC if c[0] == cc_name)
        for dL in (-12, 0, 12):
            P.append(lab_patch('%s (CC %s) dL%+d' % (obj, cc_name, dL), 'memory9',
                               'no independent source: ColorChecker patch, L shifted', (L + dL, a, b)))
    for L in WHEEL_L:
        for C in WHEEL_C:
            for k in range(24):
                h = k * 15.0
                def to_rgb(L_, C_, h_):
                    r = np.radians(h_)
                    return cl.oklab_to_srgb_lin(np.array([L_, C_ * np.cos(r), C_ * np.sin(r)]))
                C2, mapped = cl.map_chroma(to_rgb, (L, C, h))
                rgb = np.clip(to_rgb(L, C2, h), 0, 1)
                lab_int = cl.srgb_lin_to_lab(to_rgb(L, C, h))
                P.append(dict(name='wheel h%03d L%.2f C%.2f' % (h, L, C), group='wheel144',
                              source='OkLab hue x L x C', lab_int=lab_int, rgb=rgb, mapped=mapped,
                              ok_int=np.array([L, C * np.cos(np.radians(h)), C * np.sin(np.radians(h))])))
    return P


def main():
    P = build_patches()
    groups = []
    for p in P:
        if not groups or groups[-1][0] != p['group']:
            groups.append((p['group'], []))
        groups[-1][1].append(p)
    # geometry
    y = MARGIN_Y
    rows = []   # (group, header_y, [(patch, x, y)])
    pid = 0
    for g, items in groups:
        hy = y
        y += HEADER_H
        for r0 in range(0, len(items), COLS):
            for k, p in enumerate(items[r0:r0 + COLS]):
                pid += 1
                p['id'], p['x'], p['y'] = pid, MARGIN_X + k * CELL_W + (CELL_W - PATCH) // 2, y
            y += ROW_H
        rows.append((g, hy, len(items)))
    W, H = MARGIN_X * 2 + COLS * CELL_W, y + 30
    field = float(cl.srgb_enc(FIELD_Y))
    img = np.full((H, W, 3), field, float)
    for p in P:
        code = np.round(cl.srgb_enc(p['rgb']) * 65535)
        p['code'] = code.astype(int)
        p['lab_enc'] = cl.srgb_lin_to_lab(cl.srgb_dec(code / 65535))
        p['ok_enc'] = cl.srgb_lin_to_oklab(cl.srgb_dec(code / 65535))
        p.setdefault('ok_int', cl.srgb_lin_to_oklab(cl.lab_to_srgb_lin(p['lab_int'])))
        img[p['y']:p['y'] + PATCH, p['x']:p['x'] + PATCH] = code / 65535
    # labels and headers: drawn through a mask so the 16-bit patch pixels are never touched
    mask = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(mask)
    try:
        font, big = ImageFont.load_default(size=13), ImageFont.load_default(size=16)
    except TypeError:
        font = big = ImageFont.load_default()
    d.text((MARGIN_X, 22), 'Accordion test chart v1 - sRGB 16 bit, field = 18% grey - patch numbers are in test_chart_layout.csv',
           fill=255, font=big)
    titles = {'cc24': 'ColorChecker 24', 'grey21': 'Grey ramp L* 0..100', 'skin24': 'Skin (Kosenko ch.16): L 40/55/70/85 x 6 (a,b)',
              'memory9': 'Lips / sky / foliage (ColorChecker proxies, dL -12/0/+12)',
              'wheel144': 'OkLab wheel: 24 hues, rows = L .45/.65/.85 x C .05/.10'}
    for g, hy, n in rows:
        d.text((MARGIN_X, hy + 4), titles[g], fill=255, font=big)
    for p in P:
        s = str(p['id'])
        w = d.textlength(s, font=font)
        d.text((p['x'] + PATCH / 2 - w / 2, p['y'] + PATCH + 4), s, fill=255, font=font)
    m = np.asarray(mask, float)[..., None] / 255.0
    text_v = float(cl.srgb_enc(0.02))
    img = img * (1 - m) + text_v * m
    out16 = np.clip(np.round(img * 65535), 0, 65535).astype(np.uint16)
    for p in P:   # restore exact patch values (label masks never overlap, but be explicit)
        out16[p['y']:p['y'] + PATCH, p['x']:p['x'] + PATCH] = p['code']

    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    os.makedirs(os.path.join(ROOT, 'data/derived'), exist_ok=True)
    tif = os.path.join(ROOT, 'data/derived/test_chart_srgb16.tif')
    tifffile.imwrite(tif, out16, photometric='rgb', compression='zlib', resolution=(300, 300),
                     extratags=[(34675, 'B', len(icc), icc, True)])
    with open(os.path.join(ROOT, 'data/derived/test_chart_layout.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['id', 'group', 'name', 'source', 'x', 'y', 'w', 'h',
                    'L_intent', 'a_intent', 'b_intent', 'okL_intent', 'oka_intent', 'okb_intent',
                    'L_enc', 'a_enc', 'b_enc', 'okL_enc', 'oka_enc', 'okb_enc',
                    'gamut_mapped', 'dE00_intent_enc', 'R16', 'G16', 'B16', 'img_w', 'img_h'])
        for p in P:
            de = float(cl.de2000(p['lab_int'], p['lab_enc']))
            w.writerow([p['id'], p['group'], p['name'], p['source'], p['x'], p['y'], PATCH, PATCH]
                       + ['%.3f' % v for v in p['lab_int']] + ['%.4f' % v for v in p['ok_int']]
                       + ['%.3f' % v for v in p['lab_enc']] + ['%.4f' % v for v in p['ok_enc']]
                       + [int(p['mapped']), '%.2f' % de] + [int(v) for v in p['code']] + [W, H])
    n_map = sum(p['mapped'] for p in P)
    print('patches %d, image %dx%d, %s, %.2f MB' % (len(P), W, H, tif, os.path.getsize(tif) / 1e6))
    print('gamut-mapped patches: %d (' % n_map + ', '.join('%s:%d' % (g, sum(p['mapped'] for p in P if p['group'] == g)) for g, _ in groups) + ')')
    des = [float(cl.de2000(p['lab_int'], p['lab_enc'])) for p in P if p['mapped']]
    if des:
        print('intent vs encoded dE00 on mapped patches: median %.1f max %.1f' % (np.median(des), max(des)))


if __name__ == '__main__':
    main()
