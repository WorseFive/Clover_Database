#!/usr/bin/env python3
"""
重建所有 manifest.json - 扫描目录实际文件，生成准确索引
用于修复下载脚本中因重命名/转换导致的 manifest 不一致问题
"""
import json
import os
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent.parent
ALLOWED_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif'}

MAGIC_BYTES = {
    b'\xff\xd8\xff': 'jpg',
    b'\x89PNG\r\n\x1a\n': 'png',
    b'GIF87a': 'gif',
    b'GIF89a': 'gif',
    b'RIFF': 'webp',  # RIFF....WEBP
}

def detect_format(filepath: Path) -> str | None:
    try:
        with open(filepath, 'rb') as f:
            header = f.read(12)
    except:
        return None
    if header.startswith(b'\xff\xd8\xff'): return 'jpg'
    if header.startswith(b'\x89PNG\r\n\x1a\n'): return 'png'
    if header.startswith(b'GIF87a') or header.startswith(b'GIF89a'): return 'gif'
    if header.startswith(b'RIFF') and len(header) >= 12 and header[8:12] == b'WEBP': return 'webp'
    return None

def rebuild_image_manifest(category: str, dirname: str, triggers: list[str], description: str):
    """重建图片目录的 manifest"""
    img_dir = ROOT / "images" / dirname
    if not img_dir.exists():
        print(f"  ❌ 目录不存在: {img_dir}")
        return None

    items = []
    bad_files = []
    total_size = 0

    for f in sorted(img_dir.iterdir()):
        if f.name == 'manifest.json' or not f.is_file():
            continue
        ext = f.suffix.lower()
        if ext not in ALLOWED_IMAGE_EXTS:
            print(f"  ⚠️ 跳过非图片: {f.name}")
            continue

        size = f.stat().st_size
        if size == 0:
            print(f"  ⚠️ 空文件: {f.name}")
            bad_files.append(f.name)
            continue

        fmt = detect_format(f)
        if fmt is None:
            print(f"  ⚠️ 无法识别格式: {f.name}")
            bad_files.append(f.name)
            continue

        if fmt == 'webp':
            print(f"  ⚠️ webp格式: {f.name}")
            bad_files.append(f.name)
            continue

        # 修正扩展名
        correct_ext = '.' + fmt
        correct_name = f.stem + correct_ext
        if f.name != correct_name:
            correct_path = img_dir / correct_name
            if not correct_path.exists():
                f.rename(correct_path)
                print(f"  🔧 重命名: {f.name} → {correct_name}")
                f = correct_path
            else:
                # 正确扩展名文件已存在，删除当前文件（重复）
                f.unlink()
                print(f"  🗑️ 删除重复: {f.name} (→ {correct_name} 已存在)")
                continue

        items.append({
            "filename": f.name,
            "title": f.stem,
            "size": size,
        })
        total_size += size

    # 去重
    seen = set()
    unique_items = []
    for item in items:
        if item["filename"] not in seen:
            seen.add(item["filename"])
            unique_items.append(item)

    manifest = {
        "category": category,
        "description": description,
        "triggers": triggers,
        "count": len(unique_items),
        "total_size": total_size,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "items": unique_items,
    }

    manifest_path = img_dir / "manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"  ✅ {category}: {len(items)} 张图片, {manifest['total_size_mb']}MB, {len(bad_files)} 个问题文件")
    if bad_files:
        print(f"     问题文件: {bad_files}")

    return manifest

def rebuild_text_manifest(category: str, dirname: str, triggers: list[str], description: str):
    """重建文本目录的 manifest"""
    text_dir = ROOT / "texts" / dirname
    quotes_file = text_dir / "quotes.json"

    if not quotes_file.exists():
        print(f"  ❌ quotes.json 不存在: {quotes_file}")
        return None

    with open(quotes_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    count = len(data.get("quotes", []))

    manifest = {
        "category": category,
        "description": description,
        "triggers": triggers,
        "count": count,
    }
    manifest_path = text_dir / "manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"  ✅ {category}: {count} 条文案")
    return manifest

def main():
    print("🔧 重建所有 manifest...")
    print()

    # 图片
    print("🖼️ 图片目录:")
    pig = rebuild_image_manifest("pig", "pig",
        ["猪", "🐷", "🐽", "🐖"], "猪猪图片 (来源: pighub.top)")
    nailong = rebuild_image_manifest("nailong", "nailong",
        ["奶龙", "奶蛙", "🥛🐲", "🥛🐉"], "奶龙图片")
    otto = rebuild_image_manifest("otto", "otto",
        ["动物园", "电棍", "otto", "侯国玉", "炫狗", "张顺飞"], "电棍/otto表情包")

    # 文本
    print("\n📝 文本目录:")
    kfc = rebuild_text_manifest("kfc", "kfc",
        ["疯狂星期四", "肯德基", "KFC", "kfc", "v我50"], "疯狂星期四/KFC文案")
    td = rebuild_text_manifest("thunder_dragon", "thunder_dragon",
        ["部落冲突", "雷电飞龙", "雷龙", "电龙"], "雷电飞龙/部落冲突文案")
    fd = rebuild_text_manifest("fadian", "fadian",
        ["发癫"], "发癫文学文案")

    # 更新顶层 manifest
    print("\n📋 更新顶层 manifest...")
    root_path = ROOT / "manifest.json"
    with open(root_path, 'r', encoding='utf-8') as f:
        root = json.load(f)

    for cat_type, cat_name, result in [
        ("images", "pig", pig), ("images", "nailong", nailong), ("images", "otto", otto),
        ("texts", "kfc", kfc), ("texts", "thunder_dragon", td), ("texts", "fadian", fd),
    ]:
        if result:
            root["categories"][cat_type][cat_name]["count"] = result["count"]

    with open(root_path, 'w', encoding='utf-8') as f:
        json.dump(root, f, ensure_ascii=False, indent=2)

    # 统计
    total_images = sum(r["count"] for r in [pig, nailong, otto] if r)
    total_texts = sum(r["count"] for r in [kfc, td, fd] if r)
    total_size = sum(r.get("total_size", 0) for r in [pig, nailong, otto] if r)

    print(f"\n{'='*50}")
    print(f"📊 数据统计:")
    print(f"  图片: {total_images} 张 ({total_size/1024/1024:.1f}MB)")
    print(f"  文案: {total_texts} 条")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
