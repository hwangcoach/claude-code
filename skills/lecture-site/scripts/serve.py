#!/usr/bin/env python3
"""화면 편집 모드: 사이트를 띄워 놓고 화면에서 원고를 고친다.

  python3 serve.py <강의폴더> [--port 5180] [--out <폴더>/.site-edit]

- 쪽 위의 블록(문단·제목·그림·꼭지·슬라이드·근거)을 누르면 편집 창이 열린다.
  그 블록의 **마크다운 원고**를 고치고 저장하면 원고 파일(chapters/*.md, deck.md, sources.md, lecture.md)이 바뀌고,
  사이트를 다시 만든 뒤 화면이 새로 고쳐진다. 삭제·아래에 추가·위로·아래로도 같은 창에서 한다.
- 원고를 Obsidian 등에서 직접 고쳐도 1.5초 안에 다시 만들고 화면이 따라온다.
- 저장할 때마다 바꾸기 전 파일을 <강의폴더>/.edit-history/ 에 남긴다. 편집 막대의 「되돌리기」가 마지막 것부터 되돌린다.
- 표준 라이브러리만 쓴다. 이 주소(127.0.0.1)는 내 컴퓨터에서만 열린다.
"""
import argparse
import datetime
import json
import os
import shutil
import sys
import threading
import traceback
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build  # noqa: E402
from mdlite import blocks, fm_offset  # noqa: E402

LOCK = threading.Lock()
STATE = {"v": 0, "mt": {}, "warn": [], "err": "", "hist": []}


def watched(root):
    out = {}
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("site", "node_modules")]
        for f in files:
            if f.endswith((".md", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif")):
                p = os.path.join(base, f)
                try:
                    out[p] = os.path.getmtime(p)
                except OSError:
                    pass
    return out


def rebuild(root, out):
    build.WARN.clear()
    build.EDIT = True
    build.EDIT_V = STATE["v"] + 1
    try:
        pj = build.Project(root)
        build.build(pj, out)
        STATE["err"] = ""
    except SystemExit as e:
        STATE["err"] = str(e)
    except Exception:  # noqa: BLE001
        STATE["err"] = traceback.format_exc(limit=3)
    seen = []
    for w in build.WARN:
        if w not in seen:
            seen.append(w)
    STATE["warn"] = seen
    STATE["mt"] = watched(root)
    STATE["v"] += 1


def safe_path(root, rel):
    p = os.path.normpath(os.path.join(root, rel))
    if not p.startswith(root + os.sep) or not p.endswith(".md") or not os.path.isfile(p):
        raise ValueError("고칠 수 없는 경로: %s" % rel)
    return p


def units(lines, a, b, unit):
    """[a,b) 와 같은 종류의 이웃 단위 목록. block: 마크다운 블록 / section: 같은 깊이 제목부터 다음 제목까지"""
    if unit == "section":
        head = lines[a].lstrip()
        lv = len(head) - len(head.lstrip("#"))
        starts = [i for i, l in enumerate(lines) if l.startswith("#" * lv + " ")]
        out = []
        for k, st in enumerate(starts):
            end = len(lines)
            for j in range(st + 1, len(lines)):
                l2 = lines[j]
                if l2.startswith("#") and (len(l2) - len(l2.lstrip("#"))) <= lv and l2[len(l2) - len(l2.lstrip("#")):].startswith(" "):
                    end = j
                    break
            out.append((st, end))
        return out
    text = "\n".join(lines)
    off = fm_offset(text)
    body = "\n".join(lines[off:])
    return [(bl["l0"] + off, bl["l1"] + off) for bl in blocks(body)]


def apply(root, req):
    op = req.get("op")
    rel = req.get("f", "")
    path = safe_path(root, rel)
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    lines = raw.split("\n")
    a, b = int(req.get("a", 0)), int(req.get("b", 0))
    if not (0 <= a <= b <= len(lines)):
        raise ValueError("줄 범위가 맞지 않습니다")
    orig = req.get("orig")
    if orig is not None and "\n".join(lines[a:b]) != orig:
        raise RuntimeError("그사이 원고가 바뀌었습니다. 화면을 새로 고친 뒤 다시 하세요.")
    new = list(lines)
    if op == "replace":
        new[a:b] = req.get("text", "").split("\n")
    elif op == "delete":
        del new[a:b]
        while a < len(new) and a > 0 and new[a].strip() == "" and new[a - 1].strip() == "":
            del new[a]
    elif op == "insert":
        ins = req.get("text", "").split("\n")
        new[b:b] = ([""] if b > 0 and new[b - 1].strip() else []) + ins + ([""] if b < len(new) and new[b].strip() else [])
    elif op == "move":
        us = units(lines, a, b, req.get("unit", "block"))
        idx = next((i for i, u in enumerate(us) if u[0] == a), None)
        if idx is None:
            raise ValueError("옮길 블록을 찾지 못했습니다")
        j = idx + (-1 if req.get("dir") == "up" else 1)
        if not (0 <= j < len(us)):
            raise ValueError("더 옮길 곳이 없습니다")
        (x0, x1), (y0, y1) = sorted([us[idx], us[j]])
        A, gap, B = lines[x0:x1], lines[x1:y0], lines[y0:y1]
        if req.get("unit") == "section":
            if B and B[-1].strip():
                B = B + [""]
            new[x0:y1] = B + A
        else:
            new[x0:y1] = B + gap + A
    else:
        raise ValueError("모르는 작업: %s" % op)
    hdir = os.path.join(root, ".edit-history")
    os.makedirs(hdir, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    bk = os.path.join(hdir, "%s__%s" % (stamp, rel.replace("/", "__")))
    shutil.copy(path, bk)
    STATE["hist"].append((path, bk))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(new))


def undo(root):
    if not STATE["hist"]:
        raise ValueError("이번 편집 모드에서 되돌릴 것이 없습니다(.edit-history 에 이전 파일이 남아 있음)")
    path, bk = STATE["hist"].pop()
    shutil.copy(bk, path)
    return os.path.relpath(path, root)


def make_handler(root, out):
    class H(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=out, **k)

        def log_message(self, fmt, *args):
            pass

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def _json(self, code, obj):
            body = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/__edit/version":
                with LOCK:
                    if watched(root) != STATE["mt"]:
                        rebuild(root, out)
                    return self._json(200, {"v": STATE["v"], "warn": STATE["warn"], "err": STATE["err"]})
            if u.path == "/__edit/src":
                q = parse_qs(u.query)
                try:
                    p = safe_path(root, q["f"][0])
                    lines = open(p, encoding="utf-8").read().split("\n")
                    a, b = int(q["a"][0]), int(q["b"][0])
                    return self._json(200, {"text": "\n".join(lines[a:b]), "total": len(lines)})
                except Exception as e:  # noqa: BLE001
                    return self._json(400, {"error": str(e)})
            return super().do_GET()

        def do_POST(self):
            u = urlparse(self.path)
            n = int(self.headers.get("Content-Length", 0) or 0)
            try:
                req = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return self._json(400, {"error": "요청 형식 오류"})
            # 다른 사이트가 내 원고를 바꾸지 못하게: 같은 주소에서 온 요청만
            origin = self.headers.get("Origin", "")
            if origin and not origin.startswith(("http://127.0.0.1", "http://localhost")):
                return self._json(403, {"error": "허용되지 않은 요청"})
            with LOCK:
                try:
                    if u.path == "/__edit/op":
                        apply(root, req)
                    elif u.path == "/__edit/undo":
                        req["undone"] = undo(root)
                    else:
                        return self._json(404, {"error": "없는 주소"})
                except RuntimeError as e:
                    return self._json(409, {"error": str(e)})
                except Exception as e:  # noqa: BLE001
                    return self._json(400, {"error": str(e)})
                rebuild(root, out)
                return self._json(200, {"ok": True, "v": STATE["v"], "warn": STATE["warn"], "err": STATE["err"], "undone": req.get("undone")})
    return H


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir")
    ap.add_argument("--port", type=int, default=5180)
    ap.add_argument("--out")
    a = ap.parse_args()
    root = os.path.abspath(a.dir)
    out = os.path.abspath(a.out or os.path.join(root, ".site-edit"))
    rebuild(root, out)
    if STATE["err"]:
        print("빌드 오류:", STATE["err"])
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(root, out))
    print("편집 모드: http://127.0.0.1:%d/  (원고: %s)" % (a.port, root), flush=True)
    print("블록을 누르면 편집 창이 열립니다. 끝내려면 Ctrl+C. 배포용 사이트는 build 명령으로 따로 만드세요.", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
