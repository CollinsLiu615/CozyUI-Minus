#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拉取构建所需的输入（这些文件不进仓库）。

  upstream-packs/cozy-v1.10-full.zip   上游 CozyUI+ v1.10 原包（~41 MB）
  vanilla/client-<ver>.jar             各版本原版客户端 jar（构建基准）

原版 jar 的版权归 Mojang，上游原包是 39 MB 的二进制，两者都不该进 git，
所以克隆之后先跑一遍这个脚本。

    python3 tools/fetch_inputs.py
    python3 tools/fetch_inputs.py --check     # 只报告缺什么，不下载
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VANILLA = os.path.join(ROOT, "vanilla")
UPSTREAM_DIR = os.path.join(ROOT, "upstream-packs")

# 上游 v1.10 在 Modrinth 上的 CDN 直链（项目 cozyui-plus / 版本 v1.10）
UPSTREAM_NAME = "cozy-v1.10-full.zip"
UPSTREAM_URL = ("https://cdn.modrinth.com/data/G5rf50k2/versions/Sh3uNYag/"
                "%C2%A7cCozyUI%C2%A7b%2B%20%C2%A77v1.10%20%C2%A70.zip")

MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"


def needed_versions() -> list[str]:
    """构建要用到的所有 jar：每个段的基准版本 + 全局 baseline。"""
    pf = json.load(open(os.path.join(ROOT, "tools", "packformats.json"), encoding="utf-8"))
    vers = {b["jar"] for b in pf["bands"]}
    vers.add(pf.get("_baseline", "1.20.1"))
    return sorted(vers, key=lambda v: [int(x) for x in v.split(".")[:3]])


def fetch_upstream(check: bool) -> bool:
    dst = os.path.join(UPSTREAM_DIR, UPSTREAM_NAME)
    if os.path.exists(dst) and os.path.getsize(dst) > 30_000_000:
        print(f"  上游原包 已存在 {os.path.getsize(dst)//1024//1024} MB")
        return True
    if check:
        print("  上游原包 缺失")
        return False
    os.makedirs(UPSTREAM_DIR, exist_ok=True)
    print(f"  上游原包 下载中 ...")
    urllib.request.urlretrieve(UPSTREAM_URL, dst)
    print(f"  上游原包 -> {dst} {os.path.getsize(dst)//1024//1024} MB")
    return True


def fetch_vanilla(check: bool) -> bool:
    man = json.load(urllib.request.urlopen(MANIFEST_URL))
    idx = {v["id"]: v["url"] for v in man["versions"]}
    ok = True
    for ver in needed_versions():
        dst = os.path.join(VANILLA, f"client-{ver}.jar")
        if os.path.exists(dst) and os.path.getsize(dst) > 1_000_000:
            print(f"  client-{ver}.jar 已存在 {os.path.getsize(dst)//1024} KB")
            continue
        if check:
            print(f"  client-{ver}.jar 缺失")
            ok = False
            continue
        if ver not in idx:
            print(f"  client-{ver}.jar !! 不在 Mojang manifest 里")
            ok = False
            continue
        vj = json.load(urllib.request.urlopen(idx[ver]))
        cu = vj["downloads"]["client"]
        os.makedirs(VANILLA, exist_ok=True)
        print(f"  client-{ver}.jar 下载中 {cu['size']//1024} KB ...")
        urllib.request.urlretrieve(cu["url"], dst)
    return ok


def main() -> int:
    check = "--check" in sys.argv[1:]
    print("检查 / 拉取构建输入" + ("（只检查）" if check else ""))
    a = fetch_upstream(check)
    b = fetch_vanilla(check)
    if check:
        print("\n全部齐备，可以构建。" if (a and b) else "\n有缺失，去掉 --check 再跑一次。")
    else:
        print("\n完成。接下来：python3 tools/build.py && python3 tools/animate.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
