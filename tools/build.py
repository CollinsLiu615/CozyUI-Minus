#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CozyUI+ 低版本降级构建器 / CozyUI+ downgrade builder
=====================================================

背景
----
CozyUI+ 是**资源包**（resource pack），不是 mod。它的全部内容就是
`assets/**` 下的贴图 / 字体 / 语言文件，没有一行 Java。因此「适配低版本」
不是换 Gradle 版本或改 mixin，而是三件事：

  1. `pack.mcmeta` 的 `pack_format` 必须等于目标版本的资源包格式号，
     否则游戏会把它标记成「不兼容」（低版本仍可强行加载，但会一直警告）。
  2. 目标版本里**根本不存在**的资源路径要剪掉：它们不会被读取，只会白白
     撑大包体（例如 1.20.2+ 才有的 `gui/sprites/**`，在整个 1.16~1.20.1
     区间都是死文件）。
  3. 路径存在、但**版式几何变了**的贴图必须重映射，否则会出现「图还在、
     位置错」的错位渲染。这是唯一真正需要动图的部分。

第 3 步的判据
-------------
本脚本不靠猜测，而是拿目标版本的**原版客户端 jar** 当基准：
对每条贴图路径，比较「本包老版式美术所针对的版式代际」（默认 1.20.1）
与目标版本的**原版** `alpha` 掩膜（= 版式轮廓）：

  * 掩膜完全一致 -> 版式没变，本包美术可直接用（绝大多数字段都走这里）。
  * 掩膜有差异   -> 划分 16x16 单元格，逐格判断：
      - 该格掩膜一致 -> 把本包美术（4x 分辨率）搬过去；版式没变，安全。
      - 该格掩膜不同 -> 该区域的版式变了，本包美术不可信，退回目标版本
        原版贴图（放大到本包分辨率），并记为 ART_TODO 供美术后续补画。

  少数贴图有明确、可精确计算的版式差异（例如 1.19.3 起 `tabs.png` 从
  6 列 28px 变成 7 列 26px），用 RULES 里的专用规则做几何重映射，而不是
  退回原版。这些规则由 minecraft.wiki 的 Pack_format 变更记录 + 实测
  原版 jar 掩膜共同验证。

用法
----
    python3 tools/build.py                  # 构建 tools/packformats.json 里列出的全部目标
    python3 tools/build.py 1.19.2           # 只构建指定版本带
    python3 tools/build.py --keep-inert     # 保留死文件，出「一个包通吃」的通用版
    python3 tools/build.py --list           # 只列目标
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import zipfile
import zlib

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_PACK = os.path.join(ROOT, "upstream-packs", "cozy-v1.10-full.zip")
# 所有产物统一使用这张图标（换图标只改这里，重建即可）
PACK_ICON = os.path.join(ROOT, "assets", "pack.png")
VANILLA_DIR = os.path.join(ROOT, "vanilla")
DIST_DIR = os.path.join(ROOT, "dist")
WORK_DIR = os.path.join(ROOT, "work")

# 本包「老版式」美术所针对的版式代际：1.20.1（资源包格式 15）。
# 之所以是它而不是 1.20.2+：包里同时带了老版式大图 (gui/widgets.png 等)
# 和新版式 sprite，老版式那一套就是照 1.20.1 画的。
BASELINE = "1.20.1"

# 这些命名空间属于第三方 mod（jei / rei / appleskin ...），
# 它们的贴图路径由各自的 mod 版本决定，我们无从校验，一律原样保留。
FIRST_PARTY_NS = {"minecraft"}

# 只有这些前缀是「版本门控的原版覆盖」——包里给自己画的新版式 sprite，
# 只在 1.20.2+ 会被读取，老版本纯属死重量，可以安全剪掉。
# 反过来，Assets 里「原版 jar 里没有」并不等于死文件：包自己新增的
# 字体贴图、语言文件、OptiFine/OptiGUI 配置、自定义音效都被它的 json
# 引用着，剪掉就是直接坏功能。所以这里用白名单，不做「查无此项即删」。
PRUNABLE_PREFIXES = ("assets/minecraft/textures/gui/sprites/",)

# 低于目标版本资源的死文件判定里，这些顶级路径永远保留（与版本无关）。
ALWAYS_KEEP = {"pack.mcmeta", "pack.png", "LICENSE", "LICENSE.txt", "INFO.txt",
               "LICENSE_of_FluentEmoji.txt", "LICENSE_of_NotoSans.txt"}

CELL = 16  # 单元格边长（原版像素）。16px 是 MC GUI 的天然栅格。


# --------------------------------------------------------------------------
# 专用版式规则：这些路径的几何变化已知且可精确计算，不走通用单元格回退。
#
# tabs.png @ 1.19.3（见 wiki Pack_format: "tabs.png is now skinnier by 2
# pixels, with the 7th tab being added to it"）
#   1.20.1 : 8 列 x 26px = 208px
#   1.19.2 : 7 列 x 28px = 196px
# 实测原版掩膜确认两边都是「整列填充」，只有列宽和列数不同，因此把本包
# 第 i 列横向拉伸到 28px 放置即可；最后一列（搜索页）在两边都是末列，
# 源索引是 7 而不是 6。第 6 列（1.20.1 新增的第 7 个内容页）在旧版没有
# 对应位置，直接丢弃。
# --------------------------------------------------------------------------
RULES = {
    "assets/minecraft/textures/gui/container/creative_inventory/tabs.png": {
        "kind": "columns",
        "content_rows": (0, 128),     # 有效内容只占 y[0,128)
        # 实测（原版 jar 逐列占用）：
        #   pack    : x 0..181 = 7 列 x 26px
        #   1.20.1  : x 0..207 = 8 列 x 26px
        #   1.19.2  : x 0..195 = 7 列 x 28px
        # 三者在 x 232..255 都另有一块 24px 的独立元素（与列宽无关），
        # 所以列组按 1:1 映射并把 26px 横向拉伸到 28px，
        # 尾部 24px 原样保留在 x=232。
        "src_w": 26, "tgt_w": 28, "tgt_cols": 7,
        "map": [0, 1, 2, 3, 4, 5, 6],
        "preserve_from": 232,
        # 只有目标版本真的是 7 列 x 28px（内容区 196px）才拉伸。
        # 1.19.3/1.19.4/1.20.1 是 8 列 x 26px（208px），与包本身同版式，不能动。
        "expect_tgt_width": 196,
    },
}


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------
_jar_cache: dict[str, zipfile.ZipFile] = {}


def vanilla_jar(ver: str) -> zipfile.ZipFile | None:
    if ver in _jar_cache:
        return _jar_cache[ver]
    path = os.path.join(VANILLA_DIR, f"client-{ver}.jar")
    if not os.path.exists(path):
        _jar_cache[ver] = None
        return None
    z = zipfile.ZipFile(path)
    _jar_cache[ver] = z
    return z


def vanilla_assets(ver: str) -> set[str]:
    z = vanilla_jar(ver)
    if z is None:
        return set()
    return {n for n in z.namelist()
            if n.startswith("assets/") and not n.endswith("/")}


def vanilla_png(ver: str, path: str) -> Image.Image | None:
    z = vanilla_jar(ver)
    if z is None:
        return None
    try:
        return Image.open(io.BytesIO(z.read(path))).convert("RGBA")
    except KeyError:
        return None


def alpha(img: Image.Image) -> np.ndarray:
    return np.array(img)[:, :, 3] > 0


def to_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def png_size(data: bytes) -> tuple[int, int]:
    return (int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big"))


def integral_scale(pack_size, base_size) -> int | None:
    """本包分辨率相对原版基准的整数倍率；不一致/非整数返回 None。"""
    for p, b in zip(pack_size, base_size):
        if b == 0 or p % b:
            return None
    sx, sy = pack_size[0] // base_size[0], pack_size[1] // base_size[1]
    return sx if sx == sy and sx >= 1 else None


# --------------------------------------------------------------------------
# 版式修复
# --------------------------------------------------------------------------
def rule_columns(pack: Image.Image, vsrc: Image.Image, vtgt: Image.Image,
                 rule: dict, scale: int) -> tuple[Image.Image, list]:
    """按列重映射：把本包的列横向缩放到目标列宽后放到目标位置。"""
    sw, tw = rule["src_w"] * scale, rule["tgt_w"] * scale
    out = Image.new("RGBA", pack.size, (0, 0, 0, 0))
    for j, si in enumerate(rule["map"]):
        col = pack.crop((si * sw, 0, (si + 1) * sw, pack.size[1]))
        col = col.resize((tw, pack.size[1]), Image.LANCZOS)
        out.paste(col, (j * tw, 0))
    # 列组之外的元素（例如尾部那块 24px）版本间位置不变，原样搬过来。
    if rule.get("preserve_from"):
        x = rule["preserve_from"] * scale
        out.paste(pack.crop((x, 0, pack.size[0], pack.size[1])), (x, 0))
    return out, []


def rule_cells(pack: Image.Image, vsrc: Image.Image, vtgt: Image.Image,
               scale: int) -> tuple[Image.Image, list]:
    """逐 16x16 单元格判断版式是否变过；变了的那格退回目标版本原版贴图。"""
    out = Image.new("RGBA", pack.size, (0, 0, 0, 0))
    ma, mb = alpha(vsrc), alpha(vtgt)
    w, h = vtgt.size
    todo = []
    for cy in range(0, h, CELL):
        for cx in range(0, w, CELL):
            ex, ey = min(cx + CELL, w), min(cy + CELL, h)
            same = bool((ma[cy:ey, cx:ex] == mb[cy:ey, cx:ex]).all())
            box_pack = (cx * scale, cy * scale, ex * scale, ey * scale)
            if same:
                out.paste(pack.crop(box_pack), (box_pack[0], box_pack[1]))
            else:
                src = vtgt.crop((cx, cy, ex, ey))
                out.paste(src.resize(((ex - cx) * scale, (ey - cy) * scale),
                                     Image.NEAREST), (box_pack[0], box_pack[1]))
                todo.append({"x": cx, "y": cy, "w": ex - cx, "h": ey - cy})
    return out, todo


def column_coverage(img: Image.Image, rule: dict, scale: int) -> list[float]:
    """每个目标列带里有多少比例的行是被画到的（结构自检用）。"""
    m = alpha(img)
    tw = rule["tgt_w"] * scale
    y0, y1 = rule["content_rows"][0] * scale, rule["content_rows"][1] * scale
    cov = []
    for j in range(rule["tgt_cols"]):
        band = m[y0:y1, j * tw:(j + 1) * tw]
        cov.append(round(float(band.any(axis=1).mean()), 3))
    return cov


def build_texture(path: str, pack_img: Image.Image, v_src: Image.Image | None,
                  v_tgt: Image.Image | None) -> tuple[Image.Image, dict]:
    """返回 (处理后图像, 说明)。没变化就原样返回。"""
    note = {"path": path, "action": "keep"}

    # 包美术直接铺到目标版本上有多贴合？这个数与"能不能做几何修复"无关，
    # 所以只要能拿到目标版本原版就算出来，供 min_agreement 闸门使用。
    def _iou(van):
        if van is None:
            return None
        pa, ta = alpha(pack_img), alpha(van.resize(pack_img.size, Image.NEAREST))
        u = int((pa | ta).sum())
        return round(float((pa & ta).sum()) / u, 4) if u else 1.0

    ag_base = _iou(v_src)      # 包美术 vs 它本来针对的版式（1.20.1）——这就是"重绘风格距离"
    ag_tgt = _iou(v_tgt)       # 包美术 vs 目标版式
    note["pack_agreement"] = ag_tgt
    note["pack_agreement_base"] = ag_base
    # 关键量：换到目标版本后，贴合度相对它原本的贴合度掉了多少。
    # 1.0 = 版式没变（重绘风格距离保持），明显 <1 = 目标版式真的不一样。
    if ag_base and ag_tgt is not None and ag_base > 0:
        note["agreement_ratio"] = round(ag_tgt / ag_base, 4)
    # 包美术与目标原版之间不是整数倍缩放 = 两张图根本不在同一栅格上（如 villager.png）
    note["scale_ok"] = integral_scale(pack_img.size, v_tgt.size) is not None if v_tgt else None

    if v_src is None or v_tgt is None:
        note["reason"] = "no-baseline-reference"
        return pack_img, note

    # 1x1 的是占位图（例如 1.20.1 的 panorama_*.png），没有版式可言，原样保留。
    if v_src.size == (1, 1) or v_tgt.size == (1, 1):
        note["reason"] = "dummy-reference"
        return pack_img, note

    # 两边原版尺寸不同 = 版式代际差得太远（例如 villager.png 从 256x256 变成 512x2048 的分页版），
    # 逐格算术没有意义，不做修补，交给吻合度闸门决定要不要发这张图。
    if v_src.size != v_tgt.size:
        note["reason"] = "size-mismatch"
        note["sizes"] = [list(v_src.size), list(v_tgt.size)]
        return pack_img, note

    # 基准版式与目标版式的原版轮廓是否一致？一致就不用动。
    if (alpha(v_src) == alpha(v_tgt)).all():
        note["reason"] = "layout-identical"
        return pack_img, note

    scale = integral_scale(pack_img.size, v_src.size)
    if scale is None:
        note["action"] = "keep"
        note["reason"] = "non-integral-scale"
        note["pack_size"] = list(pack_img.size)
        note["base_size"] = list(v_src.size)
        return pack_img, note

    def _content_width(img):
        col = alpha(img).any(axis=0)
        i = 0
        while i < len(col) and col[i]:
            i += 1
        return i

    rule = RULES.get(path)
    if rule and rule.get("expect_tgt_width") and _content_width(v_tgt) != rule["expect_tgt_width"]:
        note["reason"] = "layout-same-as-baseline"
        return pack_img, note
    if rule and rule["kind"] == "columns":
        out, todo = rule_columns(pack_img, v_src, v_tgt, rule, scale)
        note["action"] = "columns"
        note["rule"] = {k: v for k, v in rule.items() if k != "map"}
        note["columns_coverage"] = column_coverage(out, rule, scale)
        note["art_review"] = ("auto remap: 26px -> 28px column stretch; "
                              "visual check recommended")
    else:
        out, todo = rule_cells(pack_img, v_src, v_tgt, scale)
        note["action"] = "cells"
        note["art_todo"] = todo
        note["art_todo_px"] = sum(t["w"] * t["h"] for t in todo)

    # 自检：修复后的轮廓与目标版本原版轮廓的重合度。
    o, t = alpha(out), alpha(v_tgt.resize(out.size, Image.NEAREST))
    union = int((o | t).sum())
    note["mask_agreement"] = round(float((o & t).sum()) / union, 4) if union else 1.0
    note["scale"] = scale
    return out, note


# --------------------------------------------------------------------------
# 构建单个目标
# --------------------------------------------------------------------------
def mcmeta(fmt: int, band: dict, base_version: str) -> bytes:
    desc = (f"§cCozyUI§b- §7v1.10 §8[§7MC {band['mc']}§8]§r\n"
            f"§7by §f零雾〇五 Fogg05 §7· §flow-version port: §fCollinsLiu"
            + (f" §8(base {base_version})" if base_version != BASELINE else ""))
    doc = {"pack": {"pack_format": fmt, "description": desc}}
    # 1.20.2 (fmt 18) 起才有 supported_formats；更老的版本只认 pack_format，
    # 多写字段虽然会被忽略，但为了干净还是按住版本来。
    if fmt >= 18:
        doc["pack"]["supported_formats"] = band["formats"]
    return (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


FONT_PREFIXES = ("assets/minecraft/font/", "assets/minecraft/textures/font/")


def build_target(band: dict, src_zip: zipfile.ZipFile, base_assets: set[str],
                 keep_inert: bool = False, no_fonts: bool = False) -> dict:
    ver = band["jar"]
    fmt = band["formats"][0]
    if ver is None:
        return {"band": band["id"], "skipped": "no vanilla jar configured"}
    if vanilla_jar(ver) is None:
        return {"band": band["id"], "skipped": f"vanilla/client-{ver}.jar missing"}

    tgt_assets = vanilla_assets(ver)
    entries = [n for n in src_zip.namelist() if not n.endswith("/")]

    strict = bool(band.get("strict"))
    min_agree = band.get("min_agreement")
    report = {"band": band["id"], "mc": band["mc"], "pack_format": fmt,
              "no_fonts": no_fonts, "strict": strict, "min_agreement": min_agree,
              "dropped_low_agreement": [],
              "vanilla_reference": ver, "baseline": BASELINE,
              "kept": 0, "pruned": 0, "pruned_sample": [],
              "textures": {"kept": 0, "fixed": 0, "details": []},
              "pruned_by_dir": {}}
    out_buf = io.BytesIO()

    with zipfile.ZipFile(out_buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zout:
        # pack.mcmeta 永远按目标版本重写
        zout.writestr("pack.mcmeta", mcmeta(fmt, band, BASELINE))
        # 图标统一换成工程 assets/pack.png（上游同名的 pack.png 后面会被跳过）
        if os.path.exists(PACK_ICON):
            with open(PACK_ICON, "rb") as fh:
                zout.writestr("pack.png", fh.read())

        for name in entries:
            if name in ("pack.mcmeta", "pack.png"):
                continue
            top = name.split("/")[0]
            if top in ALWAYS_KEEP or name in ALWAYS_KEEP:
                zout.writestr(name, src_zip.read(name))
                report["kept"] += 1
                continue

            if no_fonts and any(name.startswith(p) for p in FONT_PREFIXES):
                report["pruned"] += 1
                report["pruned_by_dir"]["assets/minecraft/font"] = \
                    report["pruned_by_dir"].get("assets/minecraft/font", 0) + 1
                continue

            # strict 模式：只保留目标版本原版真实存在的路径（跨度过大时用它，
            # 否则包里会有几百个目标版本根本不读的文件）
            if strict and name.startswith("assets/") and name not in tgt_assets:
                report["pruned"] += 1
                d = "/".join(name.split("/")[:4])
                report["pruned_by_dir"][d] = report["pruned_by_dir"].get(d, 0) + 1
                continue

            prunable = any(name.startswith(p) for p in PRUNABLE_PREFIXES)
            if prunable and not keep_inert:
                if name not in tgt_assets:
                    report["pruned"] += 1
                    d = "/".join(name.split("/")[:4])
                    report["pruned_by_dir"][d] = report["pruned_by_dir"].get(d, 0) + 1
                    if len(report["pruned_sample"]) < 12:
                        report["pruned_sample"].append(name)
                    continue

            data = src_zip.read(name)
            if name.endswith(".png") and name.startswith("assets/minecraft/textures/"):
                v_src = vanilla_png(BASELINE, name)
                v_tgt = vanilla_png(ver, name)
                img = Image.open(io.BytesIO(data)).convert("RGBA")
                fixed, note = build_texture(name, img, v_src, v_tgt)
                # 吻合度太低的整张丢弃：那种情况逐格修补只会得到"半原版半素材"的杂图，
                # 不如干净地回退到原版。
                unfixable = note.get("action") == "keep"
                gate_applies = strict or unfixable
                ratio = note.get("agreement_ratio")
                bad_scale = note.get("scale_ok") is False
                if min_agree is not None and gate_applies and (
                        bad_scale or (ratio is not None and ratio < min_agree)):
                    report["pruned"] += 1
                    report["dropped_low_agreement"].append(
                        {"path": name, "agreement_ratio": ratio,
                         "pack_agreement": note["pack_agreement"],
                         "pack_agreement_base": note["pack_agreement_base"],
                         "bad_scale": bad_scale})
                    continue
                data = to_png(fixed) if fixed is not img else data
                if note["action"] in ("cells", "columns"):
                    report["textures"]["fixed"] += 1
                    report["textures"]["details"].append(note)
                else:
                    report["textures"]["kept"] += 1
            zout.writestr(name, data)
            report["kept"] += 1

    report["bytes"] = out_buf.tell()
    safe = band["id"].replace(" ", "")
    prefix = "CozyUI-_nofonts" if no_fonts else "CozyUI-"
    out_path = os.path.join(DIST_DIR, f"{prefix}_{safe}.zip")
    report["zip"] = os.path.relpath(out_path, ROOT)
    with open(out_path, "wb") as fh:
        fh.write(out_buf.getvalue())
    return report


# --------------------------------------------------------------------------
# 结果核对
# --------------------------------------------------------------------------
def verify(report: dict) -> list[str]:
    """构建结果的自检，返回问题列表（空 = 通过）。"""
    problems = []
    out_path = os.path.join(ROOT, report["zip"])
    if not os.path.exists(out_path):
        return ["zip missing"]
    with zipfile.ZipFile(out_path) as z:
        bad = z.testzip()
        if bad:
            problems.append(f"corrupt entry: {bad}")
        names = set(z.namelist())
        meta = json.loads(z.read("pack.mcmeta").decode("utf-8"))
        if meta["pack"]["pack_format"] != report["pack_format"]:
            problems.append("pack_format mismatch")
        if "pack.png" not in names:
            problems.append("pack.png missing")
        need = vanilla_assets(report["vanilla_reference"])
        for n in names:
            if any(n.startswith(p) for p in PRUNABLE_PREFIXES) and n not in need:
                problems.append(f"version-gated file not pruned: {n}")
                break
        # 包自己新增、被自身 json 引用的资源必须还在，否则字体/OptiGUI 直接坏。
        required = ["pack.png"]
        if report.get("strict"):
            pass  # 1.8~1.12 用 glyph_sizes.bin，font/default.json 本就不该出现在这些包里
        elif not report.get("no_fonts"):
            required.append("assets/minecraft/font/default.json")
        else:
            if "assets/minecraft/font/default.json" in names:
                problems.append("no_fonts build still ships font/default.json")
        for must in required:
            if must not in names:
                problems.append(f"required file dropped: {must}")
        for d in report["textures"]["details"]:
            if d["action"] == "columns":
                cov = d.get("columns_coverage") or []
                if not cov or min(cov) < 0.85:
                    problems.append(
                        f"column remap incomplete on {d['path']}: coverage={cov}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="*", help="版本带 id，例如 1.19.2；省略=全部")
    ap.add_argument("--keep-inert", action="store_true",
                    help="不剪版本门控的 gui/sprites（出「一个包通吃」的通用版）")
    ap.add_argument("--no-fonts", action="store_true",
                    help="去掉内置 NotoSans/Emoji 字体（体积小、规避强制 Unicode 相关风险）")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    bands = json.load(open(os.path.join(ROOT, "tools", "packformats.json"),
                          encoding="utf-8"))["bands"]
    # 只构建低于 1.20 的版本带（1.20+ 是上游原生支持的范围）
    bands = [b for b in bands if b["formats"][0] < 15]
    if args.list:
        for b in bands:
            print(f'{b["id"]:>16}  fmt {b["formats"][0]:>2}  jar={b["jar"]}')
        return 0
    if args.targets:
        want = set(args.targets)
        bands = [b for b in bands if b["id"] in want]
        if not bands:
            print(f"没有匹配的版本带: {sorted(want)}", file=sys.stderr)
            return 2

    os.makedirs(DIST_DIR, exist_ok=True)
    src = zipfile.ZipFile(SRC_PACK)
    base_assets = vanilla_assets(BASELINE)

    results = []
    for b in bands:
        print(f'>>> {b["id"]:>16}  fmt {b["formats"][0]}  ', end="", flush=True)
        rep = build_target(b, src, base_assets, keep_inert=args.keep_inert,
                           no_fonts=args.no_fonts)
        if "skipped" in rep:
            print(f'skipped ({rep["skipped"]})')
            continue
        problems = verify(rep)
        rep["problems"] = problems
        print(f'kept={rep["kept"]:4d} pruned={rep["pruned"]:4d} '
              f'fixed={rep["textures"]["fixed"]:2d} '
              f'{rep["bytes"]/1e6:.1f}MB '
              f'{"OK" if not problems else "PROBLEMS: " + "; ".join(problems[:2])}')
        results.append(rep)

    os.makedirs(WORK_DIR, exist_ok=True)
    with open(os.path.join(WORK_DIR, "build-report.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)
    print(f"\nreport -> work/build-report.json  ({len(results)} target(s))")
    return 0 if all(not r["problems"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
