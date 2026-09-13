#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""一键移动端验证：起本地服务 + 起无头浏览器 + 跑 CDP 逐 Tab 检查 + 收尾

用法：
  python verify.py --dir "<项目目录>"                     # 自动挑主 HTML
  python verify.py --dir "<项目目录>" --main "攻略.html"
  python verify.py --url "https://xxx.app.workbuddy.host/"  # 验线上（不起本地服务）
  python verify.py --dir "<项目目录>" --shot out.png       # 顺便出张首屏图

不传 --url 时会自动：
  1. 起 `python -m http.server`（自动挑空闲端口，优先 ASCII 路径避免中文 URL 编码坑）
  2. 起无头 Chromium（Edge/Chrome 自动探测）
  3. 跑 verify_tabs.js（逐 Tab 点击、报封面/标题/溢出/undefined/图片加载）
  4. 关掉浏览器与服务

为什么不用 file://：
  CDP 需要 http 才能观察相对路径图片请求；file:// 下 Network 事件不完整。

中文路径已处理：
  HTML 文件名会被 percent-encode 后再 navigate（老脚本手动拼 URL 时踩过 404）。
"""
import argparse
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _env  # noqa: E402


def free_port(start=8901):
    for p in range(start, start + 60):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    sys.exit("找不到空闲端口")


def wait_http(port, timeout=15):
    import urllib.request
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/" % port, timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def wait_cdp(port, timeout=20):
    import urllib.request, json
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port, timeout=1) as r:
                json.load(r)
                return True
        except Exception:
            time.sleep(0.3)
    return False


def pick_main(d: pathlib.Path, explicit):
    if explicit:
        p = d / explicit
        if not p.exists():
            sys.exit("找不到主文件: %s" % p)
        return p
    cands = [f for f in d.glob("*.html")
             if not f.name.startswith("_") and "离线版" not in f.name]
    if not cands:
        sys.exit("目录下没有可用的 .html（用 --main 指定）")
    return max(cands, key=lambda f: f.stat().st_size)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None, help="项目目录（验本地时必填）")
    ap.add_argument("--main", default=None, help="主 HTML 文件名（默认取最大的）")
    ap.add_argument("--url", default=None, help="直接验证线上 URL（跳过本地服务）")
    ap.add_argument("--shot", default=None, help="首屏截图输出路径")
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--keep", action="store_true", help="跑完不关浏览器（调试用）")
    a = ap.parse_args()

    if not a.url and not a.dir:
        sys.exit(__doc__)

    browser = _env.find_browser()
    node = _env.find_node()
    if not browser:
        sys.exit("找不到 Chromium 系浏览器。装 Edge/Chrome，或用 BROWSER_PATH 环境变量指定。")
    if not node:
        sys.exit("找不到 node。装 Node 22+，或用 NODE_PATH_BIN 环境变量指定。")
    print("浏览器 : %s" % browser)
    print("node   : %s" % node)

    # ---------------- 起本地服务 ----------------
    srv = None
    if a.url:
        url = a.url
    else:
        d = pathlib.Path(a.dir).resolve()
        if not d.is_dir():
            sys.exit("目录不存在: %s" % d)
        main_html = pick_main(d, a.main)
        port = a.port or free_port()
        srv = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(port), "--directory", str(d)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not wait_http(port):
            srv.kill()
            sys.exit("本地服务起不来（端口 %d）" % port)
        # 中文文件名要 percent-encode，否则 CDP navigate 会 404
        url = "http://127.0.0.1:%d/%s" % (port, urllib.parse.quote(main_html.name))
        print("本地服务: 127.0.0.1:%d  ->  %s" % (port, main_html.name))

    # ---------------- 起浏览器 ----------------
    cdp_port = free_port(9400)
    ud = pathlib.Path(tempfile.mkdtemp(prefix="tripverify_"))
    proc = subprocess.Popen(
        [browser, "--headless=new", "--disable-gpu", "--no-first-run",
         "--no-default-browser-check", "--disable-sync",
         "--disable-background-networking",
         "--user-data-dir=" + str(ud),
         "--remote-debugging-port=%d" % cdp_port,
         "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not wait_cdp(cdp_port):
        proc.kill()
        sys.exit("浏览器 CDP 没起来（端口 %d）" % cdp_port)

    # ---------------- 跑检查 ----------------
    env = dict(os.environ, CDP_PORT=str(cdp_port))
    cmd = [node, str(HERE / "verify_tabs.js"), url]
    if a.shot:
        cmd.append(str(pathlib.Path(a.shot).resolve()))
    rc = subprocess.run(cmd, env=env).returncode

    # ---------------- 收尾 ----------------
    if not a.keep:
        for p in (proc, srv):
            if p:
                p.terminate()
                try:
                    p.wait(timeout=5)
                except Exception:
                    p.kill()
        shutil.rmtree(ud, ignore_errors=True)

    sys.exit(rc)


if __name__ == "__main__":
    main()
