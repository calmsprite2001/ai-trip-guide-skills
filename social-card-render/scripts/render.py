# -*- coding: utf-8 -*-
"""HTML 卡片批量渲图：起本地服务 + 无头 Edge(CDP) + 按 .card 截图。

用法:
    python render.py --root <http根目录> --html <相对root的html路径> --out <输出目录>
"""
import argparse
import json
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent


def find_browser():
    import os
    for k in ("BROWSER_PATH", "EDGE_PATH", "CHROME_PATH"):
        v = os.environ.get(k)
        if v and pathlib.Path(v).exists():
            return v
    for p in [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")]:
        if pathlib.Path(p).exists():
            return p
    for n in ("msedge", "microsoft-edge", "chrome", "google-chrome", "chromium"):
        w = shutil.which(n)
        if w:
            return w
    sys.exit("找不到 Chromium 系浏览器，用 BROWSER_PATH 环境变量指定")


def find_node():
    import os
    for k in ("NODE_BIN", "NODE_PATH_BIN"):
        v = os.environ.get(k)
        if v and pathlib.Path(v).exists():
            return v
    base = pathlib.Path.home() / ".workbuddy/binaries/node/versions"
    if base.exists():
        cands = sorted(base.iterdir(), reverse=True)
        for d in cands:
            exe = d / "node.exe"      # windows
            if exe.exists():
                return str(exe)
            exe = d / "bin" / "node"  # posix
            if exe.exists():
                return str(exe)
    w = shutil.which("node")
    if w:
        return w
    sys.exit("找不到 node（需要 22+，原生 WebSocket）")


def free_port(start=9400):
    for p in range(start, start + 400):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise RuntimeError("没空闲端口")


def wait_http(port, timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/" % port, timeout=2).read(64)
            return True
        except Exception:
            time.sleep(0.4)
    return False


def wait_cdp(port, timeout=40):
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port, timeout=2) as r:
                json.loads(r.read().decode())
                return True
        except Exception:
            time.sleep(0.5)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="http server 根目录")
    ap.add_argument("--html", required=True, help="相对 root 的 html 路径")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--selector", default=".card", help="要截图的元素选择器")
    ap.add_argument("--viewport", default="1080x1440", help="CSS 视口 WxH")
    ap.add_argument("--scale", type=float, default=2.0, help="clip.scale")
    a = ap.parse_args()

    root = pathlib.Path(a.root).resolve()
    if not root.is_dir():
        sys.exit("root 不存在: %s" % root)
    out = pathlib.Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    vw, vh = (int(x) for x in a.viewport.lower().split("x"))
    browser, node = find_browser(), find_node()
    print("browser:", browser)
    print("node   :", node)

    hport = free_port(8700)
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(hport), "--directory", str(root)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not wait_http(hport):
        srv.kill()
        sys.exit("本地服务起不来（端口 %d）" % hport)
    print("http   :", hport)

    cport = free_port(9600)
    ud = tempfile.mkdtemp(prefix="cardedge_")
    proc = subprocess.Popen([browser, "--headless=new", "--disable-gpu", "--no-first-run",
                             "--no-default-browser-check", "--disable-sync",
                             "--disable-background-networking", "--hide-scrollbars",
                             "--user-data-dir=" + ud,
                             "--remote-debugging-port=%d" % cport, "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not wait_cdp(cport):
        proc.kill(); srv.kill()
        sys.exit("浏览器 CDP 没起来（端口 %d）" % cport)
    print("cdp    :", cport)

    url = "http://127.0.0.1:%d/%s" % (hport, a.html.replace("\\", "/").lstrip("/"))
    rc = subprocess.run([node, str(HERE / "render.js"), str(cport), url, str(out),
                         str(vw), str(vh), str(a.scale), a.selector]).returncode

    proc.kill(); srv.kill()
    print("exit:", rc)
    sys.exit(rc)


if __name__ == "__main__":
    main()
