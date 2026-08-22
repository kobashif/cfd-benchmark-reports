#!/usr/bin/env python3
"""公開サイトの反映漏れを機械的に洗う。

    usage: python3 check_site.py [--live]

見るもの:
  1. リンク切れ         href / src の指す先がリポジトリに存在するか
  2. 孤立ファイル       置いてあるがどこからも参照されていないファイル
  3. 未 push            コミット済みだが push されていない変更
  4. 生成元との差       各レポートの生成元と公開版が一致しているか
  5. 公開中の実物       --live で GitHub Pages を取得し、手元と同じか

なぜ要るか: ケース E で、本文には壁関数の検証が入っているのに末尾の一覧だけ
「まだ試していない」のまま公開していた。人が読み返して気づくのを当てにすると
必ず漏れる。せめて機械で分かる範囲は機械に見させる。

内容の齟齬（本文と一覧の食い違いなど）はここでは検出できない。それは
STALE_CHECKS に「この文字列が残っていたら怪しい」という形で個別に足す。
"""
import argparse, hashlib, os, re, subprocess, sys, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = "https://kobashif.github.io/cfd-benchmark-reports/"

# 生成元 -> 公開先。生成元が更新されたのに公開していない、を検出する。
SOURCES = {
    "annex20-2d/index.html": "/mnt/c/Users/DZH05/claude-3/report/index.html",
    "annex20-caseE/index.html": "/mnt/c/Users/DZH05/claude-4/report/index.html",
    "crossvent/index.html": "/mnt/c/Users/DZH05/claude-2/crossvent-benchmark/index.html",
    "crossvent/grid-convergence.html":
        "/mnt/c/Users/DZH05/claude-2/crossvent-benchmark/grid-convergence.html",
    "crossvent/numerics.html":
        "/mnt/c/Users/DZH05/claude-2/crossvent-benchmark/numerics.html",
    "crossvent/videos.html":
        "/mnt/c/Users/DZH05/claude-2/crossvent-benchmark/videos.html",
}

# 残っていたら怪しい語。過去に実際やらかした型を登録していく。
# 教訓や説明の文中に出てくる語まで拾うと、警告が日常になって誰も読まなくなる。
# 「この文脈なら正当」と分かっているものはここで除外する。**除外は個別に、
# 理由を書いて足すこと。**まとめて無効化すると検出器の意味が無くなる。
ALLOW = [
    "実行中のシェルスクリプトを書き換えない",   # 教訓の見出し。状態表示ではない
    "実行中の編集はその実行を壊す",             # 同じ教訓の本文
    "バッチ実行中に run_case.sh",               # 同じ教訓の実例
]

STALE_CHECKS = [
    ("まだ試していない", "実施済みの項目が「未着手」のまま残っていないか"),
    ("未着手", "本当に未着手か。実施済みなら書き換える"),
    ("実行中", "公開時点で実行中だったものが、そのまま固定されていないか"),
    ("TODO", "書きかけが残っていないか"),
    ("lorem", "仮テキストが残っていないか"),
]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()


def html_files():
    out = []
    for d, _, fs in os.walk(ROOT):
        if ".git" in d:
            continue
        out += [os.path.join(d, f) for f in fs if f.endswith(".html")]
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="公開中の実物も取得して比べる")
    a = ap.parse_args()
    ng = 0

    # --- 1. リンク切れ -------------------------------------------------------
    print("== リンク切れ ==")
    referenced = set()
    bad = 0
    for f in html_files():
        s = open(f, encoding="utf-8", errors="ignore").read()
        base = os.path.dirname(f)
        for m in re.finditer(r'(?:href|src)="([^"]+)"', s):
            u = m.group(1)
            if u.startswith(("http", "//", "#", "data:", "mailto:")):
                continue
            t = os.path.normpath(os.path.join(base, u.split("#")[0].split("?")[0]))
            if t.endswith(os.sep) or os.path.isdir(t):
                t = os.path.join(t, "index.html")
            referenced.add(os.path.normpath(t))
            if not os.path.exists(t):
                print("  NG %s -> %s" % (os.path.relpath(f, ROOT), u))
                bad += 1
    print("  %s" % ("問題なし" if not bad else "%d 件" % bad))
    ng += bad

    # --- 2. 孤立ファイル -----------------------------------------------------
    print("\n== どこからも参照されていないファイル ==")
    orphan = []
    for d, _, fs in os.walk(ROOT):
        if ".git" in d:
            continue
        for f in fs:
            p = os.path.normpath(os.path.join(d, f))
            if f in ("check_site.py", ".nojekyll", "README.md", "index.html"):
                continue
            if p not in referenced:
                orphan.append(os.path.relpath(p, ROOT))
    if orphan:
        for o in sorted(orphan)[:20]:
            print("  ? %s" % o)
        if len(orphan) > 20:
            print("  ... 他 %d 件" % (len(orphan) - 20))
        print("  （動画など、意図して置いているものも混ざる。消す前に確認すること）")
    else:
        print("  問題なし")

    # --- 3. 生成元との差 -----------------------------------------------------
    print("\n== 生成元と公開版の一致 ==")
    for pub, src in SOURCES.items():
        p = os.path.join(ROOT, pub)
        if not os.path.exists(p):
            print("  NG 公開版が無い: %s" % pub); ng += 1; continue
        if not os.path.exists(src):
            print("  ?  生成元が見当たらない: %s" % src); continue
        if sha(p) == sha(src):
            print("  OK %s" % pub)
        else:
            print("  NG %s は生成元と違う（生成元を公開していない可能性）" % pub)
            ng += 1

    # --- 4. 未 push ----------------------------------------------------------
    print("\n== git ==")
    r = subprocess.run(["git", "-C", ROOT, "status", "--porcelain"],
                       capture_output=True, text=True)
    if r.stdout.strip():
        print("  未コミットの変更あり:")
        for l in r.stdout.strip().split("\n")[:10]:
            print("    %s" % l)
        ng += 1
    r = subprocess.run(["git", "-C", ROOT, "log", "--oneline", "origin/main..HEAD"],
                       capture_output=True, text=True)
    if r.stdout.strip():
        print("  未 push のコミット:")
        for l in r.stdout.strip().split("\n"):
            print("    %s" % l)
        ng += 1
    if not r.stdout.strip():
        print("  push 済み")

    # --- 5. 怪しい語 ---------------------------------------------------------
    print("\n== 残っていたら怪しい語 ==")
    hit = 0
    for f in html_files():
        s = open(f, encoding="utf-8", errors="ignore").read()
        for allowed in ALLOW:      # 変数名を a にしない。引数の名前空間を潰す
            s = s.replace(allowed, "")
        for w, why in STALE_CHECKS:
            n = s.count(w)
            if n:
                print("  %s: 「%s」 %d 件 — %s" % (os.path.relpath(f, ROOT), w, n, why))
                hit += 1
    if not hit:
        print("  問題なし")

    # --- 6. 公開中の実物 -----------------------------------------------------
    if a.live:
        print("\n== 公開中の実物との一致 ==")
        for pub in SOURCES:
            url = SITE + pub.replace("index.html", "")
            try:
                d = urllib.request.urlopen(url, timeout=60).read()
            except Exception as e:
                print("  NG %s 取得できない: %s" % (pub, e)); ng += 1; continue
            local = open(os.path.join(ROOT, pub), "rb").read()
            same = hashlib.sha256(d).hexdigest() == hashlib.sha256(local).hexdigest()
            print("  %s %s（%d バイト）" % ("OK" if same else "NG", pub, len(d)))
            if not same:
                print("     手元は %d バイト。Pages のビルド待ちか、push 漏れ" % len(local))
                ng += 1

    print("\n%s" % ("問題なし" if ng == 0 else "要対応 %d 件" % ng))
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
