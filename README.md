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
| `read` | 读全文：文字文章给完整正文（默认全文，正文里的图原位保留成 `[图片] URL`），图片消息列出图集 URL；`--save-dir` 把图存到本地 |
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

# 默认就是全文；想要短一点就截断
python3 weread_mp.py read MP_WXS_3073282833 --article 1 --chars 3000

# 把文中图片存到本地（文件名前缀取自标题，不同文章不会撞）
python3 weread_mp.py read MP_WXS_3073282833 --article 1 --save-dir ./imgs
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
浏览器 cookie 数据库（Chrome/Edge/Brave）
       ↓ browser-cookie3 自动解密
    wr_skey + wr_vid + ...
       ↓
GET https://weread.qq.com/web/mp/articles?bookId=MP_WXS_xxx&offset=0
       ↓
公众号文章列表（标题、摘要、阅读量、点赞量、originalId）
       ↓
GET https://weread.qq.com/web/mp/content?reviewId={bookId}_{originalId}
   （响应约 3.5MB，脚本只读前 1MB）
       ├─ og:url                  ~17KB  → canonical 公开链接（拆掉 chksm）
       ├─ picture_page_info_list  ~225KB → 图片消息的图集
       └─ rich_media_content      ~557KB → 文字正文
```

**关键点：正文不从 `mp.weixin.qq.com` 直接拿。** 那条路对桌面端会 302 到验证页、或者只给预览页（`#js_content` 里只有摘要那百来字）。但微信读书代理回来的**同一篇 HTML 里就有完整正文** —— 这才是能拿到全文的原因。

三个坑（代码注释里也有）：

1. **取正文容器必须做 `div` 括号配对**。正文里有嵌套 `<div>`，非贪婪 `(.*?)</div>` 会在第一个 `</div>` 截断 —— 旧版就是死在这里。
2. **`chksm` 要去掉**。它是每次请求现算的校验和，带着它访问 canonical 链接会 302 到 `/mp/wappoc_appmsgcaptcha`（「环境异常」）。
3. **图集 URL 是脏的**：形如 `...?wx_fmt=png\x26amp;amp;from=appmsg`，要洗掉 JS 转义和两层 HTML 实体，否则图打不开。

## 📌 2026-10 重要变更

### `originalId` 换格式了

微信读书 `mpInfo.originalId` 从 **22 字符短链 token** 变成 **75 字符不透明 id**：

```
旧  ggsDTrCt3N1elArnpLf9uw                     →  mp.weixin.qq.com/s/{id}  ✅
新  WR1EkJ9AcEvy2XsC4QGyH1gj9u83Gg4NL62g…      →  mp.weixin.qq.com/s/{id}  ❌ 参数错误
```

逆推不可行：base64 解出 56 字节，其中 36 字节熵 7.09 bit/byte（近均匀随机），
与 `mid` / `idx` 无可见对应，而且前端 JS 里根本搜不到 `originalId`（它只把
`reviewId = {bookId}_{originalId}` 原样丢给服务端）。所以 `read` 不再自己拼 URL，
改走 `/web/mp/content` 换真实链接。

### 风控验证码

`/web/mp/articles` 会返回 `errCode: -2041`，页面弹腾讯验证码（「选择最符合描述的图片」）。
过掉之后可用，但**会重新武装**，不是一次性的；同 session 的 `/web/shelf/sync` 不受影响。

脚本请求之间用**随机区间**停顿（`SLEEP_PAGE` / `SLEEP_ACCOUNT` 两个常量）—— 固定间隔
容易被认成脚本。被挡了就调大这两个区间。

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
- 正文与图集都走 `/web/mp/content`（微信读书代理的那份 HTML），不依赖 `mp.weixin.qq.com` 能否直接访问
- 自动提取 cookie 仅支持 Chrome/Edge/Brave，Firefox/Safari 需手动传入 `--cookie`

## 🧪 自检

```bash
python3 test-resolve.py
```

断言链接解析、图集解析（脏 URL / 缺宽高 / `0x0` / 数组截断）、正文提取（嵌套 `div` 不截断）。需要 Chrome 里已登录 weread.qq.com。

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