<h1 align="center">weread-mp</h1>
<p align="center">
  <strong>微信公众号订阅工具</strong><br>
  通过微信读书 API 获取公众号文章 · 全文阅读 · 关键词追踪 · 跨号搜索
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.8+-blue" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/github/stars/steptian/weread-mp" alt="Stars">
</p>

---

公众号是个封闭的花园——没有 RSS，没有开放 API，想盯几个竞品公众号的更新，每天挨个翻，累。

这个工具利用**微信读书的内部 API**，把公众号文章变成结构化的数据。你只需要在微信读书里关注了某个公众号，就能像 RSS 一样订阅它。

## ✨ 功能

| 命令 | 说明 |
|------|------|
| `list` | 列出所有已关注的公众号 |
| `articles` | 获取某公众号的历史文章列表 |
| `read` | 阅读文章完整正文 |
| `digest` | 一键遍历所有公众号生成早报 |
| `search` | 跨公众号搜索标题/摘要 |
| `export` | 导出为 Markdown / JSON |
| `track` | 关键词追踪，新文章命中时自动提醒 |

## 🚀 快速开始

### 1. 一键安装

```bash
pip install browser-cookie3 && \
git clone https://github.com/steptian/weread-mp.git && \
cd weread-mp
```

### 2. Chrome 登录微信读书

打开 [https://weread.qq.com](https://weread.qq.com)，用微信扫码登录。只需登录一次。

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

# 一键早报：所有公众号的最新文章汇总
python3 weread_mp.py digest --per 3

# 搜一下各个号里提到「马斯克」的文章
python3 weread_mp.py search 马斯克

# 设置关键词追踪，有新文章自动提醒
python3 weread_mp.py track add AI
python3 weread_mp.py track check

# 导出成 Markdown 慢慢看
python3 weread_mp.py export MP_WXS_3073282833 > articles.md
```

## 📖 命令详解

### 阅读

```bash
# 按序号阅读（会先拉列表，再读指定篇）
python3 weread_mp.py read MP_WXS_3073282833 --article 1

# 直接给链接
python3 weread_mp.py read https://mp.weixin.qq.com/s/xxx

# 显示全文（默认截取 3000 字）
python3 weread_mp.py read --full MP_WXS_3073282833 --article 1
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

### 导出

```bash
# 导出为 Markdown
python3 weread_mp.py export MP_WXS_3073282833 > articles.md

# 导出为 JSON
python3 weread_mp.py export MP_WXS_3073282833 --format json > articles.json
```

## 🔧 原理

```
浏览器 cookie 数据库
  (Chrome/Edge/Brave)
       ↓ browser-cookie3 自动解密
    wr_skey + wr_vid + ...
       ↓
    GET https://weread.qq.com/web/mp/articles
       ↓
    公众号文章列表（标题、摘要、阅读量、点赞量、原文链接）
       ↓
    GET https://mp.weixin.qq.com/s/{id}
       ↓
    文章完整正文
```

关键点：公众号文章正文其实在 `mp.weixin.qq.com` 上是**公开可访问的**，你只是不知道链接在哪。微信读书的 API 恰好能给你这个链接。

## ⚠️ cookie 过期处理

如果浏览器中的 weread.qq.com 登录过期，脚本会提示：

```
⚠️  ⚠️  ⚠️  cookie 已过期 ⚠️  ⚠️  ⚠️
请在 Chrome 中重新打开 https://weread.qq.com
扫码登录后重新运行本脚本
```

解决方法：**打开 Chrome → 访问 weread.qq.com → 扫码登录 → 重新运行**

## 💾 数据存储

追踪关键词和已读记录保存在 `~/.weread_mp_state.json`。删除此文件可重置所有状态。

## ⚠️ 局限性

- 只能获取**已在微信读书 App 中关注**的公众号（不是微信里的关注）
- 依赖浏览器中的 `wr_skey` cookie，过期需重新扫码
- 正文抓取依赖 `mp.weixin.qq.com` 公开页面，极少数情况可能被反爬
- 自动提取 cookie 仅支持 Chrome/Edge/Brave，Firefox/Safari 需手动传入 `--cookie`

## 🤝 贡献

欢迎提交 Issue 和 PR。如果你想加新功能或修 bug，直接 fork 改就行。

---

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

近两年专注 **AI Agent 实战**，独立开发 44+ AI 工具，将 AI 深度融入招聘、运营、数据分析、内容创作等真实业务场景。兼具「技术 + 业务 + 管理」三重视角，能为企业提供 AI 转型顾问与实战培训。

- 📮 **公众号**：出发-AI慢生活
- 🌌 **知识星球**：AI慢生活
- 💬 **微信**：Steptian

> 如果这个项目对你有帮助，欢迎 star、转发，也欢迎加微信交流 AI 落地～