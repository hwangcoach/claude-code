"""작은 마크다운 변환기. 표준 라이브러리만 씀(Claude Code, Cowork 어디서나 돎).

지원: 머리말(flat key: value), 문단, # 제목, **굵게**, *기울임*, `코드`, [링크](url),
- / 1. 목록, ``` 코드 블록, > 인용, 각주형 근거 [^F-1001], ::: 블록(호출 쪽에서 처리).
"""
import html
import re

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.S)


def front_matter(text):
    """'---' 사이의 key: value 를 dict 로. 값의 따옴표는 벗김. 중첩은 지원하지 않음(일부러 평평하게)."""
    m = FM_RE.match(text)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        meta[k.strip()] = v
    return meta, text[m.end():]


def esc(s):
    return html.escape(str(s), quote=True)


REF_RE = re.compile(r"((?:\[\^[A-Za-z0-9_.-]+\])+)")
ONE_REF = re.compile(r"\[\^([A-Za-z0-9_.-]+)\]")


def inline(text, ref_cb=None):
    """한 줄 안의 꾸밈. ref_cb(id) -> (번호, href) 를 주면 [^id] 를 위첨자 링크로 바꿈."""
    codes = []

    def keep_code(m):
        codes.append(m.group(1))
        return "\x00%d\x00" % (len(codes) - 1)

    t = re.sub(r"`([^`]+)`", keep_code, text)
    refs = []

    def keep_ref(m):
        refs.append(ONE_REF.findall(m.group(1)))
        return "\x01%d\x01" % (len(refs) - 1)

    t = REF_RE.sub(keep_ref, t)
    links = []

    def keep_link(m):
        links.append((m.group(1), m.group(2)))
        return "\x02%d\x02" % (len(links) - 1)

    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", keep_link, t)
    t = esc(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)

    def put_link(m):
        label, url = links[int(m.group(1))]
        ext = url.startswith("http")
        return '<a href="%s"%s>%s</a>' % (esc(url), ' rel="noopener"' if ext else "", inline(label))

    t = re.sub(r"\x02(\d+)\x02", put_link, t)

    def put_ref(m):
        ids = refs[int(m.group(1))]
        if not ref_cb:
            return ""
        parts = []
        for rid in ids:
            n, href = ref_cb(rid)
            parts.append('<a href="%s" aria-label="근거 %s">%s</a>' % (href, n, n))
        return '<sup class="ref">' + ", ".join(parts) + "</sup>"

    t = re.sub(r"\x01(\d+)\x01", put_ref, t)
    t = re.sub(r"\x00(\d+)\x00", lambda m: "<code>%s</code>" % esc(codes[int(m.group(1))]), t)
    return t


def strip_inline(text):
    """꾸밈과 근거 표시를 뺀 맨 글자(제목 slug, alt 용)."""
    t = ONE_REF.sub("", text)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"[*`]", "", t)
    return t.strip()


ATTR_RE = re.compile(r"\s*\{([^{}]*)\}\s*$")


def heading_attrs(text):
    """'제목 {#id .deep kind=glance dark}' -> ('제목', {'id':..., 'class':[...], 'kind':..., 'dark':True})"""
    m = ATTR_RE.search(text)
    attrs = {"class": []}
    if not m:
        return text.strip(), attrs
    for tok in re.findall(r'[^\s"]+="[^"]*"|\S+', m.group(1)):
        if tok.startswith("#"):
            attrs["id"] = tok[1:]
        elif tok.startswith("."):
            attrs["class"].append(tok[1:])
        elif "=" in tok:
            k, v = tok.split("=", 1)
            attrs[k] = v.strip('"')
        else:
            attrs[tok] = True
    return text[: m.start()].strip(), attrs


def blocks(text):
    """마크다운을 블록 목록으로 나눔. 각 블록은 dict(kind=...)."""
    lines = text.splitlines()
    out, i, n = [], 0, len(lines)
    last, start = 0, 0
    while i < n:
        if len(out) > last:          # 앞 반복에서 블록 하나가 끝남: 원고 줄 범위 [l0, l1) 기록(화면 편집기가 씀)
            out[-1]["l0"], out[-1]["l1"] = start, i
            last = len(out)
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue
        start = i
        if s.startswith("<!--"):
            while i < n and "-->" not in lines[i]:
                i += 1
            i += 1
            continue
        if s.startswith("```"):
            info = s[3:].strip()
            body = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
            i += 1
            out.append({"kind": "fence", "info": info, "body": "\n".join(body)})
            continue
        if s.startswith(":::"):
            info = s[3:].strip()
            body = []
            i += 1
            while i < n and lines[i].strip() != ":::":
                body.append(lines[i])
                i += 1
            i += 1
            out.append({"kind": "div", "info": info, "body": "\n".join(body)})
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            out.append({"kind": "h", "level": len(m.group(1)), "text": m.group(2)})
            i += 1
            continue
        if re.match(r"^(-{3,}|\*{3,})$", s):
            out.append({"kind": "hr"})
            i += 1
            continue
        if re.match(r"^([-*+]|\d+[.)])\s+", s):
            ordered = bool(re.match(r"^\d", s))
            items = []
            while i < n and lines[i].strip():
                t = lines[i].strip()
                mm = re.match(r"^([-*+]|\d+[.)])\s+(.*)$", t)
                if mm:
                    items.append(mm.group(2))
                elif items:
                    items[-1] += " " + t
                i += 1
            out.append({"kind": "list", "ordered": ordered, "items": items})
            continue
        if s.startswith(">"):
            body = []
            while i < n and lines[i].strip().startswith(">"):
                body.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append({"kind": "quote", "body": "\n".join(body)})
            continue
        if s.startswith("|") and s.endswith("|"):
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.match(r"^:?-{2,}:?$", c) for c in cells):
                    rows.append(cells)
                i += 1
            out.append({"kind": "table", "rows": rows})
            continue
        para = []
        while i < n and lines[i].strip() and not re.match(r"^(#{1,6}\s|```|:::|>|[-*+]\s|\d+[.)]\s|\|)", lines[i].strip()):
            para.append(lines[i].strip())
            i += 1
        out.append({"kind": "p", "text": " ".join(para)})
    if len(out) > last:
        out[-1]["l0"], out[-1]["l1"] = start, i
    return out


def fm_offset(text):
    """머리말(---)이 차지하는 줄 수. 본문 블록의 줄 번호를 파일 기준으로 바꿀 때 더함"""
    m = FM_RE.match(text)
    return text[:m.end()].count("\n") if m else 0


def render_simple(bl, ref_cb=None):
    """그림·::: 를 뺀 일반 블록 하나를 HTML 로."""
    k = bl["kind"]
    if k == "p":
        return "<p>%s</p>" % inline(bl["text"], ref_cb)
    if k == "h":
        lv = min(bl["level"] + 1, 6)
        t, _ = heading_attrs(bl["text"])
        return "<h%d>%s</h%d>" % (lv, inline(t, ref_cb), lv)
    if k == "list":
        tag = "ol" if bl["ordered"] else "ul"
        return "<%s>%s</%s>" % (tag, "".join("<li>%s</li>" % inline(x, ref_cb) for x in bl["items"]), tag)
    if k == "quote":
        inner = "".join(render_simple(b, ref_cb) for b in blocks(bl["body"]))
        return "<blockquote>%s</blockquote>" % inner
    if k == "fence":
        return '<pre class="mono">%s</pre>' % esc(bl["body"])
    if k == "table":
        rows = bl["rows"]
        if not rows:
            return ""
        head = "".join("<th>%s</th>" % inline(c, ref_cb) for c in rows[0])
        body = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % inline(c, ref_cb) for c in r) for r in rows[1:])
        return '<div class="tbl"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (head, body)
    if k == "hr":
        return "<hr>"
    return ""
