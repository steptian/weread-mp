#!/usr/bin/env python3
"""自检：resolve_wechat_url 能不能把不透明的 originalId 换成正确的 __biz/mid/idx/sn。

用法：  python3 test-resolve.py     （需要 Chrome 里已登录 weread.qq.com）

不校验 chksm —— 微信每次请求都会换一个新的 chksm，它不是稳定字段。
"""
import sys
import urllib.parse

sys.path.insert(0, ".")

import weread_mp as w

BOOK = "MP_WXS_3683094569"
OID = ("WR1EkJ9AcEvy2XsC4QGyH1gj9u83Gg4NL62gCyG7tQGa7CXrAWEFLz8Yl0Hs4wA9I4Gnh10U8Fs")
WANT = {
    "__biz": "MzY4MzA5NDU2OQ==",
    "mid": "2247484031",
    "idx": "1",
    "sn": "7381081a5994ec8952e14ba9b792bcfb",
}

url, err = w.resolve_wechat_url(w.extract_cookies(), BOOK, OID)
assert err is None, err
assert url.startswith("https://mp.weixin.qq.com/s?"), url
assert "chksm=" not in url, f"chksm 没被拆掉，链接会 302 到「环境异常」验证页: {url}"

got = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
for k, v in WANT.items():
    assert got.get(k) == v, f"{k}: 得到 {got.get(k)!r}，期望 {v!r}"

# 反例：旧的拼接方式必须拿不到东西（这正是本次修的 bug）
assert w.art_link(OID) == "", "art_link 不该再造 /s/{originalId} 这种打不开的链接"

# picture_page_info_list 解析（离线 fixture，不联网）：
# 真身是 JS 对象字面量 —— 键无引号、值后面跟 ` * 1`，不是 JSON。
FIXTURE = """
window.picture_page_info_list: [
  { cdn_url: 'https://mmbiz.qpic.cn/sz_mmbiz_png/AAA/0?wx_fmt=png',
    width: '828' * 1, height: '1800' * 1, theme_color: 'rgb(0,0,0)', is_qr_code: '0' * 1, },
  { cdn_url: 'http://mmbiz.qpic.cn/mmbiz_jpg/BBB/0?wx_fmt=jpeg',
    width: '1024' * 1, height: '1365' * 1, is_qr_code: '1' * 1, },
  { cdn_url: 'https://mmbiz.qpic.cn/mmbiz_png/CCC/0' },   // 缺宽高 → 应跳过
  { cdn_url: 'https://mmbiz.qpic.cn/mmbiz_png/DDD/640?wx_fmt=png\\x26amp;amp;from=appmsg',
    width: '1080' * 1, height: '455' * 1 },                 // 脏 URL → 要洗干净
  { cdn_url: 'https://mmbiz.qpic.cn/mmbiz_png/EEE/0',
    width: '0' * 1, height: '0' * 1 },                     // 0x0（非主图）→ 应跳过
];
window.next_thing = 1;
"""
pics = w.parse_picture_pages(FIXTURE)
assert len(pics) == 3, pics
assert pics[0] == {"url": "https://mmbiz.qpic.cn/sz_mmbiz_png/AAA/0?wx_fmt=png", "w": 828, "h": 1800}, pics[0]
assert pics[1]["w"] == 1024 and pics[1]["h"] == 1365, pics[1]
# 脏 URL：\\x26 → &，&amp;amp; → &（JS 转义 + 两层 HTML 实体）
assert pics[2]["url"] == "https://mmbiz.qpic.cn/mmbiz_png/DDD/640?wx_fmt=png&from=appmsg", pics[2]
# 没有这个字段的文章（普通正文）→ 空列表，不能报错
assert w.parse_picture_pages("<html>no such field</html>") == []
assert w.parse_picture_pages("picture_page_info_list: [ cdn_url: 'x'") == []

# 正文提取（离线 fixture）：关键是嵌套 div —— 旧代码的非贪婪 `(.*?)</div>`
# 会在第一个 </div> 截断，这就是旧版拿不到正文的原因。
BODY = '''
<div class="rich_media_content js_underline_content" id="js_content" style="visibility: hidden;">
<section><p>第一段。</p></section>
<div class="inner"><p>嵌套 div 里的第二段。</p><div><p>更深一层。</p></div></div>
<p>第三段 &amp; 结束。</p>
</div>
<div class="after">不该被吃进来</div>
'''
txt = w._html_to_text(w.extract_js_content_html(BODY))
assert "第一段。" in txt, txt
assert "更深一层。" in txt, f"嵌套 div 被截断了: {txt!r}"
assert "第三段 & 结束。" in txt, txt
assert "不该被吃进来" not in txt, f"括号配对跑过头了: {txt!r}"
assert w.extract_js_content_html("<html>没这个容器</html>") == ""

print("✅ resolve_wechat_url 通过")
print("   ", url[:88] + "…")
print(f"✅ parse_picture_pages 通过（{len(pics)} 张，含跳过与截断两种边界）")
print("✅ 正文提取通过（嵌套 div 不截断）")
