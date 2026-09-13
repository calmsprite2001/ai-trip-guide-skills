#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""移动端多宽度预览出图（iframe 锁精确 CSS 宽度）

用法：
  python shot_preview.py "D:/项目/攻略.html"
  python shot_preview.py "D:/项目/攻略.html" out.png            # 自定义输出
  python shot_preview.py "D:/项目/攻略.html" out.png 390        # 只测一个宽度

浏览器自动探测（Edge/Chrome/Chromium）。找不到时用环境变量指定：
  BROWSER_PATH="C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"

为什么用 iframe：
  Windows 125% 缩放下，Edge 无头 --window-size=390 实际渲染出的 CSS 视口是 481px，
  而 --screenshot 只存 390px 宽 -> 右侧被硬裁，会让你误判成"版式溢出"。
  iframe 内部是精确的 CSS 视口，与宿主机 DPI 无关。

注意：
  iframe 里若引用相对路径资源，外壳页必须放在待测页面的同一目录。
"""
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _env  # noqa: E402  —— 跨机器浏览器探测（EDGE_PATH / CHROME_PATH / BROWSER_PATH 可覆盖）

SHELL = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<style>
  body{margin:0;background:#3A3A3A;padding:14px;font:13px/1.5 "Microsoft YaHei",sans-serif;color:#fff}
  .row{display:flex;gap:14px;align-items:flex-start}
  .col{flex:0 0 auto}
  .lab{font-weight:800;margin-bottom:6px;font-size:13px;color:#FFD479}
  iframe{border:0;background:#fff;display:block;border-radius:4px}
</style></head><body>
<div class="row">
%s
</div>
</body></html>
"""


def find_edge():
    for p in EDGES:
        if pathlib.Path(p).exists():
            return p
    sys.exit("找不到 Edge，请修改脚本里的 EDGES 路径")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    page = pathlib.Path(sys.argv[1]).resolve()
    if not page.exists():
        sys.exit("找不到: %s" % page)

    out = pathlib.Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else (page.parent / "_preview.png")
    widths = [int(sys.argv[3])] if len(sys.argv) > 3 else [375, 390, 430]
    height = int(sys.argv[4]) if len(sys.argv) > 4 else 1500

    # ---- 生成外壳页（与待测页同目录，保证相对路径可用）----
    labels = {375: "iPhone SE", 390: "iPhone 14/15", 430: "Pro Max"}
    cols = ""
    for w in widths:
        cols += ('  <div class="col"><div class="lab">%d · %s</div>'
                 '<iframe src="%s" width="%d" height="%d"></iframe></div>\n'
                 % (w, labels.get(w, ""), page.name, w, height))

    shell = page.parent / "_preview.html"
    shell.write_text(SHELL % cols, encoding="utf-8")

    # ---- 截图 ----
    if out.exists():
        out.unlink()                      # 同路径复用会读到旧内容
    ud = pathlib.Path(tempfile.gettempdir()) / "edgepv"
    ud.mkdir(parents=True, exist_ok=True)

    total_w = sum(widths) + 14 * (len(widths) + 1)
    edge = find_edge()
    cmd = [edge, "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
           "--user-data-dir=" + str(ud),
           "--window-size=%d,%d" % (total_w, height + 60),
           "--virtual-time-budget=5000",
           "--screenshot=" + str(out),
           shell.as_uri()]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

    if out.exists():
        print("ok  预览图: %s  (%.0f KB)  宽度 %s" % (out, out.stat().st_size / 1024, widths))
        print("    外壳页: %s" % shell.name)
    else:
        print("截图失败\nstdout: %s\nstderr: %s" % (r.stdout[-800:], r.stderr[-800:]))
        sys.exit(1)


if __name__ == "__main__":
    main()
