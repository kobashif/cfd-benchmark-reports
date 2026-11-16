# 実機 2 台の結果（リーズ 西風・対策なし、500 反復）

README の 4.0 節の手順で、i7（Intel、WSL2）と M6（Apple シリコン、macOS）で走らせた結果。

## 使ったケース

- 元：M6 で作った報告書の本番の格子 `leeds-W-C1-g2`（固めたファイル `leeds-W-C1-g2.slim.tar.gz`、md5 d3e690745467859fac7af90983022f15）。
- このケースは格子を並列で作ったため、`constant/polyMesh` は格子を作る前の背景の格子（810,000 セル）だった。`processor*` から `reconstructParMesh -constant` で 1 つにまとめた（1,200,180 セル、checkMesh は元のケースと同じく 1 項目が不合格）。
- まとめたケース（system、constant、0.orig）を i7 で作り、同じものを M6 に写した。格子の 4 つのファイル（points・faces・owner・neighbour）の md5 は 2 台で同じ。

## run_machine.sh の直し

最初のままでは M6 の decomposePar が止まった。書き出しを ascii・16 桁にしてから領域を分けるため、格子の点の座標にある非正規化数（例 5.9×10⁻³¹⁵）を macOS が ascii から読み戻せなかった（`Bad token - could not get scalar value`）。また、ascii の 16 桁では倍精度を完全には書き戻せず、分けた格子が元の格子と最後の桁でずれる。

直し：領域を分ける間だけ binary で書き、計算の前に ascii・16 桁に戻す（`machine.txt` に `decompose_writeFormat: binary`）。反復の数・並列数・結果の書き出しは変えていない。2 台ともこの形で走らせ直した。

## 置いたもの

場（約 100 MB）は GitHub の 1 ファイル 100 MB の上限を超えるため入れていない。各計算機の作業フォルダに tar.gz で残してある。

- `fp_*/machine.txt`、`fp_*/log.solver`
- `compare_i7_m6_n4_i500.txt`：セルの値どうしを比べた結果（`compare_machines.py` はブランチに無かったので、同じ比べ方の小さなスクリプトを手元で書いて使った。この庫は .py を入れない決まりなので、スクリプトは入れていない）

M6 は、計算と reconstructPar が End まで済んだあと、`rm -rf processor*` の前後で bash が `Segmentation fault: 11` で落ちた。残りの手順（processor の削除・latestTime の記録・tar）を手で同じ順に行った（`machine.txt` の note）。

## 結果（500 反復、4 並列どうし）

| 場 | 最大の差 ÷ 場の最大 | 差の RMS ÷ 場の RMS | 16 桁の文字で一致したセル |
|---|---|---|---|
| U | 2.4×10⁻⁹ | 9.7×10⁻¹² | 0.0006 % |
| p | 9.0×10⁻¹¹ | 8.9×10⁻¹² | 0.02 % |
| k | 3.1×10⁻¹⁰ | 6.2×10⁻¹² | 10.9 % |
| epsilon | 7.5×10⁻¹¹ | 1.2×10⁻¹¹ | 13.4 % |
| nut | 6.0×10⁻¹² | 1.8×10⁻¹³ | 12.9 % |

500 反復目の残差も、2 台で 11〜12 桁目まで同じ（Ux の初めの残差 3.596950198104617e−05 と 3.596950198112811e−05）。

見立て（4.0 節：速度の差は最大の値の 1 % 以下）より 7 桁小さい。2 台はほぼ全セルで最後の桁が違うが、500 反復の時点では、差は場の値の 10⁻⁹ 程度にとどまる（途中の反復では比べていない）。

かかった時間：i7（Core i7-1255U）1,140 秒、M6 301 秒。

## 8 並列（i7）

走らせたが、ソルバーが始まらずに止まった。Open MPI が「8 個のスロットが無い」と断った（i7 の WSL は物理コア 6 として数え、既定ではコアの数までしか起こさない）。手順のとおり条件は変えず、やり直していない。`log.solver` の最後の 20 行は掲示板の投稿に貼った。走らせるなら、Open MPI の既定を変える（`--oversubscribe` か `--use-hwthread-cpus`）必要があり、それは条件を変えることになるので依頼者に諮る。

## 並列数を変えた比べ（2026-11-16）

同じケース・500 反復・同じ `run_machine.sh`（hierarchical で分ける）で、並列数だけを変えた。

| フォルダ | 計算機 | 並列数 | かかった時間 | mpirun に足したもの |
|---|---|---|---|---|
| `fp_apple-silicon_leeds-W-C1-g2_n4_i500_b` | M6 | 4 | 299 秒 | `--oversubscribe --bind-to none` |
| `fp_apple-silicon_leeds-W-C1-g2_n6_i500` | M6 | 6 | 247 秒 | 同上 |
| `fp_apple-silicon_leeds-W-C1-g2_n12_i500` | M6 | 12 | 222 秒 | 同上 |
| `fp_x86-laptop_leeds-W-C1-g2_n8_i500` | i7 | 8 | 865 秒 | `--oversubscribe`（物理コア 6 に 8 ランク） |

- M6 の 3 本は、mpirun が CPU の並びを読む所で止まるのを避けるため、その読み取りを外して走らせた（`machine.txt` の mpirun_args）。CPU が 1 つに見えるので `--oversubscribe` が要る。4 並列は 11-15 の結果と全セルが 1 ビットも違わなかったので、値への効きは無い
- M6 の 12 並列は、reconstructPar の後で bash が落ち、tar が抜けた（`machine.txt` の note）。500 の時刻の場はそろっていた
- 比べた結果：`compare_np_i500.txt`。まとめは README の 1 章の 5 番。並列数だけ変えると速度の最大の差は場の最大の 6〜10 %、RMS で 0.15〜0.25 %。計算機と並列数を両方変えても同じ大きさ
- 場は前回と同じく入れていない（各計算機の作業フォルダにある）
