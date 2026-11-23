#!/usr/bin/env python3
"""삽화 만들기: 원고의 ```fig <id> / type: illust 블록을 모아 ChatGPT 이미지(codex CLI)로 생성한다.

  python3 illust.py sheet <강의폴더>                 프롬프트 시트(illustrations.md)만 만듦
  python3 illust.py gen <강의폴더> [--ids a-01-i,b-02-i] [--force] [--parallel 5] [--timeout 420]

gen 은 codex CLI(ChatGPT 로그인)의 이미지 생성 도구를 씀. 최대 5장 동시.
codex 가 없거나 로그인이 안 됐거나 생성에 실패하면, illustrations.md 에 프롬프트와 저장 경로를 적어 두고
사람이 ChatGPT 에서 직접 만들어 그 경로에 저장하면 된다. 저장한 뒤 build 를 다시 돌리면 들어간다.
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import figures  # noqa: E402
import build  # noqa: E402


def collect(root):
    pj = build.Project(root)
    out = []
    for fid, spec in pj.figs.items():
        if spec.get("type") != "illust":
            continue
        rel = figures.illust_path(spec)
        out.append({"id": fid, "spec": spec, "rel": rel, "path": os.path.join(pj.root, rel),
                    "prompt": figures.illust_prompt(spec)})
    return pj, out


def is_png(path):
    try:
        with open(path, "rb") as f:
            head = f.read(8)
        return head[:8] == b"\x89PNG\r\n\x1a\n" or head[:3] == b"\xff\xd8\xff" or head[:4] == b"RIFF"
    except OSError:
        return False


def sheet(pj, items, failed=None):
    lines = ["# 삽화 프롬프트 시트", "",
             "ChatGPT(이미지 생성)에 아래 프롬프트를 그대로 붙여 넣고, 나온 이미지를 **저장 경로**에 그 파일 이름으로 저장하세요.",
             "저장한 뒤 `build.py build` 를 다시 돌리면 본문·덱·책에 들어갑니다. 가로형(16:9 또는 3:2)으로 요청하세요.", ""]
    for it in items:
        done = os.path.exists(it["path"]) and is_png(it["path"])
        state = "있음" if done else ("생성 실패 → 직접 만들기" if failed and it["id"] in failed else "없음")
        lines += ["## %s · %s" % (it["id"], state), "",
                  "- 저장 경로: `%s`" % it["rel"],
                  "- 쓰이는 곳: %s" % (it["spec"].get("caption") or ""), "",
                  "```text", it["prompt"], "```", ""]
    p = os.path.join(pj.root, "illustrations.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return p


def codex_ready():
    if not shutil.which("codex"):
        return "codex CLI 가 없습니다"
    try:
        r = subprocess.run(["codex", "login", "status"], capture_output=True, text=True, timeout=30)
    except Exception as e:  # noqa: BLE001
        return "codex 확인 실패: %s" % e
    if r.returncode != 0 or "Logged in" not in (r.stdout + r.stderr):
        return "codex 가 ChatGPT 로 로그인되어 있지 않습니다(codex login)"
    return None


def reason(err_path):
    """codex 로그에서 실패 이유 한 줄(사용량 한도, 로그인 등)"""
    try:
        with open(err_path, encoding="utf-8", errors="replace") as f:
            errs = [l.strip() for l in f if l.startswith("ERROR:")]
    except OSError:
        return ""
    if not errs:
        return ""
    msg = errs[-1][6:].strip()
    if "usage limit" in msg.lower():
        msg = "ChatGPT/Codex 사용량 한도에 걸림 — " + msg
    return ": " + msg[:220]


def gen(pj, items, parallel, timeout):
    todo = list(items)
    failed = {}
    os.makedirs(os.path.dirname(todo[0]["path"]), exist_ok=True) if todo else None
    logdir = os.path.join(pj.root, "assets", "illust", ".logs")
    os.makedirs(logdir, exist_ok=True)
    while todo:
        batch, todo = todo[:parallel], todo[parallel:]
        procs = []
        for it in batch:
            d = os.path.dirname(it["path"])
            os.makedirs(d, exist_ok=True)
            name = os.path.basename(it["path"])
            instr = ("이미지 생성 도구로 아래 프롬프트대로 가로형 이미지 한 장을 생성하고, 현재 폴더에 '%s' 파일로 저장해. "
                     "다른 파일은 만들거나 고치지 말고, 저장한 파일 경로만 한 줄로 보고해.\n\n%s") % (name, it["prompt"])
            cmd = ["codex", "exec", "--sandbox", "workspace-write", "--skip-git-repo-check", "--cd", d,
                   "-o", os.path.join(logdir, it["id"] + ".md"), instr]
            print("  생성 시작: %s → %s" % (it["id"], it["rel"]), flush=True)
            procs.append((it, subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=open(os.path.join(logdir, it["id"] + ".err"), "w")), time.time()))
        for it, pr, t0 in procs:
            try:
                pr.wait(timeout=max(1, timeout - (time.time() - t0)))
            except subprocess.TimeoutExpired:
                pr.kill()
                failed[it["id"]] = "시간 초과(%d초)%s" % (timeout, reason(os.path.join(logdir, it["id"] + ".err")))
                continue
            if not (os.path.exists(it["path"]) and os.path.getsize(it["path"]) > 0 and is_png(it["path"])):
                failed[it["id"]] = "파일이 만들어지지 않음(codex 종료 코드 %s)%s" % (pr.returncode, reason(os.path.join(logdir, it["id"] + ".err")))
            else:
                print("  완료: %s (%d KB)" % (it["id"], os.path.getsize(it["path"]) // 1024), flush=True)
    return failed


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("sheet"); p.add_argument("dir")
    p = sub.add_parser("gen"); p.add_argument("dir"); p.add_argument("--ids", default="")
    p.add_argument("--force", action="store_true"); p.add_argument("--parallel", type=int, default=5)
    p.add_argument("--timeout", type=int, default=420)
    a = ap.parse_args()
    pj, items = collect(a.dir)
    if not items:
        print("type: illust 그림이 없습니다.")
        return
    if a.cmd == "sheet":
        print("프롬프트 시트: %s (%d장)" % (sheet(pj, items), len(items)))
        return
    want = set(x.strip() for x in a.ids.split(",") if x.strip())
    todo = [it for it in items if (not want or it["id"] in want) and (a.force or not (os.path.exists(it["path"]) and is_png(it["path"])))]
    if not todo:
        print("만들 삽화가 없습니다(모두 있음). 다시 만들려면 --force")
        sheet(pj, items)
        return
    why = codex_ready()
    if why:
        p = sheet(pj, items, failed={it["id"]: why for it in todo})
        print("자동 생성 불가: %s\n직접 만들 프롬프트: %s" % (why, p))
        sys.exit(2)
    print("ChatGPT 이미지(codex)로 %d장 생성, 동시 %d장" % (len(todo), min(a.parallel, 5)))
    failed = gen(pj, todo, min(a.parallel, 5), a.timeout)
    p = sheet(pj, items, failed)
    if failed:
        print("\n실패 %d장 → 직접 만들 프롬프트: %s" % (len(failed), p))
        for k, v in failed.items():
            print("  - %s: %s" % (k, v))
        sys.exit(2)
    print("\n모두 만들었습니다. build 를 다시 돌리세요. 프롬프트 기록: %s" % p)


if __name__ == "__main__":
    main()
