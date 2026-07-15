#!/usr/bin/env python3
"""
雷电飞龙/部落冲突文案采集
从收集到的文案库编译 + 可扩展在线采集
"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

OUTPUT = Path(__file__).parent.parent / "texts" / "thunder_dragon" / "quotes.json"

# 从之前搜索结果整理的全部雷电飞龙文案
RAW_QUOTES = [
    # ── 一字划流派 ──
    "要什么技巧？从来都是一字划！",
    "划一字，动作要稳，速度要快！",
    "什么都一字划只会害了你。",
    "你只管一字划，黑的三颗星首领会想办法。",
    "首领：你这辈子就是给一字划害的。",
    "雷雷雷雷雷龙龙龙龙龙！爽！",
    "你只管一字划，剩下的交给天意。",
    "一字划雷龙，三星靠缘分。",
    "我不需要技巧，我有一字划就够了。",
    "一字划是信仰，三星是意外。",

    # ── 首领 vs 雷龙成员 ──
    "首领是这样的。成员只要玩玩闪电雷龙就可以了，而首领要踢的人可就很多了。",
    "闪电雷龙是这样的。首领只要在部落里踢踢人就可以，可是闪电雷龙要考虑的事情就很多了。",
    "成员：我手里有14个蓝色的法术。首领：我手里有一张红色的飞机票。",
    "首领别怕，我来拿闪电雷龙救你！",
    "首领：带这么多雷龙你要干什么？成员：多带点雷龙能合成三星大雷龙！",
    "首领：你和我有仇？",
    "首领：今天打完联赛，你就收拾收拾上路吧……",
    "首领：这已经是你第四次黑三了。成员：闪电雷龙会努力的！",
    "首领：你为什么带11个雷电法术？成员：因为雷龙需要电力。",
    "首领：你看看对面的阵型。成员：我看过了，很适合一字划。",

    # ── 雷龙玩家精神状态 ──
    "常年玩闪电雷龙的人大都目光呆滞。",
    "一天不玩雷龙，身上有蚂蚁在爬。",
    "你染上雷龙了？！",
    "我的天，兵营在自动训练雷电飞龙。",
    "这么玩雷龙有一种脑干缺失的美。",
    "他这么做一定有他的大病。",
    "雷龙玩家的大脑是光滑的，没有一丝褶皱。",
    "不是我在玩雷龙，是雷龙在玩我。",
    "我已经三天没玩雷龙了，现在看什么都像防空火箭。",

    # ── 黑雷/搜空地雷 ──
    "雷龙，收手吧……外面全都是搜空地雷。",
    "没有人会等雷龙，除了搜空地雷。",
    "你要是把我雷电飞龙秒了，我当场把这个搜空地雷吃下去！",
    "我可是雷电飞龙啊，几颗黑雷不要紧的。",
    "当你做好准备时，黑雷是不会找上门的，雷龙！",
    "没有骷髅的黑雷我不吃。",
    "完蛋！我被黑雷包围了！",
    "黑雷毁了部落冲突！",
    "晚上睡觉一掀开被子全是地雷。",
    "雷龙的一生：出生→飞行→遇到黑雷→去世。",
    "这个世界上没有什么是一颗黑雷解决不了的，如果有，那就两颗。",
    "搜空地雷：雷龙捕捉器。",

    # ── 吹风机/空气炮 ──
    "你以为我不敢顶着双吹风机打你？",
    "空气炮，雷电飞龙的一生之敌！",
    "算了大哥！（飞龙和龙宝宝拉着暴怒的雷龙）",
    "吹风机的存在就是为了克制雷龙，这是科学。",
    "雷龙：我能毁灭一切！吹风机：你过来啊。",

    # ── 弹幕/评论区高频 ──
    "⚡不是⚡哥们！⚡",
    "⚡老⚡比⚡灯⚡",
    "⚡闪电雷龙团我们喜欢你⚡",
    "⚡我当时害怕极了⚡",
    "⚡⚠️扌喿⚠️⚡",
    "雷龙：总感觉背后有不干净的东西。",
    "真是酣畅淋漓的吃石啊！",
    "他选择了弹幕最多的打法。",
    "首领目前情绪稳定，暂无生命迹象。",
    "你敢违抗有雷电飞龙的我吗！",
    "原来你也玩雷龙？",
    "三黑冲突！启动！",
    "雷龙来了吗？如来。",
    "雷电飞龙正在逐渐毁灭这个游戏。",
    "你打部落战要我三星，我打部落战从不三星。",

    # ── 装备/流派相关 ──
    "嗨！我是癫佬，这是我的三黑神器。",
    "星期一左边我雷龙破碎。",
    "大本放外面你还能三黑？首领气进ICU。",
    "投石车里疑似塞了个女王。",
    "你就说这是不是狗球流吧。",
    "真正的520 = 5个超法踩2个大炸打了0%。",
    "带了12个雷电却忘了带雷龙。",
    "这个阵我研究过了，用雷龙。那个阵我也研究过了，也用雷龙。",

    # ── 皮肤/外观梗 ──
    "雷龙新皮肤雷金雷电飞龙，为什么被调侃为小泥鳅？",
    "雷电飞龙：我变秃了，也变强了。",
    "同样是龙，为什么雷龙看起来不太聪明。",

    # ── 更多经典 ──
    "闪电雷龙团，我们喜欢你～",
    "雷龙：我飞得很慢，但我的伤害很高。黑雷：你好。",
    "阵型越怪，雷龙越爱。",
    "学医救不了部落冲突，雷龙也不行。",
    "闪电雷龙已经不适合这个版本了。",
    "无论版本怎么变，雷龙永远是我的首选。",
    "雷龙玩家不需要视力。",
    "我的雷龙大军呢？——被三个黑雷带走了。",
    "三星不是目的，一字划才是。",
    "玩雷龙最重要的就是自信，即使只有一星也要打出三星的气势。",
]

def main():
    # 加载已有数据
    existing_texts = set()
    if OUTPUT.exists():
        with open(OUTPUT, 'r', encoding='utf-8') as f:
            old = json.load(f)
            for q in old.get("quotes", []):
                existing_texts.add(q["text"])

    # 去重合并
    quotes = []
    seen = set()
    for i, text in enumerate(RAW_QUOTES):
        text = text.strip()
        if text and text not in seen and text not in existing_texts:
            seen.add(text)
            quotes.append({
                "id": f"td_{len(quotes)+1:04d}",
                "text": text,
            })

    # 把已有数据也加进来
    if OUTPUT.exists():
        with open(OUTPUT, 'r', encoding='utf-8') as f:
            old = json.load(f)
            for q in old.get("quotes", []):
                if q["text"] not in seen:
                    seen.add(q["text"])
                    quotes.append(q)

    quotes.sort(key=lambda q: q["id"])
    output = {
        "category": "thunder_dragon",
        "version": "1.0.0",
        "count": len(quotes),
        "quotes": quotes
    }
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"雷电飞龙文案: {len(quotes)} 条")

    # 更新 manifest
    manifest_path = Path(__file__).parent.parent / "texts" / "thunder_dragon" / "manifest.json"
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    manifest["count"] = len(quotes)
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
