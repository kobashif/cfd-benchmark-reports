#!/usr/bin/env python3
"""**図の配色を全レポートで 1 か所に集める。**

    import cfdcolors as CC
    cmap = CC.speed()                    # 風速比のコンター
    norm = CC.norm(cmap, LEVELS)         # 帯で塗るとき

なぜ 1 か所か。同じ量を、レポートごとに違う色で塗っていた
（風速比が虹色・YlGnBu・viridis・RdYlBu_r の 4 通り）。
**並べて見るたびに凡例を読み直すことになる。**さらにケース D は
ケース C の定義を読みつつ、**同じ色を自前でも持っていた**。
片方だけ直せば黙って食い違う。

割り当て

    speed()  風速比 U/U_R・速さの大きさ    青 → シアン → 緑 → 黄 → 赤
    temp()   温度                          青 → 白 → 赤（発散）
    diff()   差（計算 − 実測、Cp など）    青 → 白 → 赤（発散・0 を白に）
    age()    空気齢・滞留時間              紫 → 緑 → 黄
    height() 地形・建物の高さ              灰色

**speed は虹色である。**知覚的に等間隔ではなく、緑のあたりで変化が
見えにくい。**必ず帯（BoundaryNorm）で塗り、境界を明示する。**
連続で塗ると読み違える。この配色は SimScale の結果表示に合わせてあり、
同じケースの公開図と並べたときに色から受ける印象を揃えるためである
（**配色を合わせているだけで、図は転載していない**）。
"""
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm

# 低い順。SimScale の凡例と同じ並び。
SPEED_ANCHORS = [
    (0.00, "#0000cc"),   # 濃い青
    (0.25, "#00c8ff"),   # シアン
    (0.50, "#00d200"),   # 緑
    (0.75, "#ffe500"),   # 黄
    (1.00, "#e00000"),   # 赤
]


def speed():
    """風速比・速さの大きさ。**帯で塗ること。**"""
    return LinearSegmentedColormap.from_list("cfd_speed", SPEED_ANCHORS, N=256)


def temp():
    """温度。低いほう青・高いほう赤。"""
    return "RdYlBu_r"


def diff():
    """差。0 を白にする発散配色。"""
    return "RdBu_r"


def age():
    """空気齢・滞留時間。"""
    return "viridis"


def height():
    """地形・建物の高さ。流れの図の下敷きに使うので彩度を持たせない。"""
    return "Greys"


def norm(cmap, levels, extend="max"):
    """帯で塗るための境界。**speed を使うときは必ず通す。**"""
    n = cmap.N if hasattr(cmap, "N") else 256
    return BoundaryNorm(levels, n, extend=extend)
