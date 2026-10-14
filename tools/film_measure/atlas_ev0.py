"""Atlas step 1: one "0 EV" frame per film (12 films), Frontier, with Noritsu as a cross-check.
SG patches by the same lattice as gate1.py (functions copied, gate1.py untouched). Run from repo root:
    python3 tools/film_measure/atlas_ev0.py data/work/charts data/derived
Writes data/derived/frontier_ev0_patches.csv (both scanners) and frontier_ev0_summary.csv; prints the numbers.
"0 EV" anchor: Portra 400 at f/4 1/125 is EV 0 (page title). Same light, f/4 on every board, so a film of
speed N is at EV 0 at 1/125 * 400/N. 'title' = also confirmed by the EV list in the page title;
'iso' = by speed only; 'conditional' = no honest anchor (see ANCHOR notes).
"""
import sys, os, io, csv, math, shutil, tempfile, statistics as st
import numpy as np, cv2
from PIL import Image, ImageCms
ROOT = sys.argv[1] if len(sys.argv) > 1 else 'data/work/charts'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'data/derived'
tmp = tempfile.mkdtemp(); shutil.copy(f'{ROOT}/frontier/p02/display.icc', tmp + '/charts.icc')
os.environ['CHARTS_EXTRACT'] = tmp
sys.path.insert(0, os.path.dirname(__file__))
import colorlib as m, holes as hl, sg_lattice as sg

# film, page, frame k (same k on both scanners, checked by board), shutter, anchor
FILMS = [('Portra160', 1, 2, '1/125', 'conditional'),   # board says f 2.8/4: ISO rule gives 1/60 (f/4) or 1/125 (f/2.8)
         ('Portra400', 2, 3, '1/125', 'title'),
         ('Portra400push', 3, 3, '1/250', 'iso'),        # rated 800
         ('Portra800', 4, 3, '1/250', 'iso'),
         ('Gold', 5, 3, '1/60', 'iso'),                  # Gold 200
         ('Goldpush', 6, 3, '1/125', 'iso'),             # rated 400
         ('Ektar', 7, 3, '1/30', 'iso'),                 # gate1 used 1/60 (#2); ISO 100 -> 1/30 (#3)
         ('Ektachrome', 8, 4, '1/30', 'title'),
         ('Cross', 9, 4, '1/30', 'conditional'),         # E100 in C-41: effective speed unknown, 1/30 = nominal 100
         ('Ultramax', 10, 3, '1/125', 'title'),
         ('Colorplus', 11, 3, '1/60', 'title'),
         ('ProImage', 12, 3, '1/30', 'iso')]
P400_SERIES = {1: -3, 2: -1, 3: 0, 4: 1, 5: 2, 6: 3, 7: 4}

srgb = ImageCms.createProfile('sRGB'); icc_cache = {}
def load(path, folder):
    if folder not in icc_cache:
        icc_cache[folder] = ImageCms.ImageCmsProfile(io.BytesIO(open(f'{folder}/display.icc', 'rb').read()))
    return np.asarray(ImageCms.profileToProfile(Image.open(path).convert('RGB'), icc_cache[folder], srgb, outputMode='RGB'))
def _plates(rgb, thr):
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY); mk = (g < thr).astype(np.uint8) * 255
    mk = cv2.morphologyEx(mk, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    n, lab, stt, cen = cv2.connectedComponentsWithStats(mk)
    return lab, [(i, *stt[i][:4], stt[i][4]) for i in range(1, n) if stt[i][4] > 150000 and stt[i][2] > 600 and stt[i][3] > 400]
def find_lattice(rgb):
    last = None
    for thr in (70, 50, 90, 110, 40):
        sg.plates = lambda r, t=thr: _plates(r, t)
        sg.holes = lambda r, b, t=thr: hl.holes(r, b, thr=t)
        try:
            cen, size, P, th, n = sg.lattice(rgb)
            if n >= 100: return cen, size, P, th, n, thr
            last = (cen, size, P, th, n, thr)
        except Exception:
            pass
    return last
def lab_grid(rgb, cen, size, half=0.22):
    h = int(size * half); out = np.zeros((10, 14, 3))
    for j in range(10):
        for i in range(14):
            x, y = cen[j, i].round().astype(int)
            out[j, i] = m.lab(*np.median(rgb[y - h:y + h + 1, x - h:x + h + 1].reshape(-1, 3), 0))
    return out

frames = [(sc, f, pg, k, sh, an) for sc in ('frontier', 'noritsu') for f, pg, k, sh, an in FILMS]
frames += [(sc, 'Portra400_ev%+d' % ev, 2, k, None, 'series') for sc in ('frontier', 'noritsu') for k, ev in P400_SERIES.items() if ev in (-1, 1)]
frames += [('noritsu', 'Noritsu_p1_dup%d' % k, 1, k, None, 'dup') for k in (4, 5)]
G = {}; OV = {}
for sc, f, pg, k, sh, an in frames:
    folder = f'{ROOT}/{sc}/p{pg:02d}'
    rgb = load(f'{folder}/f_{k}.png', folder); r = find_lattice(rgb)
    if r is None: print('LATTICE FAILED', sc, f); continue
    cen, size, P, th, n, thr = r
    G[(sc, f)] = lab_grid(rgb, cen, size); OV[(sc, f)] = (rgb, cen, size)
    print('%-8s %-16s p%d #%d pitch %.1f rot %.2f holes %d thr %d' % (sc, f, pg, k, P, np.rad2deg(th), n, thr))
os.makedirs(f'{ROOT}/_atlas_ev0', exist_ok=True)
for key in [('frontier', 'Ektachrome'), ('frontier', 'Cross'), ('frontier', 'Gold'), ('noritsu', 'ProImage')]:
    if key in OV: sg.overlay(*OV[key], f'{ROOT}/_atlas_ev0/ov_{key[0]}_{key[1]}.png')

# patch sets: same rule as gate1.py (reference Portra 400 EV 0, both scanners)
Ln = G[('noritsu', 'Portra400')]; Lf = G[('frontier', 'Portra400')]
C = lambda L: np.hypot(L[..., 1], L[..., 2])
neu = (C(Ln) < 7) & (Ln[..., 0] > 12) & (C(Lf) < 12)
chrom = (Lf[..., 0] > 15) & (Ln[..., 0] > 15) & (~neu) & (C(Ln) > 12)
print('neutral %d, chromatic %d' % (neu.sum(), chrom.sum()))

# reuse check against gate1_patches.csv
g1 = {}
for r in csv.DictReader(open(f'{OUT}/gate1_patches.csv')):
    g1[(r['scanner'], r['film'], r['ev_or_board'], int(r['row']), int(r['col']))] = np.array([float(r['L']), float(r['a']), float(r['b'])])
for mine, (gf, gev) in {'Portra160': ('Portra160', '1/125'), 'Portra400': ('Portra400', '0'), 'Ektar': ('Ektar30', '1/30'), 'Ultramax': ('Ultramax', '1/125')}.items():
    for sc in ('frontier', 'noritsu'):
        d = [np.abs(G[(sc, mine)][j, i] - g1[(sc, gf, gev, j, i)]).max() for j in range(10) for i in range(14) if (sc, gf, gev, j, i) in g1]
        print('reuse check %s %s: max |dLab| vs gate1 = %.3f over %d' % (sc, mine, max(d), len(d)))

with open(f'{OUT}/frontier_ev0_patches.csv', 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(['scanner', 'film', 'page', 'frame', 'shutter', 'anchor', 'row', 'col', 'L', 'a', 'b', 'set'])
    for sc, f, pg, k, sh, an in frames:
        if (sc, f) not in G or an in ('series', 'dup'): continue
        for j in range(10):
            for i in range(14):
                L, a, b = G[(sc, f)][j, i]
                w.writerow([sc, f, pg, k, sh, an, j, i, '%.2f' % L, '%.2f' % a, '%.2f' % b, 'neutral' if neu[j, i] else 'chroma' if chrom[j, i] else 'other'])

def lch(a, b): return math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360
idx = [(j, i) for j in range(10) for i in range(14) if chrom[j, i]]
nidx = [(j, i) for j in range(10) for i in range(14) if neu[j, i]]
refmean = {p: (Lf[p] + Ln[p]) / 2 for p in idx}
sector = {p: int(lch(*refmean[p][1:])[1] // 60) for p in idx}
def compare(sc, f, ref='Portra400'):
    A, R = G[(sc, f)], G[(sc, ref)]
    dc = [m.de2000(*A[p], *R[p]) for p in idx]; dn = [m.de2000(*A[p], *R[p]) for p in nidx]
    sec = {}
    for s in range(6):
        ps = [p for p in idx if sector[p] == s]
        if not ps: continue
        dh = [((lch(*A[p][1:])[1] - lch(*R[p][1:])[1] + 180) % 360) - 180 for p in ps]
        cx = [lch(*A[p][1:])[0] / lch(*R[p][1:])[0] for p in ps]
        sec[s] = (len(ps), st.mean(dh), st.median(cx))
    return st.median(dc), np.percentile(dc, 90), st.median(dn), sec
res = {}; rows = []
print('\n=== film vs Portra 400, same scanner (chroma median/p90 dE2000, neutral median) ===')
for f, *_ in FILMS:
    if f == 'Portra400': continue
    for sc in ('frontier', 'noritsu'):
        if (sc, f) not in G: continue
        r = compare(sc, f); res[(sc, f)] = r
        secs = ' '.join('%d:%+.1f/x%.2f' % (s * 60, v[1], v[2]) for s, v in r[3].items())
        print('%-14s %-8s chroma %.2f / %.2f  neutral %.2f | %s' % (f, sc, r[0], r[1], r[2], secs))
        for s, v in r[3].items(): rows.append([sc, f, s * 60, v[0], '%.2f' % v[1], '%.3f' % v[2], '%.2f' % r[0], '%.2f' % r[1], '%.2f' % r[2]])
print('\nsector sizes (n chroma patches):', {s * 60: sum(1 for p in idx if sector[p] == s) for s in range(6)})
print('\n=== noise: Portra 400 EV -1 / +1 vs EV 0, same scanner ===')
for sc in ('frontier', 'noritsu'):
    for ev in ('Portra400_ev-1', 'Portra400_ev+1'):
        if (sc, ev) in G:
            r = compare(sc, ev); print('%-8s %s chroma %.2f / %.2f neutral %.2f | %s' % (sc, ev, r[0], r[1], r[2], ' '.join('%d:%+.1f/x%.2f' % (s * 60, v[1], v[2]) for s, v in r[3].items())))
if ('noritsu', 'Noritsu_p1_dup4') in G:
    a, b = G[('noritsu', 'Noritsu_p1_dup4')], G[('noritsu', 'Noritsu_p1_dup5')]
    print('Noritsu p1 #4 vs #5: max |dLab| = %.4f' % np.abs(a - b).max())

def ranks(x):
    o = sorted(range(len(x)), key=lambda i: x[i]); r = [0] * len(x)
    for pos, i in enumerate(o): r[i] = pos + 1
    return r
def spearman(x, y):
    rx, ry = ranks(x), ranks(y); mx = st.mean(rx)
    return sum((a - mx) * (b - mx) for a, b in zip(rx, ry)) / math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - mx) ** 2 for b in ry))
fl = [f for f, *_ in FILMS if f != 'Portra400' and ('frontier', f) in res and ('noritsu', f) in res]
for nm, k in (('chroma median', 0), ('neutral median', 2)):
    x = [res[('frontier', f)][k] for f in fl]; y = [res[('noritsu', f)][k] for f in fl]
    print('\nSpearman Frontier vs Noritsu, %s dE to Portra400, %d films: %.2f' % (nm, len(fl), spearman(x, y)))
    print('  order Fr:', [fl[i] for i in sorted(range(len(fl)), key=lambda i: x[i])])
    print('  order No:', [fl[i] for i in sorted(range(len(fl)), key=lambda i: y[i])])
fl2 = [f for f in fl if f not in ('Portra160', 'Cross')]
x = [res[('frontier', f)][0] for f in fl2]; y = [res[('noritsu', f)][0] for f in fl2]
print('Spearman chroma, without conditional anchors (%d films): %.2f' % (len(fl2), spearman(x, y)))
# per-sector agreement across scanners (hue-shift sign, chroma side of 1)
agree = tot = 0
for f in fl:
    for s in range(6):
        a, b = res[('frontier', f)][3].get(s), res[('noritsu', f)][3].get(s)
        if not a or a[0] < 3: continue
        tot += 1; agree += (a[1] * b[1] > 0) and ((a[2] - 1) * (b[2] - 1) > 0)
print('sectors (n>=3) with same hue-shift sign and same chroma side on both scanners: %d/%d' % (agree, tot))

print('\n=== median chroma of chromatic patches, all 12 films ===')
for sc in ('frontier', 'noritsu'):
    cs = [math.hypot(*G[(sc, f)][p][1:]) for f, *_ in FILMS if (sc, f) in G for p in idx]
    print('%-8s median C %.1f  (n=%d)' % (sc, st.median(cs), len(cs)))
per = [math.hypot(*G[('frontier', f)][p][1:]) / math.hypot(*G[('noritsu', f)][p][1:]) for f, *_ in FILMS for p in idx if ('frontier', f) in G and ('noritsu', f) in G]
print('paired C ratio Frontier/Noritsu: median %.2f, share > 1: %.0f%%' % (st.median(per), 100 * sum(v > 1 for v in per) / len(per)))
with open(f'{OUT}/frontier_ev0_summary.csv', 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(['scanner', 'film', 'sector_from_deg', 'n', 'mean_dhue_deg', 'median_chroma_ratio', 'dE_chroma_median', 'dE_chroma_p90', 'dE_neutral_median'])
    w.writerows(rows)
