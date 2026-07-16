#!/usr/bin/env python3
"""
重建所有 manifest.json - 扫描目录实际文件，生成准确索引

v2 (2026-07-16): 动态化改造，配合 reply 插件用户自建分类
- 分类动态发现: manifests/*.json ∪ 内置6类，不再硬编码
- 字段继承: triggers/match_mode/semantic/description/created_by
  一律从现有 manifest 继承（旧版硬编码回写会抹掉用户改动）
- 维护 manifests/_index.json 分类索引（机器人据此发现新分类）
"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent.parent
ALLOWED_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif'}

# 内置分类的出厂默认（仅在 manifest 缺失对应字段时使用）
BUILTIN_DEFAULTS = {
    'pig': (["猪", "🐷", "🐽", "🐖"], "猪猪图片 (来源: pighub.top)"),
    'nailong': (["奶龙", "奶蛙", "🥛🐲", "🥛🐉"], "奶龙图片"),
    'otto': (["动物园", "电棍", "otto", "侯国玉", "炫狗", "张顺飞"], "电棍/otto表情包"),
    'kfc': (["疯狂星期四", "肯德基", "KFC", "kfc", "v我50"], "疯狂星期四/KFC文案"),
    'thunder_dragon': (["部落冲突", "雷电飞龙", "雷龙", "电龙"], "雷电飞龙/部落冲突文案"),
    'fadian': (["发癫"], "发癫文学文案"),
}

# 语义匹配开关出厂默认（文件名乱串的分类=False）
SEMANTIC = {
    'kfc': True, 'thunder_dragon': True, 'fadian': True,
    'pig': True, 'nailong': False, 'otto': False,
}


def detect_format(filepath: Path) -> str | None:
    try:
        with open(filepath, 'rb') as f:
            header = f.read(12)
    except OSError:
        return None
    if header.startswith(b'\xff\xd8\xff'): return 'jpg'
    if header.startswith(b'\x89PNG\r\n\x1a\n'): return 'png'
    if header.startswith(b'GIF87a') or header.startswith(b'GIF89a'): return 'gif'
    if header.startswith(b'RIFF') and len(header) >= 12 and header[8:12] == b'WEBP': return 'webp'
    return None


def load_existing(category: str) -> dict:
    p = ROOT / "manifests" / f"{category}.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            print(f"  ⚠️ 现有 manifest 损坏，按新建处理: {category}")
    return {}


def inherit_meta(category: str) -> dict:
    """triggers/mode/semantic/description 继承现有 manifest > 出厂默认。
    v3 (2026-07-16): 继承 rules/next_rule_id（reply 插件 v1.2 规则组），
    缺失时不合成——插件侧 rules_from_doc 会从 triggers/match_mode 兜底。"""
    old = load_existing(category)
    def_triggers, def_desc = BUILTIN_DEFAULTS.get(category, ([], f"{category} 分类"))
    meta = {
        "description": old.get("description") or def_desc,
        "semantic": old.get("semantic", SEMANTIC.get(category, True)),
        "match_mode": old.get("match_mode", "contains"),
        "triggers": old.get("triggers") or def_triggers,
    }
    if isinstance(old.get("rules"), list) and old["rules"]:
        meta["rules"] = old["rules"]
    if old.get("next_rule_id"):
        meta["next_rule_id"] = old["next_rule_id"]
    if old.get("created_by"):
        meta["created_by"] = old["created_by"]
    return meta


def write_manifest(category: str, doc: dict) -> None:
    path = ROOT / "manifests" / f"{category}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
                    encoding='utf-8')


def rebuild_image_manifest(category: str) -> dict | None:
    img_dir = ROOT / "images" / category
    if not img_dir.is_dir():
        return None

    items, bad_files, total_size = [], [], 0
    for f in sorted(img_dir.iterdir()):
        if f.name == 'manifest.json' or not f.is_file():
            continue
        if f.suffix.lower() not in ALLOWED_IMAGE_EXTS:
            print(f"  ⚠️ 跳过非图片: {category}/{f.name}")
            continue
        size = f.stat().st_size
        if size == 0:
            bad_files.append(f.name)
            continue
        fmt = detect_format(f)
        if fmt is None or fmt == 'webp':
            print(f"  ⚠️ 格式问题: {category}/{f.name} ({fmt})")
            bad_files.append(f.name)
            continue
        correct_name = f.stem + '.' + fmt
        if f.name != correct_name:
            correct_path = img_dir / correct_name
            if not correct_path.exists():
                f.rename(correct_path)
                print(f"  🔧 重命名: {f.name} → {correct_name}")
                f = correct_path
            else:
                f.unlink()
                print(f"  🗑️ 删除重复: {f.name}")
                continue
        items.append({"filename": f.name, "title": f.stem, "size": size})
        total_size += size

    seen, unique_items = set(), []
    for item in items:
        if item["filename"] not in seen:
            seen.add(item["filename"])
            unique_items.append(item)

    manifest = {"category": category, **inherit_meta(category),
                "count": len(unique_items), "total_size": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "items": unique_items}
    write_manifest(category, manifest)
    print(f"  ✅ {category}: {len(unique_items)} 张图片, "
          f"{manifest['total_size_mb']}MB"
          f"{f', {len(bad_files)} 个问题文件' if bad_files else ''}")
    return manifest


def rebuild_text_manifest(category: str) -> dict | None:
    quotes_file = ROOT / "texts" / category / "quotes.json"
    if not quotes_file.exists():
        return None
    try:
        data = json.loads(quotes_file.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError) as e:
        print(f"  ❌ quotes.json 损坏: {category} ({e})")
        return None
    count = len(data.get("quotes", []))
    manifest = {"category": category, **inherit_meta(category), "count": count}
    write_manifest(category, manifest)
    print(f"  ✅ {category}: {count} 条文案")
    return manifest


def discover_categories() -> list[str]:
    """manifests/*.json ∪ 内置6类 ∪ 有实体目录的分类。"""
    cats: dict[str, None] = {}
    mdir = ROOT / "manifests"
    if mdir.is_dir():
        for f in sorted(mdir.glob("*.json")):
            if not f.stem.startswith("_"):
                cats[f.stem] = None
    for c in BUILTIN_DEFAULTS:
        cats.setdefault(c)
    for d in (ROOT / "images").iterdir() if (ROOT / "images").is_dir() else []:
        if d.is_dir() and d.name != "old":
            cats.setdefault(d.name)
    for d in (ROOT / "texts").iterdir() if (ROOT / "texts").is_dir() else []:
        if d.is_dir():
            cats.setdefault(d.name)
    return list(cats)


def main():
    print("🔧 重建所有 manifest (动态发现)...")
    categories = discover_categories()
    print(f"发现分类: {', '.join(categories)}\n")

    results: dict[str, dict] = {}
    for cat in categories:
        has_images = (ROOT / "images" / cat).is_dir()
        has_quotes = (ROOT / "texts" / cat / "quotes.json").exists()
        if has_images:
            r = rebuild_image_manifest(cat)
        elif has_quotes:
            r = rebuild_text_manifest(cat)
        else:
            # 本地无实体内容（如机器人自建的纯远端分类）→ 保留 manifest 原样
            r = load_existing(cat) or None
            if r:
                print(f"  ↔️ {cat}: 无本地内容目录，manifest 保留原样")
        if r:
            results[cat] = r

    # 更新顶层 manifest（仅内置6类，容错缺失项）
    root_path = ROOT / "manifest.json"
    if root_path.exists():
        root = json.loads(root_path.read_text(encoding='utf-8'))
        for group in root.get("categories", {}).values():
            for cat_name, meta in group.items():
                if cat_name in results and isinstance(meta, dict):
                    meta["count"] = results[cat_name].get("count", 0)
        root_path.write_text(json.dumps(root, ensure_ascii=False, indent=2) + "\n",
                             encoding='utf-8')

    # 🆕 维护分类索引（机器人启动只拉这一个文件发现全部分类）
    index = {"categories": [c for c in categories if c in results]}
    (ROOT / "manifests" / "_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding='utf-8')
    print(f"\n📋 _index.json: {len(index['categories'])} 个分类")

    total_images = sum(r.get("count", 0) for r in results.values() if "items" in r)
    total_texts = sum(r.get("count", 0) for r in results.values() if "items" not in r)
    print(f"\n{'=' * 50}")
    print(f"📊 图片: {total_images} 张 | 文案: {total_texts} 条")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
