#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建产物自检 / dist checker
===========================

build.py 只保证「能出包」；这个脚本回答「这个包在游戏里会不会炸」。
逐项检查（不需要启动游戏）：

  1. zip 完整性、pack.mcmeta 可解析且 pack_format 与目标版本一致、pack.png 在
  2. 每个 `*.png.mcmeta` 都有配对的 png（动画元数据悬空会刷错误日志）
  3. 字体 json 里每个 `"file"` 引用都能解析到真实贴图（本包或目标版本原版），
     否则字形整段消失
  4. OptiGUI/OptiFine 的 `.properties` 里 `texture=` 指向的 png 存在
  5. 覆盖路径真实性：assets/minecraft/textures/** 下的每个文件是否真的存在于
     目标版本原版 jar，不存在就列成 inert（不致命，但属于白带的重量）
  6. 声音引用：sounds.json 里每条 `name` 都能找到 ogg

用法：
    python3 tools/validate.py            # 检查 dist/ 下全部 zip
    python3 tools/validate.py <zip>...
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(ROOT, "dist")
VANILLA_DIR = os.path.join(ROOT, "vanilla")

# 版本带 -> (资源包格式, 原版 jar 版本)
EXPECTED = {
    "1.6.1-1.8.9": (1, "1.8.9"),
    "1.9-1.10.2": (2, "1.10.2"),
    "1.11-1.12.2": (3, "1.12.2"),
    "1.13-1.14.4": (4, "1.14.4"),
    "1.15-1.16.1": (5, "1.16.1"),
    "1.16.2-1.16.5": (6, "1.16.5"),
    "1.17-1.17.1": (7, "1.17.1"),
    "1.18-1.18.2": (8, "1.18.2"),
    "1.19-1.19.2": (9, "1.19.2"),
    "1.19.3": (12, "1.19.3"),
    "1.19.4": (13, "1.19.4"),
}



def strip_json_comments(txt: str) -> str:
    """去掉 // 与 /* */ 注释（Minecraft 的 json 允许注释），字符串内的不动。"""
    out, i, n = [], 0, len(txt)
    while i < n:
        c = txt[i]
        if c == '"':
            j = i + 1
            while j < n:
                if txt[j] == "\\":
                    j += 2
                    continue
                if txt[j] == '"':
                    break
                j += 1
            out.append(txt[i:j + 1])
            i = j + 1
        elif txt.startswith("//", i):
            j = txt.find("\n", i)
            i = n if j < 0 else j
        elif txt.startswith("/*", i):
            j = txt.find("*/", i)
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def res_to_path(ref: str) -> str:
    """字体 provider 的 file 引用 -> zip 内路径。例 minecraft:font/emoji_a.png"""
    ref = ref.strip()
    ns, _, path = ref.partition(":")
    if not path:
        ns, path = "minecraft", ns
    if not path.endswith(".png"):
        path += ".png"
    # 字体 provider 的 file 是 texture 引用，实际落在 textures/ 下
    return f"assets/{ns}/textures/{path}"

_VAN_CACHE: dict[str, set[str]] = {}


def vanilla_names(ver: str) -> set[str]:
    """目标版本原版 jar 的全部条目名（用于判断覆盖路径是否真实存在）。"""
    if ver in _VAN_CACHE:
        return _VAN_CACHE[ver]
    path = os.path.join(VANILLA_DIR, f"client-{ver}.jar")
    names = set(zipfile.ZipFile(path).namelist()) if os.path.exists(path) else set()
    _VAN_CACHE[ver] = names
    return names

UNIVERSAL = set()
# 这些版本带的字体走 glyph_sizes.bin，包里没有 font/*.json 是正确行为
NO_FONT_JSON_BANDS = {"1.6.1-1.8.9", "1.9-1.10.2", "1.11-1.12.2"}


def band_of(name: str) -> str | None:
    for band in EXPECTED:
        if name.endswith(f"_{band}.zip"):
            return band
    return None


def check(zip_path: str) -> tuple[list[str], dict]:
    band = band_of(os.path.basename(zip_path))
    problems: list[str] = []
    info: dict = {"zip": os.path.relpath(zip_path, ROOT)}

    try:
        z = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as exc:
        return [f"bad zip: {exc}"], info

    with z:
        bad = z.testzip()
        if bad:
            problems.append(f"corrupt entry: {bad}")
        names = set(z.namelist())
        info["files"] = len(names)
        info["bytes"] = os.path.getsize(zip_path)

        # 1. pack.mcmeta
        try:
            meta = json.loads(z.read("pack.mcmeta").decode("utf-8"))
            fmt = meta["pack"]["pack_format"]
            info["pack_format"] = fmt
            if band and EXPECTED[band][0] != fmt:
                problems.append(f"pack_format {fmt} != expected {EXPECTED[band][0]} for {band}")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"pack.mcmeta unreadable: {exc}")
            fmt = None
        if "pack.png" not in names:
            problems.append("pack.png missing")
        elif band in NO_FONT_JSON_BANDS and "assets/minecraft/font/default.json" in names:
            problems.append("legacy band should not ship font/default.json")

        # 通吃版必须把 supported_formats（1.20.2+）与 min/max_format（1.21.9+）都写上，
        # 否则高版本会以为只支持 format 6 而拒绝加载。
        if band in UNIVERSAL:
            pk = meta.get("pack", {})
            sf = pk.get("supported_formats")
            lo, hi = (sf if isinstance(sf, list) and len(sf) == 2 else (None, None))
            if lo is None or lo > 6 or hi is None or hi < 64:
                problems.append(f"supported_formats bad: {sf}")
            if pk.get("min_format") != lo or pk.get("max_format") != hi:
                problems.append("min_format/max_format missing or mismatched")

        # 2. .mcmeta 配对
        for n in names:
            if n.endswith(".png.mcmeta") and n[: -len(".mcmeta")] not in names:
                problems.append(f"dangling animation metadata: {n}")

        # 3. 字体引用完整性
        font_refs = 0
        for n in names:
            if not re.match(r"assets/[^/]+/font/[^/]+\.json$", n):
                continue
            try:
                doc = json.loads(strip_json_comments(z.read(n).decode("utf-8")))
            except Exception as exc:  # noqa: BLE001
                problems.append(f"font json invalid: {n}: {exc}")
                continue
            prod = set(names)
            if band:
                prod |= vanilla_names(EXPECTED[band][1])
            for prov in doc.get("providers", []):
                f = prov.get("file")
                if not f:
                    continue
                font_refs += 1
                if res_to_path(f) not in prod:
                    problems.append(f"font glyph sheet missing: {n} -> {f}")
        info["font_refs"] = font_refs

        # 4. OptiGUI / OptiFine properties 的 texture= 引用
        props = 0
        for n in names:
            if not n.endswith(".properties") or "/optifine/" not in n:
                continue
            txt = z.read(n).decode("utf-8", "replace")
            for m in re.finditer(r"^\s*texture\s*=\s*(\S+)\s*$", txt, re.M):
                props += 1
                tgt = f"{os.path.dirname(n)}/{m.group(1)}.png"
                if tgt not in names:
                    problems.append(f"optigui texture missing: {n} -> {m.group(1)}.png")
        info["optigui_refs"] = props

        # 5. 覆盖路径真实性（通吃版必然保留大量本版本用不到的文件，跳过）
        if band and band not in UNIVERSAL:
            van = vanilla_names(EXPECTED[band][1])
            inert = [n for n in names
                     if re.match(r"assets/minecraft/textures/(gui|item)/", n)
                     and n not in van]
            info["inert_overrides"] = len(inert)
            info["inert_sample"] = sorted(inert)[:5]

        # 6. sounds.json 引用
        if "assets/minecraft/sounds.json" in names:
            try:
                sj = json.loads(z.read("assets/minecraft/sounds.json").decode("utf-8"))
                missing = []
                for _key, val in sj.items():
                    for s in val.get("sounds", []):
                        name = s.get("name") if isinstance(s, dict) else s
                        if not name:
                            continue
                        p = f"assets/minecraft/sounds/{name}.ogg"
                        if p not in names:
                            missing.append(name)
                if missing:
                    problems.append(f"sounds.json references missing ogg: {missing[:3]}")
                info["sound_refs"] = sum(len(v.get("sounds", [])) for v in sj.values())
            except Exception as exc:  # noqa: BLE001
                problems.append(f"sounds.json invalid: {exc}")

        # 7. 每个 png 至少能解码
        from PIL import Image
        for n in names:
            if not n.endswith(".png") or not n.startswith("assets/"):
                continue
            try:
                with Image.open(io.BytesIO(z.read(n))) as im:
                    im.load()
            except Exception as exc:  # noqa: BLE001
                problems.append(f"png undecodable: {n}: {exc}")
                break

    return problems, info


def main() -> int:
    zips = sys.argv[1:]
    if not zips:
        zips = sorted(os.path.join(DIST_DIR, f) for f in os.listdir(DIST_DIR)
                      if f.endswith(".zip"))
        # 只保留已知版本带（避免把别的 zip 也算进来自检失败）
        zips = [p for p in zips if band_of(os.path.basename(p))]
    if not zips:
        print("dist/ 下没有可检查的产物", file=sys.stderr)
        return 2

    fails = 0
    for p in zips:
        problems, info = check(p)
        flag = "OK  " if not problems else "FAIL"
        print(f'[{flag}] {os.path.basename(p):<42} '
              f'fmt={info.get("pack_format")} files={info.get("files")} '
              f'{info.get("bytes",0)/1e6:.1f}MB '
              f'font={info.get("font_refs")} optigui={info.get("optigui_refs")} '
              f'sounds={info.get("sound_refs", "-")} inert={info.get("inert_overrides", "-")}')
        for pr in problems[:8]:
            print(f'        ! {pr}')
        if problems:
            fails += 1
    print(f'\n{len(zips) - fails}/{len(zips)} 通过')
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
