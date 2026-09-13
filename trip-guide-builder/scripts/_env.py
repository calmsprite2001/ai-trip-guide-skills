#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""跨机器环境探测（内部共用模块，不单独调用）

解决的问题：脚本被拷到别人电脑上就跑不动 —— 浏览器路径、node 路径、
默认输出目录这些每台机器都不一样。这里统一做自适应。

调用方：
  import _env
  _env.find_browser()      -> Chrome/Edge 可执行文件路径，找不到返回 None
  _env.find_node()         -> node 可执行文件路径，找不到返回 None
  _env.default_outbase()   -> 默认的项目输出根目录（pathlib.Path）

覆盖方式（环境变量优先级最高）：
  BROWSER_PATH / EDGE_PATH / CHROME_PATH   指定浏览器
  NODE_PATH_BIN                            指定 node（注意不是 NODE_PATH）
  TRIP_GUIDE_OUT                           指定默认输出根目录
"""
import os
import pathlib
import shutil
import sys

# ---------------------------------------------------------------- 浏览器

_WIN_BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]

_MAC_BROWSERS = [
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
]

# PATH 里可能出现的命令名（Linux / 各种包管理器）
_CMD_NAMES = [
    "msedge", "microsoft-edge", "microsoft-edge-stable",
    "google-chrome", "google-chrome-stable", "chrome", "chromium", "chromium-browser",
]


def find_browser():
    """返回可用的 Chromium 系浏览器路径；找不到返回 None。

    必须是 Chromium 系（Edge/Chrome/Chromium/Brave）—— verify_tabs.js
    依赖 CDP（Chrome DevTools Protocol），Firefox/Safari 不支持。
    """
    # 1) 环境变量覆盖
    for k in ("BROWSER_PATH", "EDGE_PATH", "CHROME_PATH"):
        v = os.environ.get(k)
        if v and pathlib.Path(v).exists():
            return v

    # 2) 常见安装路径
    cands = _MAC_BROWSERS if sys.platform == "darwin" else _WIN_BROWSERS
    if sys.platform.startswith("linux"):
        cands = []
    for p in cands:
        if p and pathlib.Path(p).exists():
            return p

    # 3) PATH
    for name in _CMD_NAMES:
        w = shutil.which(name)
        if w:
            return w

    # 4) macOS 用 mdfind 兜底
    if sys.platform == "darwin" and shutil.which("mdfind"):
        try:
            import subprocess
            out = subprocess.run(
                ["mdfind", "kMDItemCFBundleIdentifier == 'com.google.Chrome'"],
                capture_output=True, text=True, timeout=8).stdout
            for line in out.splitlines():
                p = pathlib.Path(line) / "Contents/MacOS/Google Chrome"
                if p.exists():
                    return str(p)
        except Exception:
            pass

    return None


# ---------------------------------------------------------------- node

def find_node():
    """返回 node 可执行文件路径；找不到返回 None。

    优先顺序：环境变量 > PATH > WorkBuddy 托管运行时（版本号最高）。
    verify_tabs.js 需要 Node 18+（用了原生 WebSocket，建议 22+）。
    """
    for k in ("NODE_PATH_BIN", "NODE_BIN"):
        v = os.environ.get(k)
        if v and pathlib.Path(v).exists():
            return v

    w = shutil.which("node")
    if w:
        return w

    exe = "node.exe" if os.name == "nt" else "node"
    roots = [
        pathlib.Path.home() / ".workbuddy" / "binaries" / "node" / "versions",
        pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "WorkBuddy" / "binaries" / "node" / "versions",
    ]
    found = []
    for r in roots:
        if not r.is_dir():
            continue
        for d in r.iterdir():
            for p in (d / exe, d / "bin" / exe):
                if p.exists():
                    found.append(p)
    if found:
        # 版本目录名倒序，取最新的
        return str(sorted(found, key=lambda p: p.parent.parent.name, reverse=True)[0])

    return None


# ---------------------------------------------------------------- 输出目录

def default_outbase():
    """默认的项目输出根目录（不含日期_主题 子目录）。

    优先顺序：
      1. 环境变量 TRIP_GUIDE_OUT
      2. Windows 上若存在非系统盘（D:）则用 D:\\旅行攻略\\ —— 避免占用 C 盘
      3. ~/旅行攻略/
    """
    v = os.environ.get("TRIP_GUIDE_OUT")
    if v:
        return pathlib.Path(v)

    if os.name == "nt":
        d = pathlib.Path("D:/")
        if d.exists():
            return d / "旅行攻略"
    return pathlib.Path.home() / "旅行攻略"


# ---------------------------------------------------------------- 自检

if __name__ == "__main__":
    print("浏览器 :", find_browser() or "!! 未找到（Chromium 系，需 Edge/Chrome/Chromium）")
    print("node   :", find_node() or "!! 未找到（verify_tabs.js 需要 Node 22+）")
    print("python :", sys.executable)
    print("输出根 :", default_outbase())
