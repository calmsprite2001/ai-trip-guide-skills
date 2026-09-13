#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""旅行攻略 · 项目骨架生成器

用法：
  python scaffold.py --title "川西环线 · 旅行攻略" --brand "川西环线" --theme C
  python scaffold.py --out "D:/旅行攻略/20260913_川西环线" --title "川西环线 · 旅行攻略"

--out 不传时自动生成：<输出根>/<今天YYYYMMDD>_<品牌>
输出根优先顺序：环境变量 TRIP_GUIDE_OUT > D:\旅行攻略（Windows 且存在 D 盘时）> ~/旅行攻略

主题：A 奶油暖调(默认) / B 清透冷调 / C 墨绿山野 / D 靛青海港
"""
import argparse
import datetime
import pathlib
import re
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _env  # noqa: E402

TPL = HERE.parent / "assets" / "template.html"

# 与 references/palettes.md 保持一致
THEMES = {
    "A": dict(name="奶油暖调", theme_color="#F7EEDC",
              paper="#F7EEDC", paper2="#FFFCF4", paper3="#F2E6CE",
              ink="#211C15", ink2="#5B5240", ink3="#8E846A",
              red="#C8503A", mustard="#E5A93C", olive="#6D8B4B",
              sky="#6FA8CF", terra="#C1764A"),
    "B": dict(name="清透冷调", theme_color="#EDF6F6",
              paper="#EDF6F6", paper2="#FFFFFF", paper3="#E2EFF0",
              ink="#1D2A33", ink2="#4A5A64", ink3="#7C8C95",
              red="#D2604A", mustard="#EFC04A", olive="#74A05A",
              sky="#4E9BC4", terra="#C98A5B"),
    "C": dict(name="墨绿山野", theme_color="#EDF2E7",
              paper="#EDF2E7", paper2="#FBFDF8", paper3="#DFE9D6",
              ink="#1B231B", ink2="#4B574A", ink3="#828F80",
              red="#B4472F", mustard="#D8A62C", olive="#4E7C3F",
              sky="#4C8A8A", terra="#9E6B44"),
    "D": dict(name="靛青海港", theme_color="#E8EFF6",
              paper="#E8EFF6", paper2="#FFFFFF", paper3="#D8E4EF",
              ink="#161F2B", ink2="#41505F", ink3="#7B8B9A",
              red="#C24A3C", mustard="#E3A933", olive="#5C8B57",
              sky="#3F7FB0", terra="#B0703F"),
}

TODO = """# {title} · 待办

由 trip-guide-builder 生成。**按顺序做完这 4 步。**

## 1. 放封面图
目录：`img/final/`
- `loop.jpg` —— 全景长卷（非城市页与总览页用）
- `<城市id>.jpg` —— 每城一张，文件名与 `CITIES[].id` 一致

生成手法见 skill `series-illustration-consistency`（图生图锁风格）。
原始大图放 `img/_raw/`，旧图备份放 `img/final_v1/`。

## 2. 改数据（只改数据，别动渲染函数）
在 `{html}` 里搜 `/* ====` 定位各块：

- [ ] `CFG` —— 标题 / 品牌 / 封面图 / 起止日期 `t0` `t1` / `totalDays` / `dayMap` / 页脚
- [ ] `PLANE` `TRAIN` `BOOK` —— 票务（含 `sale` 开售时间、`st` 状态）
- [ ] `CITIES` —— 每城 `days` / `eat` / `buy` / `walk` / `shots`
- [ ] `OV` —— 总览表 / 票夹清单 / 应急电话与防坑

字段结构见 skill 的 `references/data-schema.md`。
`PAGES` 会自动跟着 `CITIES` 走，**不用改**。

## 3. 本地验证
```bash
python {scripts}/verify.py --dir "{out}" --shot "{out}/_verify.png"
```
一条命令自动起服务 + 起浏览器 + 逐 Tab 检查（封面是否随城市切换 / 横向溢出 / undefined / 图片加载）。

只看版式（三宽度并排）：
```bash
python {scripts}/shot_preview.py "{html}"
```

核对清单：
- [ ] `CFG.totalDays` == `OV.days` 条数
- [ ] 每个 `CITIES[].id` 都有一个 Tab，且**顶部封面会随城市切换**
- [ ] `CITIES[].img` 路径与实际文件名一致
- [ ] `dayMap` 覆盖全部行程日

## 4. 发布 + 离线兜底
```bash
python {scripts}/prep_publish.py --dir "{out}"
python {scripts}/make_offline.py --dir "{out}"
```
然后用 `workbuddy_sites_deploy` 发布（更新已有应用传 `updateExistingApp: true`）。
**改过图记得换文件名**（网关忽略 query string），见 `references/pitfalls.md`。
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None,
                    help="项目输出目录（默认 <输出根>/<YYYYMMDD>_<品牌>）")
    ap.add_argument("--title", required=True, help="页面标题")
    ap.add_argument("--brand", default=None, help="顶栏短名（默认取标题前 6 字）")
    ap.add_argument("--theme", default="A", choices=list(THEMES), help="配色主题")
    ap.add_argument("--file", default=None, help="HTML 文件名（默认 <标题>.html）")
    a = ap.parse_args()

    if a.out:
        out = pathlib.Path(a.out)
    else:
        stem = (a.brand or a.title.split("·")[0].strip() or "旅行攻略")
        out = _env.default_outbase() / ("%s_%s" % (datetime.date.today().strftime("%Y%m%d"), stem))
    if not TPL.exists():
        sys.exit("模板不存在: %s" % TPL)

    t = THEMES[a.theme]
    brand = a.brand or a.title.split("·")[0].strip()[:8]
    html_name = a.file or (a.title.replace(" ", "") + ".html")

    for sub in ("img/final", "img/_raw", "build"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    s = TPL.read_text(encoding="utf-8")

    # ---- 头部占位符 ----
    s = s.replace("__TITLE__", a.title)
    s = s.replace("__BRAND__", brand)
    s = s.replace("__THEME_COLOR__", t["theme_color"])
    s = s.replace("__HERO_IMG__", "img/final/loop.jpg")
    s = s.replace("__HERO_TITLE__", a.title)
    s = s.replace("__HERO_KICK__", "出发 — 返程 · N 天")
    s = s.replace("__HERO_SUB__", "城市 A → 城市 B → 城市 C")

    # ---- CFG 里的文案（页面实际显示的是这里，必须同步）----
    kick, subline = "出发 — 返程 · N 天", "城市 A → 城市 B → 城市 C"
    s = re.sub(r"title:\s*'[^']*'", "title:   '%s'" % a.title, s, count=1)
    s = re.sub(r"brand:\s*'[^']*'", "brand:   '%s'" % brand, s, count=1)
    s = re.sub(r"heroAlt:\s*'[^']*'", "heroAlt: '全景'", s, count=1)
    s = re.sub(r"kick:\s*'[^']*'", "kick:    '%s'" % kick, s, count=1)
    s = re.sub(r"sub:\s*'[^']*'", "sub:     '%s'" % subline, s, count=1)

    # ---- 配色变量 ----
    old_root = re.search(
        r":root\{\s*\n\s*--paper:.*?\n\s*--ink:.*?\n\s*--red:.*?\n", s, re.S)
    if not old_root:
        sys.exit("模板 :root 结构不匹配")
    new_root = (
        ":root{\n"
        "  --paper:%(paper)s; --paper2:%(paper2)s; --paper3:%(paper3)s;\n"
        "  --ink:%(ink)s; --ink2:%(ink2)s; --ink3:%(ink3)s;\n"
        "  --red:%(red)s; --mustard:%(mustard)s; --olive:%(olive)s;"
        " --sky:%(sky)s; --terra:%(terra)s;\n" % t)
    s = s[:old_root.start()] + new_root + s[old_root.end():]

    dst = out / html_name
    dst.write_text(s, encoding="utf-8")

    (out / "TODO.md").write_text(
        TODO.format(title=a.title, html=html_name, out=out.as_posix(),
                    scripts=HERE.as_posix(), htmlname=html_name),
        encoding="utf-8")

    left = re.findall(r"__[A-Z_]+__", s)
    print("项目目录: %s" % out)
    print("配色主题: %s · %s  (--paper %s)" % (a.theme, t["name"], t["paper"]))
    print("主文件  : %s  (%d bytes)" % (html_name, dst.stat().st_size))
    print("待办清单: TODO.md")
    print()
    print("残留占位符: %s" % (sorted(set(left)) if left else "无"))
    print("下一步  : 放图 -> 改 CFG/PLANE/TRAIN/BOOK/CITIES/OV -> 验证 -> 发布")


if __name__ == "__main__":
    main()
