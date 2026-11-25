#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对照图生成器 / proof sheet
=========================

把「上游包美术 / 降级后的美术 / 目标版本原版」三者并排画出来，用来肉眼确认
build.py 的版式修复没有把图挪错位置。列顺序固定：

    上游(1.20.1 版式)  |  降级产物  |  目标版本原版

用法：
    python3 tools/make_proof.py 1.19-1.19.2 1.16.2-1.16.5
产物写到 docs/img/。
"""

from __future__ import annotations

import io
import os
import sys
import zipfile

from PIL import Image
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPSTREAM = os.path.join(ROOT, "upstream-packs", "cozy-v1.10-full.zip")
DIST_DIR = os.path.join(ROOT, "dist")
VANILLA_DIR = os.path.join(ROOT, "vanilla")
OUT_DIR = os.path.join(ROOT, "docs", "img")

REF_JAR = "1.20.1"          # 上游美术所针对的版式代际
BG = (28, 28, 32, 255)
GAP = 10


def open_zip(path):
    return zipfile.ZipFile(path)


def load(z, name, scale_to=None):
    try:
        im = Image.open(io.BytesIO(z.read(name))).convert("RGBA")
    except KeyError:
        return None
    if scale_to and im.size != scale_to:
        im = im.resize(scale_to, Image.LANCZOS)
    return im


def sheet(band: str, jars: dict, paths: list[str]) -> str:
    dist = os.path.join(DIST_DIR, f"CozyUI-_{band}.zip")
    if not os.path.exists(dist):
        raise SystemExit(f"missing {dist}")
    up, out, van = open_zip(UPSTREAM), open_zip(dist), open_zip(jars[band])

    rows = []
    for p in paths:
        a = load(up, p)                       # 上游 4x
        b = load(out, p)                      # 降级产物
        c = load(van, p)                      # 目标原版 1x
        if b is None:
            continue
        size = c.size if c else (b.size[0] // 4, b.size[1] // 4)
        a = load(up, p, size) if a else None
        b = b.resize(size, Image.LANCZOS) if b.size != size else b
        rows.append((p, a, b, c))

    if not rows:
        raise SystemExit(f"nothing to draw for {band}")

    # 每个纹理尺寸可能不同（32x32 到 256x256），统一用最大尺寸做格子，居中摆放
    cw = max(max(im.size[0] for im in r[1:] if im) for r in rows)
    ch = max(max(im.size[1] for im in r[1:] if im) for r in rows)
    cols = 3
    W = cols * cw + (cols + 1) * GAP
    H = len(rows) * ch + (len(rows) + 1) * GAP
    canvas = Image.new("RGBA", (W, H), BG)
    y = GAP
    for _p, a, b, c in rows:
        for i, im in enumerate((a, b, c)):
            if im is None:
                continue
            x = GAP + i * (cw + GAP)
            tone = (60, 60, 66, 255) if i == 1 else (46, 46, 50, 255)
            tile = Image.new("RGBA", (cw, ch), tone)
            tile.alpha_composite(im, ((cw - im.size[0]) // 2, (ch - im.size[1]) // 2))
            canvas.paste(tile, (x, y))
        y += ch + GAP
    os.makedirs(OUT_DIR, exist_ok=True)
    dst = os.path.join(OUT_DIR, f"proof_{band}.png")
    canvas.save(dst)
    return os.path.relpath(dst, ROOT)


def conflict_paths(band: str, jar_ver: str) -> list[str]:
    """现算：包里在这两个版式代际之间"原版轮廓不同"的图集，就是需要重新对位的那些。"""
    import zipfile as _z
    up = _z.ZipFile(UPSTREAM)
    base = _z.ZipFile(os.path.join(VANILLA_DIR, f"client-{REF_JAR}.jar"))
    tgt = _z.ZipFile(os.path.join(VANILLA_DIR, f"client-{jar_ver}.jar"))
    bn, tn = set(base.namelist()), set(tgt.namelist())
    out = []
    for n in sorted(up.namelist()):
        if not (n.startswith("assets/minecraft/textures/gui/") and n.endswith(".png")):
            continue
        if "/sprites/" in n or n not in bn or n not in tn:
            continue
        a = np.array(Image.open(io.BytesIO(base.read(n))).convert("RGBA"))[:, :, 3] > 0
        b = np.array(Image.open(io.BytesIO(tgt.read(n))).convert("RGBA"))[:, :, 3] > 0
        if a.shape != b.shape or not (a == b).all():
            out.append(n)
    return out


def main() -> int:
    import json
    bands = sys.argv[1:] or ["1.19-1.19.2"]
    ref = json.load(open(os.path.join(ROOT, "tools", "packformats.json"), encoding="utf-8"))
    jar_of = {b["id"]: b["jar"] for b in ref["bands"]}
    for band in bands:
        jar_ver = jar_of.get(band)
        if not jar_ver:
            raise SystemExit(f"unknown band {band}")
        paths = conflict_paths(band, jar_ver)
        if not paths:
            print(f"{band}: 该版本带没有任何版式差异（上游美术可直接用）")
            continue
        jars = {band: os.path.join(VANILLA_DIR, f"client-{jar_ver}.jar")}
        print(f"{band}: {sheet(band, jars, paths)}  ({len(paths)} textures)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
