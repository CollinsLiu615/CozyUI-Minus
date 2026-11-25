#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版式吻合度矩阵 / layout agreement matrix
=======================================

给每个产物 × 每个游戏版本算一个分数：包里所有**该版本会读取的图集大图**，
其 alpha 掩膜与该版本原版掩膜的 IoU 均值。

  1.00 = 版式完全对位（美术怎么变都行，只要轮廓落在原版轮廓上）
  0.9x = 轻微差异
  <0.8 = 版式错位，可能看得出来

sprite 不参与评分：它是 1:1 单图，没有共享图集坐标，不存在"版式"这回事。

用法：
    python3 tools/coverage_matrix.py                     # dist/ 下全部产物
    python3 tools/coverage_matrix.py --artifacts a.zip b.zip
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import zipfile

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(ROOT, "dist")
VANILLA_DIR = os.path.join(ROOT, "vanilla")

VERSIONS = ["1.16.5", "1.17.1", "1.18.2", "1.19.2", "1.19.3", "1.19.4",
            "1.20.1", "1.20.2", "1.21.1", "1.21.4", "1.21.8", "1.21.11"]

_cache: dict[str, zipfile.ZipFile] = {}


def jar(ver: str) -> zipfile.ZipFile:
    if ver not in _cache:
        _cache[ver] = zipfile.ZipFile(os.path.join(VANILLA_DIR, f"client-{ver}.jar"))
    return _cache[ver]


def mask(data: bytes) -> np.ndarray | None:
    try:
        return np.array(Image.open(io.BytesIO(data)).convert("RGBA"))[:, :, 3] > 0
    except Exception:  # noqa: BLE001
        return None


def atlas_paths(zf: zipfile.ZipFile) -> list[str]:
    return sorted(n for n in zf.namelist()
                  if n.startswith("assets/minecraft/textures/gui/")
                  and n.endswith(".png") and "/sprites/" not in n)


def norm(pa: np.ndarray, va: np.ndarray) -> np.ndarray | None:
    """包里是原版的整数倍分辨率（通常 4x）；降采样到原版尺寸再比轮廓。"""
    if pa.shape == va.shape:
        return pa
    if va.shape[0] and pa.shape[0] % va.shape[0] == 0:
        sc = pa.shape[0] // va.shape[0]
        if pa.shape[1] == va.shape[1] * sc:
            return pa[::sc, ::sc]
    return None


_vmask: dict[tuple[str, str], np.ndarray | None] = {}
_pmask: dict[tuple[str, str], np.ndarray | None] = {}


def score(art: zipfile.ZipFile, ver: str,
          art_key: str = "") -> tuple[float, int, list[tuple[str, float]]]:
    van = jar(ver)
    vnames = set(van.namelist())
    vals = []
    per_path = []
    for p in atlas_paths(art):
        if p not in vnames:
            continue
        if (art_key, p) in _pmask:
            pa = _pmask[(art_key, p)]
        else:
            pa = _pmask[(art_key, p)] = mask(art.read(p))
        if (ver, p) in _vmask:
            va = _vmask[(ver, p)]
        else:
            va = _vmask[(ver, p)] = mask(van.read(p))
        if pa is None or va is None:
            continue
        pa = norm(pa, va)
        if pa is None:
            continue
        u = (pa | va).sum()
        iou = float((pa & va).sum()) / u if u else 1.0
        vals.append(iou)
        per_path.append((p.replace("assets/minecraft/textures/", ""), iou))
    return (float(np.mean(vals)) if vals else float("nan"), len(vals), per_path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifacts", nargs="*")
    ap.add_argument("--worst", type=int, default=0, help="列出每个产物最差的 N 张")
    args = ap.parse_args()

    arts = args.artifacts or sorted(
        os.path.join(DIST_DIR, f) for f in os.listdir(DIST_DIR)
        if f.endswith(".zip") and not f.startswith("."))
    print(f'{"artifact":44s} ' + " ".join(f'{v:>7s}' for v in VERSIONS))
    detail = {}
    for a in arts:
        zf = zipfile.ZipFile(a)
        cells = []
        detail[os.path.basename(a)] = {}
        for v in VERSIONS:
            s, n, per = score(zf, v, os.path.basename(a))
            cells.append(f'{s:7.3f}' if n else f'{"-":>7s}')
            detail[os.path.basename(a)][v] = per
        print(f'{os.path.basename(a):44s} ' + " ".join(cells))

    if args.worst:
        print()
        for name, byver in detail.items():
            worst = sorted(((s, v, p) for v, per in byver.items() for p, s in per))[: args.worst]
            print(f'--- {name} 最差 {args.worst} 张')
            for s, v, p in worst:
                print(f'      {s:.3f}  [{v:6s}] {p}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
