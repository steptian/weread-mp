#!/usr/bin/env python3
"""
微信读书 × 公众号订阅工具

从微信读书内部 API 获取公众号文章列表。
自动从 Chrome SQLite cookie 库解密登录态，无需手动粘 cookie。
"""

import argparse
import json
import os
import re
import sys
import time
import html as html_mod
import urllib.request
import urllib.parse
from datetime import datetime, date

WEREAD_HOST = "https://weread.qq.com"
STATE_FILE = os.path.expanduser("~/.weread_mp_state.json")


# ===== 状态管理（增量监控 + 关键词追踪） =====

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"seen": {}, "keywords": []}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE) or ".", exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def mark_seen(state, book_id, original_id, title, pub_time):
    if book_id not in state["seen"]:
        state["seen"][book_id] = {}
    state["seen"][book_id][original_id] = {
        "title": title,
        "time": pub_time,
    }


def is_new(state, book_id, original_id):
    return original_id not in state.get("seen", {}).get(book_id, {})


# ===== 浏览器 cookie 提取（支持 Chrome/Edge/Brave） =====

SUPPORTED_BROWSERS = [
    ("chrome", "Google Chrome"),
    ("edge", "Microsoft Edge"),
    ("brave", "Brave"),
    ("chromium", "Chromium"),
    ("opera", "Opera"),
    ("vivaldi", "Vivaldi"),
]


def extract_cookies():
    try:
        import browser_cookie3 as bc
    except ImportError:
        print("❌ 需要 browser-cookie3 库")
        print("   安装: pip install browser-cookie3")
        print("   (支持 Chrome / Edge / Brave / Chromium / Opera / Vivaldi)")
        sys.exit(1)

    last_error = None
    for browser_fn, browser_name in SUPPORTED_BROWSERS:
        try:
            loader = getattr(bc, browser_fn, None)
            if not loader:
                continue
            cookies = loader(domain_name="weread.qq.com")
            if cookies:
                cookie_parts = []
                for c in cookies:
                    name = c.name
                    value = c.value
                    if any(ch in value for ch in [" ", ",", ";", '"']):
                        value = urllib.parse.quote(value)
                    cookie_parts.append(f"{name}={value}")
                return "; ".join(cookie_parts)
        except Exception as e:
            last_error = e
            continue

    print("❌ 未能从浏览器中提取 weread.qq.com 的 cookie")
    print("   请在 Chrome / Edge / Brave 中打开 https://weread.qq.com 并扫码登录")
    print("   也可使用 --cookie 参数手动传入:")
    print()
    print("       python3 weread_mp.py --cookie 'wr_skey=xxx; wr_vid=xxx' list")
    print()
    if last_error:
        print(f"   原始错误: {last_error}")
    sys.exit(1)

# ===== API 调用 =====

def api_call(path, cookie, params=None):
    url = f"{WEREAD_HOST}{path}"
    if params:
        qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
        url = f"{url}?{qs}"
    req = urllib.request.Request(url)
    req.add_header("Cookie", cookie)
    req.add_header("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
    req.add_header("Accept", "application/json, text/plain, */*")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        if isinstance(data, dict):
            err_code = data.get("errCode") or data.get("errcode")
            if err_code and err_code != 0:
                err_msg = data.get("errMsg") or data.get("errmsg") or ""
                if any(k in err_msg for k in ["用户不存在", "登录", "token", "过期"]):
                    print("\n⚠️  ⚠️  ⚠️  cookie 已过期 ⚠️  ⚠️  ⚠️")
                    print("   请在 Chrome 中重新打开 https://weread.qq.com")
                    print("   扫码登录后重新运行本脚本")
                    sys.exit(1)
        return data
    except urllib.request.HTTPError as e:
        if e.code in (401, 403):
            print("\n⚠️  ⚠️  ⚠️  cookie 已过期 ⚠️  ⚠️  ⚠️")
            print("   请在 Chrome 中重新打开 https://weread.qq.com")
            print("   扫码登录后重新运行本脚本")
            sys.exit(1)
        print(f"❌ HTTP {e.code}: {e.read().decode()[:300]}")
        return None
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None


# ===== 数据获取 =====

def get_mp_list(cookie):
    """获取关注的公众号列表"""
    data = api_call("/web/shelf/sync", cookie, {"userVid": "", "synckey": 0})
    if data and "books" in data:
        return [b for b in data["books"]
                if isinstance(b.get("bookId"), str)
                and b["bookId"].startswith("MP_WXS_")]
    return []


def get_articles(cookie, book_id, limit=50):
    """获取某公众号的文章列表"""
    articles = []
    offset = 0
    while len(articles) < limit:
        data = api_call("/web/mp/articles", cookie, {"bookId": book_id, "offset": offset})
        if not data or "reviews" not in data:
            break
        reviews = data.get("reviews", [])
        if not reviews:
            break
        for r in reviews:
            for s in r.get("subReviews", []):
                info = s.get("review", {}).get("mpInfo", {})
                if info.get("title"):
                    articles.append({
                        "title": info["title"],
                        "summary": info.get("content", ""),
                        "mp_name": info.get("mp_name", ""),
                        "original_id": info.get("originalId", ""),
                        "read_num": info.get("readNum", 0),
                        "like_num": info.get("likeNum", 0),
                        "time": info.get("time", 0),
                    })
        clear_all = data.get("clearAll", 0)
        if clear_all:
            break
        min_time = min(r.get("createTime", 0) for r in reviews)
        offset = min_time
        if len(reviews) < 10:
            break
        time.sleep(0.3)
    return articles


def get_article_content(url, max_chars=3000):
    """获取文章正文"""
    if not url.startswith("http"):
        url = f"https://mp.weixin.qq.com/s/{url}"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None, f"❌ 获取失败: {e}"

    title = ""
    m = re.search(r'<meta[^>]*property="og:title"[^>]*content="(.*?)"', html)
    if m:
        title = html_mod.unescape(m.group(1)).strip()
    desc = ""
    m = re.search(r'<meta[^>]*property="og:description"[^>]*content="(.*?)"', html)
    if m:
        desc = html_mod.unescape(m.group(1)).strip()
    author = ""
    m = re.search(r'<meta[^>]*property="og:article:author"[^>]*content="(.*?)"', html)
    if m:
        author = html_mod.unescape(m.group(1)).strip()
    cover = ""
    m = re.search(r'<meta[^>]*property="og:image"[^>]*content="(.*?)"', html)
    if m:
        cover = m.group(1)
    pub_time = ""
    m = re.search(r'<em[^>]*id="publish_time"[^>]*>(.*?)</em>', html)
    if m:
        pub_time = m.group(1).strip()
    if not pub_time:
        m = re.search(r'"publish_time":"(\d{4}-\d{2}-\d{2})"', html)
        if m:
            pub_time = m.group(1)
    m = re.search(r'<div[^>]*class="rich_media_content[^"]*"[^>]*id="js_content"[^>]*>(.*?)</div>', html, re.S)
    body_html = m.group(1) if m else ""
    if not body_html:
        return {"title": title, "author": author, "desc": desc, "cover": cover,
                "pub_time": pub_time, "body": "", "url": url}, None
    body_text = body_html
    body_text = re.sub(r'<br\s*/?>', "\n", body_text)
    body_text = re.sub(r'</p>', "\n", body_text)
    body_text = re.sub(r'</section>', "\n", body_text)
    body_text = re.sub(r'</div>', "\n", body_text)
    body_text = re.sub(r'<[^>]+>', "", body_text)
    body_text = re.sub(r'&nbsp;', " ", body_text)
    body_text = html_mod.unescape(body_text)
    body_text = re.sub(r'\n{3,}', "\n\n", body_text)
    body_text = body_text.strip()
    truncated = False
    if max_chars and len(body_text) > max_chars:
        body_text = body_text[:max_chars]
        truncated = True
    return {"title": title, "author": author, "desc": desc, "cover": cover,
            "pub_time": pub_time, "body": body_text, "truncated": truncated, "url": url}, None


# ===== 格式化输出 =====

def fmt_time(ts):
    return datetime.fromtimestamp(ts).strftime("%m-%d %H:%M") if ts else ""


def art_link(original_id):
    return f"https://mp.weixin.qq.com/s/{original_id}" if original_id else ""


# ===== 命令实现 =====

def cmd_list(cookie):
    mps = get_mp_list(cookie)
    if not mps:
        print("⚠️  未找到公众号，请先在微信读书 App 中关注")
        return
    print(f"\n📰 你关注的公众号 ({len(mps)}):\n")
    for i, b in enumerate(mps, 1):
        title = b.get("title", "未知")
        book_id = b.get("bookId", "")
        print(f"  {i:2d}. {title}")
        print(f"       bookId: {book_id}")
    print()


def cmd_articles(cookie, book_id, limit=50):
    print(f"\n📰 正在获取文章 (bookId: {book_id})...")
    arts = get_articles(cookie, book_id, limit)
    if not arts:
        print("⚠️  未获取到文章")
        return
    mp_name = arts[0]["mp_name"]
    print(f"\n{'='*60}")
    print(f"  {mp_name} — 共 {len(arts)} 篇")
    print(f"{'='*60}\n")
    for i, a in enumerate(arts, 1):
        t = fmt_time(a["time"])
        link = art_link(a["original_id"])
        print(f"  {i:2d}. {a['title']}")
        if t:
            print(f"       {t}  👍{a['like_num']}  👁{a.get('read_num', 0)}")
        if a["summary"]:
            print(f"       {a['summary'][:80]}")
        if link:
            print(f"       {link}")
        print()
    print(f"💡 python3 weread_mp.py read {book_id} --article N 阅读全文")


def cmd_read(cookie, target, article_idx, max_chars):
    if not target.startswith("MP_WXS"):
        # 直接 URL 或 originalId
        url = target
        if not url.startswith("http"):
            url = f"https://mp.weixin.qq.com/s/{url}"
        print(f"\n📖 正在读取文章...")
        art, err = get_article_content(url, max_chars)
        if err:
            print(err)
            return
        _print_article(art)
    else:
        arts = get_articles(cookie, target, limit=30)
        if not arts:
            return
        if article_idx <= 0 or article_idx > len(arts):
            _print_article_list(arts)
            print(f"💡 请用 --article 1~{len(arts)} 指定要读哪篇")
            return
        art = arts[article_idx - 1]
        if not art.get("original_id"):
            print("❌ 无 originalId")
            return
        url = f"https://mp.weixin.qq.com/s/{art['original_id']}"
        print(f"\n📖 正在读取: {art['title']}")
        result, err = get_article_content(url, max_chars)
        if err:
            print(err)
            return
        _print_article(result)


def _print_article_list(arts):
    if not arts:
        return
    mp_name = arts[0]["mp_name"]
    print(f"\n{'='*60}")
    print(f"  {mp_name} — 共 {len(arts)} 篇")
    print(f"{'='*60}\n")
    for i, a in enumerate(arts, 1):
        link = art_link(a["original_id"])
        t = fmt_time(a["time"])
        print(f"  {i:2d}. {a['title']}")
        if t:
            print(f"       {t}  👍{a['like_num']}  👁{a.get('read_num', 0)}")
        if a["summary"]:
            print(f"       {a['summary'][:80]}")
        if link:
            print(f"       {link}")
        print()


def _print_article(art):
    print(f"\n{'='*60}")
    print(f"  {art['title']}")
    print(f"{'='*60}")
    if art.get("author"):
        print(f"  ✍️  {art['author']}")
    if art.get("pub_time"):
        print(f"  🕐 {art['pub_time']}")
    if art.get("desc"):
        print(f"  📝 {art['desc']}")
    print(f"  🔗 {art['url']}")
    if not art["body"]:
        print("\n  (正文为空)")
    else:
        print(f"\n{art['body']}")
        if art.get("truncated"):
            print(f"\n  ...（截取前 {len(art['body'])} 字，加 --full 看全文）")


# ===== 新增: digest =====

def cmd_digest(cookie, per_account=3):
    """遍历所有公众号，拉取最新文章生成摘要"""
    mps = get_mp_list(cookie)
    if not mps:
        print("⚠️  未找到公众号")
        return

    state = load_state()
    today = date.today().isoformat()

    print(f"\n{'='*60}")
    print(f"  📰 公众号早报 — {today}")
    print(f"{'='*60}\n")

    all_new = 0
    for b in mps:
        title = b.get("title", "未知")
        book_id = b.get("bookId", "")
        print(f"── {title} ──")
        arts = get_articles(cookie, book_id, limit=per_account)
        if not arts:
            print("  (无文章)\n")
            continue
        for a in arts:
            new_flag = ""
            if is_new(state, book_id, a["original_id"]):
                new_flag = " 🆕"
                all_new += 1
                mark_seen(state, book_id, a["original_id"],
                          a["title"], a["time"])
            t = fmt_time(a["time"])
            print(f"  {t}  👍{a['like_num']}  {new_flag}")
            print(f"  {a['title']}")
            if a["summary"]:
                print(f"  {a['summary'][:120]}")
            print()

    # 关键词匹配
    keywords = state.get("keywords", [])
    if keywords:
        print(f"{'='*60}")
        print(f"  🔍 关键词追踪")
        print(f"{'='*60}")
        # 重新扫一遍所有号的全部文章找匹配
        for b in mps:
            book_id = b.get("bookId", "")
            mp_name = b.get("title", "")
            arts = get_articles(cookie, book_id, limit=10)
            matched = []
            for a in arts:
                text = (a["title"] + " " + a.get("summary", "")).lower()
                for kw in keywords:
                    if kw.lower() in text:
                        matched.append((kw, a))
                        break
            if matched:
                print(f"\n  📌 {mp_name}:")
                for kw, a in matched:
                    link = art_link(a["original_id"])
                    print(f"    [{kw}] {a['title']}")
                    print(f"           {link}")

    save_state(state)
    if all_new:
        print(f"  ✨ 发现 {all_new} 篇新文章")
    print()


# ===== 新增: search =====

def cmd_search(cookie, keyword, per_account=20):
    """跨公众号搜索文章"""
    mps = get_mp_list(cookie)
    if not mps:
        print("⚠️  未找到公众号")
        return

    kw = keyword.lower()
    print(f"\n🔍 搜索 \"{keyword}\" 共 {len(mps)} 个公众号...\n")

    found = 0
    for b in mps:
        mp_name = b.get("title", "未知")
        book_id = b.get("bookId", "")
        arts = get_articles(cookie, book_id, limit=per_account)
        matches = []
        for a in arts:
            text = (a["title"] + " " + a.get("summary", "")).lower()
            if kw in text:
                matches.append(a)
        if matches:
            print(f"── {mp_name} ({len(matches)} 篇) ──")
            for a in matches:
                found += 1
                t = fmt_time(a["time"])
                link = art_link(a["original_id"])
                print(f"  {t}  👍{a['like_num']}")
                print(f"  {a['title']}")
                print(f"  {link}")
                # 高亮匹配位置
                idx = a["title"].lower().find(kw)
                if idx >= 0:
                    ctx_start = max(0, idx - 15)
                    ctx_end = min(len(a["title"]), idx + len(kw) + 15)
                    snippet = a["title"][ctx_start:ctx_end]
                    print(f"  → ...{snippet}...")
                print()
            time.sleep(0.5)

    print(f"\n📊 共找到 {found} 篇匹配文章\n")


# ===== 新增: export =====

def cmd_export(cookie, book_id, output_format="md", limit=20):
    """导出文章列表"""
    mp_name = ""
    mps = get_mp_list(cookie)
    for b in mps:
        if b.get("bookId") == book_id:
            mp_name = b.get("title", "未知")
            break

    arts = get_articles(cookie, book_id, limit=limit)
    if not arts:
        print("⚠️  无文章可导出")
        return
    if not mp_name:
        mp_name = arts[0].get("mp_name", "未知公众号")

    if output_format == "json":
        out = json.dumps({
            "mp_name": mp_name,
            "book_id": book_id,
            "export_time": datetime.now().isoformat(),
            "articles": arts,
        }, ensure_ascii=False, indent=2)
        print(out)
    else:
        # Markdown
        lines = []
        lines.append(f"# {mp_name}")
        lines.append(f"")
        lines.append(f"> 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"> 文章数: {len(arts)}")
        lines.append(f"")
        for i, a in enumerate(arts, 1):
            t = fmt_time(a["time"])
            link = art_link(a["original_id"])
            lines.append(f"## {i}. {a['title']}")
            lines.append(f"")
            lines.append(f"- **时间**: {t}")
            lines.append(f"- **阅读**: 👍{a['like_num']}  👁{a.get('read_num', 0)}")
            lines.append(f"- **链接**: [{link}]({link})")
            if a["summary"]:
                lines.append(f"- **摘要**: {a['summary']}")
            lines.append(f"")
        print("\n".join(lines))


# ===== 新增: track (关键词追踪) =====

def cmd_track_add(keyword):
    state = load_state()
    if keyword not in state["keywords"]:
        state["keywords"].append(keyword)
        save_state(state)
    print(f"✅ 已添加追踪关键词: {keyword}")
    print(f"   当前关键词: {', '.join(state['keywords'])}")


def cmd_track_list():
    state = load_state()
    kws = state.get("keywords", [])
    if kws:
        print(f"\n🔍 追踪关键词 ({len(kws)}):\n")
        for i, kw in enumerate(kws, 1):
            print(f"  {i}. {kw}")
    else:
        print("⚠️  暂无追踪关键词")
    print()


def cmd_track_remove(keyword):
    state = load_state()
    if keyword in state["keywords"]:
        state["keywords"].remove(keyword)
        save_state(state)
        print(f"✅ 已移除追踪关键词: {keyword}")
    else:
        print(f"⚠️  关键词 \"{keyword}\" 不在追踪列表中")


def cmd_track_check(cookie):
    """检查所有公众号最新文章，匹配追踪关键词"""
    state = load_state()
    keywords = state.get("keywords", [])
    if not keywords:
        print("⚠️  暂无追踪关键词，先用 track add <keyword> 添加")
        return

    mps = get_mp_list(cookie)
    if not mps:
        print("⚠️  未找到公众号")
        return

    print(f"\n🔍 关键词追踪检查 — 共 {len(keywords)} 个关键词, {len(mps)} 个公众号\n")

    all_hits = []
    for b in mps:
        mp_name = b.get("title", "未知")
        book_id = b.get("bookId", "")
        arts = get_articles(cookie, book_id, limit=10)
        for a in arts:
            text = (a["title"] + " " + a.get("summary", "")).lower()
            for kw in keywords:
                if kw.lower() in text:
                    new_flag = " 🆕" if is_new(state, book_id, a["original_id"]) else ""
                    all_hits.append((kw, mp_name, a, new_flag))
                    break

    if all_hits:
        # 按关键词分组显示
        for kw in keywords:
            hits = [h for h in all_hits if h[0] == kw]
            if hits:
                print(f"  📌 [{kw}] ({len(hits)} 篇)")
                for _, mp_name, a, new_flag in hits:
                    t = fmt_time(a["time"])
                    link = art_link(a["original_id"])
                    print(f"     [{mp_name}] {t} {a['title']}{new_flag}")
                    print(f"     {link}")
                print()
        print(f"📊 共 {len(all_hits)} 篇命中")
    else:
        print("  无匹配文章")

    # 记录已扫描的文章
    for b in mps:
        book_id = b.get("bookId", "")
        arts = get_articles(cookie, book_id, limit=5)
        for a in arts:
            mark_seen(state, book_id, a["original_id"],
                      a["title"], a["time"])
    save_state(state)


# ===== 主入口 =====

VERSION = "2.0.0"


def main():
    parser = argparse.ArgumentParser(
        description="微信读书公众号工具 — 自动从浏览器提取 cookie")
    parser.add_argument("--cookie", "-c", help="手动指定 cookie (默认自动从浏览器提取)")
    parser.add_argument("--limit", "-n", type=int, default=50,
                        help="文章数量上限 (默认 50)")
    parser.add_argument("--version", "-v", action="store_true",
                        help="显示版本号")

    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("list", aliases=["l"], help="列出关注的公众号")

    p_art = sub.add_parser("articles", aliases=["a", "art"], help="获取文章列表")
    p_art.add_argument("book_id")

    p_info = sub.add_parser("info", aliases=["i"], help="查看公众号信息")
    p_info.add_argument("book_id")

    p_read = sub.add_parser("read", aliases=["r"], help="读取文章正文")
    p_read.add_argument("target")
    p_read.add_argument("--article", "-a", type=int, default=0)
    p_read.add_argument("--full", "-f", action="store_true")

    p_digest = sub.add_parser("digest", aliases=["d"], help="一键早报: 遍历所有公众号最新文章")
    p_digest.add_argument("--per", type=int, default=3, help="每个号取几篇 (默认 3)")

    p_search = sub.add_parser("search", aliases=["s"], help="跨公众号搜索文章")
    p_search.add_argument("keyword")
    p_search.add_argument("--per", type=int, default=20, help="每个号搜索深度 (默认 20)")

    p_export = sub.add_parser("export", aliases=["e"], help="导出文章列表")
    p_export.add_argument("book_id")
    p_export.add_argument("--format", "-f", choices=["md", "json"], default="md")

    # track 子命令组
    p_track = sub.add_parser("track", aliases=["t"], help="关键词追踪管理")
    track_sub = p_track.add_subparsers(dest="track_cmd", required=True)
    track_sub.add_parser("list", help="列出追踪关键词")
    p_ta = track_sub.add_parser("add", help="添加追踪关键词")
    p_ta.add_argument("keyword")
    p_tr = track_sub.add_parser("remove", aliases=["rm"], help="移除追踪关键词")
    p_tr.add_argument("keyword")
    track_sub.add_parser("check", aliases=["c"], help="检查新文章是否命中关键词")

    args, remaining = parser.parse_known_args()

    if args.version:
        print(f"weread-mp v{VERSION}")
        return

    if not args.cmd:
        parser.print_help()
        return

    # 获取 cookie
    cookie = args.cookie or os.environ.get("WEREAD_COOKIE", "")
    if not cookie:
        cookie = extract_cookies()

    # 路由
    if args.cmd in ("list", "l"):
        cmd_list(cookie)
    elif args.cmd in ("articles", "a", "art"):
        cmd_articles(cookie, args.book_id, args.limit)
    elif args.cmd in ("info", "i"):
        print("ℹ️  使用 articles 查看公众号信息")
    elif args.cmd in ("read", "r"):
        max_chars = 0 if args.full else 3000
        cmd_read(cookie, args.target, args.article, max_chars)
    elif args.cmd in ("digest", "d"):
        cmd_digest(cookie, args.per)
    elif args.cmd in ("search", "s"):
        cmd_search(cookie, args.keyword, args.per)
    elif args.cmd in ("export", "e"):
        cmd_export(cookie, args.book_id, args.format)
    elif args.cmd in ("track", "t"):
        if args.track_cmd == "list":
            cmd_track_list()
        elif args.track_cmd == "add":
            cmd_track_add(args.keyword)
        elif args.track_cmd in ("remove", "rm"):
            cmd_track_remove(args.keyword)
        elif args.track_cmd in ("check", "c"):
            cmd_track_check(cookie)


if __name__ == "__main__":
    main()
