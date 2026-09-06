#!/usr/bin/env python3
"""hit rate が許容偏差 W でどう動くかを描く。

    usage: plot_wsweep.py <hitrate_F.json> -o metrics/wsweep.png

査読で「W を振ったときの q の跳ね上がりは、どの誤差幅に測点が
集まっているかを表しているので、折れ線で見せたほうが分かる」と
指摘された。**表だけだと、跳ねる位置が読み取りにくい。**

**W は「測定の誤差として許す絶対偏差」である。**標準（VDI 3783
Blatt 9）が定める既定値は有料規格の中にあり確認できていないので、
本サイトは値を決め打ちにせず振って示す。この図はその振れ方そのものである。
"""
import argparse, io, json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
sys.path.insert(0, "/mnt/c/Users/DZH05/claude-5/postproc")
import jfont
jfont.use()
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cfdcolors as CC

Q_OK = 0.66


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("-o", "--out",
                    default=os.path.join(HERE, "metrics", "wsweep.png"))
    a = ap.parse_args()
    HR = json.load(io.open(a.src, encoding="utf-8"))

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.0), sharey=True)
    cm = plt.get_cmap("tab10")
    for ax, inst, ttl in ((axes[0], "RS-WT", "風洞 RS-WT"),
                          (axes[1], "RS-FO", "現地観測 RS-FO")):
        n = 0
        for i, wd in enumerate(sorted(HR)):
            rec = (HR[wd].get("instruments") or {}).get(inst)
            if not rec or not rec.get("q_by_W"):
                continue
            W = np.array([float(k) for k in sorted(rec["q_by_W"])])
            q = np.array([rec["q_by_W"][k] for k in sorted(rec["q_by_W"])])
            ax.plot(W, q, "-o", ms=4, lw=1.6, color=cm(i % 10), label=wd)
            n += 1
        ax.axhline(Q_OK, color="#b71c1c", lw=1.6, ls="--")
        ax.text(0.001, Q_OK + 0.012, "合格の目安 q = 0.66", color="#b71c1c",
                fontsize=9.5)
        ax.set_title("%s（%d 風向）" % (ttl, n), fontsize=12.5)
        ax.set_xlabel("許容する絶対偏差 W（風速比）")
        ax.grid(alpha=0.25, lw=0.5)
        ax.set_ylim(0, 1.0)
    axes[0].set_ylabel("hit rate q（当たりの割合）")
    axes[1].legend(fontsize=9, ncol=2, loc="lower right", framealpha=0.92)
    fig.suptitle("hit rate は許容偏差 W でどれだけ動くか", fontsize=14)
    fig.text(0.5, 0.015,
             "折れ線が立ち上がる位置に、測点の食い違いが集まっている。"
             "W = 0.10 付近で跳ねる風向が多く、"
             "**多くの測点が 0.06〜0.10 の差を抱えている**ことを示す。"
             "W をいくつに取るかで合否が変わるので、"
             "**単一の W で「合格」と書かない。**".replace("**", ""),
             ha="center", va="bottom", fontsize=10, color="#444")
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))
    fig.savefig(a.out, dpi=140, bbox_inches="tight")
    print("書いた: %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
