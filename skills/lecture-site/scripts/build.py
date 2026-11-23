#!/usr/bin/env python3
"""lecture-site 빌더: 강의 원고(마크다운) -> 홈 · 본문 · 발표 덱 · 책으로 보기 · 근거 사이트.

  python3 build.py new <폴더> --title "강의 제목" [--author 이름]   뼈대 만들기
  python3 build.py check <폴더>                                    원고 점검(근거 누락, 그림 오류 등)
  python3 build.py draft-deck <폴더> [--force]                      본문에서 deck.md 초안 뽑기
  python3 build.py build <폴더> [--out 출력폴더]                     사이트 만들기(기본 <폴더>/site)
  python3 build.py serve <폴더> [--port 5180]                       화면 편집 모드(블록을 눌러 원고 수정·추가·삭제)

표준 라이브러리만 씀. 원고 형식은 references/markdown-spec.md.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import figures  # noqa: E402
from mdlite import blocks, esc, fm_offset, front_matter, heading_attrs, inline, render_simple, strip_inline, ONE_REF  # noqa: E402

ASSETS = os.path.join(SKILL, "assets")
FONT_LINK = ('<link rel="preconnect" href="https://cdn.jsdelivr.net">'
             '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">')
WARN = []
EDIT_V = 0     # 편집 모드 빌드 번호(화면이 자기 버전을 알게)
EDIT = False   # serve(화면 편집 모드)일 때만 True: 원고 줄 범위(data-src)와 편집기 스크립트를 넣음


def SRC(f, a, b, attr="data-src"):
    """편집 모드에서 원고 위치 표시: data-src="chapters/01-a.md:12-18" (0 기준, 끝 제외)"""
    if not EDIT or f is None or a is None or b is None:
        return ""
    return ' %s="%s:%d-%d"' % (attr, esc(f), a, b)


def inject(html, attr):
    """블록 HTML 의 첫 태그에 속성을 끼움"""
    return re.sub(r"^<(\w+)", lambda m: "<" + m.group(1) + attr, html, count=1) if attr else html


def warn(msg):
    WARN.append(msg)


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def write(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


# =====================================================================
# 원고 읽기
# =====================================================================
class Project:
    def __init__(self, root):
        self.root = os.path.abspath(root)
        lp = os.path.join(self.root, "lecture.md")
        if not os.path.exists(lp):
            sys.exit("lecture.md 가 없습니다: %s" % lp)
        _lt = read(lp)
        self.meta, _ = front_matter(_lt)
        self.lecture_fm = (0, fm_offset(_lt))
        self.meta.setdefault("title", "제목 없는 강의")
        self.figs = {}
        self.sources = self.load_sources()
        self.chapters = self.load_chapters()
        self.vols = self.load_vols()
        self.slides = self.load_deck()

    # ---------- 근거 ----------
    def load_sources(self):
        p = os.path.join(self.root, "sources.md")
        out = {}
        if not os.path.exists(p):
            warn("sources.md 가 없습니다. 근거 목록이 비어 있게 됩니다.")
            return out
        _txt = read(p)
        _, body = front_matter(_txt)
        off = fm_offset(_txt)
        total = len(_txt.splitlines())
        cur = None
        keymap = {"주장": "claim", "claim": "claim", "종류": "kind", "kind": "kind", "출처": "url", "url": "url",
                  "source": "url", "확인": "date", "date": "date", "메모": "memo", "note": "memo", "한계": "memo"}
        for li, line in enumerate(body.splitlines()):
            s = line.strip()
            m = re.match(r"^#{2,4}\s+([A-Za-z]+-[\w.-]+)\s*(.*)$", s)
            if m:
                if cur is not None:
                    cur["b"] = li + off
                cur = {"id": m.group(1), "claim": m.group(2).strip(), "kind": "", "url": "", "date": "", "memo": "", "a": li + off, "b": total}
                out[cur["id"]] = cur
                continue
            if re.match(r"^#{1,4}\s", s) and cur is not None:
                cur["b"] = li + off
                cur = None
                continue
            if cur is None or not s:
                continue
            s = re.sub(r"^[-*]\s+", "", s)
            if ":" in s:
                k, v = s.split(":", 1)
                if k.strip() in keymap:
                    cur[keymap[k.strip()]] = v.strip()
                    continue
            cur["claim"] = (cur["claim"] + " " + s).strip()
        return out

    # ---------- 본문 ----------
    def load_chapters(self):
        d = os.path.join(self.root, "chapters")
        if not os.path.isdir(d):
            sys.exit("chapters 폴더가 없습니다.")
        files = sorted(f for f in os.listdir(d) if f.endswith(".md") and not f.startswith("_"))
        if not files:
            sys.exit("chapters 폴더에 장 파일(.md)이 없습니다. templates/chapter.md 형식으로 하나 이상 만드세요.")
        chs = []
        for i, f in enumerate(files):
            _txt = read(os.path.join(d, f))
            meta, body = front_matter(_txt)
            off = fm_offset(_txt)
            total = len(_txt.splitlines())
            cid = meta.get("id") or chr(ord("a") + i)
            ch = {"id": cid, "n": i + 1, "file": f, "title": meta.get("title", f[:-3]), "lede": meta.get("lede", ""),
                  "vol": int(meta.get("vol", meta.get("volume", 1)) or 1), "open": [], "topics": [],
                  "src": "chapters/" + f, "fm": (0, off)}
            cur = None
            tn = 0
            for bl in blocks(body):
                bl["a"], bl["b"] = bl.get("l0", 0) + off, bl.get("l1", 0) + off
                if bl["kind"] == "h" and bl["level"] == 1:
                    continue  # 장 제목은 머리말에서
                if bl["kind"] == "h" and bl["level"] == 2:
                    t, at = heading_attrs(bl["text"])
                    tn += 1
                    cur = {"id": at.get("id") or "%s-%02d" % (cid, tn), "title": t,
                           "level": "더 깊이" if ("deep" in at["class"] or at.get("level") == "더 깊이") else "핵심",
                           "blocks": [], "h": (bl["a"], bl["b"]), "sec": [bl["a"], total]}
                    if ch["topics"]:
                        ch["topics"][-1]["sec"][1] = bl["a"]
                    ch["topics"].append(cur)
                    continue
                if bl["kind"] == "fence" and bl["info"].split()[:1] == ["fig"]:
                    parts = bl["info"].split()
                    fid = parts[1] if len(parts) > 1 else "%s-f%d" % (cur["id"] if cur else cid, len(self.figs) + 1)
                    self.add_fig(fid, bl["body"], "%s 장" % f)
                    bl = {"kind": "fig", "id": fid, "a": bl["a"], "b": bl["b"]}
                (cur["blocks"] if cur else ch["open"]).append(bl)
            chs.append(ch)
        return chs

    def add_fig(self, fid, body, where):
        if fid in self.figs:
            warn("그림 id 가 겹칩니다: %s (%s). 뒤의 것을 씁니다." % (fid, where))
        try:
            spec = figures.parse(body)
            spec["_id"] = fid
            if spec.get("type") == "illust":
                if not spec.get("prompt"):
                    warn("삽화 %s 에 prompt 가 없습니다." % fid)
                if not os.path.exists(os.path.join(self.root, figures.illust_path(spec))):
                    warn("삽화 %s 아직 없음 → python3 scripts/illust.py gen <폴더> (안 되면 illustrations.md 의 프롬프트로 직접 만들어 %s 에 저장)" % (fid, figures.illust_path(spec)))
            figures.render(spec, root=self.root)
        except Exception as e:  # noqa: BLE001
            warn("그림 %s 를 그리지 못했습니다: %s" % (fid, e))
            spec = {"type": "statement", "text": "그림 오류: %s" % fid, "rows": []}
        self.figs[fid] = spec

    def fig_svg(self, fid, narrow=False):
        spec = self.figs.get(fid)
        if not spec:
            warn("없는 그림을 불렀습니다: %s" % fid)
            return figures.render({"type": "statement", "text": "없는 그림: %s" % fid, "rows": []}, narrow)
        return figures.render(spec, narrow, self.root)

    def load_vols(self):
        vols = {}
        for ch in self.chapters:
            vols.setdefault(ch["vol"], []).append(ch)
        out = []
        for v in sorted(vols):
            out.append({"n": v, "title": self.meta.get("vol%d" % v, "%d권" % v), "chapters": vols[v]})
        return out

    # ---------- 덱 ----------
    def load_deck(self):
        p = os.path.join(self.root, "deck.md")
        self.deck_file = os.path.exists(p)
        if not self.deck_file:
            warn("deck.md 가 없어 본문에서 덱 초안을 만들어 썼습니다(draft-deck 으로 파일을 만들 수 있음).")
            text = draft_deck(self)
        else:
            text = read(p)
        _, body = front_matter(text)
        off, total = fm_offset(text), len(text.splitlines())
        slides, cur = [], None
        for bl in blocks(body):
            if bl["kind"] == "h" and bl["level"] == 2:
                if cur is not None:
                    cur["b"] = bl.get("l0", 0) + off
                t, at = heading_attrs(bl["text"])
                cur = {"title": t, "kind": at.get("kind", ""), "chapter": at.get("chapter", ""), "topic": at.get("topic", ""),
                       "fig": at.get("fig", ""), "dark": bool(at.get("dark")), "level": at.get("level", "핵심"),
                       "sub": "", "notes": [], "conds": [], "ids": [], "a": bl.get("l0", 0) + off, "b": total}
                if "deep" in at["class"]:
                    cur["level"] = "더 깊이"
                for c in at["class"]:
                    if c in ("title", "cover", "glance", "explain", "statement", "fig"):
                        cur["kind"] = c
                slides.append(cur)
                continue
            if cur is None:
                continue
            k = bl["kind"]
            if k == "fence" and bl["info"].split()[:1] == ["fig"]:
                parts = bl["info"].split()
                fid = parts[1] if len(parts) > 1 else "deck-%d" % len(slides)
                self.add_fig(fid, bl["body"], "deck.md")
                cur["fig"] = fid
            elif k == "quote":
                cur["sub"] = " ".join(b.get("text", "") for b in blocks(bl["body"]) if b["kind"] == "p")
            elif k == "list":
                cur["conds"] += bl["items"]
            elif k == "p" and re.match(r"^(근거|sources?)\s*:", bl["text"], re.I):
                cur["ids"] += re.findall(r"[A-Za-z]+-[\w.-]*\w", bl["text"].split(":", 1)[1])
            elif k == "p":
                cur["notes"].append(bl["text"])
            elif k == "h" and bl["level"] >= 3:
                pass
        chmap = {c["id"]: c for c in self.chapters}
        for s in slides:
            if not s["kind"]:
                s["kind"] = "explain" if s["fig"] else "statement"
            if s["fig"] and s["fig"] in self.figs and self.figs[s["fig"]].get("tone") == "dark":
                s["dark"] = True
            if s["kind"] == "cover":
                s["dark"] = True
                ch = chmap.get(s["chapter"])
                s["kick"] = "%d장" % ch["n"] if ch else ""
            if s["fig"] and s["fig"] not in self.figs:
                warn("덱 장 '%s' 의 그림 %s 이 없습니다." % (s["title"], s["fig"]))
        return slides


# =====================================================================
# deck.md 초안
# =====================================================================
def sentences(text, n=3):
    t = strip_inline(text)
    parts = re.split(r"(?<=[.?!다요죠])\s+", t)
    return " ".join(parts[:n])


def draft_deck(pj):
    m = pj.meta
    out = ["<!-- deck.md: 장(slide)마다 '## 제목 {속성}'. 속성: kind=title|cover|glance|explain|statement, chapter=, topic=, fig=, dark, .deep",
           "     문단 = 발표 스크립트(구어체 3문장), 목록 = 조건과 한계, '근거: F-1, F-2' = 근거, '> 한 줄' = 장 위의 부제 -->", "",
           "## %s {kind=title}" % m.get("title", ""), "", "> %s" % m.get("subtitle", ""), "",
           "오늘 이야기할 것을 한 문장으로 소개합니다.", ""]
    for ch in pj.chapters:
        out += ["## %s {kind=cover chapter=%s}" % (ch["title"], ch["id"]), "", "> %s" % ch["lede"], "",
                "이 장에서 답할 질문을 말합니다.", ""]
        for tp in ch["topics"]:
            figs = [b["id"] for b in tp["blocks"] if b["kind"] == "fig"]
            paras = [b["text"] for b in tp["blocks"] if b["kind"] == "p"]
            conds = []
            for b in tp["blocks"]:
                if b["kind"] == "div" and b["info"].startswith("cond"):
                    for bb in blocks(b["body"]):
                        if bb["kind"] == "list":
                            conds += [strip_inline(x) for x in bb["items"]]
            ids = []
            for b in tp["blocks"]:
                for x in ONE_REF.findall(json.dumps(b, ensure_ascii=False)):
                    if x not in ids:
                        ids.append(x)
            deep = " .deep" if tp["level"] == "더 깊이" else ""
            subs = [b for b in tp["blocks"] if b["kind"] == "h" and b["level"] == 3]
            # h3 로 나뉜 구간: 그림마다 그 그림이 든 구간의 문단으로 스크립트 초안
            segs, seg = [], {"title": tp["title"], "figs": [], "paras": []}
            for b in tp["blocks"]:
                if b["kind"] == "h" and b["level"] >= 3:
                    segs.append(seg)
                    seg = {"title": strip_inline(heading_attrs(b["text"])[0]), "figs": [], "paras": []}
                elif b["kind"] == "fig":
                    seg["figs"].append(b["id"])
                elif b["kind"] == "p":
                    seg["paras"].append(b["text"])
            segs.append(seg)
            items = []
            for sg in segs:
                for j, fid in enumerate(sg["figs"]):
                    items.append((sg["title"] if j == 0 else tp["title"], fid, sg["paras"] or paras))
            if not items:
                items = [(tp["title"], None, paras)]
            for k, (title, fid, src) in enumerate(items):
                kind = "glance" if k == 0 else "explain"
                attrs = "kind=%s chapter=%s topic=%s" % (kind if fid else "statement", ch["id"], tp["id"])
                if fid:
                    attrs += " fig=%s" % fid
                out += ["## %s {%s%s}" % (strip_inline(title), attrs, deep), ""]
                out += [sentences(" ".join(src)) or "발표 스크립트를 씁니다.", ""]
                if k == 0 and conds:
                    out += ["- " + c for c in conds] + [""]
                if ids:
                    out += ["근거: " + ", ".join(ids), ""]
    return "\n".join(out)


# =====================================================================
# 쪽 틀
# =====================================================================
def rel(depth):
    return "../" * depth


def head(pj, title, depth, desc="", extra=""):
    m = pj.meta
    r = rel(depth)
    full = title if title == m["title"] else "%s · %s" % (title, m["title"])
    return """<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s</title>
<meta name="description" content="%s">
<meta property="og:type" content="website"><meta property="og:title" content="%s"><meta property="og:description" content="%s">
<meta name="theme-color" content="#010102">%s
%s
<link rel="stylesheet" href="%sassets/tokens.css"><link rel="stylesheet" href="%sassets/site.css">%s
<script>(function(d){var r=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches&&!/[?&]motion=1/.test(location.search);
d.documentElement.classList.add(r?'rm':'js');setTimeout(function(){d.documentElement.classList.add('done')},4000)})(document)</script>
</head>""" % (esc(full), esc(desc or m.get("subtitle", "")), esc(full), esc(desc or m.get("subtitle", "")),
                 ('<meta name="ed-v" content="%d">' % EDIT_V) if EDIT else "", FONT_LINK, r, r, extra)


def nav(pj, depth):
    r = rel(depth)
    first = pj.chapters[0]["id"] if pj.chapters else ""
    vols = ""
    for v in pj.vols:
        lis = "".join('<li><a href="%sbooks/%d/%s/index.html"><span class="n">%d장</span><span>%s</span></a></li>' % (
            r, v["n"], c["id"], c["n"], esc(c["title"])) for c in v["chapters"])
        vols += '<div class="bm-vol"><a class="bm-v" href="%sbooks/%d/index.html"><span class="n">%d권</span><span>%s</span></a><ul>%s</ul></div>' % (
            r, v["n"], v["n"], esc(v["title"]), lis)
    return ('<a class="skip" href="#main">본문 바로 가기</a>'
            '<header class="nav bar" id="nav"><div class="wrap"><a class="mark" href="%sindex.html">%s</a>'
            '<nav aria-label="사이트"><ul class="nav-l"><li><a href="%s%s/index.html">본문</a></li>'
            '<li><a href="%sdeck/index.html">발표 덱</a></li>'
            '<li class="nav-bm"><div class="bm"><a class="bm-a" href="%sbooks/index.html">책으로 보기</a>'
            '<button type="button" class="bm-b" aria-expanded="false" aria-controls="bm-p" hidden>책으로 보기</button>'
            '<div class="bm-p" id="bm-p" hidden><div class="wrap bm-in">%s</div></div></div></li>'
            '<li><a href="%ssources/index.html">근거</a></li></ul></nav></div></header>') % (
        r, esc(pj.meta["title"]), r, first, r, r, vols, r)


def foot(pj, depth, scripts=("site.js",)):
    r = rel(depth)
    by = pj.meta.get("author", "")
    s = "".join('<script src="%sassets/%s" defer></script>' % (r, x) for x in scripts + (("edit.js",) if EDIT else ()))
    return ('<footer class="foot"><div class="wrap"><a class="mark" href="%sindex.html">%s</a>%s</div></footer>%s</body></html>' % (
        r, esc(pj.meta["title"]), ('<p class="by">지은이 %s</p>' % esc(by)) if by else "", s))


def figure_html(pj, fid, extra=""):
    if pj.figs.get(fid, {}).get("type") in ("image", "illust"):   # 사진·삽화는 한 벌만(용량 두 배 방지)
        return '<figure class="plate fig" data-fig="%s" data-reveal%s><div class="fa">%s</div></figure>' % (esc(fid), extra, pj.fig_svg(fid))
    return '<figure class="plate fig" data-fig="%s" data-reveal%s><div class="fw">%s</div><div class="fn">%s</div></figure>' % (
        esc(fid), extra, pj.fig_svg(fid), pj.fig_svg(fid, True))


# =====================================================================
# 본문 쪽
# =====================================================================
class Refs:
    def __init__(self, pj, ch, depth=1):
        self.pj, self.ch, self.order, self.depth = pj, ch, [], depth

    def cb(self, rid):
        if rid not in self.order:
            self.order.append(rid)
            if rid not in self.pj.sources:
                warn("%s장: 근거 목록에 없는 id %s" % (self.ch["n"], rid))
            self.pj.used.setdefault(rid, [])
            if self.ch["id"] not in self.pj.used[rid]:
                self.pj.used[rid].append(self.ch["id"])
        n = self.order.index(rid) + 1
        return n, "#r-%d" % n


def src_meta(pj, s, depth, with_link=True):
    r = rel(depth)
    url = s.get("url", "")
    parts = []
    if s.get("kind"):
        parts.append('<span class="m-kind">%s</span>' % esc(s["kind"]))
    if url:
        if url.startswith("http"):
            short = re.sub(r"^https?://(www\.)?", "", url)
            parts.append('<a href="%s" rel="noopener">%s</a>' % (esc(url), esc(short)))
        else:
            parts.append(esc(url))
    if s.get("date"):
        parts.append("%s 확인" % esc(s["date"]))
    if with_link:
        parts.append('<a href="%ssources/index.html#%s">근거 목록에서 보기</a>' % (r, esc(s["id"])))
    return '<span aria-hidden="true"> · </span>'.join(parts)


def render_blocks(pj, bls, refs):
    out = []
    prose = []

    def flush():
        if prose:
            out.append('<div class="prose">%s</div>' % "".join(prose))
            prose.clear()

    for b in bls:
        k = b["kind"]
        sa = SRC(refs.ch.get("src"), b.get("a"), b.get("b"))
        if k == "fig":
            flush()
            out.append(figure_html(pj, b["id"], sa))
        elif k == "h" and b["level"] >= 3:
            flush()
            t, at = heading_attrs(b["text"])
            out.append('<h3 class="sub" data-reveal%s>%s</h3>' % (sa, inline(t, refs.cb)))
        elif k == "div":
            flush()
            info = b["info"]
            name = info.split()[0] if info else "note"
            label = info[len(name):].strip()
            inner = "".join(render_simple(x, refs.cb) for x in blocks(b["body"]))
            if name == "cond":
                out.append('<details class="cond"%s><summary>%s</summary><div class="cond-b">%s</div></details>' % (
                    sa, esc(label or "조건과 한계"), inner))
            elif name in ("tip", "note", "warn", "key"):
                out.append('<aside class="call call-%s" data-reveal%s>%s%s</aside>' % (
                    name, sa, ('<p class="call-h">%s</p>' % esc(label)) if label else "", inner))
            else:
                out.append('<div class="box"%s>%s</div>' % (sa, inner))
        else:
            prose.append(inject(render_simple(b, refs.cb), sa))
    flush()
    return "".join(out)


def page_chapter(pj, ch, i):
    depth = 1
    refs = Refs(pj, ch, depth)
    rail = "".join('<li><a href="#%s">%s</a></li>' % (t["id"], esc(strip_inline(t["title"]))) for t in ch["topics"])
    topics = ""
    for t in ch["topics"]:
        lv = '<p class="lv">더 깊이</p>' if t["level"] == "더 깊이" else ""
        topics += ('<article class="topic" id="%s" aria-labelledby="h-%s"%s><header class="topic-head" data-reveal>%s'
                   '<h2 class="topic-h" id="h-%s"%s>%s</h2></header>%s</article>') % (
            t["id"], t["id"], SRC(ch["src"], t["sec"][0], t["sec"][1], "data-sec"), lv, t["id"],
            SRC(ch["src"], t["h"][0], t["h"][1]), inline(t["title"], refs.cb), render_blocks(pj, t["blocks"], refs))
    opening = render_blocks(pj, ch["open"], refs).replace('<div class="prose">', '<div class="prose open" data-reveal>', 1)
    reflist = ""
    for n, rid in enumerate(refs.order, 1):
        s = pj.sources.get(rid, {"id": rid, "claim": "근거 목록(sources.md)에 없는 id 입니다.", "kind": "확인 필요"})
        reflist += '<li id="r-%d"><span class="rn">%d</span><div><p class="claim">%s</p><p class="meta">%s</p></div></li>' % (
            n, n, inline(s["claim"]), src_meta(pj, s, depth))
    refsec = ('<section class="refs" aria-labelledby="h-refs"><h2 class="topic-h" id="h-refs">이 장의 근거</h2><ol>%s</ol></section>' % reflist) if reflist else ""
    prev = pj.chapters[i - 1] if i > 0 else None
    nxt = pj.chapters[i + 1] if i + 1 < len(pj.chapters) else None
    pn = '<nav class="pn" aria-label="장 이동">'
    if prev:
        pn += '<a class="pn-a pn-prev" href="../%s/index.html"><span class="pn-k">이전 장 · %d장</span><span class="pn-t">%s</span></a>' % (prev["id"], prev["n"], esc(prev["title"]))
    if nxt:
        pn += '<a class="pn-a pn-next" href="../%s/index.html"><span class="pn-k">다음 장 · %d장</span><span class="pn-t">%s</span></a>' % (nxt["id"], nxt["n"], esc(nxt["title"]))
    pn += "</nav>"
    tocm = '<details class="toc-m"><summary>이 장에서 볼 것</summary><ol>%s</ol></details>' % rail
    html = head(pj, "%d장 %s" % (ch["n"], ch["title"]), depth, ch["lede"]) + '<body class="p-chunk">' + nav(pj, depth)
    html += ('<main id="main" class="wrap ch"><aside class="rail" aria-label="%d장 안의 꼭지"><a class="rail-ch" href="#top">%d장 %s</a><ol>%s</ol></aside>'
             '<div class="doc"><header class="doc-head" id="top"%s><p class="kick"><a href="../books/%d/index.html">%d권</a><span aria-hidden="true"> · </span>%d장</p>'
             '<h1 class="doc-h"><span class="mask"><span class="mask-in">%s</span></span></h1>%s'
             '<p class="chview"><a href="../books/%d/%s/index.html">이 장을 책으로 보기</a><a href="../deck/index.html#%s">이 장을 덱으로 보기</a></p>%s</header>'
             '%s%s%s%s</div></main>') % (
        ch["n"], ch["n"], esc(ch["title"]), rail, SRC(ch["src"], ch["fm"][0], ch["fm"][1]), ch["vol"], ch["vol"], ch["n"], esc(ch["title"]),
        ('<p class="lede">%s</p>' % esc(ch["lede"])) if ch["lede"] else "", ch["vol"], ch["id"], pj.deck_start.get(ch["id"], 1), tocm,
        opening, topics, refsec, pn)
    html += foot(pj, depth)
    ch["ref_order"] = refs.order
    return html


# =====================================================================
# 발표 덱(파일 하나로 자립)
# =====================================================================
def page_deck(pj):
    secs = []
    for s in pj.slides:
        cls = ["slide"]
        if s["dark"]:
            cls.append("dark")
        kind = s["kind"]
        attrs = 'data-kind="%s" data-chunk="%s" data-topic="%s" data-level="%s"' % (
            kind, esc(s["chapter"] or ""), esc(s["topic"] or ""), esc(s["level"]))
        notes = "".join("<p>%s</p>" % inline(n) for n in s["notes"])
        if s["conds"]:
            notes += "<h4>조건과 한계</h4><ul>%s</ul>" % "".join("<li>%s</li>" % inline(c) for c in s["conds"])
        if s["ids"]:
            notes += '<p class="ids">근거 %s</p>' % esc(", ".join(s["ids"]))
        aside = '<aside class="notes">%s</aside>' % notes
        if kind == "title":
            cls.append("titlecard")
            inner = '<div class="tc"><h1 data-anim>%s</h1>%s%s</div>' % (
                esc(s["title"]), ('<p class="tag" data-anim>%s</p>' % inline(s["sub"])) if s["sub"] else "",
                ('<p class="by">%s</p>' % esc(pj.meta.get("author", ""))) if pj.meta.get("author") else "")
        elif kind == "cover":
            cls.append("cover")
            inner = '<div class="cv"><p class="kick" data-anim>%s</p><h1 data-anim>%s</h1>%s</div>' % (
                esc(s.get("kick", "")), esc(s["title"]), ('<p class="q" data-anim>%s</p>' % inline(s["sub"])) if s["sub"] else "")
        elif not s["fig"]:
            cls.append("nofig")
            inner = '<h1 data-anim>%s</h1>%s' % (esc(s["title"]), ('<p class="q" data-anim>%s</p>' % inline(s["sub"])) if s["sub"] else "")
        else:
            inner = '<h1 data-title data-anim>%s</h1>%s<div class="fig" data-anim>%s</div>' % (
                esc(s["title"]), ('<p class="sub" data-anim>%s</p>' % inline(s["sub"])) if s["sub"] else "", pj.fig_svg(s["fig"]))
        if pj.deck_file:
            attrs += SRC("deck.md", s.get("a"), s.get("b"))
        secs.append('<section class="%s" %s>%s%s</section>' % (" ".join(cls), attrs, inner, aside))
    css = read(os.path.join(ASSETS, "deck.css"))
    js = read(os.path.join(ASSETS, "deck.js"))
    return ("""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s · 발표 덱</title>%s%s<style>%s</style></head>
<body><div id="stage">%s<div id="edge"></div><div id="bar"></div><div id="num"></div><div id="notesPanel"></div></div>
<a id="home" href="../index.html" aria-label="강의 첫 화면">%s</a>
<div id="help" hidden><p>→ Space 다음 · ← 이전 · 숫자+Enter 이동 · N 발표자 노트 · F 전체 화면 · ? 도움말</p></div>
<script>%s</script>%s</body></html>""") % (esc(pj.meta["title"]), ('<meta name="ed-v" content="%d">' % EDIT_V) if EDIT else "", FONT_LINK, css, "\n".join(secs), esc(pj.meta["title"]), js,
                                         ('<script>%s</script>' % read(os.path.join(ASSETS, "edit.js"))) if EDIT else "")


# =====================================================================
# 책
# =====================================================================
def cover_svg(pj, v):
    pals = [("#123A63", "#3378AD", "#7FB2D9"), ("#0E6E62", "#2F8F80", "#CFE5E0"), ("#0B1F33", "#C2662E", "#9DB3C9"),
            ("#3B2F6B", "#5E6AD2", "#B9C0F2")]
    a, b, c = pals[(v["n"] - 1) % len(pals)]
    W, H = 400, 560
    lines = figures.wrap(v["title"], 34, W - 80, 800)
    t = "".join('<text x="40" y="%d" font-size="34" font-weight="800" fill="#F3F6FA" letter-spacing="-1">%s</text>' % (
        150 + i * 44, esc(x)) for i, x in enumerate(lines))
    bars = ""
    for i in range(7):
        w = [300, 220, 260, 140, 320, 180, 240][(i + v["n"]) % 7]
        bars += '<rect x="40" y="%d" width="%d" height="12" rx="2" fill="%s" opacity="%.2f"/>' % (292 + i * 22, w, b if i % 3 else c, 0.9 - i * 0.09)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" font-family="Pretendard, sans-serif">'
            '<rect width="%d" height="%d" fill="%s"/><rect width="10" height="%d" fill="%s"/>'
            '<text x="40" y="84" font-size="22" font-weight="700" fill="%s">%d권</text>%s%s'
            '<text x="40" y="500" font-size="20" font-weight="600" fill="#F3F6FA" opacity=".9">%s</text>'
            '<text x="40" y="528" font-size="15" font-weight="500" fill="%s">%s</text></svg>') % (
        W, H, W, H, a, H, b, c, v["n"], t, bars, esc(pj.meta["title"]), c, esc(pj.meta.get("author", "")))


def book_source(pj, v):
    """권 하나의 원고를 <template> 안에 넣음. book.js 가 A5 쪽으로 나눔."""
    out = []
    for ch in v["chapters"]:
        refs = Refs(pj, ch, 3)
        body = render_blocks(pj, ch["open"], refs)
        for t in ch["topics"]:
            body += '<h2 class="b-h2">%s</h2>' % inline(t["title"], refs.cb)
            body += render_blocks(pj, t["blocks"], refs)
        notes = ""
        for n, rid in enumerate(refs.order, 1):
            s = pj.sources.get(rid, {"claim": rid, "kind": ""})
            notes += "<li><span>%d</span> %s%s</li>" % (n, esc(strip_inline(s["claim"])), (" (%s)" % esc(s.get("kind"))) if s.get("kind") else "")
        if notes:
            body += '<h3 class="b-notes-h">근거</h3><ol class="b-notes">%s</ol>' % notes
        # 책에서는 접는 단을 펼친 상자로, 화면용 속성은 뺌
        body = re.sub(r"<details class=\"cond\"><summary>(.*?)</summary><div class=\"cond-b\">", r'<div class="b-cond"><p class="b-cond-h">\1</p><div>', body)
        body = body.replace("</div></details>", "</div></div>").replace(" data-reveal", "")
        body = re.sub(r'<div class="fn">.*?</div></figure>', "</figure>", body, flags=re.S)
        out.append('<section data-ch="%s" data-title="%d장 %s"><p class="b-kick">%d장</p><h1 class="b-h1">%s</h1>%s%s</section>' % (
            ch["id"], ch["n"], esc(ch["title"]), ch["n"], esc(ch["title"]),
            ('<p class="b-lede">%s</p>' % esc(ch["lede"])) if ch["lede"] else "", body))
    return "".join(out)


def page_books(pj):
    depth = 1
    vols = ""
    for v in pj.vols:
        chs = "".join('<li><span class="chn">%d장</span><a class="chname" href="%d/%s/index.html">%s</a></li>' % (
            c["n"], v["n"], c["id"], esc(c["title"])) for c in v["chapters"])
        vols += ('<article class="vol" data-reveal><a class="vol-cover" href="%d/index.html"><img src="../assets/cover-%d.svg" width="400" height="560" alt="%d권 표지: %s"></a>'
                 '<p class="vol-no">%d권</p><h2><a href="%d/index.html">%s</a></h2><ol class="chs">%s</ol></article>') % (
            v["n"], v["n"], v["n"], esc(v["title"]), v["n"], v["n"], esc(v["title"]), chs)
    html = head(pj, "책으로 보기", depth) + '<body class="p-books">' + nav(pj, depth)
    html += '<main id="main"><header class="chead wrap"><h1 class="t2">책으로 보기</h1><p class="t3">%d권 · 인쇄하면 A5 책 그대로 PDF가 됩니다</p></header><div class="shelf-l wrap">%s</div></main>' % (len(pj.vols), vols)
    return html + foot(pj, depth)


def page_volume(pj, v, ch=None):
    depth = 3 if ch else 2
    r = rel(depth)
    book_extra = '<link rel="stylesheet" href="%sassets/book.css">' % r
    data = {"vol": v["n"], "title": v["title"], "lecture": pj.meta["title"], "author": pj.meta.get("author", ""),
            "date": pj.meta.get("date", ""), "only": ch["id"] if ch else "",
            "chapters": [{"id": c["id"], "n": c["n"], "title": c["title"]} for c in v["chapters"]]}
    tmpl = '<template id="bk-src">%s</template><script type="application/json" id="bk-data">%s</script>' % (
        book_source(pj, v), json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    cover = '<img class="bk-cover-img" src="%sassets/cover-%d.svg" alt="">' % (r, v["n"])
    if ch:
        idx = v["chapters"].index(ch)
        title = "%d권 %d장 %s" % (v["n"], ch["n"], ch["title"])
        top = ('<header class="chead vhead wrap"><p class="kick"><a href="../index.html">%d권</a> · %d장</p><h1 class="t2">%s</h1>'
               '<p class="chview"><a href="%s%s/index.html">이 장을 본문으로 읽기</a><button type="button" class="btn ghost" data-print>인쇄 · PDF로 저장</button></p></header>') % (
            v["n"], ch["n"], esc(ch["title"]), r, ch["id"])
        moves = '<nav class="vmoves wrap" aria-label="장 이동"><a class="vm" href="../index.html"><span class="vm-k">권 첫머리</span><span class="vm-n">%d권 %s</span></a>' % (v["n"], esc(v["title"]))
        if idx + 1 < len(v["chapters"]):
            nx = v["chapters"][idx + 1]
            moves += '<a class="vm vm-next" href="../%s/index.html"><span class="vm-k">다음 장 · %d장</span><span class="vm-n">%s</span></a>' % (nx["id"], nx["n"], esc(nx["title"]))
        moves += "</nav>"
    else:
        title = "%d권 %s" % (v["n"], v["title"])
        chs = "".join('<li><span class="chn">%d장</span><a class="chname" href="%s/index.html">%s</a><span class="chone">%s</span></li>' % (
            c["n"], c["id"], esc(c["title"]), esc(c["lede"])) for c in v["chapters"])
        top = ('<header class="bk-head wrap">%s<div><p class="vol-no">%d권</p><h1 class="t2">%s</h1><ol class="chs">%s</ol>'
               '<p class="acts"><a class="btn" href="%s/index.html">%d장부터 보기 <span aria-hidden="true">→</span></a>'
               '<button type="button" class="btn ghost" data-print>인쇄 · PDF로 저장</button></p></div></header>') % (
            cover, v["n"], esc(v["title"]), chs, v["chapters"][0]["id"], v["chapters"][0]["n"])
        moves = ""
    viewer = ('<section class="viewer wrap" aria-label="쪽 넘겨 보기"><div class="flip-top"><p class="flip-n" aria-live="polite">쪽을 나누는 중…</p>'
              '<p class="flip-go"><button type="button" class="btn ghost" data-go="-1">이전 쪽</button><button type="button" class="btn ghost" data-go="1">다음 쪽</button></p></div>'
              '<ol class="flip" tabindex="0" aria-label="책 쪽, 옆으로 넘겨 봄"></ol></section>')
    html = head(pj, title, depth, extra=book_extra) + '<body class="p-book%s">' % (" p-view" if ch else "") + nav(pj, depth)
    html += '<main id="main">%s%s%s</main>%s' % (top, viewer, moves, tmpl)
    return html + foot(pj, depth, ("site.js", "book.js"))


# =====================================================================
# 근거 쪽
# =====================================================================
def page_sources(pj):
    depth = 1
    chmap = {c["id"]: c for c in pj.chapters}
    groups = {c["id"]: [] for c in pj.chapters}
    rest = []
    for sid, s in pj.sources.items():
        used = pj.used.get(sid, [])
        (groups[used[0]] if used and used[0] in groups else rest).append(s)
    secs = ""

    def item(s):
        used = pj.used.get(s["id"], [])
        uses = ", ".join('<a href="../%s/index.html">%d장 %s</a>' % (u, chmap[u]["n"], esc(chmap[u]["title"])) for u in used if u in chmap)
        meta = src_meta(pj, s, depth, False)
        if uses:
            meta += '<span aria-hidden="true"> · </span><span class="m-used">쓰인 곳 %s</span>' % uses
        memo = ('<p class="memo">%s</p>' % inline(s["memo"])) if s.get("memo") else ""
        return ('<li id="%s"' + SRC("sources.md", s.get("a"), s.get("b")).replace("%", "%%") + '><p class="sid">%s</p><div><p class="claim">%s</p>%s<p class="meta">%s</p></div></li>') % (
            esc(s["id"]), esc(s["id"]), inline(s["claim"]), memo, meta)

    for c in pj.chapters:
        if groups[c["id"]]:
            secs += '<section class="wrap src-ch" aria-labelledby="h-src-%s"><h2 class="src-ch-h" id="h-src-%s">%d장 %s</h2><ol class="src-list">%s</ol></section>' % (
                c["id"], c["id"], c["n"], esc(c["title"]), "".join(item(s) for s in groups[c["id"]]))
    if rest:
        secs += '<section class="wrap src-ch"><h2 class="src-ch-h">그 밖의 근거</h2><ol class="src-list">%s</ol></section>' % "".join(item(s) for s in rest)
    lede = pj.meta.get("sources_lede", "이 자료의 사실 문장이 기대는 근거 전체입니다. 공식 문서는 확인한 날짜를, 직접 잰 값은 잰 날짜를 적었습니다.")
    html = head(pj, "근거 목록", depth) + '<body class="p-sources">' + nav(pj, depth)
    html += '<main id="main"><header class="chead wrap"><h1 class="t2">근거 목록</h1><p class="src-lede">%s</p><p class="src-count">근거 %d개</p></header>%s</main>' % (
        esc(lede), len(pj.sources), secs)
    return html + foot(pj, depth)


# =====================================================================
# 홈
# =====================================================================
def page_home(pj):
    m = pj.meta
    first = pj.chapters[0]
    hero_bg = ""
    if m.get("hero") and os.path.exists(os.path.join(pj.root, m["hero"])):
        hero_bg = '<img class="bg" src="assets/%s" alt="">' % os.path.basename(m["hero"])
    else:
        fid = next((s["fig"] for s in pj.slides if s["fig"]), None)
        if fid:
            hero_bg = '<div class="bg bg-fig">%s</div>' % pj.fig_svg(fid)
    toc = "".join('<li><a href="%s/index.html">%s</a></li>' % (c["id"], esc(c["title"])) for c in pj.chapters)
    ffig = next((b["id"] for t in first["topics"] for b in t["blocks"] if b["kind"] == "fig"), None)
    read_prev = ('<div class="mini-doc"><p class="mini-kick">1장</p><p class="mini-h">%s</p>%s</div>' % (
        esc(first["title"]), ('<div class="plate mini-fig">%s</div>' % pj.fig_svg(ffig)) if ffig else ""))
    dslide = next((s for s in pj.slides if s["fig"] and not s["dark"]), None) or next((s for s in pj.slides if s["fig"]), None)
    deck_prev = ('<div class="mini-slide%s"><p class="ms-h">%s</p><div class="ms-fig">%s</div></div>' % (
        " dark" if dslide["dark"] else "", esc(dslide["title"]), pj.fig_svg(dslide["fig"]))) if dslide else ""
    shelf = "".join('<li><a href="books/%d/index.html"><img src="assets/cover-%d.svg" width="400" height="560" alt="%d권 표지: %s" loading="lazy"></a></li>' % (
        v["n"], v["n"], v["n"], esc(v["title"])) for v in pj.vols)
    html = head(pj, m["title"], 0) + '<body class="p-home">' + nav(pj, 0)
    html += """<main id="main">
<section class="hero" aria-labelledby="h-hero"%s><div class="bgwrap" aria-hidden="true">%s</div>
<div class="hero-in"><h1 id="h-hero"><span class="mask"><span class="mask-in">%s</span></span></h1>
<p class="line" data-in="blur">%s</p><a class="btn" href="%s/index.html" data-in="rise">%s <span aria-hidden="true">→</span></a></div></section>
<section class="sec learn" aria-labelledby="h-learn"><div class="wrap"><h2 class="learn-h" id="h-learn" data-reveal>%s</h2><ol class="toc">%s</ol></div></section>
<section class="sec" aria-labelledby="h-read"><div class="wrap"><div class="sec-h" data-reveal><h2 class="t2" id="h-read">본문 읽기</h2><a class="go" href="%s/index.html">본문 열기 <span aria-hidden="true">→</span></a></div>
<figure class="frame media" data-media>%s</figure></div></section>
<section class="sec" aria-labelledby="h-deck"><div class="wrap"><div class="sec-h" data-reveal><h2 class="t2" id="h-deck">발표 덱</h2><a class="go" href="deck/index.html">덱 열기 <span aria-hidden="true">→</span></a></div>
<figure class="frame media" data-media>%s</figure></div></section>
<section class="sec" aria-labelledby="h-book"><div class="sec-h wrap" data-reveal><h2 class="t2" id="h-book">책으로 보기</h2><a class="go" href="books/index.html">책 열기 <span aria-hidden="true">→</span></a></div>
<ul class="shelf" data-media>%s</ul></section>
<section class="sec" aria-labelledby="h-proof"><div class="sec-h wrap" data-reveal><h2 class="t2" id="h-proof">모든 수치는 근거 %d개에 연결</h2><a class="go" href="sources/index.html">근거 목록 <span aria-hidden="true">→</span></a></div></section>
</main>""" % (SRC("lecture.md", pj.lecture_fm[0], pj.lecture_fm[1]), hero_bg, esc(m["title"]), esc(m.get("subtitle", "")), first["id"], esc(m.get("cta", "1장부터 읽기")),
              esc(m.get("toc_label", "%d개의 장" % len(pj.chapters))), toc, first["id"], read_prev, deck_prev, shelf, len(pj.sources))
    return html + foot(pj, 0)


# =====================================================================
# 명령
# =====================================================================
def deck_starts(pj):
    out = {}
    for i, s in enumerate(pj.slides):
        if s["chapter"] and s["chapter"] not in out:
            out[s["chapter"]] = i + 1
    return out


def check(pj):
    pj.used = {}
    pj.deck_start = deck_starts(pj)
    for i, ch in enumerate(pj.chapters):
        page_chapter(pj, ch, i)
        if not ch["topics"]:
            warn("%d장 %s: 꼭지(## 제목)가 없습니다." % (ch["n"], ch["title"]))
        for t in ch["topics"]:
            if not any(b["kind"] == "fig" for b in t["blocks"]):
                warn("%d장 꼭지 '%s': 그림이 없습니다(덱에서는 큰 문장 장이 됨)." % (ch["n"], strip_inline(t["title"])))
    for s in pj.slides:
        if s["kind"] not in ("title", "cover") and not s["notes"]:
            warn("덱 '%s': 발표 스크립트(문단)가 없습니다." % s["title"])
        for rid in s["ids"]:
            if rid not in pj.sources:
                warn("덱 '%s': 근거 목록에 없는 id %s" % (s["title"], rid))
    unused = [k for k in pj.sources if k not in pj.used]
    if unused:
        warn("본문에서 쓰지 않은 근거 %d개: %s" % (len(unused), ", ".join(unused[:12]) + (" …" if len(unused) > 12 else "")))
    return {"chapters": len(pj.chapters), "topics": sum(len(c["topics"]) for c in pj.chapters), "figures": len(pj.figs),
            "slides": len(pj.slides), "sources": len(pj.sources), "volumes": len(pj.vols)}


def build(pj, out):
    stats = check(pj)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, "assets"))
    for f in ("tokens.css", "site.css", "book.css", "site.js", "book.js") + (("edit.js",) if EDIT else ()):
        shutil.copy(os.path.join(ASSETS, f), os.path.join(out, "assets", f))
    if pj.meta.get("hero") and os.path.exists(os.path.join(pj.root, pj.meta["hero"])):
        shutil.copy(os.path.join(pj.root, pj.meta["hero"]), os.path.join(out, "assets"))
    for v in pj.vols:
        write(os.path.join(out, "assets", "cover-%d.svg" % v["n"]), cover_svg(pj, v))
    write(os.path.join(out, "index.html"), page_home(pj))
    for i, ch in enumerate(pj.chapters):
        write(os.path.join(out, ch["id"], "index.html"), page_chapter(pj, ch, i))
    write(os.path.join(out, "deck", "index.html"), page_deck(pj))
    write(os.path.join(out, "books", "index.html"), page_books(pj))
    for v in pj.vols:
        write(os.path.join(out, "books", str(v["n"]), "index.html"), page_volume(pj, v))
        for ch in v["chapters"]:
            write(os.path.join(out, "books", str(v["n"]), ch["id"], "index.html"), page_volume(pj, v, ch))
    write(os.path.join(out, "sources", "index.html"), page_sources(pj))
    return stats


TEMPLATES = os.path.join(SKILL, "templates")


def cmd_new(a):
    root = os.path.abspath(a.dir)
    if os.path.exists(os.path.join(root, "lecture.md")):
        sys.exit("이미 강의 폴더입니다: %s" % root)
    os.makedirs(os.path.join(root, "chapters"), exist_ok=True)
    today = datetime.date.today().isoformat()
    for src, dst in (("lecture.md", "lecture.md"), ("plan.md", "plan.md"), ("chapter.md", "chapters/01-a.md"),
                     ("sources.md", "sources.md")):
        t = read(os.path.join(TEMPLATES, src))
        t = t.replace("{{title}}", a.title).replace("{{author}}", a.author or "").replace("{{date}}", today)
        write(os.path.join(root, dst), t)
    print("만들었습니다: %s\n다음: plan.md 로 기획 → chapters/*.md · sources.md 작성 → draft-deck → build" % root)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new"); p.add_argument("dir"); p.add_argument("--title", required=True); p.add_argument("--author", default="")
    p = sub.add_parser("check"); p.add_argument("dir")
    p = sub.add_parser("draft-deck"); p.add_argument("dir"); p.add_argument("--force", action="store_true")
    p = sub.add_parser("build"); p.add_argument("dir"); p.add_argument("--out")
    p = sub.add_parser("serve", help="화면 편집 모드(블록을 눌러 원고를 고침)"); p.add_argument("dir"); p.add_argument("--port", default="5180")
    a = ap.parse_args()
    if a.cmd == "serve":
        import serve
        sys.argv = ["serve.py", a.dir, "--port", str(a.port)]
        return serve.main()
    if a.cmd == "new":
        return cmd_new(a)
    if a.cmd == "draft-deck":
        dp = os.path.join(a.dir, "deck.md")
        if os.path.exists(dp) and not a.force:
            sys.exit("deck.md 가 이미 있습니다. 덮어쓰려면 --force")
        if os.path.exists(dp):
            os.replace(dp, dp + ".bak")
            print("기존 deck.md 를 deck.md.bak 으로 옮겼습니다.")
        pj = Project(a.dir)
        write(dp, draft_deck(pj))
        print("deck.md 초안을 만들었습니다(%d장). 스크립트 문장을 구어체로 다듬으세요." % read(dp).count("\n## "))
        return
    pj = Project(a.dir)
    if a.cmd == "check":
        stats = check(pj)
    else:
        out = os.path.abspath(a.out or os.path.join(pj.root, "site"))
        stats = build(pj, out)
        print("사이트를 만들었습니다: %s/index.html" % out)
    print("장 %(chapters)d · 꼭지 %(topics)d · 그림 %(figures)d · 덱 %(slides)d장 · 근거 %(sources)d · 권 %(volumes)d" % stats)
    seen = []
    for w in WARN:
        if w not in seen:
            seen.append(w)
    if seen:
        print("\n확인할 것 %d건:" % len(seen))
        for w in seen:
            print("  - " + w)
    else:
        print("확인할 것 없음.")


if __name__ == "__main__":
    main()
