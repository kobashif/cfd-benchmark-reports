#!/usr/bin/env python3
"""**経緯のページ**を仕様（JSON）から作る。

    usage: make_history.py <spec.json> -o <out.html>

家の型（`cfd-report` スキル「結果と経緯は別ページにする」）では、
訂正・誤りの記録・検討の途中経過は本編から切り出して別ページに置く。
そのページを**手書きの HTML で作ると、レポートごとに体裁がずれる。**
既に 5 本が手書きで、CSS を貼り回している。ここで 1 本にまとめる。

仕様の形（JSON）

    {
     "title":  "検討の経緯",
     "docline": "AIJ ケース C 風環境 CFD 解析報告書 — CFD-AIJ-C-001",
     "back":   "index.html",
     "intro":  "<p>…このページは結果ではない…</p>",
     "sections": [{"h": "1. …", "html": "<p>…</p>"}, …]
    }

**本文（html）はそのまま出す。**エスケープしない。書く側が HTML を
書く前提である（既存の 5 本と同じ）。
"""
import argparse, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reportkit as RK


def build(spec):
    o = ['<!doctype html><html lang="ja"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>%s — %s</title>" % (spec.get("docline", ""),
                                     spec.get("title", "検討の経緯")),
         "<style>%s</style></head><body><div class=\"wrap\">" % RK.CSS]
    back = spec.get("back", "index.html")
    o.append('<p class="capnote"><a href="%s">← 結果のページへ戻る</a></p>' % back)
    o.append("<h1>%s</h1>" % spec.get("title", "検討の経緯"))
    o.append('<p class="capnote"><b>このページは結果ではない。</b>'
             'どこで誤り、どう直したかの記録である。'
             '結果は<a href="%s">本編</a>にある。</p>' % back)
    for s in spec["sections"]:
        o.append("<h2>%s</h2>" % s["h"])
        o.append(s["html"])
    o.append('<p class="capnote"><a href="%s">← 結果のページへ戻る</a></p>' % back)
    o.append("</div></body></html>")
    return "".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    spec = json.load(io.open(a.spec, encoding="utf-8"))
    if not spec.get("sections"):
        raise SystemExit("**節が 1 つも無い。経緯が無いなら頁を作らない**")
    h = build(spec)
    io.open(a.out, "w", encoding="utf-8").write(h)
    print("書いた: %s（%.1f KB・%d 節）"
          % (a.out, len(h.encode("utf-8")) / 1024, len(spec["sections"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
