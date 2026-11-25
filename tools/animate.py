#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RGBA 渐变注入器 —— 把上游 1.20.2+ 的 sprite 动画搬回 ≤1.19.4 的整图集
=====================================================================

上游是怎么做 RGB 循环的
----------------------
不是着色器、不是 OptiFine，而是 **1.20.2 才有的 sprite 动画**：

    gui/sprites/hud/experience_bar_progress.png     728x160 = 8 帧 x 20px
    gui/sprites/hud/hotbar_selection.png            96x736  = 8 帧 x 92px
    + .mcmeta: {"animation":{"frametime":100,"interpolate":true}}

frametime 100 = 5 秒/帧，8 帧 = 一轮 40 秒，interpolate 让帧间平滑过渡。

≤1.20.1 没有 sprite 系统，经验条画在 `bars.png`（1.13+）或 `icons.png`
（1.8~1.12）里的固定矩形，选中框画在 `widgets.png` 的 (0,0,24,24)。

所以移植办法是：**把整张图集做成动画**，每个帧只有那一个矩形换色，
其余像素逐字节相同 —— 视觉上就等价于"只有经验条/选中框在缓慢变色"。

代 价：
  * 内存/显存 = 帧数 x 原图面积。4x 的 1024x1024 图集 x 8 帧 = 32 MB/张。
  * 这是唯一可行的老版本方案（mcmeta 的 animation 只能作用于整张纹理）。

另外「控件动画」上游是 `button_highlighted` 的 16 帧脉冲（frametime 1），
和选中框的 5 秒/帧差 100 倍，**同一张 widgets.png 里装不下两个动画定义**，
所以本工具只做 RGB，按钮脉冲放弃（上游自己也标注该效果需要 ≥1.21）。

用法：
    python3 tools/animate.py                 # 处理 dist/ 下全部 zip
    python3 tools/animate.py <zip>...        # 只处理指定的
    python3 tools/animate.py --dry-run       # 只报告会动哪几张图
"""

from __future__ import annotations

import io
import json
import os
import sys
import zipfile

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPSTREAM = os.path.join(ROOT, "upstream-packs", "cozy-v1.10-full.zip")
DIST_DIR = os.path.join(ROOT, "dist")

FRAMES = 8          # 上游就是 8 帧
FRAMETIME = 100     # tick，= 5 秒/帧 -> 一轮 40 秒

SPRITE = "assets/minecraft/textures/gui/sprites/hud/experience_bar_progress.png"

_PF_PATH = os.path.join(ROOT, "tools", "packformats.json")
PACK_FORMATS = json.load(open(_PF_PATH, encoding="utf-8"))

# 目标图集 -> [(1x 坐标矩形 (x,y,w,h), 模式)]
#   模式 "hue"  : 只把色相换掉，保留明暗/饱和度结构。用于本来就带颜色的条。
#   模式 "tint" : 把色相换掉并把饱和度顶到目标值。用于本来是白/灰的框。
#
# 坐标都是 **原版 1x** 坐标，实际处理时按包内倍数放大。
#   经验条前景 (0,69,182,5)：1.8~1.20.1 全部同一个位置，没变过。
#   快捷栏选中框 (0,0,24,24)：同理。
TARGETS = {
    # 经验条前景：实测 1.8.9 / 1.10.2 / 1.12.2 / 1.14.4 / 1.16.1 / 1.16.5 / 1.17.1 /
    # 1.18.2 / 1.19.2 / 1.19.3 / 1.19.4 全部是 icons.png 的 (0,69,182,5)，
    # 906 像素、饱和 0.59、均价 #436830 —— 十一代一个像素都没挪过。
    # （bars.png 里只有 Boss 血条，是纯黑 + 代码染色，不能动。）
    "assets/minecraft/textures/gui/icons.png": [((0, 69, 182, 5), "hue")],
    # 快捷栏选中框：(0,0,24,24)，576 像素、纯灰 #3D3D30，得用 tint 染色才看得见。
    "assets/minecraft/textures/gui/widgets.png": [((0, 0, 24, 24), "tint")],
}


# --------------------------------------------------------------------------
# 1. 从上游 sprite 里抠出 8 个色相
# --------------------------------------------------------------------------
def upstream_hues() -> list[int]:
    z = zipfile.ZipFile(UPSTREAM)
    im = Image.open(io.BytesIO(z.read(SPRITE))).convert("RGBA")
    fh = im.height // FRAMES
    hues = []
    for i in range(FRAMES):
        f = im.crop((0, i * fh, im.width, (i + 1) * fh))
        hsv = f.convert("RGB").convert("HSV")
        a = np.array(f)[:, :, 3] > 0
        h = np.array(hsv.split()[0])
        s = np.array(hsv.split()[1])
        m = a & (s > 60)          # 只统计有颜色的像素，避开白边
        if m.sum() < 20:
            m = a
        hues.append(int(np.median(h[m])))
    return hues


# --------------------------------------------------------------------------
# 2. 单帧着色
# --------------------------------------------------------------------------
def recolor(img: Image.Image, box: tuple[int, int, int, int],
            hue: int, mode: str) -> Image.Image:
    """只改 box 内的像素，box 外逐字节不变。"""
    x, y, w, h = box
    out = img.copy()
    reg = out.crop((x, y, x + w, y + h))
    alpha = reg.getchannel("A")
    hsv = reg.convert("RGB").convert("HSV")
    hh, ss, vv = hsv.split()

    new_h = Image.new("L", hh.size, hue)
    if mode == "tint":
        # 白/灰框没有色相可言，把饱和度也顶上去，否则改了 H 也看不出颜色
        new_s = Image.new("L", ss.size, max(110, int(np.percentile(np.array(ss)[np.array(alpha) > 0], 60)) if (np.array(alpha) > 0).any() else 110))
        hsv = Image.merge("HSV", (new_h, new_s, vv))
    else:
        hsv = Image.merge("HSV", (new_h, ss, vv))

    recolored = hsv.convert("RGB")
    recolored.putalpha(alpha)
    out.paste(recolored, (x, y))
    return out


# --------------------------------------------------------------------------
# 3. 把一张图集变成"只有某个矩形在变"的动画条
# --------------------------------------------------------------------------
def animate(img: Image.Image, specs: list[tuple[tuple[int, int, int, int], str]],
            hues: list[int]) -> Image.Image:
    frames = []
    for i, hue in enumerate(hues):
        f = img
        for box, mode in specs:
            f = recolor(f, box, hue, mode)
        frames.append(f)
    w = img.width
    out = Image.new("RGBA", (w, img.height * len(frames)))
    for i, f in enumerate(frames):
        out.paste(f, (0, i * img.height))
    return out


def mcmeta_for(frame_h: int) -> bytes:
    doc = {"animation": {"frametime": FRAMETIME, "interpolate": True, "height": frame_h}}
    return json.dumps(doc, separators=(",", ":")).encode("utf-8")


def scale_of(pack_img: Image.Image, van_img: Image.Image) -> int:
    if van_img.width == 0:
        return 1
    sc = pack_img.width // van_img.width
    return sc if sc >= 1 and pack_img.width % van_img.width == 0 else 1


# --------------------------------------------------------------------------
# 4. 对一个 zip 注入
# --------------------------------------------------------------------------
def inject(zip_path: str, jar_path: str | None, hues: list[int],
           dry_run: bool = False) -> dict:
    src = zipfile.ZipFile(zip_path)
    names = set(src.namelist())
    report = {"zip": os.path.basename(zip_path), "animated": [], "skipped": []}

    if jar_path and os.path.exists(jar_path):
        van = zipfile.ZipFile(jar_path)
    else:
        van = None

    plan = []
    for path, specs in TARGETS.items():
        if path not in names:
            report["skipped"].append((path.rsplit("/", 1)[-1], "包内没有该图集"))
            continue
        pim = Image.open(io.BytesIO(src.read(path))).convert("RGBA")
        vim = None
        if van and path in van.namelist():
            vim = Image.open(io.BytesIO(van.read(path))).convert("RGBA")
        base_sc = 4
        if vim is not None:
            sc = scale_of(pim, vim)
        else:
            # 没有原版可参照：用图宽 / 256 估算（GUI 图集原版都是 256 宽）
            sc = max(1, pim.width // 256) if pim.width % 256 == 0 else 1
            report["skipped"].append((path.rsplit("/", 1)[-1], f"按图宽推断 {sc}x"))
        real_specs = []
        ok = True
        for (x, y, w, h), mode in specs:
            box = (x * sc, y * sc, w * sc, h * sc)
            if box[2] <= 0 or box[3] <= 0 or box[0] + box[2] > pim.width or box[1] + box[3] > pim.height:
                report["skipped"].append((path.rsplit("/", 1)[-1], f"矩形越界 {box}"))
                ok = False
                break
            real_specs.append((box, mode))
        if not ok:
            continue
        plan.append((path, pim, real_specs, sc))

    if dry_run:
        report["animated"] = [(p.rsplit("/", 1)[-1], c) for p, _, s, c in plan for _ in [0]]
        report["animated"] = [(p.rsplit("/", 1)[-1], sc) for p, _, _, sc in plan]
        report["frame_bytes"] = [pim.width * pim.height * 4 * FRAMES for _, pim, _, _ in plan]
        return report

    tmp = zip_path + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
        skip = {p for p, _, _, _ in plan}
        for item in src.infolist():
            if item.filename in skip:
                continue
            dst.writestr(item, src.read(item.filename))
        for path, pim, specs, sc in plan:
            anim = animate(pim, specs, hues)
            buf = io.BytesIO()
            anim.save(buf, format="PNG", optimize=True)
            data = buf.getvalue()
            dst.writestr(path, data)
            dst.writestr(path + ".mcmeta", mcmeta_for(pim.height))
            report["animated"].append({
                "file": path.rsplit("/", 1)[-1],
                "scale": f"{sc}x",
                "frame": f"{pim.width}x{pim.height}",
                "frames": FRAMES,
                "bytes": len(data),
                "vram_mb": round(pim.width * pim.height * 4 * FRAMES / 1024 / 1024, 1),
            })
    os.replace(tmp, zip_path)
    return report


def main() -> int:
    args = [a for a in sys.argv[1:]]
    dry = "--dry-run" in args
    args = [a for a in args if not a.startswith("--")]

    hues = upstream_hues()
    print("上游 8 帧色相 (0-255):", hues)
    rgb = [Image.new("HSV", (1, 1), (h, 220, 230)).convert("RGB").getpixel((0, 0)) for h in hues]
    print("对应近似颜色:        ", ["#%02X%02X%02X" % c for c in rgb])

    if args:
        zips = args
    else:
        zips = sorted(os.path.join(DIST_DIR, f) for f in os.listdir(DIST_DIR)
                      if f.endswith(".zip"))
    if not zips:
        print("dist/ 下没有 zip")
        return 1

    total = 0
    for z in zips:
        base = os.path.basename(z)
        jar = None
        for b in PACK_FORMATS["bands"]:
            if base.endswith(f"_{b['id']}.zip"):
                jar = os.path.join(ROOT, "vanilla", f"client-{b['jar']}.jar")
                break
        rep = inject(z, jar, hues, dry)
        tag = " [dry-run]" if dry else ""
        print(f"\n{rep['zip']}{tag}")
        if dry:
            for f, sc in rep["animated"]:
                print(f"   会动画化 {f} ({sc}x)")
        else:
            for a in rep["animated"]:
                print(f"   ✓ {a['file']:14s} {a['scale']} 帧{a['frame']} x{a['frames']}帧 "
                      f"{a['bytes']/1024:.0f}KB  显存约 {a['vram_mb']}MB")
                total += a["bytes"]
        for name, why in rep["skipped"]:
            print(f"   - {name:14s} 跳过：{why}")
    if not dry:
        print(f"\n动画数据合计 {total/1024/1024:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
