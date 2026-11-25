# CozyUI- — 低版本适配（1.6.1 → 1.19.4）

[English](README.md) · **简体中文**

把 [Fogg05/CozyUI-Plus](https://github.com/Fogg05/CozyUI-Plus)（官方 **最低 1.20**）降级移植到
**1.6.1 一直到 1.19.4**，并附带一套可复现的构建与自检工具。

> **先说最关键的一件事**：CozyUI+ **不是 mod，是资源包**（Modrinth 项目类型 `resourcepack`）。
> 官方仓库里只有 README、宣传素材和 `.psd` 源文件，没有一行 Java、没有 `build.gradle`。
> 所以「适配低版本」不涉及 Gradle / Loom / Yarn 映射 / mixin，**不需要 JDK**——
> 它是个纯粹的**资源路径 + 版式几何**问题。推导与实测见 [docs/适配方案.md](docs/适配方案.md)。
>
> 商店文案（英文，Modrinth / CurseForge 通用）见 [docs/description-en.md](docs/description-en.md)。
>
> **本仓库是独立移植，不是上游的 fork**。原包美术、设计、字体版权归 [零雾〇五 Fogg05](https://github.com/Fogg05)，
> 按 GPL-3.0 再分发；逐条修改说明见 [NOTICE](NOTICE)。

---

## 下载与安装

| 平台 | 地址 |
|---|---|
| **Modrinth** | <https://modrinth.com/resourcepack/cozyui-minus> |
| **CurseForge** | <https://www.curseforge.com/minecraft/texture-packs/cozyui-minus> |

按自己的游戏版本选文件，丢进 `.minecraft/resourcepacks/` 启用即可（**不要解压**）。图标统一为
`assets/pack.png`。本仓库不存放成品包，`dist/` 由本地构建产生，见下文「从源码构建」。

### 一个格式号一个包：63 个正式版全部零警告

`pack_format` 只能填一个整数，游戏把它和当前版本的期望值比较，**不相等就显示黄字**
（"为旧版本 / 新版本制作"）。所以要让每个版本都看不见提示，只有一条路：
**每个资源包格式号单独出一个包**。11 个格式号 → 11 个包，每包的 `pack_format`
与该格式号下**所有**版本完全相等：

| 文件 | 覆盖版本 | `pack_format` | 体积 | RGB 渐变 |
|---|---|:--:|--:|---|
| `CozyUI-_1.6.1-1.8.9.zip` | 1.6.1 – 1.8.9 | 1 | 5.3 MB | 经验条 |
| `CozyUI-_1.9-1.10.2.zip` | 1.9 – 1.10.2 | 2 | 5.4 MB | 经验条 |
| `CozyUI-_1.11-1.12.2.zip` | 1.11 – 1.12.2 | 3 | 6.0 MB | 经验条 |
| `CozyUI-_1.13-1.14.4.zip` | 1.13 – 1.14.4 | 4 | 39.2 MB | 经验条 + 选中框 |
| `CozyUI-_1.15-1.16.1.zip` | 1.15 – 1.16.1 | 5 | 39.3 MB | 经验条 + 选中框 |
| `CozyUI-_1.16.2-1.16.5.zip` | 1.16.2 – 1.16.5 | 6 | 39.3 MB | 经验条 + 选中框 |
| `CozyUI-_1.17-1.17.1.zip` | 1.17 – 1.17.1 | 7 | 39.3 MB | 经验条 + 选中框 |
| `CozyUI-_1.18-1.18.2.zip` | 1.18 – 1.18.2 | 8 | 39.3 MB | 经验条 + 选中框 |
| `CozyUI-_1.19-1.19.2.zip` | 1.19 – 1.19.2 | 9 | 39.3 MB | 经验条 + 选中框 |
| `CozyUI-_1.19.3.zip` | 1.19.3 | 12 | 39.3 MB | 经验条 + 选中框 |
| `CozyUI-_1.19.4.zip` | 1.19.4 | 13 | 39.3 MB | 经验条 + 选中框 |

对照覆盖量：1.6.1–1.12.2 共 **36** 个正式版、1.13–1.14.4 共 **8** 个、1.15–1.19.2 共 **17** 个、
1.19.3–1.19.4 共 **2** 个，合计 **63 个，一个不漏**。`1.20` 及以上用**上游原包**
（官方就从 1.20 起支持），不重叠。

> 为什么不做成一个通吃包？`pack_format` 只有一个数，一个包只能精确匹配一个格式号；
> 合并必然让其中一批版本看到黄字。要零提示，只能一格式号一包。

### RGB 渐变（40 秒一轮）

上游的 RGB 循环**不是着色器，也不是 OptiFine**，而是 1.20.2 才有的 sprite 动画：
`experience_bar_progress.png` 8 帧 × `frametime:100`（5 秒/帧）× `interpolate:true` = **40 秒一轮**。
≤1.20.1 没有 sprite 系统，所以 [tools/animate.py](tools/animate.py) 把它搬成**整图集动画**：

- 经验条前景在 `icons.png` 的 `(0,69,182,5)`——实测 1.8.9 到 1.19.4 **十一代一个像素都没挪过**；
- 快捷栏选中框在 `widgets.png` 的 `(0,0,24,24)`——同样十一代不变；
- 8 帧里只有这两块矩形换色，其余像素逐字节相同，视觉上就等于"只有它在缓慢变色"。

色相直接取自上游 sprite 的 8 帧中位数：橙 → 黄 → 黄绿 → 绿 → 青 → 蓝 → 紫 → 品红
（[预览图](docs/img/gradient_preview.png)）。

代价：mcmeta 的 `animation` 只能作用于**整张纹理**，所以 `icons.png` / `widgets.png` 会变成
1024×8192，各占约 32 MB 显存（两张合计 64 MB）。1.6.1~1.12.2 三段的 `widgets.png` 因版式差 37%
已回退原版，所以那三段**只有经验条渐变，没有选中框渐变**。

> 上游还有"按钮高亮脉冲"（`button_highlighted`，16 帧 × `frametime:1`），但它和选中框的
> 5 秒/帧差 100 倍，**同一张 `widgets.png` 装不下两个动画定义**；统一帧率需要 800 帧（52 MB），
> 故放弃——上游自己也标注该效果需要 ≥1.21。

---

## 各版本能覆盖到什么

1.6.1 → 1.19.4 之间界面被改过好几轮，光栅版式（下称"版式"）变化大的地方，本移植**宁可回退原版也不发错位的图**：

| | 1.13+ | 1.6.1 – 1.12.2 |
|---|:--:|:--:|
| 容器面板（背包/箱子/熔炉/合成/酿造/信标/漏斗/铁砧/附魔/村民…） | ✅ | ✅ |
| 标题界面全景图 | ✅ | ✅ |
| 按钮 / 滑条 / 输入框 / 快捷栏（`widgets.png`） | ✅ | ❌ 原版 |
| HUD 血量·饥饿·护甲（`icons.png`） | ✅ | ✅ |
| 创造模式页签底板 | ✅ | ✅ |
| 内置字体（Emoji+ / MCsans+） | ✅ | ❌ 不适用 |
| 酿造台配方 / 附魔小图标 | ✅ | ❌ 依赖内置字体 |
| MOD 皮肤（JEI/REI/苹果皮…） | ✅ | ❌ |
| OptiGUI 彩色容器背景 | ✅ 需装 OptiGUI | ❌ |
| 经验条 / 选中框 RGB 循环 | ✅ 已移植（40 秒一轮） | ✅ 经验条（选中框因 widgets 回退原版） |

---

## 从源码构建

仓库里**不带二进制**：打包好的 11 个 zip 在
[Modrinth](https://modrinth.com/resourcepack/cozyui-minus) / CurseForge 发布；
原版 jar 受 Mojang 版权约束、上游原包 39 MB，也都不适合进 git。克隆后先拉输入（约 250 MB）：

```bash
python3 tools/fetch_inputs.py    # 上游 v1.10 原包 + 12 个原版客户端 jar
python3 tools/build.py           # 11 个包 -> dist/
python3 tools/animate.py         # 注入 RGB 渐变
python3 tools/validate.py        # 自检，应输出 11/11 通过
```

依赖：Python 3.9+、`pillow`、`numpy`（`scipy` 只有 `coverage_matrix.py` 用到）。

## 快速验证

```bash
# 全部 11 个包 + 自检
python3 tools/build.py
python3 tools/validate.py

# 注入 RGB 渐变（8 帧 x 5 秒 = 40 秒一轮）
python3 tools/animate.py

# 版式吻合度矩阵（产物 × 版本）
python3 tools/coverage_matrix.py

# 对照图（上游 / 降级 / 目标原版 三栏）
python3 tools/make_proof.py 1.6.1-1.8.9 1.19-1.19.2

# 只构建某几带 / 出无字体版
python3 tools/build.py 1.19-1.19.2
python3 tools/build.py --no-fonts 1.19.4
```

游戏内冒烟清单（**未经真机验证**，务必自己过一遍）：

1. 创造模式物品栏左侧标签页 → 图标是否对准各自的页（唯一建议人眼确认的地方）
2. 背包 / 合成台 / 熔炉 / 铁砧 / 附魔台 / 织布机 / 切石机 / 村民交易 → 面板与格子对齐
3. HUD：血量 / 饥饿 / 护甲 / 经验条 / 准星 / Boss 血条
4. 快捷栏与背包热键栏选中框
5. 标题界面按钮、toast、聊天栏标签
6. 1.6.1–1.12.2 额外确认：只有容器面板是贴图风格，按钮仍是原版——这是已知且故意的

---

## 目录结构

```
tools/build.py            降级构建器（版本带 → pack.mcmeta / 剪枝 / 版式重映射 / 吻合度闸门）
tools/animate.py          RGB 渐变注入器（上游 8 帧色相 → 老版式图集动画，40 秒一轮）
tools/build_universal.py  单包通吃构建器（已停用：零警告要求一格式号一包）
tools/validate.py         产物自检（不需要进游戏）
tools/coverage_matrix.py  版式吻合度矩阵（产物 × 版本）
tools/make_proof.py       生成「上游 / 降级 / 原版」三栏对照图
tools/fetch_inputs.py     拉构建输入（上游原包 + 原版 jar，不进仓库）
tools/packformats.json    资源包格式号表（含每带的策略）
docs/适配方案.md           完整技术方案与实测证据
docs/description-en.md    商店描述（英文，Modrinth / CurseForge）
docs/img/                 对照图与渐变预览
assets/pack.png           全产物统一图标
dist/                     构建产物
vanilla/                  各版本原版客户端 jar（构建基准）
upstream-packs/           上游 v1.10 原始包
github-repo/              上游仓库源码压缩包（只有素材，无包体）
work/build-report.json    构建报告（含每张图的吻合度与丢弃原因）
```

---

## 已知限制

1. **没有真机验证**。所有结论来自原版 jar 逐图像素比对 + 结构自检 + 资源引用完整性，
   已做到可证伪（`tools/validate.py` 15/15 全绿），但没有游戏内截图。
2. **1.6.1–1.12.2 的按钮 / 控件回退原版**。那个年代的 `widgets.png` 版式与 1.13+ 差 37%，
   强行套用会错位，所以整张回退原版（`icons.png` 是保住的，所以 HUD 与经验条渐变都在）。
   想补齐需要手写一张「控件矩形映射表」。
3. **RGB 渐变已移植，但有显存代价**：`icons.png` / `widgets.png` 各 8 帧 × 1024×1024 ≈ 32 MB，
   两张合计 64 MB。低配机器删掉对应的 `.png.mcmeta` 即可关掉动画（纹理退回单帧，不会错位）。
   控件动画（按钮高亮脉冲）因与选中框共用一张图、帧率差 100 倍，无法移植。
4. **`tabs.png` 的 26→28 列级拉伸**：1.19.3+ 的列宽从 28px 变 26px 且多一页，
   构建器做 7.7% 横向拉伸，几何对得上、圆角页会略扁。
5. **单元格回退处会露出原版色块**：版式变过的小块退回目标版本原版贴图，保证不错位、
   但风格不统一。精确坐标在 `work/build-report.json` 的 `art_todo`。
6. **内置字体对「强制 Unicode」不友好**：上游把 `font/uniform.json` 整个换成了 emoji/UI 位图，
   开强制 Unicode 后非拉丁字形可能消失。这是上游自身行为；需要规避就用 `nofonts` 版。
7. **第三方 mod 贴图未做版本校验**（18 个命名空间）。只在对应 mod 版本匹配时生效；
   1.6.1–1.12.2 的包里已全部剔除。

---

## 许可

上游 CozyUI+ 为 **GPL-3.0-only**，内置字体基于 NotoSans（SIL OFL）与 Fluent Emoji（MIT）。
本适配产物是上游美术的修改版再分发，**沿用相同许可**；完整版权归属与逐条修改说明见
[NOTICE](NOTICE)，许可全文见 [LICENSE](LICENSE)。

* 美术 / 设计 / 原包：**[零雾〇五 Fogg05](https://github.com/Fogg05)**
* 低版本移植 / 打包 / 工具：**CollinsLiu**
