#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键安装 ai-trip-guide-skills 到本机 skills 目录。

用法:
    python install.py                    # 自动探测 skills 目录并安装
    python install.py --target <目录>    # 指定 skills 目录
    python install.py --dry-run          # 只显示会做什么，不实际写入
"""
import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
SKILLS = ["trip-guide-builder", "social-card-render"]


def find_skills_dir():
    """探测本机 skills 目录。"""
    home = pathlib.Path.home()
    cands = [
        home / ".workbuddy" / "skills",   # WorkBuddy
        home / ".codex" / "skills",       # Codex
        home / ".claude" / "skills",      # Claude Code（备用）
    ]
    for c in cands:
        # 父目录存在（客户端装过）就认
        if c.parent.exists():
            return c
    return cands[0]


def human(p):
    try:
        return str(p.relative_to(pathlib.Path.home()))
    except ValueError:
        return str(p)


def main():
    ap = argparse.ArgumentParser(description="安装 ai-trip-guide-skills")
    ap.add_argument("--target", help="skills 目录（不传则自动探测）")
    ap.add_argument("--dry-run", action="store_true", help="只显示，不写入")
    a = ap.parse_args()

    # ---- 校验源 ----
    missing = [s for s in SKILLS if not (HERE / s / "SKILL.md").exists()]
    if missing:
        print("!! 源目录不完整，缺少:", ", ".join(missing))
        print("   请在仓库根目录运行本脚本。")
        return 1

    target = pathlib.Path(a.target).expanduser().resolve() if a.target else find_skills_dir()
    print("源仓库    :", HERE)
    print("目标 skills:", human(target))
    print()

    if a.dry_run:
        print("[dry-run] 将执行以下操作：")
    else:
        target.mkdir(parents=True, exist_ok=True)

    # ---- 先环境自检（用仓库内的脚本，避免动到已安装的旧版本）----
    envpy = HERE / "trip-guide-builder" / "scripts" / "_env.py"
    if envpy.exists():
        print("\n--- 环境自检 ---")
        try:
            subprocess.run([sys.executable, str(envpy)], check=False)
        except Exception as e:
            print("自检脚本执行失败:", e)

    installed = []
    for name in SKILLS:
        src = HERE / name
        dst = target / name
        nfiles = sum(1 for p in src.rglob("*") if p.is_file())
        print("  %-22s -> %s  (%d 个文件)" % (name, human(dst), nfiles))

        if a.dry_run:
            continue

        # 已存在则备份
        if dst.exists():
            bak = dst.with_name(dst.name + ".bak-" + time.strftime("%Y%m%d%H%M%S"))
            shutil.move(str(dst), str(bak))
            print("     已存在，原目录备份到:", human(bak))

        shutil.copytree(src, dst, ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", "*.pyo"))
        installed.append(name)

    if a.dry_run:
        print("\n[dry-run] 未做任何修改。去掉 --dry-run 实际执行。")
        return 0

    print("\n安装完成:", ", ".join(installed))
    print("已安装位置:", human(target))
    print("\n下一步：重启客户端（或新开会话），然后说「帮我做旅行攻略」。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
