"""Run ColorChecker 24 through Color Precision demo RGB tables (nonRAW).

Usage: python3 -I tools/cp_demo/measure.py <repo_root> [srgb]
Writes data/derived/cp_demo_patches.csv, cp_demo_anchors.csv; prints checks.
Table space: primaries enum 2 / gamma enum 2 read from the table, taken to be
ProPhoto (ROMM, D50) with plain 1.8 gamma; 'srgb' argument = sensitivity run
with sRGB primaries/gamma instead (not written to CSV).
"""
import csv, hashlib, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import struct
import crs_table

ROOT = sys.argv[1]
ALT = len(sys.argv) > 2 and sys.argv[2] == 'srgb'
PROF = os.path.join(ROOT, 'data/raw/cp_demo/Profiles')
NONRAW = os.path.join(PROF, 'Color Precision Demo - nonRAW')
FILMS = ['Portra 400', 'Pro 400H', 'Velvia 50', 'Gold pushed']
SCANNERS = ['Frontier', 'Noritsu']

# BabelColor ColorChecker averages (Pascale, "RGB coordinates of the Macbeth ColorChecker", 2006), Lab D50
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

D50 = (0.96422, 1.0, 0.82521)
M_PP = [[1.3459433, -0.2556075, -0.0511118], [-0.5445989, 1.5081673, 0.0205351], [0.0, 0.0, 1.2118128]]  # XYZ(D50)->ROMM
M_PP_INV = [[0.7976749, 0.1351917, 0.0313534], [0.2880402, 0.7118741, 0.0000857], [0.0, 0.0, 0.8252100]]
# sRGB via Bradford-adapted D50 matrices (Lindbloom)
M_S = [[3.1338561, -1.6168667, -0.4906146], [-0.9787684, 1.9161415, 0.0334540], [0.0719453, -0.2289914, 1.4052427]]
M_S_INV = [[0.4360747, 0.3850649, 0.1430804], [0.2225045, 0.7168786, 0.0606169], [0.0139322, 0.0971045, 0.7141733]]

def mul(m, v): return [sum(m[i][j] * v[j] for j in range(3)) for i in range(3)]
def f(t): return t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116
def fi(t): return t ** 3 if t ** 3 > 216 / 24389 else (116 * t - 16) / (24389 / 27)
def lab2xyz(L, a, b):
    fy = (L + 16) / 116
    return [D50[0] * fi(fy + a / 500), D50[1] * fi(fy), D50[2] * fi(fy - b / 200)]
def xyz2lab(X, Y, Z):
    fx, fy, fz = f(X / D50[0]), f(Y / D50[1]), f(Z / D50[2])
    return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)]
def enc(x):
    if ALT: return 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055
    return math.copysign(abs(x) ** (1 / 1.8), x)
def dec(x):
    if ALT: return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return math.copysign(abs(x) ** 1.8, x)
def lab2rgb(lab):
    return [enc(min(max(c, 0.0), 1.0)) for c in mul(M_S if ALT else M_PP, lab2xyz(*lab))]
def rgb2lab(rgb):
    return xyz2lab(*mul(M_S_INV if ALT else M_PP_INV, [dec(c) for c in rgb]))

def de2000(l1, l2):
    L1, a1, b1 = l1; L2, a2, b2 = l2
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2); Cm = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = a1 * (1 + G), a2 * (1 + G)
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360; h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dL, dC = L2 - L1, C2p - C1p
    dh = h2p - h1p
    if C1p * C2p == 0: dh = 0
    elif dh > 180: dh -= 360
    elif dh < -180: dh += 360
    dH = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dh / 2))
    Lm, Cmp = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0: hm = h1p + h2p
    elif abs(h1p - h2p) <= 180: hm = (h1p + h2p) / 2
    else: hm = (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2
    T = 1 - 0.17 * math.cos(math.radians(hm - 30)) + 0.24 * math.cos(math.radians(2 * hm)) \
        + 0.32 * math.cos(math.radians(3 * hm + 6)) - 0.20 * math.cos(math.radians(4 * hm - 63))
    SL = 1 + 0.015 * (Lm - 50) ** 2 / math.sqrt(20 + (Lm - 50) ** 2)
    SC, SH = 1 + 0.045 * Cmp, 1 + 0.015 * Cmp * T
    RT = -2 * math.sqrt(Cmp ** 7 / (Cmp ** 7 + 25 ** 7)) * math.sin(math.radians(60 * math.exp(-((hm - 275) / 25) ** 2)))
    return math.sqrt((dL / SL) ** 2 + (dC / SC) ** 2 + (dH / SH) ** 2 + RT * (dC / SC) * (dH / SH))

def load_table(path):
    _, refs, tabs = crs_table.read_xmp(path)
    d = crs_table.decode_table(tabs[refs['RGBTable']])
    btt, ver, dims, n = struct.unpack('<4I', d[:16])
    assert (btt, ver, dims) == (1, 1, 3), (btt, ver, dims)
    vals = struct.unpack('<%dh' % (n ** 3 * 3), d[16:16 + n ** 3 * 6])
    prim, gam, gamut, amin, amax = struct.unpack('<3I2d', d[16 + n ** 3 * 6:16 + n ** 3 * 6 + 28])
    # stored as int16 delta from the identity grid; order r (outer), g, b, channel
    lut = []
    k = 0
    for r in range(n):
        for g in range(n):
            for b in range(n):
                nom = (r, g, b)
                lut.append(tuple((nom[c] * 65535 / (n - 1) + vals[k + c]) / 65535 for c in range(3)))
                k += 3
    return dict(n=n, lut=lut, prim=prim, gamma=gam, gamut=gamut, amount=(amin, amax), digest=hashlib.md5(d).hexdigest())

def apply(t, rgb):
    n, lut = t['n'], t['lut']
    p = [min(max(c, 0.0), 1.0) * (n - 1) for c in rgb]
    i = [min(int(x), n - 2) for x in p]; fr = [p[c] - i[c] for c in range(3)]
    out = [0.0, 0.0, 0.0]
    for dr in (0, 1):
        for dg in (0, 1):
            for db in (0, 1):
                w = (fr[0] if dr else 1 - fr[0]) * (fr[1] if dg else 1 - fr[1]) * (fr[2] if db else 1 - fr[2])
                v = lut[((i[0] + dr) * n + i[1] + dg) * n + i[2] + db]
                for c in range(3): out[c] += w * v[c]
    return out

def hue(a, b): return math.degrees(math.atan2(b, a)) % 360
def dh(h1, h2): return (h2 - h1 + 180) % 360 - 180

T = {(fm, sc): load_table(os.path.join(NONRAW, '%s +0EV %s.xmp' % (fm, sc))) for fm in FILMS for sc in SCANNERS}
for k, t in T.items(): print('table', k, 'n=%d prim=%d gamma=%d gamut=%d amount=%s' % (t['n'], t['prim'], t['gamma'], t['gamut'], t['amount']))

# camera variants: is the table the same as nonRAW?
same = {}
for cam in sorted(os.listdir(PROF)):
    for fm in FILMS:
        for sc in SCANNERS:
            p = os.path.join(PROF, cam, '%s +0EV %s.xmp' % (fm, sc))
            if os.path.exists(p): same.setdefault(cam, []).append(load_table(p)['digest'] == T[(fm, sc)]['digest'])
for cam, v in same.items(): print('same table as nonRAW:', cam, '%d/%d' % (sum(v), len(v)))

# identity check: grey ramp in table space
print('\ngrey ramp: max chroma C*ab out, L in->out (5 steps)')
for k, t in T.items():
    cs, ls = [], []
    for s in range(1, 21):
        v = s / 20
        lo = rgb2lab(apply(t, [v, v, v])); li = rgb2lab([v, v, v])
        cs.append(math.hypot(lo[1], lo[2]))
        if s % 4 == 0: ls.append('%.0f->%.0f' % (li[0], lo[0]))
    print(' %-24s maxC=%.2f medC=%.2f  %s' % (k, max(cs), sorted(cs)[10], ' '.join(ls)))

out = {}
rows = []
for (fm, sc), t in T.items():
    for name, L, a, b in CC:
        o = rgb2lab(apply(t, lab2rgb((L, a, b))))
        out[(fm, sc, name)] = o
        rows.append([fm, sc, name, L, a, b] + ['%.2f' % x for x in o] + ['%.2f' % de2000((L, a, b), o)])
if ALT:
    for fm in FILMS:
        print(fm, ' '.join('%s a=%.1f b=%.1f' % (n, *out[(fm, 'Frontier', n)][1:]) for n in ('light skin', 'blue sky', 'foliage')))
    sys.exit()
with open(os.path.join(ROOT, 'data/derived/cp_demo_patches.csv'), 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(['film', 'scanner', 'patch', 'L_in', 'a_in', 'b_in', 'L_out', 'a_out', 'b_out', 'dE00'])
    w.writerows(rows)
print('\nmedian dE00 per profile (24 patches / 18 colour / 6 neutral)')
for (fm, sc) in T:
    d = [float(r[9]) for r in rows if r[0] == fm and r[1] == sc]
    md = lambda x: sorted(x)[len(x) // 2]
    print(' %-12s %-8s %.1f / %.1f / %.1f  max %.1f' % (fm, sc, md(d), md(d[:18]), md(d[18:]), max(d)))

# anchors
ANCH = [('skin_dark', 'dark skin'), ('skin_light', 'light skin'), ('sky', 'blue sky'), ('foliage', 'foliage'),
        ('neutral_8', 'neutral 8'), ('neutral_5', 'neutral 5'), ('neutral_3.5', 'neutral 3.5')]
with open(os.path.join(ROOT, 'data/derived/cp_demo_anchors.csv'), 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(['film', 'scanner', 'anchor', 'patch', 'L', 'a', 'b', 'C', 'h_deg', 'b_minus_a', 'dL', 'dC', 'dh_deg', 'dE00'])
    for fm in [None] + FILMS:
        for sc in ([''] if fm is None else SCANNERS):
            for an, pn in ANCH:
                ref = next(c[1:] for c in CC if c[0] == pn)
                o = ref if fm is None else out[(fm, sc, pn)]
                C, h = math.hypot(o[1], o[2]), hue(o[1], o[2])
                C0, h0 = math.hypot(ref[1], ref[2]), hue(ref[1], ref[2])
                w.writerow([fm or 'reference', sc, an, pn] + ['%.1f' % x for x in (*o, C, h, o[2] - o[1], o[0] - ref[0], C - C0, dh(h0, h))] + ['%.2f' % de2000(ref, o)])

# sectors: Noritsu vs Frontier, and Pro 400H vs Portra 400, on 18 colour patches, by hue of reference output
def sectors(pairs, label):
    S = {}
    for name, (o1, o2) in pairs.items():
        C1 = math.hypot(o1[1], o1[2])
        if C1 < 8: continue
        s = int(hue(o1[1], o1[2]) // 60)
        S.setdefault(s, []).append((dh(hue(o1[1], o1[2]), hue(o2[1], o2[2])), math.hypot(o2[1], o2[2]) / C1, o2[0] - o1[0]))
    print(label)
    for s in sorted(S):
        v = S[s]; m = lambda i: sum(x[i] for x in v) / len(v)
        print('  %3d-%3d n=%d dh=%+.1f C x%.2f dL=%+.1f' % (s * 60, s * 60 + 60, len(v), m(0), m(1), m(2)))
    return S

names = [c[0] for c in CC[:18]]
sectors({n: (out[('Portra 400', 'Frontier', n)], out[('Portra 400', 'Noritsu', n)]) for n in names}, '\nprofiles Portra 400 Frontier->Noritsu (CC24, sector by Frontier hue)')
for sc in SCANNERS:
    sectors({n: (out[('Portra 400', sc, n)], out[('Pro 400H', sc, n)]) for n in names}, 'profiles Portra 400 -> Pro 400H, %s' % sc)

# atlas: Portra 400 EV 0, Frontier -> Noritsu, same 74 SG patches
A = {}
for r in csv.DictReader(open(os.path.join(ROOT, 'data/derived/gate1_patches.csv'))):
    if r['film'] == 'Portra400' and r['ev_or_board'] == '0':
        A.setdefault((int(r['row']), int(r['col'])), {})[r['scanner']] = [float(r[x]) for x in 'Lab']
pairs = {k: (v['frontier'], v['noritsu']) for k, v in A.items() if len(v) == 2}
sectors(pairs, 'atlas scans Portra 400 EV0 Frontier->Noritsu (SG, n=%d patches, C>=8 only)' % len(pairs))
