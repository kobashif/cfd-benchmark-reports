#!/usr/bin/env python3
"""受託解析レポートの共通骨格。

各ベンチマークのレポート生成器（claude-3 / claude-4 / claude-5 の
postproc/build_report*.py）がこれを読んで、同じ体裁で出力する。

    表紙（文書番号・版数・発行日・解析コード・照合データ・準拠基準）
    改訂履歴
    目次（自動生成）
    章番号つきの見出し
    図表の通し番号
    適用範囲および留意事項
    参考文献
    付録（図表一覧）
    奥付

**読み物ではなく検査できる文書にする。** 見出しは中立な名詞句にする
（「分かったこと」「踏んだ罠」のような物語調にしない）。数値は本文に
直書きせず、計算結果から機械的に入れる。

分冊で出す場合は volume（「第 2 編」など）を与える。図表番号は分冊ごとに
1 から振り直し、表紙に分冊名を出す。

なぜ 1 箇所にまとめるか: 体裁を各生成器に写すと、片方だけ直して食い違う。
実際、通風レポートで同じ内容が 2 箇所に公開され、片方が訂正前の値のまま
残っていた。
"""
import base64, io, os, re

__all__ = ["CSS", "Doc", "num", "pct"]

CSS = """
:root{--ground:#EEF1F4;--paper:#FFFFFF;--sunk:#F2F5F7;--ink:#14202B;
--muted:#55697A;--faint:#8496A3;--rule:#C9D4DC;--rule2:#8FA3B0;
--accent:#14406B;--good:#0E6B52;--warn:#9A5B06;--bad:#95261C;
--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-size:15px;
line-height:1.85;font-family:-apple-system,BlinkMacSystemFont,
"Hiragino Kaku Gothic ProN","Noto Sans JP","Yu Gothic",sans-serif;
font-feature-settings:"palt"}
.sheet{max-width:960px;margin:0 auto;background:var(--paper);
padding:52px 62px 84px;box-shadow:0 1px 3px rgba(20,32,43,.10)}
.cover{border-bottom:3px double var(--rule2);padding-bottom:30px;margin-bottom:8px}
.cover .kind{font-family:var(--mono);font-size:11.5px;letter-spacing:.22em;
color:var(--accent);margin-bottom:10px}
.cover .vol{font-size:13px;color:var(--muted);margin-bottom:16px;
font-weight:600;letter-spacing:.04em}
.cover h1{font-size:27px;line-height:1.45;margin:0 0 6px;font-weight:700}
.cover .sub{font-size:16.5px;color:var(--muted);margin:0 0 26px}
.cover dl{display:grid;grid-template-columns:8.5em 1fr;gap:3px 16px;
font-size:13.5px;margin:0}
.cover dt{color:var(--faint)}
.cover dd{margin:0;font-family:var(--mono);font-variant-numeric:tabular-nums}
.series{font-size:13px;color:var(--muted);border:1px solid var(--rule);
background:var(--sunk);padding:10px 16px;margin:18px 0 0}
.series a{color:var(--accent)}
h2{font-size:19px;margin:44px 0 12px;padding:10px 0 8px;
border-top:2px solid var(--rule2);border-bottom:1px solid var(--rule)}
h3{font-size:15.5px;margin:26px 0 8px;color:var(--accent)}
h4{font-size:14px;margin:18px 0 6px}
p{margin:0 0 12px}
ul,ol{margin:0 0 12px;padding-left:1.5em}
li{margin:0 0 4px}
nav.toc{background:var(--sunk);border:1px solid var(--rule);padding:18px 26px;
margin:26px 0 8px;font-size:14px}
nav.toc h2{border:none;margin:0 0 8px;padding:0;font-size:15px}
nav.toc ol{list-style:none;padding:0;margin:0;columns:2;column-gap:34px}
nav.toc li{margin:0 0 3px;break-inside:avoid}
nav.toc a{color:var(--ink);text-decoration:none;border-bottom:1px dotted var(--rule2)}
nav.toc a:hover{color:var(--accent)}
.scroller{overflow-x:auto;margin:6px 0 4px}
table{border-collapse:collapse;width:100%;font-size:13.5px;background:var(--paper)}
th,td{border:1px solid var(--rule);padding:7px 10px;text-align:left;
vertical-align:top}
th{background:var(--sunk);font-weight:600;font-size:12.5px;color:var(--muted)}
td.num{font-family:var(--mono);font-variant-numeric:tabular-nums;text-align:right}
tbody tr:nth-child(even){background:#FAFCFD}
caption{caption-side:top;text-align:left;font-size:13px;color:var(--muted);
padding:10px 0 5px;font-weight:600}
.capnote{font-size:12.5px;color:var(--faint);margin:3px 0 20px;line-height:1.7}
figure{margin:16px 0 22px}
img,video{max-width:100%;height:auto;border:1px solid var(--rule);
background:var(--paper)}
figcaption{font-size:13px;color:var(--muted);font-weight:600;margin-top:8px}
figcaption .n{color:var(--accent)}
.note{border:1px solid var(--rule);border-left:4px solid var(--accent);
background:var(--sunk);padding:13px 17px;margin:16px 0;font-size:14px}
.note.good{border-left-color:var(--good)}
.note.warn{border-left-color:var(--warn)}
.note.bad{border-left-color:var(--bad)}
.note h4{margin:0 0 6px;font-size:14px}
.note p:last-child{margin-bottom:0}
span.good{color:var(--good);font-weight:600}
span.warn{color:var(--warn);font-weight:600}
span.bad{color:var(--bad);font-weight:600}
code{font-family:var(--mono);font-size:.9em;background:var(--sunk);
padding:1px 4px;border-radius:2px}
.refs{font-size:13.5px}
.refs li{margin-bottom:7px}
.sig{margin-top:44px;border-top:1px solid var(--rule);padding-top:14px;
font-size:12.5px;color:var(--faint);font-family:var(--mono)}
@media print{body{background:#fff}.sheet{box-shadow:none;max-width:none;padding:0}
h2{break-after:avoid}figure,table{break-inside:avoid}nav.toc{break-after:page}}
@media(max-width:760px){.sheet{padding:30px 20px 60px}nav.toc ol{columns:1}
.cover h1{font-size:22px}}
"""


def num(v, fmt="%.4g", dash="—"):
    """欠測を黙って数字にしない。"""
    if v is None:
        return dash
    try:
        if isinstance(v, float) and v != v:
            return dash
        return fmt % v
    except (TypeError, ValueError):
        return str(v)


def pct(v, fmt="%.0f %%"):
    return "—" if v is None else fmt % (100.0 * v)


class Doc(object):
    """章番号・図番号・表番号を通しで振り、目次を自動で作る。"""

    def __init__(self, repdir, title, subtitle, docno, rev, date,
                 volume=None, meta=None, series=None):
        self.rep = repdir
        self.body, self.toc = [], []
        self.nfig = self.ntbl = self.nvid = 0
        self.figs, self.tbls = [], []
        self.title, self.subtitle = title, subtitle
        self.docno, self.rev, self.date = docno, rev, date
        self.volume = volume
        self.meta = meta or []
        self.series = series or []

    # ------------------------------------------------------------ 本体 --
    def a(self, s):
        self.body.append(s)

    def cover(self):
        self.a('<div class="sheet">')
        self.a('<div class="cover">')
        self.a('<div class="kind">数値流体解析 報告書 / CFD ANALYSIS REPORT</div>')
        if self.volume:
            self.a('<div class="vol">%s</div>' % self.volume)
        self.a("<h1>%s</h1>" % self.title)
        if self.subtitle:
            self.a('<p class="sub">%s</p>' % self.subtitle)
        rows = [("文書番号", self.docno), ("版数", self.rev),
                ("発行日", self.date)] + list(self.meta)
        self.a("<dl>%s</dl>"
               % "".join("<dt>%s</dt><dd>%s</dd>" % kv for kv in rows))
        if self.series:
            self.a('<div class="series"><b>本報告書はシリーズの一編です。</b> %s</div>'
                   % " ／ ".join(self.series))
        self.a("</div>")

    def revisions(self, rows, note=None):
        self.tbl("改訂履歴", ["版", "日付", "改訂内容"], rows, note)

    def toc_placeholder(self):
        self.a("__TOC__")

    def h2(self, numstr, title):
        # 「1.」は番号、「付録 A」は名称なので区切りを変える。
        sep = "　" if str(numstr).startswith("付録") else ". "
        aid = "s" + re.sub(r"[^0-9A-Za-z]", "_", str(numstr))
        self.toc.append((aid, "%s%s%s" % (numstr, sep, title)))
        self.a('<h2 id="%s">%s%s%s</h2>' % (aid, numstr, sep, title))

    def h3(self, numstr, title):
        self.a("<h3>%s %s</h3>" % (numstr, title))

    # ------------------------------------------------------------ 図表 --
    def fig(self, name, caption, note=None, maxw=940):
        self.nfig += 1
        self.figs.append((self.nfig, caption))
        p = os.path.join(self.rep, name)
        if not os.path.exists(p):
            self.a('<p class="capnote">（図 %d　%s — 画像 %s が未生成）</p>'
                   % (self.nfig, caption, name))
            return
        b = base64.b64encode(open(p, "rb").read()).decode()
        kind = "svg+xml" if name.lower().endswith(".svg") else "png"
        self.a('<figure><img src="data:image/%s;base64,%s" alt="%s" '
               'style="width:100%%;max-width:%dpx">'
               '<figcaption><span class="n">図 %d</span>　%s</figcaption>%s</figure>'
               % (kind, b, caption, maxw, self.nfig, caption,
                  '<p class="capnote">%s</p>' % note if note else ""))

    def video(self, src, caption, note=None, maxw=940):
        self.nvid += 1
        self.a('<figure><video controls style="width:100%%;max-width:%dpx">'
               '<source src="%s" type="video/mp4"></video>'
               '<figcaption><span class="n">動画 %d</span>　%s</figcaption>%s</figure>'
               % (maxw, src, self.nvid, caption,
                  '<p class="capnote">%s</p>' % note if note else ""))

    def tbl(self, caption, head, rows, note=None):
        self.ntbl += 1
        self.tbls.append((self.ntbl, caption))
        h = "".join("<th>%s</th>" % c for c in head)
        body = ""
        for r in rows:
            tds = ""
            for c in r:
                c = "" if c is None else str(c)
                isnum = re.fullmatch(r"[-+0-9.,%\s×^<>=eE−:/]*|—", c)
                tds += ('<td class="num">%s</td>' if isnum else "<td>%s</td>") % c
            body += "<tr>%s</tr>" % tds
        self.a('<div class="scroller"><table><caption>表 %d　%s</caption>'
               "<thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>"
               % (self.ntbl, caption, h, body))
        if note:
            self.a('<p class="capnote">%s</p>' % note)

    def note(self, heading, html, kind=""):
        self.a('<div class="note %s"><h4>%s</h4>%s</div>' % (kind, heading, html))

    # ------------------------------------------------------------ 付録 --
    def appendix_lists(self):
        self.h2("付録", "図表一覧")
        if self.figs:
            self.a("<p><b>図</b></p><ol>%s</ol>"
                   % "".join("<li>%s</li>" % c for _, c in self.figs))
        if self.tbls:
            self.a("<p><b>表</b></p><ol>%s</ol>"
                   % "".join("<li>%s</li>" % c for _, c in self.tbls))

    def colophon(self, extra=()):
        lines = ["文書番号 %s ／ 版 %s ／ 発行 %s" % (self.docno, self.rev, self.date)]
        lines += list(extra)
        self.a('<div class="sig">%s</div>'
               % "".join("<div>%s</div>" % x for x in lines))
        self.a("</div>")

    # ------------------------------------------------------------ 出力 --
    def render_toc(self):
        return ('<nav class="toc"><h2>目次</h2><ol>%s</ol></nav>'
                % "".join('<li><a href="#%s">%s</a></li>' % t for t in self.toc))

    def write(self, path, description=""):
        head = ["<!doctype html>", '<html lang="ja">', "<head>",
                '<meta charset="utf-8">',
                '<meta name="viewport" content="width=device-width,initial-scale=1">',
                "<title>%s — %s 版 %s</title>"
                % (re.sub(r"<[^>]+>", " ", self.title), self.docno, self.rev)]
        if description:
            head.append('<meta name="description" content="%s">' % description)
        head += ["<style>%s</style>" % CSS, "</head>", "<body>"]
        out = "\n".join(head + self.body + ["</body>", "</html>"])
        out = out.replace("__TOC__", self.render_toc())
        io.open(path, "w", encoding="utf-8").write(out + "\n")
        return len(out.encode("utf-8"))
