"""Gate of iteration 1: how much does the scanner's auto-levelling erase film differences?
Small sample (22 frames of Charts), SG patches by the lattice of sg_lattice.py. Run from repo root:
    python3 tools/film_measure/gate1.py data/work/charts data/derived
Writes data/derived/gate1_patches.csv (Lab per frame per patch) and gate1_summary.csv; prints the numbers.
"""
import sys, os, io, csv, shutil, tempfile, itertools
import numpy as np, cv2
from PIL import Image, ImageCms
ROOT = sys.argv[1] if len(sys.argv) > 1 else 'data/work/charts'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'data/derived'
tmp = tempfile.mkdtemp(); shutil.copy(f'{ROOT}/frontier/p02/display.icc', tmp + '/charts.icc')
os.environ['CHARTS_EXTRACT'] = tmp
sys.path.insert(0, os.path.dirname(__file__))
import colorlib as m, find_plates as fp, holes as hl, sg_lattice as sg

# (scanner, page, k, film, ev) ; EV only where the board map is known (Portra 400), else None
P400_EV = {1: -3, 2: -1, 3: 0, 4: 1, 5: 2, 6: 3, 7: 4}
FR = []
for sc in ('frontier', 'noritsu'):
    FR += [(sc, 1, 2, 'Portra160', '1/125'), (sc, 7, 2, 'Ektar', '1/60'), (sc, 7, 3, 'Ektar30', '1/30'), (sc, 10, 3, 'Ultramax', '1/125')]
    FR += [(sc, 2, k, 'Portra400', P400_EV[k]) for k in range(1, 8)]
FILMS = ['Portra160', 'Portra400', 'Ektar', 'Ultramax']
REF = {'Portra160': 2, 'Portra400': 3, 'Ektar': 2, 'Ultramax': 3}

srgb = ImageCms.createProfile('sRGB'); icc_cache = {}
def load(path, folder):
    if folder not in icc_cache:
        p = f'{folder}/display.icc'
        icc_cache[folder] = ImageCms.ImageCmsProfile(io.BytesIO(open(p, 'rb').read()))
    return np.asarray(ImageCms.profileToProfile(Image.open(path).convert('RGB'), icc_cache[folder], srgb, outputMode='RGB'))

def find_lattice(rgb):
    """sg_lattice.lattice with the black-plate threshold relaxed when the frame is over/under-exposed."""
    last = None
    for thr in (70, 50, 90, 110, 40):
        sg.plates = lambda r, t=thr: _plates(r, t)
        sg.holes = lambda r, b, t=thr: hl.holes(r, b, thr=t)
        try:
            cen, size, P, th, n = sg.lattice(rgb)
            if n >= 100: return cen, size, P, th, n, thr
            last = (cen, size, P, th, n, thr)
        except Exception as e:
            last = None
    return last
def _plates(rgb, thr):
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY); mk = (g < thr).astype(np.uint8) * 255
    mk = cv2.morphologyEx(mk, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(mk)
    out = [(i, *st[i][:4], st[i][4]) for i in range(1, n) if st[i][4] > 150000 and st[i][2] > 600 and st[i][3] > 400]
    return lab, out

def lab_grid(rgb, cen, size, half=0.22, off=(0, 0)):
    h = int(size * half); out = np.zeros((10, 14, 3))
    for j in range(10):
        for i in range(14):
            x, y = (cen[j, i] + np.array(off)).round().astype(int)
            out[j, i] = m.lab(*np.median(rgb[y - h:y + h + 1, x - h:x + h + 1].reshape(-1, 3), 0))
    return out

def de(A, B, mask, keepL=True):
    a = A[mask]; b = B[mask]
    return np.array([m.de2000(x[0], x[1], x[2], x[0] if not keepL else y[0], y[1], y[2]) for x, y in zip(a, b)])

# ---- sample frames
data = {}; info = []
for sc, pg, k, film, ev in FR:
    folder = f'{ROOT}/{sc}/p{pg:02d}'
    rgb = load(f'{folder}/f_{k}.png', folder)
    r = find_lattice(rgb)
    if r is None: print('LATTICE FAILED', sc, pg, k); continue
    cen, size, P, th, n, thr = r
    data[(sc, film, ev)] = (rgb, cen, size)
    info.append((sc, film, ev, rgb.shape[1], rgb.shape[0], P, np.rad2deg(th), n, thr))
    print('%-8s %-10s ev=%-5s %dx%d pitch %.1f rot %.2f holes %d thr %d' % (sc, film, ev, rgb.shape[1], rgb.shape[0], P, np.rad2deg(th), n, thr))
os.makedirs(f'{ROOT}/_gate1', exist_ok=True)
for key in [('frontier', 'Ektar', '1/60'), ('noritsu', 'Ultramax', '1/125'), ('noritsu', 'Portra400', -3)]:
    if key in data:
        rgb, cen, size = data[key]; sg.overlay(rgb, cen, size, f'{ROOT}/_gate1/ov_{key[0]}_{key[1]}_{key[2]}.png'.replace('/', '/', 1).replace('1/60', '1-60').replace('1/125', '1-125'))

def grids(off=(0, 0), half=0.22):
    return {k: lab_grid(v[0], v[1], v[2], half, off) for k, v in data.items()}
G = grids()

# ---- fixed patch sets from the reference (Portra 400 EV 0, both scanners; same rule as compare_scanners.py)
Ln = G[('noritsu', 'Portra400', 0)]; Lf = G[('frontier', 'Portra400', 0)]
C = lambda L: np.hypot(L[..., 1], L[..., 2])
neu = (C(Ln) < 7) & (Ln[..., 0] > 12) & (C(Lf) < 12)
chrom = (Lf[..., 0] > 15) & (Ln[..., 0] > 15) & (~neu) & (C(Ln) > 12)
print('\nneutral patches %d (L %.0f-%.0f), chromatic %d' % (neu.sum(), Ln[..., 0][neu].min(), Ln[..., 0][neu].max(), chrom.sum()))

def stat(d): return (np.median(d), np.percentile(d, 90), len(d)) if len(d) else (np.nan, np.nan, 0)
def fmt(s): return '%.2f / %.2f (n=%d)' % s

def series(G, sc):
    rows = []
    ref = G[(sc, 'Portra400', 0)]
    for ev in (-3, -1, 1, 2, 3, 4):
        g = G[(sc, 'Portra400', ev)]
        row = [ev]
        for mk in (neu, chrom):
            for keepL in (True, False): row.append(stat(de(g, ref, mk, keepL)))
        rows.append(row)
    return rows
def pairs_scanners(G, evs=None):
    out = {}
    for film, ev0 in [('Portra160', '1/125'), ('Portra400', 0), ('Ektar', '1/60'), ('Ultramax', '1/125')]:
        out[film] = {(nm, kl): de(G[('frontier', film, ev0)], G[('noritsu', film, ev0)], mk, kl)
                     for nm, mk in (('neu', neu), ('chrom', chrom)) for kl in (True, False)}
    return out
def pairs_films(G, sc):
    ev0 = {'Portra160': '1/125', 'Portra400': 0, 'Ektar': '1/60', 'Ultramax': '1/125'}
    out = {}
    for a, b in itertools.combinations(FILMS, 2):
        out[(a, b)] = {(nm, kl): de(G[(sc, a, ev0[a])], G[(sc, b, ev0[b])], mk, kl)
                       for nm, mk in (('neu', neu), ('chrom', chrom)) for kl in (True, False)}
    return out
def pool(dd, nm, kl): return np.concatenate([v[(nm, kl)] for v in dd.values()])

summary = []
def report(G, tag):
    res = {}
    S = pairs_scanners(G)
    res['b'] = {(nm, kl): pool(S, nm, kl) for nm in ('neu', 'chrom') for kl in (True, False)}
    res['v_fr'] = {(nm, kl): pool(pairs_films(G, 'frontier'), nm, kl) for nm in ('neu', 'chrom') for kl in (True, False)}
    res['v_no'] = {(nm, kl): pool(pairs_films(G, 'noritsu'), nm, kl) for nm in ('neu', 'chrom') for kl in (True, False)}
    res['v'] = {k: np.concatenate([res['v_fr'][k], res['v_no'][k]]) for k in res['b']}
    return res, S
R, S0 = report(G, 'base')

print('\n=== (a) series Portra 400 inside one scanner: dE vs EV 0 frame; median / p90 (n)  [neutrals+L | neutrals no L | colour+L | colour no L]')
for sc in ('frontier', 'noritsu'):
    print(sc)
    for row in series(G, sc): print('  EV %+d: ' % row[0] + ' | '.join(fmt(s) for s in row[1:]))
print('\n=== grey patches (neutral set): median L*, median C* per frame (flattening)')
for sc in ('frontier', 'noritsu'):
    print(sc, ' '.join('EV%+d: L %.0f C %.1f' % (ev, np.median(G[(sc, 'Portra400', ev)][..., 0][neu]), np.median(C(G[(sc, 'Portra400', ev)])[neu])) for ev in (-3, -1, 0, 1, 2, 3, 4)))
print('\n=== (b) Frontier vs Noritsu, same film same EV')
for film, v in S0.items(): print('  %-10s neu(L) %s | neu(noL) %s | col(L) %s | col(noL) %s' % (film, *[fmt(stat(v[(nm, kl)])) for nm in ('neu', 'chrom') for kl in (True, False)]))
print('  POOLED     ' + ' | '.join(fmt(stat(R['b'][(nm, kl)])) for nm in ('neu', 'chrom') for kl in (True, False)))
print('\n=== (c) film vs film, same scanner, same EV (6 pairs per scanner)')
for sc in ('frontier', 'noritsu'):
    PF = pairs_films(G, sc)
    for (a, b), v in PF.items(): print('  %-8s %-9s-%-9s neu(L) %s | col(L) %s | col(noL) %s' % (sc, a, b, fmt(stat(v[('neu', True)])), fmt(stat(v[('chrom', True)])), fmt(stat(v[('chrom', False)]))))
    print('  %-8s POOLED' % sc, ' | '.join(fmt(stat(R['v_' + sc[:2] if False else ('v_fr' if sc == 'frontier' else 'v_no')][(nm, kl)])) for nm in ('neu', 'chrom') for kl in (True, False)))
print('  BOTH POOLED (c)  ' + ' | '.join(fmt(stat(R['v'][(nm, kl)])) for nm in ('neu', 'chrom') for kl in (True, False)))
print('  (b) POOLED       ' + ' | '.join(fmt(stat(R['b'][(nm, kl)])) for nm in ('neu', 'chrom') for kl in (True, False)))
# extra (b): all 7 EV of Portra 400
ex = {(nm, kl): np.concatenate([de(G[('frontier', 'Portra400', ev)], G[('noritsu', 'Portra400', ev)], mk, kl) for ev in P400_EV.values()])
      for nm, mk in (('neu', neu), ('chrom', chrom)) for kl in (True, False)}
print('  (b) Portra 400, all 7 EV pooled ' + ' | '.join(fmt(stat(ex[k])) for k in ex))

# Ektar sensitivity: ISO-equivalent frame (1/30) instead of 1/60
ev0 = {'Portra160': '1/125', 'Portra400': 0, 'Ektar30': '1/30', 'Ultramax': '1/125'}
F2 = ['Portra160', 'Portra400', 'Ektar30', 'Ultramax']
v2 = {nm_kl: np.concatenate([de(G[(sc, a, ev0[a])], G[(sc, b, ev0[b])], mk, kl) for sc in ('frontier', 'noritsu') for a, b in itertools.combinations(F2, 2)])
      for nm_kl, (mk, kl) in {('neu', True): (neu, True), ('chrom', True): (chrom, True), ('chrom', False): (chrom, False)}.items()}
b2 = np.concatenate([de(G[('frontier', f, ev0[f])], G[('noritsu', f, ev0[f])], chrom, True) for f in F2])
print('\n=== sensitivity: Ektar at 1/30 (ISO-equivalent) instead of 1/60: (c) neu(L) %s | col(L) %s | col(noL) %s ; (b) col(L) %s' % (
    fmt(stat(v2[('neu', True)])), fmt(stat(v2[('chrom', True)])), fmt(stat(v2[('chrom', False)])), fmt(stat(b2))))

# ---- labelling error: shift lattice / change window
print('\n=== labelling error: frame shifted / window size changed; (b) col(L) and (c) col(L) medians, (c)-(b)')
var = [((0, 0), 0.22)] + [(o, 0.22) for o in [(3, 0), (-3, 0), (0, 3), (0, -3), (2, 2), (-2, -2), (2, -2), (-2, 2)]] + [((0, 0), 0.16), ((0, 0), 0.30)]
tab = []
for off, half in var:
    Gv = grids(off, half); Rv, _ = report(Gv, 'v')
    sb, sv = stat(Rv['b'][('chrom', True)]), stat(Rv['v'][('chrom', True)])
    nb, nv = stat(Rv['b'][('neu', True)]), stat(Rv['v'][('neu', True)])
    tab.append((off, half, nb[0], nv[0], sb[0], sv[0], sb[1], sv[1]))
    print('  off %-8s half %.2f | neu med (b) %.2f (c) %.2f | col med (b) %.2f (c) %.2f | col p90 (b) %.2f (c) %.2f' % (str(off), half, *tab[-1][2:]))
t = np.array([x[2:] for x in tab])
print('  range over variants: neu med (b) %.2f-%.2f (c) %.2f-%.2f | col med (b) %.2f-%.2f (c) %.2f-%.2f | col p90 (b) %.2f-%.2f (c) %.2f-%.2f' % tuple(
    v for i in range(6) for v in (t[:, i].min(), t[:, i].max())))

# ---- tables
os.makedirs(OUT, exist_ok=True)
with open(f'{OUT}/gate1_patches.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['scanner', 'film', 'ev_or_board', 'row', 'col', 'L', 'a', 'b', 'set'])
    for (sc, film, ev), g in sorted(G.items(), key=lambda x: str(x[0])):
        for j in range(10):
            for i in range(14):
                s = 'neutral' if neu[j, i] else ('chroma' if chrom[j, i] else 'other')
                w.writerow([sc, film, ev, j, i, *np.round(g[j, i], 2), s])
with open(f'{OUT}/gate1_summary.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['question', 'patch_set', 'with_lightness', 'n', 'median_dE00', 'p90_dE00'])
    for q, d in (('b_scanner_vs_scanner', R['b']), ('c_film_vs_film_same_scanner', R['v'])):
        for (nm, kl), arr in d.items():
            s = stat(arr); w.writerow([q, nm, kl, s[2], round(s[0], 2), round(s[1], 2)])
print('\nwrote', OUT)
