---
name: weread-mp
description: 通过微信读书内部 API 订阅任意公众号，主题阅读、关键词追踪。自动从浏览器 cookie 库解密登录态。
version: 2.0.0
tags:
  - 公众号
  - 微信读书
  - 订阅
  - RSS
  - weread
requirements:
  - browser-cookie3
trigger:
  - 公众号
  - 微信文章
  - 公众号文章
  - 订阅公众号
  - 抓公众号
  - 获取公众号内容
---

# WeRead MP — 微信公众号订阅工具

通过微信读书（weread.qq.com）的内部 API 获取已关注的公众号文章列表，支持自动解密浏览器 cookie、全文阅读、跨号搜索、关键词追踪。

## ✨ 功能

| 功能 | 说明 |
|------|------|
| **list** | 列出所有已关注的公众号 |
| **articles** | 获取某公众号的历史文章列表 |
| **read** | 阅读文章完整正文 |
| **digest** | 一键遍历所有公众号生成早报 |
| **search** | 跨公众号搜索标题/摘要 |
| **export** | 导出为 Markdown / JSON |
| **track** | 关键词追踪，新文章命中时自动提醒 |

## 🚀 快速开始

### 1. 一键安装

```bash
pip install browser-cookie3 && \
git clone https://github.com/steptian/weread-mp.git && \
cd weread-mp
```

### 2. Chrome 登录微信读书

打开 https://weread.qq.com ，用微信扫码登录。只需登录一次。

### 3. 在微信读书 App 中关注公众号

在手机微信读书 App 中搜索并关注你想订阅的公众号，关注后会在「书架」中显示。

### 4. 使用

```bash
# 列出关注的公众号
python3 weread_mp.py list

# 查看某公众号的最新文章
python3 weread_mp.py articles MP_WXS_3073282833

# 读第 1 篇文章全文
python3 weread_mp.py read MP_WXS_3073282833 --article 1

# 一键早报
python3 weread_mp.py digest --per 3
```

## 📖 命令详解

### 基础

```bash
# 列出关注的公众号
python3 weread_mp.py list

# 获取文章列表（含阅读量、点赞量、原文链接）
python3 weread_mp.py articles MP_WXS_3073282833
python3 weread_mp.py --limit 5 articles MP_WXS_3073282833
```

### 阅读

```bash
# 按序号阅读（会自动先拉列表，再读指定篇）
python3 weread_mp.py read MP_WXS_3073282833 --article 1

# 直接给链接
python3 weread_mp.py read https://mp.weixin.qq.com/s/xxx

# 或直接给 originalId
python3 weread_mp.py read ggsDTrCt3N1elArnpLf9uw

# 显示全文（默认截取 3000 字）
python3 weread_mp.py read --full MP_WXS_3073282833 --article 1
```

### 早报

```bash
# 遍历所有关注的公众号，拉取最新 3 篇
python3 weread_mp.py digest --per 3

# 自动标注 🆕 新文章，匹配追踪关键词
python3 weread_mp.py digest --per 2
```

### 搜索

```bash
# 跨所有公众号搜索关键词
python3 weread_mp.py search 马斯克

# 控制每个号的搜索深度
python3 weread_mp.py search 马斯克 --per 5
```

### 导出

```bash
# 导出为 Markdown
python3 weread_mp.py export MP_WXS_3073282833 > articles.md

# 导出为 JSON
python3 weread_mp.py export MP_WXS_3073282833 --format json > articles.json
```

### 关键词追踪

```bash
# 添加追踪关键词
python3 weread_mp.py track add 比亚迪

# 查看追踪列表
python3 weread_mp.py track list

# 移除关键词
python3 weread_mp.py track remove 比亚迪

# 检查新文章是否命中关键词
python3 weread_mp.py track check
```

`track check` 会扫描所有公众号的最新文章，命中关键词的自动列出，并记录已读状态避免重复提醒。

### 手动指定 cookie（备用）

```bash
# 如果自动提取失败，可从浏览器开发者工具中复制 cookie
python3 weread_mp.py --cookie "wr_skey=xxx; wr_vid=xxx" list
```

## 🔧 原理

```
浏览器 cookie 数据库
  (Chrome: ~/Library/Application Support/Google/Chrome/Default/Cookies)
  (Edge:   ~/Library/Application Support/Microsoft Edge/Default/Cookies)
  (Brave:  ~/Library/Application Support/BraveSoftware/Brave-Browser/Default/Cookies)
       ↓ browser-cookie3 自动解密
    wr_skey + wr_vid + ...
       ↓
    GET https://weread.qq.com/web/mp/articles?bookId=MP_WXS_xxx&offset=0
       ↓
    公众号文章列表（标题、摘要、阅读量、点赞量、原文链接）
       ↓
    GET https://mp.weixin.qq.com/s/{originalId}
       ↓
    文章完整正文
```

## ⚠️ 常见问题

### cookie 过期

如果 Chrome 中 weread.qq.com 的登录过期，脚本会提示：

```
⚠️  ⚠️  ⚠️  cookie 已过期 ⚠️  ⚠️  ⚠️
请在 Chrome 中重新打开 https://weread.qq.com
扫码登录后重新运行本脚本
```

解决方法：**打开 Chrome → 访问 weread.qq.com → 扫码登录 → 重新运行**

### 不支持 Chrome？

`browser-cookie3` 支持以下浏览器：

- Google Chrome
- Microsoft Edge
- Brave
- Chromium
- Vivaldi

如果使用 Firefox 或 Safari，建议用 `--cookie` 参数手动传入 cookie。

### 找不到公众号？

确保已在**手机微信读书 App** 中搜索并关注目标公众号，关注后公众号会出现在书架中。

### pip install 报错？

```bash
# macOS
pip3 install browser-cookie3

# 如果遇到权限问题
pip3 install --user browser-cookie3
```

## 💾 数据存储

追踪关键词和已读记录保存在 `~/.weread_mp_state.json`。

```json
{
  "seen": {
    "MP_WXS_3073282833": {
      "ggsDTrCt3N1elArnpLf9uw": {
        "title": "「马嘉祺」让大模型翻车...",
        "time": 1780027464
      }
    }
  },
  "keywords": ["比亚迪", "大模型"]
}
```

删除此文件可重置所有状态。

## ⚠️ 局限性

- 只能获取**已在微信读书 App 中关注**的公众号
- 依赖浏览器中的 `wr_skey` cookie，过期需重新扫码
- 正文抓取依赖 `mp.weixin.qq.com` 公开页面，极少数情况可能被反爬
- 与 weread 官方 API key 体系（`wrk-xxx`）**不互通**，需两套认证
- 目前仅支持 Chrome/Chromium 系浏览器自动提取 cookie，Firefox/Safari 需手动传入

## 📃 许可

MIT

## ⚠️ 免责声明

本工具使用了**微信读书（weread.qq.com）的非公开内部接口**，该接口未经腾讯官方文档化或授权。请知悉：

- **仅供个人学习与研究使用**，请勿用于商业用途或大规模抓取
- 请合理控制调用频率，避免对微信读书服务造成负担
- 使用者应自行承担使用风险，作者不对因使用本工具导致的任何问题负责
- 如腾讯官方对此类使用方式提出异议，本仓库将立即配合下架

如果你喜欢这个工具并希望它持续可用，请低调使用，不要大规模传播或商业化。

---

## 👤 关于作者

**添先盼（Steptian）** — 22 年互联网老兵，腾讯 6 年技术经理（T3-2），历任京东高级技术经理、多家公司 CTO/技术 VP，3 次创业经历。

近两年全身心投入 **AI Agent 实战**，独立开发 44+ AI 工具，将 AI 深度融入招聘、运营、数据分析、内容创作等真实业务场景。兼具「技术 + 业务 + 管理」三重视角，能为企业提供 AI 转型顾问与实战培训。

- 📮 公众号：**出发-AI慢生活**
- 🌌 知识星球：**AI慢生活**
- 💬 个人微信：**Steptian**

> 如果这个项目对你有帮助，欢迎 star、转发，也欢迎加微信交流 AI 落地～
