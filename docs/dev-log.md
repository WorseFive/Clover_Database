# Clover_Database 开发日志

> 自动回复数据库：数据采集、验证、管理面板
> 最后更新: 2026-07-15

---

## 2026-07-15: 阶段1 — 数据库建立

### 做了什么
- 创建 GitHub 仓库 `WorseFive/Clover_Database` + 本地副本 `d:/A_VPN/Clover_Database/`
- 搭建完整目录结构: `texts/` (kfc/thunder_dragon/fadian) + `images/` (pig/nailong/otto)
- 编写 `scripts/validate.py` 数据验证脚本
- 定义数据规范: 图片格式(魔法字节检测)、文件命名、manifest一致性、JSON有效性

### 设计决策
- 本地数据库仅用于数据验证，不是机器人数据源
- 机器人通过 GitHub Raw URL 按需获取内容，节约VPS内存
- 图片强制魔法字节检测: 扩展名必须匹配实际格式
- manifest.json 必须与目录实际内容一致

### 踩的坑
- 无

---

## 2026-07-15: 阶段2 — 数据采集

### KFC 文案 (278条)
- **来源**: `api.shadiao.pro/kfc` + `60s.viki.moe/v2/kfc`
- **方式**: Python 脚本循环调用 API，去重
- **问题**: shadiao API 偶尔返回非KFC内容（数学题、广告等），清洗掉 22 条无效数据
- **脚本**: `scripts/scrape_kfc.py`

### 雷电飞龙文案 (82条)
- **来源**: B站/微信社区手动整理
- **分类**: 一字划流派、首领对话、黑雷梗、吹风机梗、弹幕高频、装备流派
- **脚本**: `scripts/scrape_thunder_dragon.py`

### 发癫文案 (52条)
- **来源**: 手动整理 + 发癫文学语料库
- **分类**: 经典发癫体、发疯体、胡言乱语体、抽象发癫、伪哲学、emoji发癫
- **脚本**: `scripts/scrape_fadian.py`

### 猪猪图片 (1085张, 384MB)
- **来源**: pighub.top
- **API端点**: `/api/images?sort=2` → 返回全部图片元数据
- **发现过程**: 逆向 `koishi-plugin-get-random-pig` 开源插件源码找到 `/api/all-images` 和 `/api/images` 端点
- **问题1**: 文件名含中文 → URL编码解决
- **问题2**: 扩展名与实际格式不匹配（.png实为jpg）→ `rebuild_manifests.py` 自动修复
- **问题3**: 存在 `.jpeg` 和 `.jpg` 同名重复 → 去重逻辑
- **问题4**: 特殊文件名（`.jpg`、`猪叠....jpg`等）→ 手动清理
- **脚本**: `scripts/download_pigs.py`

### 电棍表情包 (1079张, 93MB)
- **来源1**: gengtu.net（16张）
  - 从标签页 `/memes/tag/dian-gun-otto/` 获取页面列表
  - 梗图页 HTML 中提取 `/i/download/memes/` 下载链接
  - 搜索功能被 403 封锁
- **来源2**: doutula.com（1063张）
  - 搜索关键词: 电棍, otto, 侯国玉, 炫狗, 张顺飞, 电昆, 棍棍, 吉吉国, 轮椅人, 国玉, 说的道理
  - 从 `data-original` 属性提取图片URL
  - SSL证书过期 → 禁用证书验证
  - 图片托管在 `img.doutupk.com`
- **问题**: gengtu 搜索被 403，fabiaoqing.com SSL握手失败
- **最终**: 1038张 → 清理重复和无效文件后达1079张

### 奶龙图片 (464张, 124MB)
- **来源1**: duitang.com 堆糖（61张）
  - 5个专辑: 124280721(231张), 121026620(89张), 86254810, 109796626(285张), 106283826(50张)
  - 缩略图URL去除 `.thumb.WxH` 后缀获取原图
  - 分页失效 → 每页返回相同54张缩略图
  - 专辑135473755(350张) 为atlas格式，获取48张
- **来源2**: doutula.com 斗图啦（403张）
  - 搜索关键词: 奶龙, 奶蛙, 奶龙表情包, 奶龙动图, 奶龙gif, 奶龙可爱
  - 同上 SSL 证书问题
- **问题**: 缩略图文件混入正式目录 → 删除27个 `.thumb.` 文件
- **最终**: 491张 → 清除缩略图后464张

### 采集总量
| 类别 | 数量 | 大小 |
|------|------|------|
| 猪猪图片 | 1,085 | 384MB |
| 电棍表情包 | 1,079 | 93MB |
| 奶龙图片 | 464 | 124MB |
| KFC文案 | 278 | 文本 |
| 雷龙文案 | 82 | 文本 |
| 发癫文案 | 52 | 文本 |
| **合计** | **3,040项** | **601MB** |

---

## 2026-07-15: 阶段3 — 管理面板

### 做了什么
- 在 `worsefive.github.io/static/app.html` 新增第二页：🗄️ 数据库管理
- 双页导航：VPS面板（不动） + 数据库管理（新增）

### 功能清单
- **添加图片**: 独立弹窗，支持拖拽/点击/Ctrl+V粘贴
- **删除图片**: 缩略图网格浏览 + 多选删除
- **重命名图片**: 选中单张 → 输入新文件名
- **数据概览**: GitHub API 实时读取各分类数量
- **修复扩展名**: 自动 `.jpeg` → `.jpg`

### 技术实现
- GitHub API 直连操作仓库 (PUT/DELETE/GET)
- 图片上传: FileReader → ArrayBuffer → Base64 → GitHub Content API
- 缩略图: GitHub Raw URL 直链加载
- 拖拽: dragover/drop 事件 + File API
- 粘贴: document paste 事件 + Clipboard API
- Token 存储在 localStorage
- PocketBase 后端不受影响（VPS面板独立运行）

### 踩的坑
- GitHub 443端口被墙 → 切换网络后推送成功
- gh CLI 和 git 走不同通道（gh可用时git不一定可用）
- 文件名含中文需 URL 编码
- `.jpeg` 和 `.jpg` 重复文件 → 扩展名统一修复
- doutula SSL 证书过期 → 禁用证书验证
- gengtu 搜索被 403 → 改用标签页发现 + 全面搜索多关键词
- duitang 分页返回重复数据 → 多专辑并发采集

---

## 2026-07-15: 已知问题

1. **GitHub 网络不稳定**: 部分地区443端口被墙，需切换网络推送
2. **duitang 分页失效**: 每页返回相同数据，无法翻页获取全部231张
3. **gengtu 搜索封锁**: 返回403，只能通过标签页间接发现
4. **doutula SSL过期**: 每次请求需禁用证书验证
5. **奶龙未达500**: 464张，差36张（可选后续补充）

---

## 2026-07-15: 阶段3.5 — 面板修复 + 网络优化

### 面板故障
- **问题**: 点击按钮无响应
- **根因**: `PocketBase` CDN加载失败 → `new PocketBase()`抛异常 → 整个JS崩溃，VPS面板和DB面板全部瘫痪
- **修复**: VPS面板和DB面板解耦为两个独立IIFE，try-catch保护，PocketBase挂了不影响DB面板
- **验证**: JS花括号159/159，HTML div 105/105，21个函数全部暴露到window

### 混合内容拦截
- **问题**: HTTPS页面(`worsefive.github.io`) → HTTP API(`166.88.98.215:8090`) 被浏览器拦截
- **修复**: VPS安装nginx，自签SSL证书，8443端口反代→8090
- **验证**: `curl -k https://166.88.98.215:8443/api/health` → 200

### GitHub网络不稳定
- **问题**: 国内GitHub 443端口间歇性不通
- **根因**: WireGuard只路由内网，GitHub走公网被墙
- **修复**: SSH SOCKS5隧道 → VPS → GitHub，端口1080
- **Git配置**: `http.proxy socks5h://127.0.0.1:1080` (全局)
- **自动启动**: `~/.bashrc` 检测隧道状态，挂了自动拉起

### URL锚点路由
- `app.html#vps` → VPS面板
- `app.html#database` → 数据库面板
- 三个快捷启动脚本: `dashboard_vps.bat` / `dashboard_database.bat` / `dashboard_all.bat`

## 下一步计划

- [ ] 阶段4: 开发 `auto_reply` AstrBot 插件（关键词匹配 + GitHub Raw 按需获取）
- [ ] 部署到 VPS 测试
- [ ] 补充奶龙图片至500+
- [ ] web面板增加文案管理功能（添加/删除/编辑文案）
