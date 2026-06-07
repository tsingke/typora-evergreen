#!/usr/bin/env python3
"""
Obsidian → Typora 链接转换工具

将 Obsidian 的 [[wikilink]] 语法转换为 Typora 可识别的标准 markdown 链接。
支持两种模式:
  1. 直接转换文件:  python3 obsidian-to-typora.py  input.md  output.md
  2. 批量转换目录:  python3 obsidian-to-typora.py  /path/to/vault/  /path/to/output/

转换规则:
  [[Note]]          →  [Note](./Note.md)
  [[Note|显示名]]    →  [显示名](./Note.md)
  [[Note#标题]]      →  [Note → 标题](./Note.md)
  ![[image.png]]    →  ![](./image.png)
  [[Note#^块引用]]   →  [Note (块引用)](./Note.md)

使用方式:
  1) 单个文件: python3 obsidian-to-typora.py 我的笔记.md 转换后.md
  2) 整库拷贝: python3 obsidian-to-typora.py ~/obsidian-vault ~/Desktop/for-typora
"""

import re
import os
import sys
import shutil
from pathlib import Path


def convert_wikilink(match):
    """将单个 [[wikilink]] 转换为标准 markdown 链接"""
    content = match.group(1)
    is_embed = match.group(0).startswith("!")  # ![[...]] 嵌入

    # 分离 display text 和目标
    # [[target|display]] — 直接在 | 处拆分（Obsidian 中 \| 的 \ 是编辑器转义）
    # 拆分后清理 target 尾部多余的 \，display 头部多余的 \
    parts = content.split("|", 1)
    target = parts[0].strip().rstrip("\\")
    display = parts[1].strip().lstrip("\\") if len(parts) > 1 else None

    # 还原转义字符：\| → |, \[ → [, \] → ]
    target = target.replace(r"\|", "|").replace(r"\[", "[").replace(r"\]", "]")
    if display:
        display = display.replace(r"\|", "|").replace(r"\[", "[").replace(r"\]", "]")

    # 分离 section/block 引用
    # [[target#heading]] 或 [[target#^blockid]]
    if "#" in target:
        target_part, section = target.split("#", 1)
    else:
        target_part = target
        section = None

    # 清理目标文件名（用 ./ 前缀让 Typora 明确识别为相对路径）
    target_file = "./" + target_part.strip() + ".md"

    if is_embed:
        # ![[image.png]] → ![](image.png)
        # ![[note]] → 嵌入模式（Typora 不支持，转换为引用链接）
        ext = os.path.splitext(target)[1].lower()
        if ext in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"):
            return f"![](./{target})"
        else:
            display_text = display or target_part
            return f"[📄 {display_text}]({target_file})"
    else:
        # [[target]] → [target](target.md)
        # [[target|display]] → [display](target.md)
        display_text = display or target_part

        if section:
            if section.startswith("^"):
                # [[target#^blockref]] → 块引用（无法精确转换）
                return f"[{display_text} ⤴]({target_file})"
            else:
                # [[target#heading]] → 标题引用
                return f"[{display_text} → {section}]({target_file})"
        else:
            return f"[{display_text}]({target_file})"


def convert_file(text):
    """转换文本中所有 Obsidian 链接语法"""

    # 1. 先处理 ![[...]] 嵌入
    text = re.sub(r'!\[\[([^\]]+)\]\]', convert_wikilink, text)

    # 2. 再处理 [[...]] 链接
    text = re.sub(r'\[\[([^\]]+)\]\]', convert_wikilink, text)

    return text


def process_file(input_path, output_path):
    """转换单个 markdown 文件"""
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"  ❌ 读取失败: {input_path} — {e}")
        return False

    converted = convert_file(content)

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(converted)
        print(f"  ✅ {input_path.name} → {output_path.name}")
        return True
    except Exception as e:
        print(f"  ❌ 写入失败: {output_path} — {e}")
        return False


def process_directory(input_dir, output_dir):
    """批量转换目录下的所有 markdown 文件"""
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    if not input_path.is_dir():
        print(f"❌ 输入目录不存在: {input_dir}")
        return

    # 创建输出目录
    output_path.mkdir(parents=True, exist_ok=True)

    success = 0
    total = 0

    for md_file in input_path.rglob("*.md"):
        total += 1
        rel_path = md_file.relative_to(input_path)
        out_file = output_path / rel_path

        # 保持目录结构
        out_file.parent.mkdir(parents=True, exist_ok=True)

        if process_file(md_file, out_file):
            success += 1

        # 同时也复制非 markdown 资源文件（图片等）
        # （会在第二轮处理）

    # 复制图片等资源文件（不转换，仅拷贝）
    for ext in ("*.png", "*.jpg", "*.jpeg", "*.gif", "*.svg", "*.webp", "*.bmp", "*.pdf"):
        for res_file in input_path.rglob(ext):
            rel_path = res_file.relative_to(input_path)
            out_file = output_path / rel_path
            if not out_file.exists():
                out_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(res_file, out_file)

    print(f"\n📊 总计: {total} 个文件，成功转换 {success} 个")
    print(f"📁 输出目录: {output_path.absolute()}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    if os.path.isdir(input_path):
        process_directory(input_path, output_path)
    else:
        process_file(Path(input_path), Path(output_path))


if __name__ == "__main__":
    main()
