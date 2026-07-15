# 🍀 Clover_Database 用户手册

Clover QQ Bot 自动回复数据库。存储文案、表情包、图片等自动回复内容，机器人通过 GitHub Raw URL 按需获取。

## 目录结构

```
Clover_Database/
├── texts/                  # 文本类回复
│   ├── kfc/               # 疯狂星期四文案 (278条)
│   ├── thunder_dragon/    # 雷电飞龙文案 (82条)
│   └── fadian/            # 发癫文案 (52条)
├── images/                 # 图片类回复
│   ├── pig/               # 猪猪图片 (1085张, pighub.top)
│   ├── nailong/           # 奶龙图片 (464张, doutula+duitang)
│   └── otto/              # 电棍表情包 (1079张, doutula+gengtu)
├── scripts/               # 工具脚本
│   ├── validate.py        # 数据验证
│   ├── rebuild_manifests.py # 重建manifest索引
│   ├── download_pigs.py   # 下载猪猪图片
│   ├── download_nailong.py # 下载奶龙图片
│   └── scrape_*.py        # 文案采集脚本
├── docs/
│   ├── README.md          # 本手册
│   └── dev-log.md         # 开发日志
├── manifests/              # 所有子目录索引(集中管理)
│   ├── pig.json
│   ├── nailong.json
│   ├── otto.json
│   ├── kfc.json
│   ├── thunder_dragon.json
│   └── fadian.json
└── manifest.json          # 顶层索引
```

## 数据规范

### 图片规范

| 规则 | 说明 |
|------|------|
| 格式 | 仅 `.jpg` `.jpeg` `.png` `.gif` |
| 命名 | 中文/英文/数字/下划线/连字符 |
| 禁止 | 纯数字文件名、乱码、非图片格式 |
| 大小 | 单文件 < 10MB |
| 扩展名 | 必须与魔法字节匹配（webp改png = 违规） |

### 文本规范

```json
{
  "category": "kfc",
  "version": "1.0.0",
  "count": 278,
  "quotes": [
    {"id": "kfc_0001", "text": "文案内容...", "source": "shadiao"}
  ]
}
```

每条记录必须有唯一 `id`，空文本 = 警告。

### manifest 规范

所有子目录索引集中在 `manifests/` 目录下，与数据文件分离：
- `manifests/pig.json`、`nailong.json`、`otto.json` — 图片索引
- `manifests/kfc.json`、`thunder_dragon.json`、`fadian.json` — 文本索引
- `count` 必须与实际文件数一致
- `items` 数组包含所有文件名，不能有孤儿文件或幽灵引用

## 管理面板

地址：`https://worsefive.github.io/app.html` → 点击 **🗄️ 数据库管理**

### 配置 Token

1. 前往 [GitHub Settings → Tokens](https://github.com/settings/tokens)
2. 创建 Personal Access Token，勾选 `public_repo` 权限
3. 在面板的 "🔑 GitHub Token" 栏粘贴保存

### 添加图片

1. 点击 **打开添加窗口**
2. **三种方式传入图片：**
   - 拖拽图片到弹窗区域内
   - 点击弹窗区域选择文件
   - Ctrl+V 粘贴剪贴板中的图片
3. 选择分类 → 确认/修改文件名 → 点击提交

### 删除图片

1. 在浏览区选择分类
2. 点击图片选中（红框高亮），可多选
3. 点击 **🗑️ 删除选中**

### 重命名图片

1. 选中一张图片（仅支持单选）
2. 点击 **✏️ 重命名**
3. 输入新文件名（保留扩展名）

### 修复扩展名

点击 **🔧 修复扩展名** — 自动将 `.jpeg` 统一为 `.jpg`

## 命令行工具

### 数据验证

```bash
cd d:/A_VPN/Clover_Database
python scripts/validate.py
```

检查项：图片格式(魔法字节)、文件名、JSON有效性、manifest一致性、空文件、文件大小、扩展名匹配。

### 重建 Manifest

```bash
python scripts/rebuild_manifests.py
```

扫描所有目录，自动修复扩展名、删除重复文件、生成准确的 manifest.json。

### 采集数据

```bash
python scripts/scrape_kfc.py           # KFC文案 (在线API)
python scripts/scrape_thunder_dragon.py # 雷龙文案 (内置库)
python scripts/scrape_fadian.py         # 发癫文案 (内置库)
python scripts/download_pigs.py         # 猪猪图片 (pighub.top API)
python scripts/download_nailong.py      # 奶龙图片 (duitang)
```

## 数据来源

| 类别 | 来源 | 方式 |
|------|------|------|
| 🐷 猪猪图片 | [pighub.top](https://pighub.top) | API `/api/images?sort=2` |
| 🎭 电棍表情包 | [doutula.com](https://www.doutula.com) | 搜索页抓取 |
| 🎭 电棍表情包 | [gengtu.net](https://gengtu.net) | 标签页+梗图页 |
| 🥛 奶龙图片 | [doutula.com](https://www.doutula.com) | 搜索页抓取 |
| 🥛 奶龙图片 | [duitang.com](https://www.duitang.com) | 专辑页抓取 |
| 🍗 KFC文案 | [api.shadiao.pro](https://api.shadiao.pro/kfc) | 免费API |
| 🍗 KFC文案 | [60s.viki.moe](https://60s.viki.moe/v2/kfc) | 免费API |

## GitHub 仓库

- 数据库：`https://github.com/WorseFive/Clover_Database`
- Raw URL：`https://raw.githubusercontent.com/WorseFive/Clover_Database/main/`
- 机器人通过 Raw URL 按需获取内容，本地数据库仅用于验证
