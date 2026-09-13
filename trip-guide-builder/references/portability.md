# 跨机器可移植性（把 skill 交给别人用）

> 这个 skill 默认按 **WorkBuddy 环境**设计。换一台机器、换一个人跑，
> 差异不在流程，在**能力可用性**和**环境路径**。
> 这一份说清：什么是必需的、什么是可降级的、缺了怎么办。

---

## 一、能力盘点（三档）

### ✅ 必需 —— WorkBuddy 内置，人人都有

| 能力 | 本 skill 用在哪 | 缺了会怎样 |
|---|---|---|
| 文件读写 + Shell | 全部阶段 | 没法工作 |
| 联网搜索 / 网页抓取 | ③ 核实（查票价 / 预约 / 地址） | 数据无法核验，只能标"以官方公告为准" |
| `ImageGen`（图生图） | ⑤ 配图 | 走降级路径 A（见第三节） |
| `workbuddy_sites_deploy` | ⑦b 发布上线 | 走降级路径 B |
| `present_files` | 交付展示 | 改成直接把路径写在回复里 |

### 🟡 可选 —— 装了更好，不装不影响主流程

| 能力 | 用在哪 | 没有时怎么办 |
|---|---|---|
| `agent-mail` 智能体邮箱 | ⑦ 把链接发到用户邮箱 | 直接把链接复制给用户，手动转发 |
| 三个配套 skill（见第二节） | 配图 / 验证 / 旧文档抽取 | **本 skill 已内联关键步骤**，不装也能跑 |

### ❌ 明确不需要 —— 别去接

- **金融类连接器**（行情 / 基金 / 宏观数据）—— 旅游数据不在里面。
  硬接只会因为连接器掉绑把整个流程掐断（自动化任务的硬依赖失败会在十几毫秒内整体终止）。

---

## 二、配套 skill：全部是可选的

本 skill 在正文里引用了三个兄弟 skill。**它们是"增强"，不是"依赖"** ——
别人的机器上大概率没装，所以每个引用点都已在本 skill 内部写好等效步骤。

| 引用的 skill | 提供什么 | 本 skill 内的等效内容 |
|---|---|---|
| `series-illustration-consistency` | 系列配图风格统一 | ⑤ 配图 一节已写全：母版图生图 + `input_fidelity:"high"` + 地标清单替换 + 串行独立目录 + 裁水印尺寸参数 |
| `mobile-html-headless-verify` | 移动端验证 / 破缓存 | ⑦ 验证 一节 + `scripts/verify.py` 一键验证；破缓存手法在 `references/pitfalls.md` |
| `markitdown-skill` / `pdfkit-py` | 旧行程书文本抽取 | ① 追问里给了 `pymupdf` 三行代码；PDF 也能用别的方式转文本 |
| `grill-me` | 通用需求追问 | ① 阶段的追问话术是它的旅游领域定制版，已完整写在 `references/interview.md` |

**结论：只装 `trip-guide-builder` 这一个 skill，全流程就能跑完。**
看到"见 skill xxx"时，当补充阅读即可，不必先去找那个 skill。

---

## 三、两条降级路径

### 降级 A · 没有 `ImageGen`（配额耗尽 / 不可用）

封面图改为以下之一，**优先级从高到低**：

1. **用户自备照片** —— 让用户发几张手机里的风景照，用 PIL 统一尺寸成 1280×740，
   加一层配色同色系的半透明蒙版 + 描边，视觉上贴近设计系统。
2. **CSS 纯色封面** —— 模板里把 `<img>` 换成纯 CSS 色块 + 大字地标清单：
   ```html
   <div class="hero-css" style="background:var(--paper3);border-bottom:2.5px solid var(--ink)">
     <div style="font-size:44px;font-weight:900;line-height:1.1">呼和浩特</div>
     <div style="font-size:13px;color:var(--ink2)">草原 · 火山 · 召庙 · 烧麦</div>
   </div>
   ```
   **照样能上线**，只是少了插画感染力。
3. **只留总览图** —— 各城市页回落同一张全景图（但需在页面标注"配图待补"）。

⚠️ 无论哪条路径，**每城封面必须跟随城市切换** —— 这个逻辑（`show()` 里读 `CITIES[k].img`）不能省，
否则会出现"用户说图没变、其实是根本没渲染"的经典事故。

### 降级 B · 不能发布在线链接

| 场景 | 交付方式 |
|---|---|
| 完全没有托管能力 | 只交**离线单文件版**（`make_offline.py`），用户存手机直接打开 |
| 用户自己有服务器 / 云盘 | 交 `publish/` 整个目录，让用户自己传 |
| 只想本地看 | 交 `<主题>·旅行攻略.html` + `img/` 目录，双击浏览器打开 |

**离线单文件版在任何情况下都要生成** —— 它不只是兜底，
对"戈壁、沙漠、深山没信号"的场景本身就是刚需。

---

## 四、环境自适配（脚本层已处理）

`scripts/_env.py` 统一探测，其余脚本都走它。**不用改代码**，必要时用环境变量覆盖：

| 要探测的东西 | 自动探测顺序 | 环境变量覆盖 |
|---|---|---|
| **浏览器** | `BROWSER_PATH`/`EDGE_PATH`/`CHROME_PATH` → Windows 常见安装路径 → macOS `/Applications` → `PATH` 里的 `msedge`/`chrome`/`chromium` → macOS `mdfind` | `BROWSER_PATH` |
| **node** | `NODE_PATH_BIN` → `PATH` → `~/.workbuddy/binaries/node/versions/*`（取最高版本） | `NODE_PATH_BIN` |
| **python** | `sys.executable`（跑脚本的那个） | — |
| **输出根目录** | `TRIP_GUIDE_OUT` → `D:\旅行攻略`（有 D 盘时）→ `~/旅行攻略` | `TRIP_GUIDE_OUT` |

自检：
```bash
python scripts/_env.py
# 浏览器 : C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe
# node   : C:\Users\...\node.exe
# python : C:\...\python.exe
# 输出根 : D:\旅行攻略
```

**浏览器必须是 Chromium 系**（Edge / Chrome / Chromium / Brave）——
`verify_tabs.js` 依赖 CDP（Chrome DevTools Protocol），Firefox / Safari 不支持。

**node 需要 18+**（用了原生 `WebSocket`），建议 22+。

---

## 五、跨用户差异（要问，别假设）

以下是**每个用户都不同**的，别沿用上一份攻略的设定：

| 项 | 怎么处理 |
|---|---|
| **输出目录** | 默认 `<输出根>/<YYYYMMDD>_<主题>/`；用户指定就听用户的 |
| **配色偏好** | 给 `assets/palette-sample.html` 截图让他挑，别替他定 |
| **是否要配图** | 有人只要信息密度，觉得插画占地方 —— 问一句 |
| **是否要发布** | 有人只想要离线文件（公司内网、不外发） |
| **有无邮箱** | 没有就不发，直接给链接 |
| **Windows / macOS** | 脚本已跨平台；但 `--window-size` DPI 陷阱是 **Windows 特有**，Mac 上不会误报 |

⚠️ 特别注意：**不要把某个用户的私有约定当成 skill 默认值**
（例如"输出必须放 D 盘某个特定目录"是个人习惯，不是 skill 规范）。
skill 里只保留通用的默认值，个人偏好通过参数或环境变量传。

---

## 六、把 skill 交给朋友

### 方式 1 · 直接给目录（最快）

```
~/.workbuddy/skills/trip-guide-builder/     ← 整个目录打包发过去
```

对方解压到自己的 `~/.workbuddy/skills/` 下，重启 WorkBuddy 即可。
**有 `agent_created: true` 标记的 skill 可以这样直接拷。**

### 方式 2 · 让对方自己复制（不想发文件）

把 `SKILL.md` + `references/` + `scripts/` + `assets/` 全文贴给对方，
让他用 WorkBuddy 的 `skill-creator` 建一个同名 skill。

### 交接时必须一并说明的三件事

1. **启动语**：「帮我做旅行攻略」
2. **前提**：需要 WorkBuddy（配图 / 发布走内置能力）；浏览器装 Edge 或 Chrome
3. **可降级**：没有配图额度、不发邮箱，都照样能出攻略

---

## 七、首次在新机器上跑的自检顺序

```bash
# 1. 环境探测
python scripts/_env.py

# 2. 骨架生成（顺手验证脚本链通不通）
python scripts/scaffold.py --title "测试 · 旅行攻略" --brand 测试 --out "<临时目录>"

# 3. 一键验证（起服务 + 起浏览器 + 逐 Tab）
python scripts/verify.py --dir "<临时目录>" --shot "<临时目录>/_v.png"

# 4. 发布目录 + 离线版
python scripts/prep_publish.py --dir "<临时目录>"
python scripts/make_offline.py  --dir "<临时目录>"
```

四步全过 = 环境就绪。**任何一步报错，先看是不是没装浏览器 / 没装 node。**
