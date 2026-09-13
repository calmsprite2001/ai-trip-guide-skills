#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成「离线单文件版」：图片全部 base64 内联，零外部请求。

用法：
  python make_offline.py --dir "<项目目录>"
  python make_offline.py --dir "<项目目录>" --main "川西环线·旅行攻略.html"

产物：<项目目录>/<主文件名>_离线版.html
用途：戈壁、沙漠、深山、边境等无信号路段；或存手机直接打开。
"""
import argparse
import base64
import pathlib
import re
import sys


def pick_main(d: pathlib.Path, explicit):
    """返回 (源主文件路径, 用于生成的内容路径)
    内容优先取 publish/index.html（可能已插入票务入口），文件名取源主文件。"""
    if explicit:
        p = d / explicit
        if not p.exists():
            sys.exit("找不到主文件: %s" % p)
        return p, p
    cands = [f for f in d.glob("*.html")
             if not f.name.startswith("_") and "离线版" not in f.name]
    if not cands:
        sys.exit("目录下没有可用的 .html")
    src = max(cands, key=lambda f: f.stat().st_size)
    pub = d / "publish" / "index.html"
    return (src, pub) if pub.exists() else (src, src)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--main", default=None)
    ap.add_argument("--imgdir", default="img/final", help="图片目录（相对项目目录）")
    a = ap.parse_args()

    d = pathlib.Path(a.dir)
    src_path, content_path = pick_main(d, a.main)
    src = content_path.read_text(encoding="utf-8")
    if content_path != src_path:
        print("内容取自: %s" % content_path.relative_to(d).as_posix())

    # ---- 外部依赖体检 ----
    ext = []
    ext += re.findall(r'<script[^>]+src="(https?://[^"]+)"', src)
    ext += re.findall(r'<link[^>]+href="(https?://[^"]+)"', src)
    ext += re.findall(r'src="(https?://[^"]+)"', src)
    print("外部依赖: %s" % (ext if ext else "无"))

    # ---- 内联图片 ----
    pattern = re.compile(r"img/[A-Za-z0-9_\-/]*?([A-Za-z0-9_\-]+\.(?:jpg|jpeg|png))(\?v=\d+)?")
    seen = set()
    cache = {}
    missing = []

    def rep(m):
        fn = m.group(1)
        if fn in cache:
            return cache[fn]
        p = d / a.imgdir / fn
        if not p.exists():
            missing.append(fn)
            return m.group(0)
        b = "data:image/%s;base64,%s" % (
            "png" if fn.lower().endswith("png") else "jpeg",
            base64.b64encode(p.read_bytes()).decode())
        cache[fn] = b
        seen.add(fn)
        print("   内联 %-22s %6d KB -> %6d KB" % (fn, p.stat().st_size // 1024, len(b) // 1024))
        return b

    out = pattern.sub(rep, src)

    leftover = sorted(set(re.findall(r"img/final/[^\"'\s)]+", out)))
    dst = d / (src_path.stem + "_离线版.html")
    dst.write_text(out, encoding="utf-8")

    print()
    if missing:
        print("!! 找不到的图片: %s" % sorted(set(missing)))
    print("内联 %d 张" % len(seen))
    print("残留外部引用: %s" % (leftover if leftover else "无"))
    print("产物: %s  (%.2f MB)" % (dst.name, dst.stat().st_size / 1048576))
    print("\n推到手机：微信「文件传输助手」发给自己 -> 用浏览器打开")
    print("iOS 可再「添加到主屏幕」，当 App 用。")


if __name__ == "__main__":
    main()
