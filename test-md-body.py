#!/usr/bin/env python3
"""自检：正文 `[图片] URL` → Markdown 内嵌图的转换（纯函数，不联网）。

跑：python3 test-md-body.py
"""
import os
import tempfile

import weread_mp as w

SAVED = {"https://mmbiz.qpic.cn/A/640?wx_fmt=jpeg": "标题01.jpg",
         "https://mmbiz.qpic.cn/B/640?wx_fmt=jpeg": "标题02.jpg"}

# 1) 下到本地的图 → 变成相对路径的 Markdown 图片
got = w._md_body("前文\n[图片] https://mmbiz.qpic.cn/A/640?wx_fmt=jpeg\n后文", SAVED)
assert got == "前文\n![](标题01.jpg)\n后文", got

# 2) 没下到本地的图 → 保留原 URL，不静默丢图
got = w._md_body("[图片] https://mmbiz.qpic.cn/ZZZ/640", SAVED)
assert got == "[图片](https://mmbiz.qpic.cn/ZZZ/640)", got

# 3) 没有 URL 的裸占位符 → 原样保留
assert w._md_body("[图片]", SAVED) == "[图片]"

# 4) 同一张图出现两次 → 两处都换
got = w._md_body("[图片] https://mmbiz.qpic.cn/B/640?wx_fmt=jpeg\n"
                 "文字\n[图片] https://mmbiz.qpic.cn/B/640?wx_fmt=jpeg", SAVED)
assert got.count("![](标题02.jpg)") == 2, got

# 5) 正文里的普通方括号链接不受影响（只匹配行首的 [图片] 标记）
txt = "参考[图片]说明\n[图片] https://mmbiz.qpic.cn/A/640?wx_fmt=jpeg"
assert w._md_body(txt, SAVED) == "参考[图片]说明\n![](标题01.jpg)"

# 6) 图片消息：正文为空 → 用图集补成图块，顺序不变
art = {"title": "混知", "body": "", "url": "https://mp.weixin.qq.com/s/x"}
with tempfile.TemporaryDirectory() as d:
    md = w.write_article_md(art, d, SAVED, [{"url": "https://mmbiz.qpic.cn/B/640?wx_fmt=jpeg"}])
    assert os.path.basename(md) == "混知.md", md
    with open(md, encoding="utf-8") as f:
        txt = f.read()
    assert txt.startswith("# 混知"), txt
    assert "![](标题02.jpg)" in txt

print("✅ _md_body / write_article_md 全部通过")
