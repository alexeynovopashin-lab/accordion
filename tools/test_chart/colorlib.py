"""Colour maths shared by make_chart.py, measure_chart.py, predict_decoder.py (numpy).

Lab = CIELAB D50, XYZ relative to D50, sRGB through Bradford-adapted D50 matrices
(same constants as tools/cp_demo/measure.py), OkLab = Ottosson 2020 from linear sRGB.
ICC reading: matrix/TRC profiles only (sRGB, Adobe RGB, Display P3, ProPhoto, ...).
"""
import struct

import numpy as np

D50 = np.array([0.96422, 1.0, 0.82521])
M_S_INV = np.array([[0.4360747, 0.3850649, 0.1430804],     # linear sRGB -> XYZ D50
                    [0.2225045, 0.7168786, 0.0606169],
                    [0.0139322, 0.0971045, 0.7141733]])
M_S = np.linalg.inv(M_S_INV)
M_PP_INV = np.array([[0.7976749, 0.1351917, 0.0313534],    # linear ProPhoto (ROMM) -> XYZ D50
                     [0.2880402, 0.7118741, 0.0000857],
                     [0.0, 0.0, 0.8252100]])
M_PP = np.linalg.inv(M_PP_INV)


# ---- transfer curves -------------------------------------------------------
def srgb_enc(x):
    x = np.asarray(x, float)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.sign(x) * np.abs(x) ** (1 / 2.4) - 0.055)


def srgb_dec(x):
    x = np.asarray(x, float)
    return np.where(x <= 0.04045, x / 12.92, np.sign(x) * ((np.abs(x) + 0.055) / 1.055) ** 2.4)


# ---- Lab D50 ---------------------------------------------------------------
def _f(t):
    return np.where(t > 216 / 24389, np.cbrt(t), (24389 / 27 * t + 16) / 116)


def _fi(t):
    return np.where(t ** 3 > 216 / 24389, t ** 3, (116 * t - 16) / (24389 / 27))


def xyz_to_lab(xyz):
    xyz = np.asarray(xyz, float)
    f = _f(xyz / D50)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lab_to_xyz(lab):
    lab = np.asarray(lab, float)
    fy = (lab[..., 0] + 16) / 116
    return np.stack([_fi(fy + lab[..., 1] / 500), _fi(fy), _fi(fy - lab[..., 2] / 200)], -1) * D50


def lab_to_srgb_lin(lab):
    return lab_to_xyz(lab) @ M_S.T


def srgb_lin_to_lab(rgb):
    return xyz_to_lab(np.asarray(rgb, float) @ M_S_INV.T)


# ---- OkLab (linear sRGB, D65 white) -------------------------------------------
_M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                [0.2119034982, 0.6806995451, 0.1073969566],
                [0.0883024619, 0.2817188376, 0.6299787005]])
_M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                [1.9779984951, -2.4285922050, 0.4505937099],
                [0.0259040371, 0.7827717662, -0.8086757660]])


def srgb_lin_to_oklab(rgb):
    lms = np.cbrt(np.asarray(rgb, float) @ _M1.T)
    return lms @ _M2.T


def oklab_to_srgb_lin(lab):
    lms = np.asarray(lab, float) @ np.linalg.inv(_M2).T
    return (lms ** 3) @ np.linalg.inv(_M1).T


# ---- gamut -----------------------------------------------------------------
def in_gamut(rgb_lin, tol=1e-4):
    rgb_lin = np.asarray(rgb_lin)
    return np.all((rgb_lin >= -tol) & (rgb_lin <= 1 + tol), axis=-1)


def map_chroma(to_rgb, polar, tol=1e-4):
    """Reduce chroma at constant (L, h) until `to_rgb(L, C, h)` is inside sRGB.

    to_rgb(L, C, h_deg) -> linear sRGB (3,), polar = (L, C, h_deg). Returns (C, mapped_flag).
    """
    L, C, h = polar
    if in_gamut(to_rgb(L, C, h), tol):
        return C, False
    lo, hi = 0.0, C
    for _ in range(40):
        mid = (lo + hi) / 2
        if in_gamut(to_rgb(L, mid, h), tol):
            lo = mid
        else:
            hi = mid
    return lo, True


def lab_to_rgb_mapped(lab):
    """Lab D50 -> (linear sRGB in gamut, Lab actually encoded, mapped flag). Constant L and hue."""
    L, a, b = [float(v) for v in lab]
    C, h = np.hypot(a, b), np.degrees(np.arctan2(b, a))

    def to_rgb(L_, C_, h_):
        r = np.radians(h_)
        return lab_to_srgb_lin(np.array([L_, C_ * np.cos(r), C_ * np.sin(r)]))

    L = min(max(L, 0.0), 100.0)
    C2, mapped = map_chroma(to_rgb, (L, C, h))
    rgb = np.clip(to_rgb(L, C2, h), 0.0, 1.0)
    return rgb, srgb_lin_to_lab(rgb), mapped


# ---- CIEDE2000 -----------------------------------------------------------------
def de2000(lab1, lab2):
    l1, l2 = np.asarray(lab1, float), np.asarray(lab2, float)
    L1, a1, b1 = l1[..., 0], l1[..., 1], l1[..., 2]
    L2, a2, b2 = l2[..., 0], l2[..., 1], l2[..., 2]
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cm = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = a1 * (1 + G), a2 * (1 + G)
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dL, dC = L2 - L1, C2p - C1p
    dh = h2p - h1p
    zero = C1p * C2p == 0
    dh = np.where(zero, 0.0, np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh)))
    dH = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lm, Cmp = (L1 + L2) / 2, (C1p + C2p) / 2
    hs = h1p + h2p
    hm = np.where(zero, hs, np.where(np.abs(h1p - h2p) <= 180, hs / 2, np.where(hs < 360, (hs + 360) / 2, (hs - 360) / 2)))
    T = (1 - 0.17 * np.cos(np.radians(hm - 30)) + 0.24 * np.cos(np.radians(2 * hm))
         + 0.32 * np.cos(np.radians(3 * hm + 6)) - 0.20 * np.cos(np.radians(4 * hm - 63)))
    SL = 1 + 0.015 * (Lm - 50) ** 2 / np.sqrt(20 + (Lm - 50) ** 2)
    SC, SH = 1 + 0.045 * Cmp, 1 + 0.015 * Cmp * T
    RT = -2 * np.sqrt(Cmp ** 7 / (Cmp ** 7 + 25 ** 7)) * np.sin(np.radians(60 * np.exp(-((hm - 275) / 25) ** 2)))
    return np.sqrt((dL / SL) ** 2 + (dC / SC) ** 2 + (dH / SH) ** 2 + RT * (dC / SC) * (dH / SH))


def hue_deg(a, b):
    return np.degrees(np.arctan2(b, a)) % 360


def hue_diff(h1, h2):
    return (h2 - h1 + 180) % 360 - 180


# ---- ICC (matrix/TRC) ----------------------------------------------------------
def _curve(data, off):
    typ = data[off:off + 4]
    if typ == b'curv':
        n = struct.unpack('>I', data[off + 8:off + 12])[0]
        if n == 0:
            return lambda x: np.asarray(x, float)
        if n == 1:
            g = struct.unpack('>H', data[off + 12:off + 14])[0] / 256.0
            return lambda x, g=g: np.sign(x) * np.abs(x) ** g
        tab = np.frombuffer(data[off + 12:off + 12 + 2 * n], '>u2').astype(float) / 65535
        xs = np.linspace(0, 1, n)
        return lambda x, tab=tab, xs=xs: np.interp(x, xs, tab)
    if typ == b'para':
        ft = struct.unpack('>H', data[off + 8:off + 10])[0]
        cnt = [1, 3, 4, 5, 7][ft]
        p = [struct.unpack('>i', data[off + 12 + 4 * i:off + 16 + 4 * i])[0] / 65536.0 for i in range(cnt)]
        g = p[0]
        a, b, c, d, e, f = (p[1:] + [0.0] * 6)[:6] if ft else (1, 0, 0, 0, 0, 0)
        if ft == 0:
            return lambda x, g=g: np.sign(x) * np.abs(x) ** g
        if ft == 1:
            return lambda x: np.where(x >= -b / a, (a * x + b) ** g, 0.0)
        if ft == 2:
            return lambda x: np.where(x >= -b / a, (a * x + b) ** g + c, c)
        if ft == 3:
            return lambda x: np.where(x >= d, (a * x + b) ** g, c * x)
        return lambda x: np.where(x >= d, (a * x + b) ** g + e, c * x + f)
    raise ValueError('unsupported TRC type %r' % typ)


def read_icc(icc):
    """-> dict(M=colorants->XYZ D50 (3x3), trc=[3 funcs], desc, version) for a matrix/TRC profile."""
    if icc is None:
        raise ValueError('no ICC')
    n = struct.unpack('>I', icc[128:132])[0]
    tags = {}
    for i in range(n):
        sig, off, size = struct.unpack('>4sII', icc[132 + 12 * i:144 + 12 * i])
        tags[sig] = (off, size)
    for need in (b'rXYZ', b'gXYZ', b'bXYZ', b'rTRC', b'gTRC', b'bTRC'):
        if need not in tags:
            raise ValueError('not a matrix/TRC profile (no %s)' % need.decode())
    cols = []
    for sig in (b'rXYZ', b'gXYZ', b'bXYZ'):
        o = tags[sig][0]
        cols.append([struct.unpack('>i', icc[o + 8 + 4 * k:o + 12 + 4 * k])[0] / 65536.0 for k in range(3)])
    desc = ''
    if b'desc' in tags:
        o, sz = tags[b'desc']
        raw = icc[o:o + sz]
        if raw[:4] == b'desc':
            desc = raw[12:12 + struct.unpack('>I', raw[8:12])[0] - 1].decode('latin1')
        elif raw[:4] == b'mluc':   # first record: length, offset from tag start
            ln, of = struct.unpack('>II', raw[20:28])
            desc = raw[of:of + ln].decode('utf-16-be', 'ignore')
    return dict(M=np.array(cols).T, trc=[_curve(icc, tags[s][0]) for s in (b'rTRC', b'gTRC', b'bTRC')],
                desc=desc.strip('\x00 '), version=icc[8])


def icc_to_lab(prof, rgb):
    """rgb: (...,3) float 0..1 encoded in the profile -> Lab D50 (profile PCS is D50)."""
    rgb = np.asarray(rgb, float)
    lin = np.stack([prof['trc'][c](rgb[..., c]) for c in range(3)], -1)
    return xyz_to_lab(lin @ prof['M'].T)
