#!/usr/bin/env python3
"""
Clover_Database 数据验证脚本

验证所有数据的规范性：
- 图片格式 (jpg/jpeg/png/gif) + 魔法字节检测
- 文件名规范 (中文/英文/数字/下划线/连字符)
- manifest.json 一致性
- JSON 有效性
- 空文件检测
- 图片尺寸限制
"""

import json
import re
import sys
from pathlib import Path

# Windows GBK 兼容
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent.parent

# ══════════════════════════════════════════
# 配置
# ══════════════════════════════════════════

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_FILENAME_LEN = 100

# 文件名允许: 中文、英文、数字、下划线、连字符、点(扩展名)
FILENAME_PATTERN = re.compile(r'^[一-鿿\w\-]+\.\w+$')
# 禁止纯数字/纯乱码文件名
MEANINGFUL_PATTERN = re.compile(r'[一-鿿\w]')

TEXT_CATEGORIES = {"kfc", "thunder_dragon", "fadian"}
IMAGE_CATEGORIES = {"pig", "nailong", "otto"}

VALID_MATCH_MODES = {"contains", "exact"}


def discover_categories() -> tuple[set, set]:
    """动态发现分类（v2, 配合用户自建分类）：
    texts/<cat>/quotes.json 存在 → 文本类；images/<cat>/ 存在 → 图片类。
    内置6类兜底。"""
    texts = set(TEXT_CATEGORIES)
    images = set(IMAGE_CATEGORIES)
    tdir, idir = ROOT / "texts", ROOT / "images"
    if tdir.is_dir():
        for d in tdir.iterdir():
            if d.is_dir() and (d / "quotes.json").exists():
                texts.add(d.name)
    if idir.is_dir():
        for d in idir.iterdir():
            if d.is_dir() and d.name != "old":
                images.add(d.name)
    return texts, images

# ══════════════════════════════════════════
# 图片魔法字节
# ══════════════════════════════════════════

MAGIC_BYTES = {
    b'\xff\xd8\xff': 'jpg',
    b'\x89PNG\r\n\x1a\n': 'png',
    b'GIF87a': 'gif',
    b'GIF89a': 'gif',
}

def check_magic_bytes(filepath: Path) -> tuple[str | None, bool]:
    """检测文件实际格式。返回 (检测到的格式, 是否匹配扩展名)"""
    ext = filepath.suffix.lower()
    try:
        with open(filepath, 'rb') as f:
            header = f.read(12)
    except Exception:
        return None, False

    detected = None
    for magic, fmt in MAGIC_BYTES.items():
        if header.startswith(magic):
            detected = fmt
            break

    if detected is None:
        return None, False

    # jpg 和 jpeg 视为同一种
    expected = 'jpg' if ext in ('.jpg', '.jpeg') else ext.lstrip('.')
    return detected, (detected == expected)


# ══════════════════════════════════════════
# 验证函数
# ══════════════════════════════════════════

class Validator:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.passed: int = 0
        self.failed: int = 0

    def error(self, msg: str):
        self.errors.append(f"❌ {msg}")
        self.failed += 1

    def warn(self, msg: str):
        self.warnings.append(f"⚠️ {msg}")

    def ok(self, _msg: str = ""):
        self.passed += 1

    # ── 文件名验证 ──────────────────────

    def validate_filename(self, filepath: Path, category: str) -> bool:
        """验证单个文件名是否规范（仅在图片目录上下文调用；
        v2: 不再依赖硬编码分类集合，动态分类同样校验）"""
        name = filepath.name

        # 检查扩展名（图片目录一律按图片规则）
        ext = filepath.suffix.lower()
        if ext != '.json' and ext not in ALLOWED_IMAGE_EXTENSIONS:
            self.error(f"[{category}] 不允许的图片格式: {name} (仅允许 jpg/jpeg/png/gif)")
            return False

        # 文件名长度
        if len(name) > MAX_FILENAME_LEN:
            self.warn(f"[{category}] 文件名过长 ({len(name)}字符): {name}")

        # 文件名格式 (中文/英文/数字/下划线/连字符)
        if not FILENAME_PATTERN.match(name):
            self.error(f"[{category}] 文件名含非法字符: {name}")
            return False

        # 必须有实际含义 (不能是纯数字或乱码)
        stem = filepath.stem
        if not MEANINGFUL_PATTERN.search(stem):
            self.error(f"[{category}] 文件名无实际含义: {name}")
            return False

        # 禁止纯数字文件名
        if re.match(r'^\d+$', stem):
            self.error(f"[{category}] 文件名不能是纯数字: {name}")
            return False

        return True

    # ── 图片验证 ──────────────────────

    def validate_image(self, filepath: Path, category: str):
        """验证图片文件"""
        name = filepath.name

        # 文件大小
        size = filepath.stat().st_size
        if size == 0:
            self.error(f"[{category}] 空文件: {name}")
            return
        if size > MAX_FILE_SIZE:
            self.error(f"[{category}] 文件过大 ({size/1024/1024:.1f}MB): {name} (限制10MB)")
            return

        # 魔法字节检测
        detected, matches = check_magic_bytes(filepath)
        if detected is None:
            self.error(f"[{category}] 无法识别图片格式 (不是有效图片): {name}")
            return
        if not matches:
            self.error(
                f"[{category}] 文件扩展名与内容不匹配: {name} "
                f"(扩展名={filepath.suffix}, 实际={detected})"
            )
            return

        self.ok(f"[{category}] ✓ {name} ({size/1024:.0f}KB)")

    # ── 文本验证 ──────────────────────

    def validate_text_dir(self, dirpath: Path, category: str):
        """验证文本目录"""
        quotes_file = dirpath / "quotes.json"
        manifest_file = ROOT / "manifests" / f"{category}.json"

        # manifest 存在且有效
        if not manifest_file.exists():
            self.error(f"[{category}] 缺少 manifests/{category}.json")
            return
        manifest = self._load_json(manifest_file, category)
        if manifest is None:
            return
        if manifest.get("category") != category:
            self.error(f"[{category}] manifest.json 中 category 不匹配: {manifest.get('category')}")

        # quotes.json 存在且有效
        if not quotes_file.exists():
            self.error(f"[{category}] 缺少 quotes.json")
            return
        quotes_data = self._load_json(quotes_file, category)
        if quotes_data is None:
            return

        quotes = quotes_data.get("quotes", [])
        if not isinstance(quotes, list):
            self.error(f"[{category}] quotes.json 中 quotes 必须是数组")
            return

        # 验证每条记录
        seen_ids = set()
        for i, q in enumerate(quotes):
            if not isinstance(q, dict):
                self.error(f"[{category}] quotes[{i}] 不是对象")
                continue
            qid = q.get("id")
            if not qid:
                self.error(f"[{category}] quotes[{i}] 缺少 id")
            elif qid in seen_ids:
                self.error(f"[{category}] quotes[{i}] 重复 id: {qid}")
            else:
                seen_ids.add(qid)
            text = q.get("text", "")
            if not text or not text.strip():
                self.warn(f"[{category}] quotes[{i}] 文本为空")

        # 同步 count
        actual_count = len(quotes)
        manifest_count = manifest.get("count", -1)
        if manifest_count != actual_count:
            self.error(
                f"[{category}] manifest count ({manifest_count}) ≠ quotes 实际数量 ({actual_count})"
            )
        else:
            self.ok(f"[{category}] ✓ quotes.json 含 {actual_count} 条文案, manifest一致")

    # ── 图片目录验证 ──────────────────────

    def validate_image_dir(self, dirpath: Path, category: str):
        """验证图片目录"""
        manifest_file = ROOT / "manifests" / f"{category}.json"

        if not manifest_file.exists():
            self.error(f"[{category}] 缺少 manifests/{category}.json")
            return
        manifest = self._load_json(manifest_file, category)
        if manifest is None:
            return

        # 获取目录下所有图片文件
        actual_files = set()
        for f in dirpath.iterdir():
            if f.is_file() and f.suffix.lower() in ALLOWED_IMAGE_EXTENSIONS:
                actual_files.add(f.name)
                self.validate_filename(f, category)
                self.validate_image(f, category)
            elif f.is_file() and f.name != "manifest.json":
                self.error(f"[{category}] 目录中存在非图片文件: {f.name}")

        # manifest 中的文件列表
        manifest_items = manifest.get("items", [])
        manifest_files = {item.get("filename", "") for item in manifest_items}

        # 孤儿文件 (在目录中但不在manifest)
        orphan = actual_files - manifest_files
        for f in orphan:
            self.error(f"[{category}] 文件未在 manifest 中注册: {f}")

        # 幽灵引用 (在manifest但文件不存在)
        ghost = manifest_files - actual_files
        for f in ghost:
            self.error(f"[{category}] manifest 引用了不存在的文件: {f}")

        # 验证每个 manifest item
        seen_filenames = set()
        for item in manifest_items:
            if not isinstance(item, dict):
                self.error(f"[{category}] manifest item 不是对象")
                continue
            fn = item.get("filename", "")
            if not fn:
                self.error(f"[{category}] manifest item 缺少 filename")
                continue
            if fn in seen_filenames:
                self.error(f"[{category}] manifest 中重复 filename: {fn}")
            seen_filenames.add(fn)

        # 同步 count
        actual_count = len(actual_files)
        manifest_count = manifest.get("count", -1)
        if manifest_count != actual_count:
            self.error(
                f"[{category}] manifest count ({manifest_count}) ≠ 实际文件数 ({actual_count})"
            )
        else:
            self.ok(f"[{category}] ✓ {actual_count} 张图片, manifest一致")

    # ── 顶层 manifest ──────────────────────

    def validate_root_manifest(self):
        """验证顶层 manifest.json"""
        root_manifest = self._load_json(ROOT / "manifest.json", "ROOT")
        if root_manifest is None:
            return

        cats = root_manifest.get("categories", {})
        for cat_type in ("texts", "images"):
            if cat_type not in cats:
                self.error(f"[ROOT] manifest 缺少 categories.{cat_type}")
                continue
            for cat_name, cat_info in cats[cat_type].items():
                expected_path = cat_info.get("path", "")
                full_path = ROOT / expected_path
                if not full_path.exists():
                    self.error(f"[ROOT] 路径不存在: {expected_path}")


    # ── 工具函数 ──────────────────────

    def _load_json(self, filepath: Path, category: str) -> dict | None:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            self.error(f"[{category}] JSON 解析失败 {filepath.name}: {e}")
            return None
        except Exception as e:
            self.error(f"[{category}] 读取失败 {filepath.name}: {e}")
            return None

    # ── 主入口 ──────────────────────

    def run(self):
        print("═" * 60)
        print("🍀 Clover_Database 数据验证")
        print("═" * 60)

        # 验证顶层 manifest
        self.validate_root_manifest()

        # 动态发现全部分类（内置 + 用户自建）
        text_cats, image_cats = discover_categories()

        # 验证分类 manifest 的 match_mode/semantic 字段合法性
        print("\n🏷️ manifest 字段验证:")
        mdir = ROOT / "manifests"
        index_cats = []
        if (mdir / "_index.json").exists():
            try:
                index_cats = json.loads(
                    (mdir / "_index.json").read_text(encoding='utf-8')
                ).get("categories", [])
                self.ok()
            except json.JSONDecodeError as e:
                self.error(f"[_index] JSON 解析失败: {e}")
        for cat in sorted(text_cats | image_cats):
            mpath = mdir / f"{cat}.json"
            if not mpath.exists():
                self.error(f"[{cat}] manifest 缺失: manifests/{cat}.json")
                continue
            try:
                m = json.loads(mpath.read_text(encoding='utf-8'))
            except json.JSONDecodeError as e:
                self.error(f"[{cat}] manifest JSON 解析失败: {e}")
                continue
            mode = m.get("match_mode", "contains")
            if mode not in VALID_MATCH_MODES:
                self.error(f"[{cat}] match_mode 非法: {mode!r} (仅允许 contains/exact)")
            else:
                self.ok()
            if not isinstance(m.get("semantic", False), bool):
                self.error(f"[{cat}] semantic 必须是布尔值: {m.get('semantic')!r}")
            else:
                self.ok()
            if not m.get("triggers"):
                self.warn(f"[{cat}] 无触发词（自动回复不会触发）")
            if index_cats and cat not in index_cats:
                self.error(f"[{cat}] 未登记到 manifests/_index.json")

        # 验证文本目录
        print("\n📝 文本类验证:")
        for cat in sorted(text_cats):
            dirpath = ROOT / "texts" / cat
            if dirpath.exists():
                self.validate_text_dir(dirpath, cat)
            else:
                self.error(f"[{cat}] 目录不存在")

        # 验证图片目录
        print("\n🖼️ 图片类验证:")
        for cat in sorted(image_cats):
            dirpath = ROOT / "images" / cat
            if dirpath.exists():
                self.validate_image_dir(dirpath, cat)
            else:
                self.error(f"[{cat}] 目录不存在")

        # ── 报告 ──
        print("\n" + "═" * 60)
        print("📊 验证报告")
        print("═" * 60)

        if self.warnings:
            print(f"\n⚠️  警告 ({len(self.warnings)}):")
            for w in self.warnings:
                print(f"   {w}")

        if self.errors:
            print(f"\n❌ 错误 ({len(self.errors)}):")
            for e in self.errors:
                print(f"   {e}")

        total = self.passed + self.failed
        print(f"\n通过: {self.passed}/{total}")
        if self.failed > 0:
            print(f"失败: {self.failed} 项")
            return 1
        else:
            print("✅ 全部通过!")
            return 0


if __name__ == "__main__":
    import sys
    v = Validator()
    sys.exit(v.run())
