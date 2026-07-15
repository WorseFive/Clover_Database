#!/usr/bin/env python3
"""
PigHub 猪猪图片批量下载
1. 从 pighub.top API 获取所有图片元数据
2. 下载图片，自动转换 webp → png
3. 命名规范化
4. 更新 manifest.json
"""
import json
import re
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent.parent
PIG_DIR = ROOT / "images" / "pig"
API_URL = "https://pighub.top/api/images?sort=2"
BASE_URL = "https://pighub.top"
DELAY = 0.1  # 请求间隔，避免被封
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://pighub.top/",
}

def sanitize_filename(name: str) -> str:
    """清理文件名，移除不安全字符"""
    # 保留中文、英文、数字、下划线、连字符、点
    name = re.sub(r'[^\w一-鿿\-\.]', '_', name)
    # 多下划线合并
    name = re.sub(r'_+', '_', name)
    # 首尾去掉下划线
    name = name.strip('_')
    # 限制长度
    if len(name) > 80:
        stem, ext = name.rsplit('.', 1) if '.' in name else (name, '')
        name = f"{stem[:70]}.{ext}"
    return name

def detect_format(filepath: Path) -> str | None:
    """通过魔术字节检测实际格式"""
    try:
        with open(filepath, 'rb') as f:
            header = f.read(12)
    except Exception:
        return None

    if header.startswith(b'\xff\xd8\xff'):
        return 'jpg'
    if header.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
        return 'gif'
    if header.startswith(b'RIFF') and header[8:12] == b'WEBP':
        return 'webp'
    return None

def convert_to_png(filepath: Path) -> bool:
    """将 webp 或其他格式转为 png (需要 Pillow)"""
    try:
        from PIL import Image
        img = Image.open(filepath)
        new_path = filepath.with_suffix('.png')
        img.save(new_path, 'PNG')
        filepath.unlink()  # 删除原文件
        return True
    except ImportError:
        print("  ⚠️ Pillow 未安装，无法转换 webp")
        return False
    except Exception as e:
        print(f"  ⚠️ 转换失败: {e}")
        return False

def download_image(url: str, dest: Path) -> bool:
    """下载单张图片"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            if len(data) == 0:
                return False
            dest.write_bytes(data)
            return True
    except Exception as e:
        print(f"  ❌ 下载失败: {e}")
        return False

def main():
    # 加载已有 manifest
    manifest_path = PIG_DIR / "manifest.json"
    existing_files = set()
    if manifest_path.exists():
        with open(manifest_path, 'r', encoding='utf-8') as f:
            old_manifest = json.load(f)
            for item in old_manifest.get("items", []):
                existing_files.add(item.get("filename", ""))

    print(f"📡 获取 PigHub 图片列表...")
    req = urllib.request.Request(API_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        api_data = json.loads(resp.read().decode("utf-8"))

    images = api_data.get("data", [])
    print(f"🐷 共 {len(images)} 张图片")
    print(f"📂 已有 {len(existing_files)} 张本地图片")

    items = []
    skipped = 0
    downloaded = 0
    converted = 0
    failed = 0

    for i, img in enumerate(images):
        filename = img.get("filename", "")
        img_url = img.get("image_url", "")
        title = img.get("title", "")

        if not filename or not img_url:
            skipped += 1
            continue

        # 清理文件名
        clean_name = sanitize_filename(filename)
        ext = clean_name.rsplit('.', 1)[-1].lower() if '.' in clean_name else ''

        # webp 文件需要转换
        needs_convert = (ext == 'webp')
        if needs_convert:
            clean_name = clean_name.rsplit('.', 1)[0] + '.png'

        if clean_name in existing_files:
            # 文件已存在，保留现有记录
            for item in old_manifest.get("items", []):
                if item.get("filename") == clean_name:
                    items.append(item)
                    break
            skipped += 1
            if i % 100 == 0:
                print(f"  [{i+1}/{len(images)}] 跳过 {skipped} 已存在, 下载 {downloaded}...")
            continue

        dest = PIG_DIR / clean_name
        # URL编码中文字符
        parsed = urllib.parse.urlparse(BASE_URL + img_url)
        encoded_path = urllib.parse.quote(parsed.path, safe='/')
        full_url = parsed._replace(path=encoded_path).geturl()

        # 下载
        if i % 50 == 0:
            print(f"  [{i+1}/{len(images)}] 下载中... 已下载 {downloaded}")

        if download_image(full_url, dest):
            current_path = dest
            current_name = clean_name

            # 检测实际格式
            detected = detect_format(current_path)
            if detected is None:
                print(f"  ❌ 无法识别格式: {current_name}")
                current_path.unlink(missing_ok=True)
                failed += 1
                continue

            # webp 转换
            if detected == 'webp':
                if convert_to_png(current_path):
                    converted += 1
                    current_name = current_name.rsplit('.', 1)[0] + '.png'
                    current_path = PIG_DIR / current_name
                else:
                    current_path.unlink(missing_ok=True)
                    failed += 1
                    continue

            # 扩展名修正
            current_ext = current_path.suffix.lower().lstrip('.')
            if detected != 'webp' and detected != current_ext and detected != 'jpg' and current_ext != 'jpeg':
                # 只有确实不匹配时才修正（jpg/jpeg视为相同）
                correct_ext = detected
                correct_name = current_name.rsplit('.', 1)[0] + f'.{correct_ext}'
                correct_path = PIG_DIR / correct_name
                current_path.rename(correct_path)
                print(f"  🔧 修正扩展名: {current_name} → {correct_name}")
                current_path = correct_path
                current_name = correct_name

            # 确认文件存在
            if not current_path.exists():
                print(f"  ❌ 文件丢失: {current_name}")
                failed += 1
                continue

            items.append({
                "id": img.get("id", 0),
                "filename": current_name,
                "title": title,
                "size": current_path.stat().st_size,
                "source_url": full_url,
            })
            downloaded += 1
            existing_files.add(current_name)

        else:
            failed += 1

        time.sleep(DELAY)

    # 保存 manifest
    manifest = {
        "category": "pig",
        "description": "猪猪图片",
        "source": "pighub.top",
        "triggers": ["猪", "🐷", "🐽", "🐖"],
        "count": len(items),
        "items": items
    }
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"✅ 完成!")
    print(f"  下载: {downloaded}")
    print(f"  转换: {converted}")
    print(f"  跳过: {skipped}")
    print(f"  失败: {failed}")
    print(f"  总计: {len(items)} 张猪猪图片")
    print(f"{'='*50}")

    # 更新顶层 manifest
    root_manifest_path = ROOT / "manifest.json"
    with open(root_manifest_path, 'r', encoding='utf-8') as f:
        root = json.load(f)
    root["categories"]["images"]["pig"]["count"] = len(items)
    with open(root_manifest_path, 'w', encoding='utf-8') as f:
        json.dump(root, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
