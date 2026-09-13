---
name: social-card-render
description: 把内容做成社交平台图文卡片（小红书 / 朋友圈 / 微信群 / 公众号首图）并批量导出 PNG/JPG。核心手法是用 HTML 排 1080×1440 的卡片（保真度、字体、圆角、渐变远超 PIL 手排），再用无头 Edge + CDP 按 .card 元素逐个 clip 截图，最后 PIL 统一压缩命名。当用户说「做小红书图」「发朋友圈的图」「把这份内容做成图文」「排版成卡片图」「帖子配图」「封面图」时使用。也适用于把已有的长截图嵌入卡片做"成品展示"页。
agent_created: true
---

# 社交卡片图渲染（HTML → CDP 截图 → 批量导出）

## 为什么不用 PIL 直接画

需要中文大字、圆角卡片、渐变遮罩、多级排版时，PIL 的 `ImageDraw` 要手算每个元素的坐标，
改一个字就要重算全版。**用 HTML + CSS 排，浏览器帮你做布局**，改文案只改 HTML。
代价只是多一步"截图"，而这一步有稳定流程。

## 目录约定

```
<项目>/
  <某个静态目录>/          ← http server 的根，卡片和素材都要在这里面能访问到
  source/                  ← 素材（图片等）
  cards.html               ← 卡片定义，每张一个 <section class="card" id="cN">
  scripts/render.py        ← 起服务 + 起浏览器 + 调 render.js
  scripts/render.js        ← CDP 协议，按 .card 截图
  shots/                   ← 需要嵌入卡片的原始截图（可选）
  final/                   ← 渲染出的 PNG（1080×1440 @2x）
  ready/                   ← 后处理（缩放 + JPG + 按发布顺序命名）
```

## 卡片规范（小红书）

| 项 | 值 |
|---|---|
| 画布 | `1080 × 1440`（3:4，小红书占屏最大） |
| 渲染倍数 | `deviceScaleFactor:1` + `clip.scale:2` → 输出 2160×2880 |
| 成品尺寸 | 缩到 **1440×1920**，JPG q90（每张 250–400 KB） |
| 安全边距 | 左右各 70px，上 60–80px |
| 中文粗体 | `"Microsoft YaHei"` + `font-weight:900`（Windows 自带，无需引字体） |

**配色经验**（暖色调内容）：奶油底 `#FDF6E8`、墨字 `#2E2A24`、强调砖红 `#B05C34`、
卡片描边 `#EADFC8`、次要文字 `#6B5F4E`。同一套配色贯穿全部卡片，视觉才成套。

## 用法

```bash
python scripts/render.py --root <http根目录> --html <相对root的html> --out <输出目录>
```

例：

```bash
python scripts/render.py --root "D:/proj" --html "cards.html" --out "D:/proj/final"
```

`--root` 决定 http server 根，`--html` 是相对 root 的路径。卡片里的图片用**相对该 html 的路径**引用。

## 🔴 关键坑（都踩过）

1. **不要在自己的脚本里 spawn 浏览器再连 CDP。**
   实测在 Windows 上这样会静默挂死（fetch `/json` 轮询超时，进程不死也不出结果）。
   **正确做法：Python 负责起 http server + Popen 浏览器并轮询 `/json/version` 确认就绪，
   Node 只做 CDP 协议**。`render.py` 就是这个分工。

2. **截图倍数 = `deviceScaleFactor` × `clip.scale`**，不是相加也不是取一。
   390 CSS px 的截图，`dsf=2` + `clip.scale=2` → 输出 **1560 px**。
   要 1080 宽就设 `dsf=1` + `clip.scale=2`。

3. **超长截图嵌进卡片时，顶部的 hero 大图会占满整个可视区**，看起来几张卡片一模一样。
   解决：`.stage img { margin-top:-Npx }` 跳过 hero。
   `N` 的算法：`N = (原图里想从哪开始的 y 坐标) × (卡片里 img 显示宽 / 原图宽)`。
   改完一定**再看一眼渲染结果**，别盲信。

4. **卡片高度是硬裁的**。内容超 1440px 会被 `overflow:hidden` 切掉且不报错。
   渲染后必须把 9 张拼成一张缩略总览图检查（见下方脚本），溢出会一眼看到。

5. **中文路径**：Python `subprocess` 调浏览器/Node 时，URL 用 `pathlib.Path.as_uri()`
   或 `http://127.0.0.1:PORT/相对路径`（ASCII 化后再传），不要直接把中文路径塞进命令行参数。

6. **Bash 工具在部分 Windows 环境下 PATH 会间歇为空**（`dirname: command not found`、`exit 127`）。
   表现是整条命令失败且前面步骤的输出全丢。规避方式有两种：
   - 命令前显式导出 PortableGit 的路径（按你的实际安装位置改）：
     ```bash
     export PATH="/c/Program Files/Git/usr/bin:/c/Program Files/Git/mingw64/bin:/c/Windows/System32:/c/Windows"
     ```
   - 或者干脆**不接管道**（`| tail` / `| grep` 会放大问题），改成重定向到日志文件再用 Read 工具读。

## 渲染后必做：拼缩略总览自检

```python
from PIL import Image
import pathlib
d = pathlib.Path(OUT)
fs = ['c%d' % i for i in range(1, N + 1)]
W = 300
ims = [Image.open(d / (f + '.png')).convert('RGB').resize((W, 400), Image.LANCZOS) for f in fs]
sh = Image.new('RGB', (W * 5 + 10 * 6, 400 * 2 + 10 * 3), '#333')
for i, im in enumerate(ims):
    r, c = divmod(i, 5)
    sh.paste(im, (10 + c * (W + 10), 10 + r * 410))
sh.save(d / '_preview.png')
```

然后 **Read 这张 `_preview.png`** —— 一次就能看出哪张压字、哪张空、哪张内容重复。

## 后处理（统一尺寸 + 命名）

```python
names = {'c1': '01_封面', 'c2': '02_方法', ...}
for k, v in names.items():
    im = Image.open(src / (k + '.png')).convert('RGB').resize((1440, 1920), Image.LANCZOS)
    im.save(out / (v + '.jpg'), 'JPEG', quality=90, optimize=True)
```

**按发布顺序命名**（`01_封面`、`02_…`），用户上传时不用再想顺序。

## 内容层面的经验（小红书）

- **封面 = 图 + 大字**，字要 8–13 字，带数字或反差。水印/占位账号名记得提醒用户改。
- **方法类内容只占 1 张图**，别把整篇写成教程。涨粉靠"读者能得到什么"，方法只是差异化引子。
- **必须有 1 张"真实产出截图"**（证明不是嘴上说说），截图要裁到有信息量的区块，别露 hero。
- **结尾卡放硬提醒 + 引导**，比放"求关注"有效得多。
