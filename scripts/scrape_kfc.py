#!/usr/bin/env python3
"""
KFC 疯狂星期四文案采集
调用多个免费API，去重后存入 quotes.json
"""
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

OUTPUT = Path(__file__).parent.parent / "texts" / "kfc" / "quotes.json"
TARGET = 300  # 目标采集数量
DELAY = 0.5    # 请求间隔(秒)

APIS = [
    {
        "name": "shadiao",
        "url": "https://api.shadiao.pro/kfc",
        "extract": lambda r: r["data"]["text"]
    },
    {
        "name": "60s",
        "url": "https://60s.viki.moe/v2/kfc",
        "extract": lambda r: r["data"]["kfc"]
    },
]

def fetch(api: dict) -> str | None:
    try:
        req = urllib.request.Request(api["url"], headers={"User-Agent": "CloverBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return api["extract"](data)
    except Exception as e:
        print(f"  [{api['name']}] 请求失败: {e}")
        return None

def main():
    # 加载已有数据
    existing = {}
    if OUTPUT.exists():
        with open(OUTPUT, 'r', encoding='utf-8') as f:
            old = json.load(f)
            for q in old.get("quotes", []):
                existing[q["text"]] = q

    print(f"已有 {len(existing)} 条KFC文案, 目标 {TARGET} 条")
    new_count = 0
    attempts = 0
    max_attempts = TARGET * 3  # 最多尝试3倍目标次数

    while len(existing) < TARGET and attempts < max_attempts:
        for api in APIS:
            if len(existing) >= TARGET:
                break
            text = fetch(api)
            attempts += 1
            if text and text.strip() and text not in existing:
                qid = f"kfc_{len(existing)+1:04d}"
                existing[text] = {
                    "id": qid,
                    "text": text.strip(),
                    "source": api["name"]
                }
                new_count += 1
                print(f"  [{len(existing)}/{TARGET}] {text[:50]}...")
            time.sleep(DELAY)

    # 保存
    quotes = list(existing.values())
    quotes.sort(key=lambda q: q["id"])
    output = {
        "category": "kfc",
        "version": "1.0.0",
        "count": len(quotes),
        "quotes": quotes
    }
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n完成! 共 {len(quotes)} 条 (新增 {new_count})")
    # 更新 manifest
    manifest_path = Path(__file__).parent.parent / "texts" / "kfc" / "manifest.json"
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    manifest["count"] = len(quotes)
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"manifest.json count 已更新为 {len(quotes)}")

if __name__ == "__main__":
    main()
