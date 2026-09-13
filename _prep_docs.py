# -*- coding: utf-8 -*-
"""把山西攻略的成品图压进 docs/，供 README 引用。

用法：python _prep_docs.py
产物：docs/*.jpg  +  docs/*.png
"""
import pathlib

from PIL import Image

SRC = pathlib.Path(r"D:/旅行攻略/20260913_山西古建5日")
DST = pathlib.Path(r"D:/旅行攻略/_github/ai-trip-guide-skills/docs")
DST.mkdir(parents=True, exist_ok=True)


def resize_keep(img, target_w):
    """等比缩到指定宽度，返回新图。"""
    w, h = img.size
    if w <= target_w:
        return img
    nw = target_w
    nh = round(h * target_w / w)
    return img.resize((nw, nh), Image.LANCZOS)


def save_jpg(src, out, width, quality=82):
    img = Image.open(src).convert("RGB")
    img = resize_keep(img, width)
    p = DST / out
    img.save(p, "JPEG", quality=quality, optimize=True, progressive=True)
    print(f"  {out:32s} {img.size[0]}x{img.size[1]}  {p.stat().st_size / 1024:6.1f} KB")
    return p


def crop_tall(src, out, width, max_ratio=2.6, quality=82):
    """超长截图裁掉下半部分，避免在 README 里被拉成一条线。

    保留顶部 max_ratio 倍宽度的内容（顶部信息密度最高）。
    """
    img = Image.open(src).convert("RGB")
    w, h = img.size
    limit = int(w * max_ratio)
    if h > limit:
        img = img.crop((0, 0, w, limit))
    img = resize_keep(img, width)
    p = DST / out
    img.save(p, "JPEG", quality=quality, optimize=True, progressive=True)
    print(f"  {out:32s} {img.size[0]}x{img.size[1]}  {p.stat().st_size / 1024:6.1f} KB")
    return p


print("=== 城市水彩长卷（4 张，README 主视觉）===")
for name in ["loop", "datong", "taiyuan", "pingyao"]:
    save_jpg(SRC / "img" / "final" / f"{name}.jpg", f"cover-{name}.jpg", 1200)

print("\n=== 攻略页实拍（手机版式）===")
crop_tall(SRC / "xhs" / "shots" / "overview.png", "guide-overview.jpg", 620, max_ratio=2.8)
crop_tall(SRC / "xhs" / "shots" / "wallet.png", "guide-wallet.jpg", 620, max_ratio=2.8)

print("\n=== 小红书卡片（social-card-render 产物）===")
save_jpg(SRC / "xhs" / "ready" / "01_封面.jpg", "xhs-01-cover.jpg", 760)
save_jpg(SRC / "xhs" / "ready" / "02_方法.jpg", "xhs-02-method.jpg", 760)
save_jpg(SRC / "xhs" / "ready" / "09_避坑与引导.jpg", "xhs-09-tips.jpg", 760)

print("\n=== 汇总 ===")
total = 0
for f in sorted(DST.iterdir()):
    if f.is_file():
        total += f.stat().st_size
print(f"共 {len(list(DST.iterdir()))} 个文件，合计 {total / 1024:.1f} KB")
