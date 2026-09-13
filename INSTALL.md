# 安装说明

> 假设你已经装了 **WorkBuddy 或 Codex**。详细前提见 [README.md](README.md#前置条件)。

## 方式一：一键安装（推荐）

仓库带了一个安装脚本，会自动把两个 skill 拷到正确位置并跑环境自检。

```bash
# 先克隆
git clone https://github.com/<your-name>/ai-trip-guide-skills.git
cd ai-trip-guide-skills

# 安装
python install.py
```

脚本做的事：

1. 探测本机 skills 目录（WorkBuddy 优先，找不到会提示你手动指定）
2. 把 `trip-guide-builder/` 和 `social-card-render/` 整个拷过去（已存在会先备份）
3. 跑一遍环境自检，报告浏览器 / Node / Python 是否就绪

指定安装位置：

```bash
python install.py --target ~/.workbuddy/skills
```

只想看看会发生什么，不实际写入：

```bash
python install.py --dry-run
```

## 方式二：手动安装

```bash
# Windows (PowerShell)
Copy-Item -Recurse -Force .\trip-guide-builder  "$env:USERPROFILE\.workbuddy\skills\"
Copy-Item -Recurse -Force .\social-card-render "$env:USERPROFILE\.workbuddy\skills\"

# macOS / Linux
cp -r trip-guide-builder  ~/.workbuddy/skills/
cp -r social-card-render ~/.workbuddy/skills/
```

> **拷的是整个文件夹，不要拆散。**
> `SKILL.md` 是入口，`references/` `scripts/` `assets/` 必须跟它同级，
> 少一层目录客户端就扫不到。

## 装完验证

```bash
python ~/.workbuddy/skills/trip-guide-builder/scripts/_env.py
```

期望输出：

```
浏览器 : C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe
node   : C:\Program Files\nodejs\node.exe
python : C:\Python311\python.exe
输出根 : D:\旅行攻略
```

任何一项显示 `!! 未找到`，用环境变量覆盖后重试：

| 变量 | 作用 | 示例 |
|---|---|---|
| `BROWSER_PATH` | 指定 Chromium 系浏览器 | `export BROWSER_PATH="/path/to/msedge"` |
| `NODE_PATH_BIN` | 指定 node（需 22+） | `export NODE_PATH_BIN="/path/to/node"` |
| `TRIP_GUIDE_OUT` | 指定攻略输出根目录 | `export TRIP_GUIDE_OUT="D:/旅行攻略"` |

然后**重启客户端**（或新开一个会话），让宿主重新扫描 skills 目录。

## 确认加载成功

在会话里说：

```
帮我做旅行攻略
```

能正常进入追问流程（先问"想去哪几个城市、从哪出发"）就说明加载成功了。

## 卸载

删掉对应目录即可：

```bash
rm -rf ~/.workbuddy/skills/trip-guide-builder
rm -rf ~/.workbuddy/skills/social-card-render
```

## 常见安装问题

**Q：客户端里说了「帮我做旅行攻略」但没反应？**

依次排查：
1. 目录层级对不对 —— 应该是 `skills/trip-guide-builder/SKILL.md`，不是 `skills/trip-guide-builder/trip-guide-builder/SKILL.md`
2. 客户端重启了没有 —— skills 目录是启动时扫描的
3. `SKILL.md` 开头的 frontmatter 有没有被破坏 —— 需要 `---` 包裹的 `name` 和 `description`

**Q：`_env.py` 报找不到 node，但我明明装了？**

可能装的是 22 以下版本。CDP 截图依赖 Node 22+ 的原生 `WebSocket`，低版本会报 `WebSocket is not defined`。
升级后如果还找不到，用 `NODE_PATH_BIN` 显式指定路径。

**Q：跑 verify.py 卡住不动？**

通常是浏览器启动有问题。verify.py 会等 CDP 端口就绪（默认 40 秒超时）。
如果超时，检查 `BROWSER_PATH` 指向的是不是 Chromium 系浏览器 ——
Firefox / Safari **不支持** CDP，必须用 Edge / Chrome / Chromium。
