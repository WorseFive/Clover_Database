#!/usr/bin/env python3
"""
奶龙图片采集 - 从duitang(堆糖)的多张专辑下载
URL转换: thumb.300_0.gif_jpeg → .gif (原始图)
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent.parent
NL_DIR = ROOT / "images" / "nailong"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 奶龙相关的duitang专辑
ALBUMS = [
    "https://m.duitang.com/album/?id=124280721",  # 231张
    "https://m.duitang.com/album/?id=121026620",  # 89张
]

def thumb_to_original(thumb_url: str) -> str | None:
    """将缩略图URL转换为原图URL"""
    # 移除 .thumb.WxH 部分
    original = re.sub(r'\.thumb\.\d+_\d+', '', thumb_url)
    # 移除 _jpeg, _webp, _png 后缀
    original = re.sub(r'_(jpeg|webp|png)$', '', original)
    # 清理可能的双扩展名
    # 确保有正确的扩展名
    if not re.search(r'\.(jpg|jpeg|png|gif|webp)$', original, re.I):
        if '.gif' in thumb_url.lower():
            original += '.gif'
        elif '.png' in thumb_url.lower():
            original += '.png'
        elif '.jpeg' in thumb_url.lower() or '.jpg' in thumb_url.lower():
            original += '.jpg'
    # 过滤掉明显不是图片的URL
    if any(x in original for x in ['favicon', 'icon', 'avatar']):
        return None
    if '.ico' in original.lower():
        return None
    return original

def download_image(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            if len(data) < 100:  # 太小不像是真图片
                return False
            dest.write_bytes(data)
            return True
    except Exception as e:
        return False

def detect_format(filepath: Path) -> str | None:
    try:
        with open(filepath, 'rb') as f:
            header = f.read(12)
    except:
        return None
    if header.startswith(b'\xff\xd8\xff'): return 'jpg'
    if header.startswith(b'\x89PNG\r\n\x1a\n'): return 'png'
    if header.startswith(b'GIF87a') or header.startswith(b'GIF89a'): return 'gif'
    if header.startswith(b'RIFF') and header[8:12] == b'WEBP': return 'webp'
    return None

def main():
    NL_DIR.mkdir(parents=True, exist_ok=True)

    # 加载已有数据
    manifest_path = NL_DIR / "manifest.json"
    existing_files = set()
    if manifest_path.exists():
        with open(manifest_path, 'r', encoding='utf-8') as f:
            old = json.load(f)
            for item in old.get("items", []):
                existing_files.add(item.get("filename", ""))

    items = []
    downloaded = 0
    skipped = 0
    failed = 0

    for album_url in ALBUMS:
        print(f"\n📂 专辑: {album_url}")
        page = 1
        while True:
            page_url = f"{album_url}&page={page}" if page > 1 else album_url
            try:
                req = urllib.request.Request(page_url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    html = resp.read().decode('utf-8', errors='ignore')
            except Exception as e:
                print(f"  ❌ 页面加载失败: {e}")
                break

            thumbs = re.findall(r'https?://c-ssl\.dtstatic\.com/uploads/[^\"<> ]+', html)
            if not thumbs:
                print(f"  📄 第{page}页: 无更多图片")
                break

            print(f"  📄 第{page}页: {len(thumbs)} 张缩略图")

            for thumb in thumbs:
                original = thumb_to_original(thumb)
                if not original:
                    continue

                # 从URL提取文件名
                parsed = urllib.parse.urlparse(original)
                fname = parsed.path.split('/')[-1]
                if not fname or len(fname) < 5:
                    continue

                # 清理文件名
                fname = re.sub(r'[^\w\-\.]', '_', fname)

                if fname in existing_files:
                    skipped += 1
                    continue

                dest = NL_DIR / fname
                if download_image(original, dest):
                    # 检测格式
                    fmt = detect_format(dest)
                    if fmt is None:
                        dest.unlink(missing_ok=True)
                        failed += 1
                        continue

                    # 修正扩展名
                    expected_ext = dest.suffix.lower().lstrip('.')
                    if fmt != expected_ext and not (fmt == 'jpg' and expected_ext == 'jpeg'):
                        correct_name = dest.stem + f'.{fmt}'
                        correct_dest = NL_DIR / correct_name
                        dest.rename(correct_dest)
                        dest = correct_dest
                        fname = correct_name

                    items.append({
                        "filename": fname,
                        "size": dest.stat().st_size,
                        "source_url": original,
                    })
                    downloaded += 1
                    existing_files.add(fname)
                    if downloaded % 20 == 0:
                        print(f"    已下载 {downloaded}...")
                    time.sleep(0.2)
                else:
                    failed += 1

            page += 1
            time.sleep(1)
            if page > 10:  # 最多10页
                break

    # 保存
    manifest = {
        "category": "nailong",
        "description": "奶龙图片",
        "triggers": ["奶龙", "奶蛙", "🥛🐲", "🥛🐉"],
        "count": len(items),
        "items": items
    }
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 奶龙图片: 下载 {downloaded}, 跳过 {skipped}, 失败 {failed}, 总计 {len(items)}")

    # 更新顶层manifest
    root_manifest_path = ROOT / "manifest.json"
    with open(root_manifest_path, 'r', encoding='utf-8') as f:
        root = json.load(f)
    root["categories"]["images"]["nailong"]["count"] = len(items)
    with open(root_manifest_path, 'w', encoding='utf-8') as f:
        json.dump(root, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
