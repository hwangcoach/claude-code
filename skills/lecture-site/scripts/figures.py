"""선언형 그림 블록 -> SVG. 본문 도판, 덱 장, 책 쪽이 같은 SVG 를 씀(원본의 FigLib 역할).

```fig a-01-a
type: stat
tone: dark
value: 51,071
label: 입력 토큰
grid: 51
grid_note: 한 칸 1,000토큰 · 대부분 내가 치지 않은 글
mark: 내가 친 한 줄
caption: 입력 토큰 51,071개 가운데 내가 친 글은 점 하나만큼
```

넓은 판 W=1760, 좁은 판 W=900(휴대폰). 색은 덱 토큰(남색 + 구리색 강조). 같은 뜻 = 같은 색.
data-key: 같은 꼭지의 두 그림에서 같은 이름의 행/카드가 덱의 carry 전환으로 이어짐.
class="beat" data-beat=N: 덱에서 한 번 누를 때마다 하나씩 나옴(steps: yes).
"""
import base64
import math
import mimetypes
import os
import re
from html import escape

C = {
    "ink": "#0B1F33", "n100": "#D5E4F1", "n300": "#7FB2D9", "n500": "#3378AD", "n700": "#123A63",
    "alt": "#EEF2F6", "muted": "#4E6074", "teal": "#0E6E62", "tealPale": "#CFE5E0",
    "copper": "#C2662E", "copperText": "#A9501C", "dark": "#0B1F33", "onDark": "#F3F6FA",
    "darkMuted": "#9DB3C9", "darkCell": "#16314F", "white": "#FFFFFF",
}
SEQ = ["n700", "n500", "n300", "n100"]
TYPES = ["stat", "bars", "stack", "compare", "flow", "list", "statement", "table", "sankey", "timeline", "terminal", "image", "illust", "svg"]


# ---------- 글자 폭 어림(Pretendard 기준) ----------
def cw(ch):
    o = ord(ch)
    if 0xAC00 <= o <= 0xD7A3 or 0x3130 <= o <= 0x318F or 0x4E00 <= o <= 0x9FFF:
        return 0.93
    if ch == " ":
        return 0.28
    if ch in ",.:;'|!`":
        return 0.28
    if ch in "()[]{}-–—/":
        return 0.38
    if ch.isdigit():
        return 0.6
    if ch.isupper():
        return 0.66
    if ch.isalpha():
        return 0.54
    return 0.6


def tw(s, size, weight=500):
    return sum(cw(c) for c in str(s)) * size * (1.03 if weight >= 700 else 1.0)


def wrap(s, size, maxw, weight=500):
    """한국어는 어절 단위로, 너무 긴 어절은 글자 단위로 줄을 나눔."""
    words, lines, cur = str(s).split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if tw(t, size, weight) <= maxw or not cur:
            if tw(t, size, weight) > maxw and not cur:
                buf = ""
                for ch in w:
                    if tw(buf + ch, size, weight) > maxw and buf:
                        lines.append(buf)
                        buf = ""
                    buf += ch
                cur = buf
            else:
                cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def r1(v):
    return ("%.1f" % v).rstrip("0").rstrip(".")


def slug(s):
    s = re.sub(r"\s+", "-", str(s).strip())
    return re.sub(r'["<>&]', "", s)[:40]


class Pal:
    def __init__(self, dark):
        self.dark = dark
        self.bg = C["dark"] if dark else C["white"]
        self.ink = C["onDark"] if dark else C["ink"]
        self.muted = C["darkMuted"] if dark else C["muted"]
        self.cell = C["darkCell"] if dark else C["alt"]
        self.accent = C["copper"]
        self.accentText = "#E08A55" if dark else C["copperText"]
        self.bar = C["n500"]
        self.strong = C["n300"] if dark else C["n700"]


def T(x, y, s, size=34, w=500, fill=None, a="start", cls="", extra=""):
    return '<text x="%s" y="%s" font-size="%s" font-weight="%s" fill="%s" text-anchor="%s"%s%s>%s</text>' % (
        r1(x), r1(y), r1(size), w, fill or C["ink"], a, (' class="%s"' % cls) if cls else "", extra, escape(str(s)))


def ML(x, y, lines, size, w=500, fill=None, a="start", lh=1.32):
    return "".join(T(x, y + i * size * lh, t, size, w, fill, a) for i, t in enumerate(lines))


def R(x, y, w, h, fill, rx=0, extra=""):
    return '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s"%s/>' % (
        r1(x), r1(y), r1(max(w, 0)), r1(max(h, 0)), r1(rx), fill, extra)


def G(body, key=None, beat=None):
    attrs = ""
    if key:
        attrs += ' data-key="%s"' % escape(key)
    if beat is not None:
        attrs += ' class="beat" data-beat="%d"' % beat
    return "<g%s>%s</g>" % (attrs, body)


def arrow(x1, y1, x2, y2, col, sw=4, head=16):
    ang = math.atan2(y2 - y1, x2 - x1)
    bx, by = x2 - head * math.cos(ang), y2 - head * math.sin(ang)
    p1 = (bx + head * 0.55 * math.sin(ang), by - head * 0.55 * math.cos(ang))
    p2 = (bx - head * 0.55 * math.sin(ang), by + head * 0.55 * math.cos(ang))
    return ('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s"/>' % (r1(x1), r1(y1), r1(bx), r1(by), col, sw) +
            '<polygon points="%s,%s %s,%s %s,%s" fill="%s"/>' % (r1(x2), r1(y2), r1(p1[0]), r1(p1[1]), r1(p2[0]), r1(p2[1]), col))


def svg(W, H, body, label, pal):
    bg = R(0, 0, W, H, pal.bg, 0) if pal.dark else ""
    return ('<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="%s"%s>'
            '<title>%s</title>%s%s</svg>') % (W, math.ceil(H), escape(label), ' class="dk"' if pal.dark else "",
                                              escape(label), bg, body)


# ---------- 명세 읽기 ----------
def parse(text):
    spec, rows = {}, []
    raw = text.strip()
    if raw.startswith("<svg"):
        return {"type": "svg", "raw": raw, "rows": []}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("- "):
            cells = [c.strip() for c in s[2:].split("|")]
            rows.append(cells)
        elif ":" in s:
            k, v = s.split(":", 1)
            spec[k.strip()] = v.strip()
    spec["rows"] = rows
    spec.setdefault("type", "list" if rows else "statement")
    return spec


def flag(cells, i):
    return len(cells) > i and cells[i].lower() in ("hl", "*", "강조", "!")


def num(v):
    try:
        return float(re.sub(r"[^\d.\-]", "", str(v)) or 0)
    except ValueError:
        return 0.0


def yes(v):
    return str(v).lower() in ("yes", "true", "1", "y", "예", "네")


# ---------- 형식별 그리기 ----------
def f_stat(s, W, p, narrow):
    value, label = s.get("value", ""), s.get("label", "")
    grid = int(num(s.get("grid", 0)))
    rows = s["rows"]
    step = yes(s.get("steps"))
    leftW = W if (narrow or (not grid and not rows)) else W * 0.44
    vs = min(240 if not narrow else 190, leftW * 0.96 / max(tw(value, 1, 800), 0.1))
    center = not grid and not rows
    ax = W / 2 if center else 0
    anchor = "middle" if center else "start"
    # 큰 수 + 이름표(왼쪽 묶음)
    y = vs * 0.9 + 20
    left = G(T(ax, y, value, vs, 800, p.ink, anchor), key="stat-" + slug(label or value))
    y += 70
    if label:
        ll = wrap(label, 48, leftW)
        left += G(ML(ax, y, ll, 48, 700, p.muted, anchor), key="lab-" + slug(label))
        y += 48 * 1.32 * len(ll)
    leftH = y
    right, H = "", leftH
    if grid:
        gx = 0 if narrow else W * 0.5
        gw = W - gx
        gy = (leftH + 40) if narrow else 40
        note = s.get("grid_note", "")
        if note:
            right += T(gx, gy + 34, note, 34, 700, p.ink)
            gy += 70
        cols, gap = 10, (12 if not narrow else 8)
        cell = (gw - (cols - 1) * gap) / cols
        gb = "".join(R(gx + (i % cols) * (cell + gap), gy + (i // cols) * (cell + gap), cell, cell, p.bar, 2) for i in range(grid))
        right += G(gb, key="grid")
        nrows = math.ceil(grid / cols) or 1
        gh = nrows * (cell + gap)
        mark = s.get("mark", "")
        if mark:
            lr, lc = divmod(grid, cols)
            mx = gx + lc * (cell + gap) + cell / 2
            my = gy + lr * (cell + gap) + cell / 2
            m = '<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="4"/>' % (r1(mx), r1(my), r1(cell * 0.3), p.accent)
            m += '<circle cx="%s" cy="%s" r="5" fill="%s"/>' % (r1(mx), r1(my), p.ink)
            m += '<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="3"/>' % (r1(mx + cell * 0.36), r1(my), r1(mx + cell * 0.9), r1(my), p.ink)
            m += T(mx + cell, my + 13, mark, 36, 700, p.ink)
            right += G(m, key="mark", beat=1 if step else None)
            gh = max(gh, (lr + 1) * (cell + gap))
        H = max(leftH, gy + gh) if not narrow else gy + gh
    elif rows:
        rx = 0 if narrow else W * 0.54
        ry = (leftH + 60) if narrow else 40
        for i, cells in enumerate(rows):
            lab = cells[0]
            val = cells[1] if len(cells) > 1 else ""
            col = p.accentText if flag(cells, 2) else p.strong
            g = T(rx, ry + 96, val, 104, 800, col) + T(rx, ry + 150, lab, 34, 600, p.muted)
            right += G(g, key=slug(lab), beat=i if (step and i) else None)
            ry += 200
        H = max(leftH, ry) if not narrow else ry
    if not narrow and (grid or rows) and H > leftH:
        # 큰 수를 오른쪽 묶음 가운데 높이로(바깥 g 에만 transform: 덱 carry 는 안쪽 data-key 에 CSS transform 을 씀)
        left = '<g transform="translate(0 %s)">%s</g>' % (r1((H - leftH) / 2), left)
    return left + right, H + 20


def f_bars(s, W, p, narrow):
    rows = s["rows"]
    unit = s.get("unit", "")
    vals = [num(r[1]) if len(r) > 1 else 0 for r in rows]
    mx = num(s["max"]) if s.get("max") else (max(vals) if vals else 1) or 1
    ls = 36
    note = s.get("note", "")
    y = 0
    body = ""
    if note:
        body += T(0, 34, note, 32, 700, p.muted)
        y = 70
    labW = 0 if narrow else min(max([tw(r[0], ls, 700) for r in rows] + [0]) + 30, W * 0.34)
    valW = max([tw((r[2] if len(r) > 2 and r[2] and not flag(r, 2) else (r[1] if len(r) > 1 else "")) + unit, 36, 800) for r in rows] + [0]) + 24
    barX = labW
    barMax = W - labW - valW
    bh = 52 if not narrow else 44
    step = yes(s.get("steps"))
    for i, r in enumerate(rows):
        lab = r[0]
        v = vals[i]
        disp = (r[2] if len(r) > 2 and r[2] and not flag(r, 2) else (r[1] if len(r) > 1 else "")) + unit
        hl = flag(r, 2) or flag(r, 3)
        col = p.accent if hl else (p.bar if i else (C["n300"] if p.dark else C["n700"]))
        g = ""
        if narrow:
            g += T(0, y + 34, lab, 34, 700, p.ink)
            y += 50
        else:
            g += T(labW - 30, y + bh / 2 + 12, lab, ls, 700, p.ink, "end")
        bw = max(barMax * v / mx, 4)
        g += R(barX, y, bw, bh, col, 3)
        g += T(barX + bw + 16, y + bh / 2 + 13, disp, 36, 800, p.accentText if hl else p.ink)
        body += G(g, key=slug(lab), beat=i if (step and i) else None)
        y += bh + (34 if not narrow else 30)
    return body, y


def f_stack(s, W, p, narrow):
    rows = s["rows"]
    vals = [num(r[1]) if len(r) > 1 else 0 for r in rows]
    tot = sum(vals) or 1
    step = yes(s.get("steps"))
    body, y = "", 0
    note = s.get("note", "")
    if note:
        body += T(0, 34, note, 32, 700, p.muted)
        y = 64
    total = s.get("total", "")
    if total:
        body += T(W, 34, total, 34, 800, p.ink, "end")
        y = 64
    bh = 120 if not narrow else 90
    x = 0
    segs, legend = "", ""
    ly = y + bh + 60
    colW = W if narrow else W / 2
    for i, r in enumerate(rows):
        hl = flag(r, 3) or flag(r, 2)
        col = p.accent if hl else C[SEQ[min(i, 3)]]
        if p.dark and not hl and SEQ[min(i, 3)] == "n700":
            col = C["n300"]
        w = W * vals[i] / tot
        beat = i if (step and i) else None
        segs += G(R(x, y, max(w - 3, 2), bh, col, 2), key=slug(r[0]), beat=beat)
        x += w
        lx = 0 if narrow or i % 2 == 0 else colW
        disp = r[1]
        desc = r[2] if len(r) > 2 and not flag(r, 2) else ""
        lg = R(lx, ly, 28, 28, col, 3) + T(lx + 44, ly + 26, "%s  %s" % (r[0], disp), 36, 800, p.ink)
        dl = wrap(desc, 28, colW - 80) if desc else []
        if dl:
            lg += ML(lx + 44, ly + 70, dl, 28, 500, p.muted)
        legend += G(lg, key="lg-" + slug(r[0]), beat=beat)
        if narrow or i % 2 == 1 or i == len(rows) - 1:
            ly += 70 + 28 * 1.32 * max(len(dl), 1) + 20
    body += segs + legend
    return body, ly


def f_compare(s, W, p, narrow):
    rows = s["rows"]
    n = max(len(rows), 1)
    step = yes(s.get("steps"))
    arrows = yes(s.get("arrow", "no"))
    gap = 90 if arrows else 40
    body, y0 = "", 0
    note = s.get("note", "")
    if note:
        body += T(0, 34, note, 32, 700, p.muted)
        y0 = 70
    if narrow:
        cw_ = W
    else:
        cw_ = (W - gap * (n - 1)) / n
    ch = 0
    cards = []
    for i, r in enumerate(rows):
        title = r[0]
        val = r[1] if len(r) > 1 else ""
        desc = r[2] if len(r) > 2 and not flag(r, 2) else ""
        hl = flag(r, 2) or flag(r, 3)
        vs = min(130, (cw_ - 80) / max(tw(val, 1, 800), 0.1))
        dl = wrap(desc, 32, cw_ - 80) if desc else []
        h = 60 + 40 + 30 + vs + 40 + len(dl) * 32 * 1.4 + 40
        cards.append((title, val, dl, hl, vs, h))
        ch = max(ch, h)
    y = y0
    for i, (title, val, dl, hl, vs, h) in enumerate(cards):
        x = 0 if narrow else i * (cw_ + gap)
        cy = y if narrow else y0
        hh = h if narrow else ch
        g = R(x, cy, cw_, hh, C["darkCell"] if p.dark else C["alt"], 16)
        if hl:
            g += R(x, cy, 8, hh, p.accent, 0)
        g += T(x + 40, cy + 70, title, 36, 700, p.muted)
        g += T(x + 40, cy + 110 + vs * 0.9, val, vs, 800, p.accentText if hl else p.ink)
        g += ML(x + 40, cy + 110 + vs + 60, dl, 32, 500, p.muted, lh=1.4)
        body += G(g, key=slug(title), beat=i if (step and i) else None)
        if arrows and i < n - 1 and not narrow:
            body += arrow(x + cw_ + 14, cy + hh / 2, x + cw_ + gap - 14, cy + hh / 2, p.muted, 5, 20)
        if narrow:
            y += h + 30
    return body, (y if narrow else y0 + ch)


def f_flow(s, W, p, narrow):
    rows = s["rows"]
    n = max(len(rows), 1)
    step = yes(s.get("steps"))
    body, y0 = "", 0
    note = s.get("note", "")
    if note:
        body += T(0, 34, note, 32, 700, p.muted)
        y0 = 70
    vertical = narrow or n > 6
    gap = 80
    if vertical:
        bw = W
    else:
        bw = (W - gap * (n - 1)) / n
    items = []
    bh = 0
    for i, r in enumerate(rows):
        t = wrap(r[0], 38, bw - 60 - (90 if vertical else 0), 800)
        d = wrap(r[1], 28, bw - 60 - (90 if vertical else 0)) if len(r) > 1 and not flag(r, 1) else []
        h = 40 + (0 if vertical else 90) + len(t) * 38 * 1.25 + (12 + len(d) * 28 * 1.4 if d else 0) + 40
        if vertical:
            h = max(h, 120)
        items.append((t, d, flag(r, 2) or flag(r, 1), h))
        bh = max(bh, h)
    y = y0
    for i, (t, d, hl, h) in enumerate(items):
        hh = h if vertical else bh
        x = 0 if vertical else i * (bw + gap)
        cy = y
        fill = (C["darkCell"] if p.dark else C["alt"])
        g = R(x, cy, bw, hh, fill, 16)
        if hl:
            g += R(x, cy, bw, 8, p.accent, 0)
        cx_, cy_ = (x + 60, cy + hh / 2) if vertical else (x + 60, cy + 66)
        g += '<circle cx="%s" cy="%s" r="30" fill="%s"/>' % (r1(cx_), r1(cy_), p.accent if hl else (C["n300"] if p.dark else C["n700"]))
        g += T(cx_, cy_ + 12, str(i + 1), 32, 800, C["white"] if not p.dark else C["dark"], "middle")
        tx = x + (120 if vertical else 30)
        ty = (cy + 40 + 30) if vertical else (cy + 130 + 30)
        if vertical:
            ty = cy + (hh - (len(t) * 38 * 1.25 + (12 + len(d) * 28 * 1.4 if d else 0))) / 2 + 32
        g += ML(tx, ty, t, 38, 800, p.ink, lh=1.25)
        if d:
            g += ML(tx, ty + len(t) * 38 * 1.25 + 12, d, 28, 500, p.muted, lh=1.4)
        body += G(g, key=slug(rows[i][0]), beat=i if (step and i) else None)
        if i < n - 1:
            if vertical:
                body += arrow(x + 60, cy + hh + 4, x + 60, cy + hh + 36, p.muted, 4, 14)
            else:
                body += arrow(x + bw + 12, cy + bh / 2, x + bw + gap - 12, cy + bh / 2, p.muted, 5, 20)
        if vertical:
            y += hh + 40
    return body, (y - 40 if vertical else y0 + bh)


def f_list(s, W, p, narrow):
    rows = s["rows"]
    step = yes(s.get("steps"))
    two = (not narrow) and len(rows) > 4
    colW = W / 2 - 30 if two else W
    body, y0 = "", 0
    note = s.get("note", "")
    if note:
        body += T(0, 34, note, 32, 700, p.muted)
        y0 = 70
    half = math.ceil(len(rows) / 2) if two else len(rows)
    ys = [y0, y0]
    for i, r in enumerate(rows):
        col = 1 if two and i >= half else 0
        x = col * (colW + 60)
        y = ys[col]
        hl = flag(r, 2) or flag(r, 1)
        t = wrap(r[0], 44, colW - 110, 700)
        d = wrap(r[1], 30, colW - 110) if len(r) > 1 and not flag(r, 1) else []
        g = T(x, y + 58, "%d" % (i + 1), 64, 800, p.accent if hl else (C["n300"] if p.dark else C["n500"]))
        g += ML(x + 100, y + 48, t, 44, 700, p.ink, lh=1.25)
        hh = len(t) * 44 * 1.25
        if d:
            g += ML(x + 100, y + 48 + hh + 6, d, 30, 500, p.muted, lh=1.45)
            hh += 6 + len(d) * 30 * 1.45
        body += G(g, key=slug(r[0]), beat=i if (step and i) else None)
        ys[col] = y + max(hh, 70) + 46
    return body, max(ys) - 30


def f_statement(s, W, p, narrow):
    text = s.get("text", "")
    size = float(s.get("size", 76 if not narrow else 64))
    plain = text.replace("==", "")
    lines = wrap(plain, size, W * (0.92 if narrow else 0.86), 800)
    hl = set(re.findall(r"==(.+?)==", text))
    body, y = "", size
    for ln in lines:
        # 강조 구간은 구리색
        parts, cur = [], ln
        for h in hl:
            if h in cur:
                a, b = cur.split(h, 1)
                parts = [(a, False), (h, True), (b, False)]
                break
        if not parts:
            parts = [(ln, False)]
        spans = "".join('<tspan fill="%s">%s</tspan>' % (p.accentText if on else p.ink, escape(t)) for t, on in parts if t)
        body += '<text x="0" y="%s" font-size="%s" font-weight="800">%s</text>' % (r1(y), r1(size), spans)
        y += size * 1.3
    if s.get("by"):
        body += T(0, y + 30, s["by"], 36, 600, p.muted)
        y += 80
    return G(body, key="statement"), y


def f_table(s, W, p, narrow):
    head = [c.strip() for c in s.get("head", "").split("|")] if s.get("head") else []
    rows = s["rows"]
    allr = ([head] if head else []) + rows
    ncol = max(len(r) for r in allr) if allr else 1
    fs = 32 if not narrow else 28
    widths = [max(tw(r[c] if c < len(r) else "", fs, 700) for r in allr) + 48 for c in range(ncol)]
    tot = sum(widths)
    widths = [w * W / tot for w in widths]
    y, body = 0, ""
    rh = fs * 2.2
    step = yes(s.get("steps"))
    for i, r in enumerate(allr):
        is_head = head and i == 0
        hl = any(flag([c], 0) for c in r[ncol:]) if len(r) > ncol else False
        g = R(0, y, W, rh, (C["n700"] if not p.dark else C["n500"]) if is_head else ((C["darkCell"] if p.dark else C["alt"]) if i % 2 else p.bg))
        x = 0
        for c in range(ncol):
            v = r[c] if c < len(r) else ""
            g += T(x + 24, y + rh / 2 + fs * 0.36, v, fs, 700 if (is_head or c == 0) else 500,
                   C["white"] if is_head else (p.accentText if hl else p.ink))
            x += widths[c]
        ri = i - (1 if head else 0)
        body += G(g, key=slug(r[0]) if not is_head else "thead", beat=ri if (step and not is_head and ri) else None)
        y += rh
    return body, y


def f_image(s, W, p, narrow, root=None):
    src = s.get("src", "")
    ratio = s.get("ratio", "16:9")
    a, b = (num(x) for x in ratio.split(":")) if ":" in ratio else (16, 9)
    H = W * b / (a or 16)
    href = src
    if root and src and not src.startswith(("http", "data:")):
        path = os.path.join(root, src)
        if os.path.exists(path):
            mt = mimetypes.guess_type(path)[0] or "image/png"
            with open(path, "rb") as f:
                href = "data:%s;base64,%s" % (mt, base64.b64encode(f.read()).decode())
    return ('<image href="%s" x="0" y="0" width="%d" height="%s" preserveAspectRatio="xMidYMid meet"/>' % (escape(href), W, r1(H))), H


_UID = [0]


def uid(prefix):
    _UID[0] += 1
    return "%s%d" % (prefix, _UID[0])


def ribbon(x1, a1, b1, x2, a2, b2, col, extra=""):
    """왼쪽 (a1~b1) 띠가 오른쪽 (a2~b2) 로 흘러 들어가는 리본(원본 a.js 의 ribbon 과 같은 곡선)"""
    m = (x1 + x2) / 2
    return ('<path d="M%s %s C%s %s %s %s %s %s L%s %s C%s %s %s %s %s %s Z" fill="%s"%s/>' % (
        r1(x1), r1(a1), r1(m), r1(a1), r1(m), r1(a2), r1(x2), r1(a2),
        r1(x2), r1(b2), r1(m), r1(b2), r1(m), r1(b1), r1(x1), r1(b1), col, extra))


def f_sankey(s, W, p, narrow):
    """여러 항목이 한 기둥(전체)으로 흘러 들어가는 리본 그림. 원본 3번 장 「입력 전부터 들어 있는 세 항목」 꼴.
    행: - 이름 | 값 | 설명 | hl 또는 rest(빗금, '그 밖의 것')"""
    rows = s["rows"]
    vals = [max(num(r[1]) if len(r) > 1 else 0, 0) for r in rows]
    tot = sum(vals) or 1
    step = yes(s.get("steps"))
    body, top = "", 0
    if s.get("note"):
        body += T(0, 34, s["note"], 32, 700, p.muted)
        top = 70
    hatch = uid("hatch")
    body += ('<defs><pattern id="%s" width="16" height="16" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
             '<rect width="16" height="16" fill="%s"/><rect width="7" height="16" fill="%s"/></pattern></defs>') % (
        hatch, C["darkCell"] if p.dark else C["white"], C["n300"])
    target = s.get("target", "")
    if target:
        top += 56
    TH = 520 if not narrow else 560
    labW = W * (0.36 if not narrow else 0.5)
    colX = W * (0.64 if not narrow else 0.86)
    colW = 56 if not narrow else 48
    minSlot, gap = (96 if not narrow else 120), 22
    hs = [v / tot * TH for v in vals]
    slots = [max(h, minSlot) for h in hs]
    LH = sum(slots) + gap * (len(rows) - 1)
    colY = top + max(0, (LH - TH) / 2)
    leftY = top + max(0, (TH - LH) / 2)
    if target:
        body += T(colX + colW / 2, colY - 24, target, 30, 700, p.ink, "middle" if narrow else "start")
    seq = [C["n700"], C["n500"], C["n300"], C["n100"]] if not p.dark else [C["n300"], C["n500"], C["n100"], C["darkMuted"]]
    sy, ty, k, hl_span = leftY, colY, 0, []
    for i, r in enumerate(rows):
        hl = flag(r, 3) or flag(r, 2)
        rest = any(c.lower() == "rest" for c in r[2:])
        col = "url(#%s)" % hatch if rest else (p.accent if hl else seq[k % 4])
        if not hl and not rest:
            k += 1
        h = max(hs[i], 3)
        a1 = sy + (slots[i] - h) / 2
        g = R(labW, a1, 14, h, col, 2)
        g += ribbon(labW + 14, a1, a1 + h, colX, ty, ty + h, col, ' opacity="%s"' % (".9" if not rest else "1"))
        g += R(colX, ty, colW, h, col, 0)
        name = r[0]
        desc = r[2] if len(r) > 2 and r[2].lower() not in ("hl", "*", "강조", "!", "rest") else ""
        cy = sy + slots[i] / 2
        ax, an = (labW - 24, "end") if not narrow else (0, "start")
        maxw = labW - 40
        nl = wrap(name + ((" " + r[1]) if s.get("show_values", "yes") != "no" and len(r) > 1 else ""), 38, maxw, 800)
        dl = wrap(desc, 26, maxw) if desc else []
        bh = len(nl) * 38 * 1.15 + (len(dl) * 26 * 1.35 + 6 if dl else 0)
        yy = cy - bh / 2 + 32
        g += ML(ax, yy, nl, 38, 800, p.accentText if hl else (p.muted if rest else p.ink), an, 1.15)
        if dl:
            g += ML(ax, yy + len(nl) * 38 * 1.15 + 2, dl, 26, 500, p.muted, an, 1.35)
        body += G(g, key=slug(name), beat=i if (step and i) else None)
        if hl:
            hl_span.append((ty, ty + h))
        sy += slots[i] + gap
        ty += hs[i]
    H = max(colY + TH, leftY + LH)
    co = s.get("callout", "")
    if co and hl_span:
        a, b = min(x[0] for x in hl_span), max(x[1] for x in hl_span)
        if not narrow:
            bx = colX + colW + 24
            g = '<path d="M%s %s h14 v%s h-14" fill="none" stroke="%s" stroke-width="4"/>' % (r1(bx), r1(a), r1(b - a), p.accent)
            cx = bx + 44
            cl = wrap(co, 50, W - cx, 800)
            sub = wrap(s.get("callout_sub", ""), 28, W - cx) if s.get("callout_sub") else []
            ch = len(cl) * 50 * 1.2 + (len(sub) * 28 * 1.35 + 14 if sub else 0)
            cy = (a + b) / 2 - ch / 2 + 44
            g += ML(cx, cy, cl, 50, 800, p.accentText, lh=1.2)
            if sub:
                g += ML(cx, cy + len(cl) * 50 * 1.2 + 10, sub, 28, 600, p.ink, lh=1.35)
        else:
            cl = wrap(co, 44, W, 800)
            g = ML(0, H + 70, cl, 44, 800, p.accentText, lh=1.2)
            H += 70 + len(cl) * 44 * 1.2
        body += G(g, key="callout", beat=len(rows) if step else None)
    return body, H + 10


def f_timeline(s, W, p, narrow):
    """시간 순서의 사건. 행: - 시점 | 사건 | 설명 | hl"""
    rows = s["rows"]
    n = max(len(rows), 1)
    step = yes(s.get("steps"))
    body, top = "", 0
    if s.get("note"):
        body += T(0, 34, s["note"], 32, 700, p.muted)
        top = 70
    line = C["n300"] if not p.dark else C["darkMuted"]
    if narrow:
        y = top + 20
        for i, r in enumerate(rows):
            hl = flag(r, 3) or flag(r, 2)
            ev = wrap(r[1] if len(r) > 1 else "", 36, W - 90, 800)
            ds = wrap(r[2], 26, W - 90) if len(r) > 2 and not flag(r, 2) else []
            hh = 46 + len(ev) * 36 * 1.25 + (len(ds) * 26 * 1.4 + 6 if ds else 0)
            g = '<circle cx="24" cy="%s" r="%d" fill="%s"/>' % (r1(y + 14), 16 if hl else 12, p.accent if hl else C["n500"])
            g += T(70, y + 26, r[0], 30, 800, p.accentText if hl else (C["n300"] if p.dark else C["n500"]))
            g += ML(70, y + 74, ev, 36, 800, p.ink, lh=1.25)
            if ds:
                g += ML(70, y + 74 + len(ev) * 36 * 1.25, ds, 26, 500, p.muted, lh=1.4)
            if i < n - 1:
                body += '<line x1="24" y1="%s" x2="24" y2="%s" stroke="%s" stroke-width="3"/>' % (r1(y + 30), r1(y + hh + 16), line)
            body += G(g, key=slug(r[0]), beat=i if (step and i) else None)
            y += hh + 30
        return body, y
    colW = min(W / n - 28, 420) if n > 1 else W * 0.6
    pad = colW / 2 + 4                      # 양 끝 글자가 판 밖으로 나가지 않게
    xs = [W / 2] if n == 1 else [pad + i * (W - 2 * pad) / (n - 1) for i in range(n)]
    ay = top + 90
    body += '<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="4"/>' % (r1(xs[0]), r1(ay), r1(xs[-1]), r1(ay), line)
    H = ay
    for i, r in enumerate(rows):
        hl = flag(r, 3) or flag(r, 2)
        x = xs[i]
        ev = wrap(r[1] if len(r) > 1 else "", 34, colW, 800)
        ds = wrap(r[2], 26, colW) if len(r) > 2 and not flag(r, 2) else []
        g = '<circle cx="%s" cy="%s" r="%d" fill="%s"/>' % (r1(x), r1(ay), 20 if hl else 14, p.accent if hl else C["n500"])
        g += T(x, ay - 40, r[0], 32, 800, p.accentText if hl else (C["n300"] if p.dark else C["n500"]), "middle")
        g += ML(x, ay + 76, ev, 34, 800, p.ink, "middle", 1.25)
        hh = ay + 76 + len(ev) * 34 * 1.25
        if ds:
            g += ML(x, hh + 4, ds, 26, 500, p.muted, "middle", 1.4)
            hh += 4 + len(ds) * 26 * 1.4
        H = max(H, hh)
        body += G(g, key=slug(r[0]), beat=i if (step and i) else None)
    return body, H


def f_terminal(s, W, p, narrow):
    """터미널 창. 행 = 한 줄. '$ ' 나 '> ' 로 시작하면 내가 친 명령, 그 밖은 출력. 줄 끝 '| hl' = 강조"""
    fs = 30 if not narrow else 24
    lh = fs * 1.6
    step = yes(s.get("steps"))
    bar = 56
    inner = W - 80
    lines = []
    for r in s["rows"]:
        hl = len(r) > 1 and r[-1].lower() in ("hl", "*", "강조", "!")
        txt = "|".join(r[:-1] if hl else r)
        cmd = txt.startswith(("$ ", "> "))
        for j, part in enumerate(wrap(txt, fs, inner, 500) if tw(txt, fs) > inner else [txt]):
            lines.append((part, cmd and j == 0, cmd, hl))
    H = bar + 36 + len(lines) * lh + 24
    body = R(0, 0, W, H, C["dark"], 16) + R(0, 0, W, bar, C["n700"], 16) + R(0, bar - 16, W, 16, C["n700"])
    for i in range(3):
        body += '<circle cx="%d" cy="%d" r="8" fill="%s"/>' % (32 + i * 28, bar // 2, C["darkMuted"])
    if s.get("title"):
        body += T(W / 2, bar / 2 + 9, s["title"], 24, 600, C["darkMuted"], "middle")
    y = bar + 36 + fs
    for i, (t, first_cmd, cmd, hl) in enumerate(lines):
        if first_cmd:
            g = ('<text class="mono" x="40" y="%s" font-size="%d" xml:space="preserve"><tspan fill="%s">%s</tspan>'
                 '<tspan fill="%s">%s</tspan></text>') % (r1(y), fs, C["n300"], escape(t[:2]), "#E08A55" if hl else C["onDark"], escape(t[2:]))
        else:
            g = '<text class="mono" x="40" y="%s" font-size="%d" fill="%s" xml:space="preserve">%s</text>' % (
                r1(y), fs, "#E08A55" if hl else (C["onDark"] if cmd else C["darkMuted"]), escape(t))
        body += G(g, beat=i if (step and i) else None) if step else g
        y += lh
    return body, H


ILLUST_STYLE = ("Flat editorial illustration for a lecture slide. Clean vector shapes, generous negative space, "
                "limited palette: deep navy #123A63, blue #3378AD, light blue #7FB2D9, pale blue #D5E4F1, "
                "and exactly one small accent in copper #C2662E. {bg}. Absolutely no text, letters, numbers, "
                "logos or watermarks. Calm, modern, slightly geometric, people (if any) simplified without facial detail. "
                "Aspect ratio {ratio}.")


def illust_prompt(s):
    """삽화 생성용 완성 프롬프트(그림 블록의 prompt + 덱 색 규칙)"""
    bg = "Dark navy background #0B1F33" if s.get("tone") == "dark" else "Plain white background"
    style = s.get("style") or ILLUST_STYLE.format(bg=bg, ratio=s.get("ratio", "16:9"))
    return "%s\n\nScene: %s" % (style, s.get("prompt", "").strip())


def illust_path(s):
    return s.get("src") or "assets/illust/%s.png" % s.get("_id", "illust")


def f_illust(s, W, p, narrow, root=None):
    ratio = s.get("ratio", "16:9")
    a, b = (num(x) for x in ratio.split(":")) if ":" in ratio else (16, 9)
    H = W * b / (a or 16)
    src = illust_path(s)
    path = os.path.join(root, src) if root else ""
    if path and os.path.exists(path):
        img, _ = f_image(dict(s, src=src), W, p, narrow, root)
        return img, H
    # 아직 안 만든 삽화: 자리 표시(빌드 경고에도 나옴)
    body = R(2, 2, W - 4, H - 4, C["alt"] if not p.dark else C["darkCell"], 16,
             ' stroke="%s" stroke-width="4" stroke-dasharray="18 12"' % C["n300"])
    cx, cy = W / 2, H * 0.36
    body += '<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (r1(cx + 90), r1(cy - 40), r1(H * 0.05), C["n300"])
    body += '<polygon points="%s,%s %s,%s %s,%s" fill="%s"/>' % (r1(cx - 200), r1(cy + 90), r1(cx - 60), r1(cy - 60), r1(cx + 80), r1(cy + 90), C["n500"])
    body += '<polygon points="%s,%s %s,%s %s,%s" fill="%s"/>' % (r1(cx - 20), r1(cy + 90), r1(cx + 90), r1(cy - 10), r1(cx + 200), r1(cy + 90), C["n700"])
    body += T(cx, cy + 170, "삽화 자리 · %s" % s.get("_id", ""), 40, 800, p.muted, "middle")
    pl = wrap(s.get("prompt", ""), 28, W * 0.8)[:4]
    body += ML(cx, cy + 226, pl, 28, 500, p.muted, "middle", 1.4)
    return body, H


RENDER = {"stat": f_stat, "bars": f_bars, "stack": f_stack, "compare": f_compare, "flow": f_flow,
          "list": f_list, "statement": f_statement, "table": f_table,
          "sankey": f_sankey, "timeline": f_timeline, "terminal": f_terminal}


def render(spec, narrow=False, root=None):
    W = 900 if narrow else 1760
    t = spec.get("type", "statement")
    label = spec.get("caption") or spec.get("label") or spec.get("text") or spec.get("note") or t
    if t == "svg":
        return spec["raw"]
    p = Pal(spec.get("tone", "") == "dark")
    pad = 64 if p.dark else 0
    if t == "image":
        body, H = f_image(spec, W, p, narrow, root)
        return svg(W, H, body, label, Pal(False))
    if t == "illust":
        body, H = f_illust(spec, W, p, narrow, root)
        return svg(W, H, body, label, Pal(False))
    if t not in RENDER:
        raise ValueError("모르는 그림 형식: %s (가능: %s)" % (t, ", ".join(TYPES)))
    body, H = RENDER[t](spec, W - 2 * pad, p, narrow)
    if pad:
        body = '<g transform="translate(%d %d)">%s</g>' % (pad, pad, body)
    return svg(W, H + 2 * pad + 10, body, label, p)
