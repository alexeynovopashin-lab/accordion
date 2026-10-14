"""Decode crs:Table_<hash> strings from Lightroom/ACR XMP profiles.

Format follows Adobe DNG SDK, dng_big_table.cpp (DecodeFromString /
dng_rgb_table::GetStream): base85 with a custom alphabet, 4 bytes -> 5 chars,
little-endian, least significant digit first; the decoded block is a 4-byte
little-endian uncompressed size followed by a zlib stream. Code written here
from that description; no SDK code copied.
"""
import re
import struct
import zlib

ENC = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-:+=^!/*?`'|()[]{}@%$#"
DEC = {c: i for i, c in enumerate(ENC)}


def b85_decode(s):
    out = bytearray()
    s = "".join(ch for ch in s if ch in DEC)
    for i in range(0, len(s), 5):
        chunk = s[i:i + 5]
        x, mul = 0, 1
        for ch in chunk:
            x += DEC[ch] * mul
            mul *= 85
        n = len(chunk) - 1  # a partial group of k+1 chars carries k bytes
        out += struct.pack("<I", x & 0xFFFFFFFF)[: (4 if len(chunk) == 5 else n)]
    return bytes(out)


def decode_table(s):
    raw = b85_decode(s)
    size = struct.unpack("<I", raw[:4])[0]
    data = zlib.decompress(raw[4:])
    assert len(data) == size, (len(data), size)
    return data


def read_xmp(path):
    txt = open(path, encoding="utf-8").read()
    tables = dict(re.findall(r'crs:Table_([0-9A-F]+)="([^"]*)"', txt))
    refs = dict(re.findall(r'crs:(RGBTable|LookTable)="([0-9A-F]+)"', txt))
    return txt, refs, tables
