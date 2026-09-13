#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""重建发布目录 publish/

用法：
  python prep_publish.py --dir "<项目目录>"
  python prep_publish.py --dir "<项目目录>" --main "川西环线·旅行攻略.html"

做的事：
  1. 清空并重建 <dir>/publish/
  2. 主 HTML -> index.html，并额外复制一份 guide.html（绕客户端缓存的备用入口）
  3. 其余 .html 一并拷入（排除 _ 开头、publish、离线版）
  4. img/ 整体拷入（保持相对路径）
  5. 若存在票务页，在主 HTML 的票夹页顶部插入跳转入口（尽力而为，失败不中断）
"""
import argparse
import pathlib
import re
import shutil
import sys

SKIP_PREFIX = ("_",)


def pick_main(d: pathlib.Path, explicit):
    if explicit:
        p = d / explicit
        if not p.exists():
            sys.exit("找不到主文件: %s" % p)
        return p
    cands = [f for f in d.glob("*.html")
             if not f.name.startswith(SKIP_PREFIX)
             and "离线版" not in f.name]
    if not cands:
        sys.exit("目录下没有可用的 .html")
    return max(cands, key=lambda f: f.stat().st_size)


BANNER = (
    "  h += '<div class=\"panel\" style=\"background:var(--paper3)\">';\n"
    "  h += '<div style=\"font-size:13.5px;font-weight:800;margin-bottom:5px\">"
    "⏰ 每项票的抢票倒计时</div>';\n"
    "  h += '<div style=\"font-size:12.5px;color:var(--ink2);margin-bottom:10px\">"
    "本页给你「什么时候开抢」，倒计时页给你「还剩几天几小时」——实时刷新。</div>';\n"
    "  h += '<div class=\"acts\"><a class=\"btn pri\" href=\"ticket.html\">"
    "打开抢票倒计时 →</a></div>';\n"
    "  h += '</div>';\n"
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="项目目录")
    ap.add_argument("--main", default=None, help="主 HTML 文件名（默认取最大的）")
    ap.add_argument("--ticket", default="票务抢票倒计时.html", help="票务页文件名")
    a = ap.parse_args()

    d = pathlib.Path(a.dir)
    if not d.is_dir():
        sys.exit("目录不存在: %s" % d)

    pub = d / "publish"
    if pub.exists():
        shutil.rmtree(pub)
    (pub / "img").mkdir(parents=True)

    main_html = pick_main(d, a.main)
    src = main_html.read_text(encoding="utf-8")

    # ---- 票务页入口（尽力而为）----
    ticket_src = d / a.ticket
    if ticket_src.exists() and "ticket.html" not in src:
        pat = re.compile(r"(function walletPage\(\)\{\s*\n\s*var h = '';\s*\n)")
        if pat.search(src):
            src = pat.sub(lambda m: m.group(1) + BANNER, src, count=1)
            print("  已插入票务入口 -> ticket.html")
        else:
            print("  !! 没找到 walletPage 锚点，跳过票务入口")

    (pub / "index.html").write_text(src, encoding="utf-8")
    (pub / "guide.html").write_text(src, encoding="utf-8")   # 备用入口

    # ---- 其余 html ----
    n_html = 2
    for f in sorted(d.glob("*.html")):
        if f.name.startswith(SKIP_PREFIX) or "离线版" in f.name or f == main_html:
            continue
        if f.name == a.ticket:
            (pub / "ticket.html").write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
            print("  票务页 -> ticket.html")
        else:
            shutil.copy2(f, pub / f.name)
        n_html += 1

    # ---- 图片 ----
    n_img = 0
    imgdir = d / "img" / "final"
    if imgdir.is_dir():
        (pub / "img" / "final").mkdir(parents=True, exist_ok=True)
        for f in sorted(imgdir.glob("*.jpg")) + sorted(imgdir.glob("*.png")):
            shutil.copy2(f, pub / "img" / "final" / f.name)
            n_img += 1

    # ---- 报告 ----
    total = 0
    print("\npublish/ 内容:")
    for f in sorted(pub.rglob("*")):
        if f.is_file():
            total += f.stat().st_size
            print("   %-34s %8d B" % (f.relative_to(pub).as_posix(), f.stat().st_size))
    print("\nHTML %d 个 · 图片 %d 张 · 合计 %.2f MB" % (n_html, n_img, total / 1048576))

    # ---- 体检 ----
    bad = re.findall(r"__[A-Z_]+__", src)
    if bad:
        print("!! 主文件仍有未替换占位符: %s" % sorted(set(bad)))
    else:
        print("占位符检查: 通过")


if __name__ == "__main__":
    main()
