# Clover_Database 🍀

Clover QQ Bot 自动回复数据库。存放文案、表情包、图片等自动回复内容。

## 目录结构

```
Clover_Database/
├── texts/                  # 文本类回复
│   ├── kfc/               # 疯狂星期四文案
│   ├── thunder_dragon/    # 雷电飞龙文案
│   └── fadian/            # 发癫文案
├── images/                 # 图片类回复
│   ├── pig/               # 猪猪图片 (来源: pighub.top)
│   ├── nailong/           # 奶龙图片
│   └── otto/              # 电棍表情包 (来源: gengtu.net)
├── scripts/
│   └── validate.py        # 数据验证脚本
└── manifest.json          # 顶层索引
```

## 数据规范

### 图片
- 格式: 仅 `.jpg` `.jpeg` `.png` `.gif`
- 命名: `描述_序号.扩展名`，如 `猪睡觉_001.png`
- 禁止乱码文件名、禁止非图片格式文件
- 单文件 < 10MB

### 文本
- 格式: JSON 数组
- 每条记录: `{"id": "唯一ID", "text": "文案内容", "tags": ["标签"]}`

### manifest.json
- 每个目录必须有 manifest.json 索引文件
- 记录该目录下所有文件的元信息

## 使用方式

机器人通过 GitHub Raw URL 按需获取内容：
- `https://raw.githubusercontent.com/WorseFive/Clover_Database/main/...`
- 或通过 jsDelivr CDN 加速
