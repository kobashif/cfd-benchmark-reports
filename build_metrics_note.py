#!/usr/bin/env python3
"""検証指標の考え方を、独立した 1 編として組み立てる。

    usage: build_metrics_note.py [--hitrate <hitrate_F.json>]
           -> metrics/index.html

**なぜ別頁にするか。**RMSE と R² だけでは足りない場面の扱いは、
ケース F に限った話ではない。各報告書に同じ説明を写すと、片方だけ
直して食い違う（通風レポートで実際に起きた）。**1 箇所に置いて、
各報告書から参照する。**

数値は claude-10/report/hitrate_F.json などから読む。**本文に直書きしない。**

出典
    VDI 3783 Blatt 9: Environmental meteorology - Prognostic microscale
        wind field models - Evaluation for flow around buildings and obstacles
    COST Action 732: Model evaluation guidance and protocol document
    AIJ UWE Benchmark Dataset - Case F (Shinjuku), doi:10.5281/zenodo.15589622
"""
import argparse, datetime, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reportkit as RK

DEF_HR = "/mnt/c/Users/DZH05/claude-10/report/hitrate_F.json"
DEF_VAR = "/mnt/c/Users/DZH05/claude-10/report/variants_F_E.json"
DEF_MET = "/mnt/c/Users/DZH05/claude-10/report"


def jload(p):
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else {}


def both_r2(rows):
    """同じ点から 2 つの R² を出す。**分母が違う。**

        ガイドブック型  1 - S(y-ax)^2 / S(y-ybar)^2   分母は計算値
        1:1 型（NS）    1 - S(y-x)^2  / S(x-xbar)^2   分母は実測値
    """
    import numpy as np
    x = np.array([r["exp"] for r in rows], float)
    y = np.array([r["cfd"] for r in rows], float)
    a = float((x * y).sum() / (x * x).sum())
    gb = 1 - ((y - a * x) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    ns = 1 - ((y - x) ** 2).sum() / ((x - x.mean()) ** 2).sum()
    return float(gb), float(ns)


def rows_of(wd, repdir):
    """その風向の照合行（風洞優先、無ければ現地）。"""
    import glob
    best = None
    for q in sorted(glob.glob(os.path.join(repdir, "metrics_F_*.json"))):
        d = json.load(io.open(q, encoding="utf-8"))
        if d.get("wd") != wd:
            continue
        if best is None or len(d["run"]) >= len(best["run"]):
            best = d
    if not best:
        return None, None
    for k, v in best["results"].items():
        if k.startswith("RS-WT"):
            return v["rows"], "風洞"
    for k, v in best["results"].items():
        if k.startswith("RS-FO"):
            return v["rows"], "現地"
    return None, None


def r2_of(wd, repdir):
    """その風向の R²（風洞優先、無ければ現地）を metrics から拾う。"""
    import glob
    best = None
    for p in sorted(glob.glob(os.path.join(repdir, "metrics_F_*.json"))):
        d = json.load(io.open(p, encoding="utf-8"))
        if d.get("wd") != wd:
            continue
        if best is None or len(d["run"]) >= len(best["run"]):
            best = d
    if not best:
        return None, None
    for k, v in best["results"].items():
        if k.startswith("RS-WT"):
            return v["r2"], "風洞"
    for k, v in best["results"].items():
        if k.startswith("RS-FO"):
            return v["r2"], "現地"
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hitrate", default=DEF_HR)
    ap.add_argument("--variants", default=DEF_VAR)
    ap.add_argument("--metrics", default=DEF_MET)
    ap.add_argument("--rev", default="1.0")
    ap.add_argument("--docno", default="CFD-METRICS-001")
    ap.add_argument("--date", default=None)
    a = ap.parse_args()
    date = a.date or datetime.date.today().isoformat()
    HR = jload(a.hitrate)
    VR = jload(a.variants)
    rep = os.path.join(HERE, "metrics")
    os.makedirs(rep, exist_ok=True)

    D = RK.Doc(
        rep,
        "検証指標の考え方<br>RMSE と R² だけでは足りない場面",
        "実測値の小さい点・測定の不確かな点をどう扱うか。"
        "hit rate（VDI 3783/9・COST Action 732）の導入と、"
        "測点を除いてよい条件",
        a.docno, a.rev, date,
        meta=[("適用範囲", "本サイトの全ベンチマーク報告書に共通"),
              ("参照元", "各報告書の妥当性確認の章から参照される"),
              ("題材", "AIJ ケース F（新宿・実市街地）の実測と計算")],
        series=["本編は個別のケースに属さない共通の編である"])
    D.cover()
    D.revisions([[a.rev, date,
                  "初版。hit rate の導入、W の決め方、"
                  "測点を除いてよい条件、ケース F 東風向の実例"]])
    D.toc_placeholder()

    # ---------------------------------------------------------- 1 --
    D.h2("1", "R² は「どの定義か」を書かずに使わない")
    D.a("<p>同じ「決定係数」という語が、少なくとも 2 つの別の量を"
        "指す。<b>分母が違う。</b></p>")
    D.tbl("2 つの決定係数",
          ["呼び方", "式", "分母", "負のときの意味"],
          [["ガイドブック型（原点通過回帰）",
            "1 − Σ(y−ax)² / Σ(y−ȳ)²　　a = Σxy/Σx²",
            "<b>計算値</b> y の分散",
            "原点を通る比例関係が、計算値のばらつきを"
            "計算値の平均以下にしか説明できない"],
           ["1:1 型（Nash–Sutcliffe）",
            "1 − Σ(y−x)² / Σ(x−x̄)²",
            "<b>実測値</b> x の分散",
            "実測の平均を答えにした方がまだ当たる"]],
          "x = 実測、y = 計算。<b>本サイトの報告書は上段の形"
          "（分母が計算値の分散）を用いている。</b>")
    D.a('<div class="note bad"><h4>訂正 &mdash; 「資料と同じ定義」とは書けない</h4>'
        "<p>初版はこの形を「AIJ ガイドブック 5.2 と同じ形」と書いていた。"
        "<b>資料を照合せずに書いていた。</b>指摘を受けて資料に当たった。</p>"
        "<p><b>資料は R² の定義を示していない。</b>図 5.2.4 とその周辺"
        "（第 3 編 5.2、pp.148-152）に式は無く、図中に "
        "「y = 0.91x／R² = 0.86」と値だけが置かれている。"
        "巻末の記号表にも無い。<b>したがって「同じ定義」と書ける根拠は、"
        "そもそも資料の側に存在しない。</b></p>"
        "<p>ただし図から 2 つ分かった。"
        "<b>軸は x = 実験・y = CFD で、本サイトと同じ向きである。</b>"
        "そして<b>中心化しない定義（分母 &Sigma;y²）は除外できる</b>&mdash;"
        "同図の k は R² = &minus;0.13 と負だが、原点通過の最小二乗では"
        "分母を &Sigma;y² に取ると "
        "R² = (&Sigma;xy)² / (&Sigma;x²&middot;&Sigma;y²) となり、"
        "<b>負になりえない</b>（2 万通りの乱数で確認）。"
        "残るのは中心化した 2 つだが、<b>どちらかは図からは決まらない。</b></p>"
        "<p><b>本サイトは分母を計算値の分散とする。</b>資料と同じかどうかは"
        "言わない。<b>傾き a は定義が一意（a = &Sigma;xy/&Sigma;x²）なので"
        "比較してよいが、R² を資料の値と並べるときは"
        "「別の量かもしれない」と断ること。</b></p></div>")
    rr2 = []
    for wd in sorted(HR or {}):
        rr, src = rows_of(wd, a.metrics)
        if not rr:
            continue
        gb, ns = both_r2(rr)
        rr2.append([wd, src, "%+.3f" % gb, "%+.3f" % ns,
                    "<b>逆転</b>" if (gb >= 0) != (ns >= 0) else ""])
    if rr2:
        D.tbl("同じ計算・同じ実測でも、定義が変われば値も符号も変わる"
              "（ケース F）",
              ["風向", "測器", "ガイドブック型", "1:1 型", "符号"], rr2,
              "<b>正負が逆転する風向がある。</b>"
              "「決定係数が正だから当たっている」とは言えない。"
              "<b>報告書には式そのものを書く。</b>")
    D.note("この取り違えを実際にやった",
           "公開済みの報告書に「決定係数 −0.22 は負であり、実測の平均値を"
           "返すより当たらない」と書いたが、用いていたのはガイドブック型で、"
           "その説明は 1:1 型のものだった。"
           "<b>数値は正しく、説明文だけが定義に合っていなかった。</b>"
           "2026-09-06 に訂正した。")

    D.h2("2", "問題")
    D.a("<p>RMSE と R² は<b>全点を同じ重みで足す。</b>したがって"
        "<b>実測値の小さい点と、測定そのものが不確かな点が結果を支配する。</b>"
        "その 2 つは実務でしばしば同じ点である。風速の小さい場所は"
        "測るのが難しい。</p>")
    fo = None
    for wd, rec in (HR or {}).items():
        r = rec.get("instruments", {}).get("RS-FO", {})
        if "W_from_sigma" in r:
            fo = r["W_from_sigma"]
            break
    if fo:
        D.a("<p>ケース F の現地観測を例にとる。データセットは測点ごとに"
            "ばらつき <code>sigma_U/R</code> を持っており、その中央値は"
            "<b>%.3f</b> である。実測値の中央値が 0.250 なので、"
            "<b>測定のばらつきが値の 3 割を超える。</b>"
            "この上に RMSE を当てると、測れていない量を当てにいくことになる。</p>"
            % fo["median"])

    rows = []
    for wd, rec in (HR or {}).items():
        r2, src = r2_of(wd, a.metrics)
        inst = rec.get("instruments", {})
        q = None
        if "RS-WT" in inst:
            q = inst["RS-WT"]["q_by_W"].get("0.06")
            qs = "風洞 q = %.2f" % q
        elif "RS-FO" in inst:
            q = inst["RS-FO"].get("W_from_sigma", {}).get("q")
            qs = "現地 q = %.2f" % q if q is not None else "—"
        else:
            qs = "—"
        # **閾値を決めて食い違いを見る。**R² は 0.5 以上を「良い」、
        # hit rate は 0.66 以上を「合格」とする（後者は規格の目安）。
        # 前者に規格はないので、こちらで決めた値であることを注に書く。
        mark = ""
        if r2 is not None and q is not None:
            if (r2 >= 0.5) != (q >= 0.66):
                mark = "<b>食い違う</b>"
        rows.append([wd, "%+.3f" % r2 if r2 is not None else "—",
                     src or "—", qs, mark])
    if rows:
        D.tbl("R² と hit rate は同じ順位を与えない（ケース F・風向ごと）",
              ["風向", "R²", "R² の測器", "hit rate（W = 0.06 / σ）", "備考"],
              rows,
              "R² は 0.5 以上を「良い」、hit rate は 0.66 以上を「合格」と"
              "して食い違いを印した。<b>後者は規格の目安、前者は当方が"
              "決めた値である。</b><br>"
              "<b>2 つの指標は逆向きにも食い違う。</b>"
              "東（E）は R² が低い（+0.103）のに hit rate は 0.69 で合格し、"
              "南西（SW）は R² が高い（+0.680）のに hit rate は 0.59 で"
              "届かない。R² は点の並び方を、hit rate は点ごとの外れ方を"
              "見ている。<b>別のことを測っている。</b>")
        D.a('<div class="note"><h4>なぜ逆向きに食い違うのか</h4>'
            "<p><b>R² は差を二乗して足す。</b>大きく外れた点が数個あれば、"
            "その二乗が総和を支配する。ほかの点がどれだけ揃っていても、"
            "値は下がる。<b>外れの「大きさ」に効く指標である。</b></p>"
            "<p><b>hit rate は帯に入ったかどうかを数える。</b>"
            "帯を 1 歩出た点も、大きく外れた点も、同じ「1 つの外れ」として"
            "数える。<b>外れの「個数」に効く指標である。</b></p>"
            "<p>東（E）は<b>多くの点が帯に収まり、少数が大きく外れている</b>"
            "&mdash;だから hit rate は高く、R² は低い。"
            "南西（SW）は逆で、<b>点の並びは比例関係に乗っているが、"
            "多くの点が帯の外にある</b>。"
            "<b>どちらか一方だけを見て良し悪しを決めない。</b></p></div>")

    # ---------------------------------------------------------- 2 --
    D.h2("3", "hit rate の定義")
    D.a("<p>欧州の微気象モデル評価では、点ごとに<b>2 つの許容幅の"
        "どちらか</b>を満たせば「当たり」と数える。</p>")
    D.a('<p class="note" style="font-family:var(--mono)">'
        "当たり ⟺ |M − O| ≤ W　<b>または</b>　|M − O| / |O| ≤ D</p>")
    D.tbl("記号", ["記号", "意味", "本サイトで用いる値"],
          [["M", "計算値", "—"],
           ["O", "実測値", "—"],
           ["W", "許容する絶対偏差（測定誤差の大きさ）", "3 章"],
           ["D", "許容する相対偏差", "0.25"],
           ["q", "当たりの割合（hit rate）", "合格の目安 0.66 以上"]],
          "D = 0.25 と q ≥ 0.66 は VDI 3783 Blatt 9 および "
          "COST Action 732 による。")
    D.a('<p class="note"><b>実測値が 0 の点をどう扱うか。</b>'
        "相対の側は |O| で割るので、O = 0 の点があるとそのままでは"
        "0 除算になる。<b>本サイトの実装は、|O| が丸め誤差の水準"
        "（10<sup>&minus;12</sup>）以下のとき相対の項を無限大として扱い、"
        "絶対偏差 |M − O| ≤ W だけで判定する。</b>"
        "微小量を分母に足す方法は取らない&mdash;足す量で結果が変わり、"
        "その量に根拠を置けないためである。</p>"
        "<p>本サイトが扱っているデータには 0 の実測値は無い"
        "（ケース F の最小値は風洞 0.094・現地 0.080）。"
        "<b>それでも規則は決めて書いておく。</b>"
        "他のデータに当てたときに黙って壊れないようにするためである。</p>")
    D.a("<p><b>W が実測値の小さい点を救う。</b>相対誤差がどれだけ大きくても、"
        "絶対差が測定誤差の中なら当たりになる。"
        "<b>点を消さずに、重みだけが下がる。</b>"
        "これが「重要でない点を無視してよいか」という問いに対する、"
        "規格の側の答えである。<b>無視するのではなく、"
        "許容幅を二本立てにする。</b></p>")

    # ---------------------------------------------------------- 3 --
    D.h2("4", "W をどう決めるか")
    D.a("<p><b>規格は変数ごとに W を定めているが、規格本体は有償であり、"
        "本サイトでは値を確認していない。したがって推測で置かない。</b>"
        "代わりに次の 2 通りとし、読み手が自分の W で読み替えられるように"
        "する。</p>")
    D.a("<ul>"
        "<li><b>測定のばらつきが公表されている場合</b>——それをそのまま "
        "W にする。ケース F の現地観測は測点ごとに "
        "<code>sigma_U/R</code> を持つので、点ごとの W として使う。"
        "<b>最も根拠が明確である。</b></li>"
        "<li><b>公表されていない場合</b>——W を振って q の動きを示す。"
        "単一の値を選ばない。</li></ul>")
    sw = None
    for wd, rec in (HR or {}).items():
        inst = rec.get("instruments", {})
        if "RS-WT" in inst:
            sw = (wd, inst["RS-WT"])
            break
    if sw:
        wd, r = sw
        ks = sorted(r["q_by_W"].keys(), key=float)
        D.tbl("W を振ったときの hit rate（例: ケース F 風向 %s・風洞 %d 点）" % (wd, r["n"]),
              ["W"] + ks,
              [["q"] + ["%.2f" % r["q_by_W"][k] for k in ks]],
              "<b>W = 0 は相対偏差だけで判定した場合である。</b>"
              "W を上げると当たりが増えるのは当然であり、"
              "<b>W の根拠を書かずに q だけを示してはならない。</b>")
        # **表だけでは跳ねる位置が読み取りにくい。**折れ線で示す。
        _p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "metrics", "wsweep.png")
        if os.path.exists(_p):
            import base64
            _b = base64.b64encode(io.open(_p, "rb").read()).decode("ascii")
            D.a('<figure><img src="data:image/png;base64,%s" '
                'alt="W を振ったときの hit rate" '
                'style="width:100%%;height:auto;display:block">'
                "<figcaption>W を振ったときの hit rate（ケース F・全風向）。"
                "<b>折れ線が立ち上がる位置に、測点の食い違いが集まっている。</b>"
                "風洞では W = 0.10 付近で跳ねる風向が多く、"
                "<b>多くの測点が 0.06〜0.10 の差を抱えている</b>ことが読める。"
                "破線は合格の目安 q = 0.66。"
                "<b>W をいくつに取るかで合否が変わるので、"
                "単一の W で「合格」と書かない。</b></figcaption></figure>"
                % _b)

    # ---------------------------------------------------------- 4 --
    D.h2("5", "測点を除いてよい条件")
    D.a("<p>計算の主目的に照らして重要でない箇所を評価から外すことは、"
        "<b>次の 3 つをすべて満たす場合に限り</b>正当である。</p>")
    D.tbl("測点を除くための条件", ["条件", "なぜ必要か"],
          [["基準を<b>当てはめる前に</b>決める",
            "結果を見てから決めると、都合の良い部分集合を選べてしまう"],
           ["基準が<b>重要性</b>に基づく（当たり外れではない）",
            "「歩行者が立てない場所」は重要性、"
            "「合わなかった点」は当たり外れである。後者は選別にあたる"],
           ["<b>除いたことと理由を書き、除く前の値も併記する</b>",
            "読み手が自分で判断できる形にする"]],
          "<b>この 3 つを満たせないなら、除かずに hit rate を使う。</b>"
          "W が同じ役目を果たし、しかも恣意性が残らない。")

    # ---------------------------------------------------------- 5 --
    D.h2("6", "実例 — ケース F 東風向の 1 点")
    if VR:
        op = VR.get("oscillating_point", {})
        D.a("<p>ケース F の風向 E では、13 点のうち<b>1 点だけ</b>が"
            "定常計算のなかで振動し続けた（測点 %s）。"
            "書き出した時刻ごとに %.3f と %.3f を往復し、振れは %.4f。"
            "残る 12 点の振れは中央値で 0.0002 である。</p>"
            % (op.get("no", "—"), op.get("phase_mean", 0),
               op.get("last", 0), op.get("spread", 0)))
        rows = []
        for k in ("全13点・最終時刻", "全13点・末尾4時刻の平均",
                  "静かな12点・最終時刻"):
            v = VR.get(k)
            if not v:
                continue
            rows.append([k.replace("・", " ／ "), v["n"],
                         "%.3f" % v["slope"], "%+.3f" % v["r2"],
                         "%.4f" % v["rmse"], "%+.4f" % v["bias"]])
        if rows:
            D.tbl("1 点の扱いを変えたときの指標（ケース F 風向 E・現地観測）",
                  ["扱い", "点数", "傾き", "R²", "RMSE", "偏り"], rows,
                  "<b>どの扱いでも R² は負のままである。</b>"
                  "したがって振動する 1 点はこの風向の不一致の主因ではない。"
                  "<b>もし扱いによって R² が正負をまたいでいたなら、"
                  "1 通りだけを示すことは誠実でない。</b>"
                  "本サイトでは扱いを変えた結果を並べて示す。")
    D.a("<p>この例が示すのは、<b>除くか除かないかを決める前に、"
        "除いた場合と除かない場合の両方を計算しておく</b>ことの意味である。"
        "結論が変わらないなら、どちらを主に据えても議論は成り立つ。"
        "結論が変わるなら、<b>それ自体が報告すべき事実である。</b></p>")

    # ---------------------------------------------------------- 6 --
    D.h2("7", "本サイトでの報告の仕方")
    D.a("<ul>"
        "<li><b>RMSE・R²・hit rate を併記する。</b>どれか 1 つでは"
        "判断を誤る</li>"
        "<li><b>hit rate には W と D を必ず添える。</b>"
        "W の根拠（測定のばらつきか、振った値か）も書く</li>"
        "<li><b>測点を除いた場合は、除く前の値も出す</b></li>"
        "<li><b>定常計算が落ち着かない点があれば、その点と振れ幅を示す</b></li>"
        "</ul>")

    # ---------------------------------------------------------- 7 --
    D.h2("8", "参考文献")
    D.a("<ol>"
        "<li>VDI 3783 Blatt 9: <i>Environmental meteorology — Prognostic "
        "microscale wind field models — Evaluation for flow around buildings "
        "and obstacles</i>. Verein Deutscher Ingenieure.</li>"
        "<li>COST Action 732: <i>Model evaluation guidance and protocol "
        "document</i>. Britter, R. and Schatzmann, M. (eds.), 2007.</li>"
        "<li>Di Sabatino, S. ほか: <i>A model evaluation protocol for urban "
        "scale flow and dispersion models</i>.</li>"
        "<li>Tominaga, Y. ほか (2008). AIJ guidelines for practical "
        "applications of CFD to pedestrian wind environment around buildings. "
        "<i>JWEIA</i> 96, 1749–1761.</li>"
        "<li>AIJ UWE Benchmark Dataset — Case F (Shinjuku), "
        "doi:10.5281/zenodo.15589622（CC BY 4.0）</li>"
        "</ol>")
    D.a('<p class="note"><b>規格本体（VDI 3783 Blatt 9）は有償であり、'
        "本サイトでは購入していない。</b>したがって規格が定める W の値は"
        "参照していない。本編の W の扱いは、公開文献に記載された定義"
        "（D = 0.25、q ≥ 0.66）にもとづく<b>当方の判断である。</b></p>")

    D.appendix_lists()
    D.colophon(extra=(
        "本編の数値は hitrate_F.json、variants_F_E.json、metrics_F_*.json "
        "から機械的に生成しており、本文に直接記入した値は無い。",))
    p = os.path.join(rep, "index.html")
    n = D.write(p, "RMSE と R² だけでは足りない場面の扱い。"
                   "hit rate（VDI 3783/9・COST 732）の導入と、"
                   "測点を除いてよい条件")
    print("書いた: %s" % p)
    print("  図 %d 点 / 表 %d 点  風向 %d" % (D.nfig, D.ntbl, len(HR or {})))
    if not HR:
        print("  **hitrate_F.json を読めなかった。表が空になっている**")
    return 0


if __name__ == "__main__":
    sys.exit(main())
