#!/usr/bin/env bash
# 計算機の違いを測るため、同じケースを同じ条件で走らせ、結果を 1 つの tar.gz にまとめる。
# 使い方（OpenFOAM の環境を読み込んだ端末で。Docker なら同じコンテナの中で）:
#   bash run_machine.sh ケースのフォルダ 反復の数 並列数
#   例: bash run_machine.sh ~/cases/leeds_W_C1 500 4
# そろえること: 2 台で同じケース・同じ反復の数・同じ並列数にする。
# ケースのフォルダは書き換えない（コピーして走らせる）。
set -euo pipefail
src=${1:?ケースのフォルダ}; iters=${2:-500}; np=${3:-4}
src=$(cd "$src" && pwd)
host=$(hostname -s 2>/dev/null || hostname)
tag="fp_${host}_$(basename "$src")_n${np}_i${iters}"
work="$PWD/$tag"
[ -e "$work" ] && { echo "既にある: $work（消してからやり直す）"; exit 1; }
mkdir -p "$work"
# メッシュ・初期値・設定だけをコピーする（結果の時刻のフォルダと processor* は持ってこない）
cp -r "$src/system" "$src/constant" "$work/"
if   [ -d "$src/0.orig" ]; then cp -r "$src/0.orig" "$work/0"
elif [ -d "$src/0" ];      then cp -r "$src/0" "$work/0"
else echo "0 か 0.orig が無い"; exit 1; fi
cd "$work"
solver=$(foamDictionary -entry application -value system/controlDict)
start=$(foamDictionary -entry startTime -value system/controlDict 2>/dev/null || echo 0)
dt=$(foamDictionary -entry deltaT -value system/controlDict)
end=$(python3 -c "print(repr($start + $iters * $dt))" 2>/dev/null || echo "$iters")

# 条件をそろえる：反復の数で止める、16 桁の ascii で書く、最後だけ書く
foamDictionary -entry startFrom  -set startTime  system/controlDict >/dev/null
foamDictionary -entry startTime  -set "$start"   system/controlDict >/dev/null
foamDictionary -entry endTime    -set "$end"     system/controlDict >/dev/null
foamDictionary -entry writeControl   -set timeStep        system/controlDict >/dev/null
foamDictionary -entry writeInterval  -set "$iters"        system/controlDict >/dev/null
# 領域を分ける間は binary で書く（格子を 1 ビットも変えないため。ascii の 16 桁では倍精度を書き戻せず、
# また macOS は 1e-315 のような非正規化数を ascii から読めず decomposePar が止まる）。計算の前に ascii に戻す
foamDictionary -entry writeFormat    -set binary          system/controlDict >/dev/null
foamDictionary -entry writePrecision -set 16              system/controlDict >/dev/null
foamDictionary -entry writeCompression -set off           system/controlDict >/dev/null
foamDictionary -entry purgeWrite     -set 0               system/controlDict >/dev/null
# 判定で止まらないようにする（定常の residualControl を外す）
for k in SIMPLE PIMPLE; do
  foamDictionary -entry "$k/residualControl" -remove system/fvSolution >/dev/null 2>&1 || true
done
# 並列の分け方：毎回同じになる hierarchical
if [ "$np" -gt 1 ]; then
  n1=$(python3 -c "
import math; n=$np; a=[1,1,1]
for i in range(3):
    f=round(n**(1/(3-i)))
    while n%f: f-=1
    a[i]=f; n//=f
a.sort(reverse=True); print(*a)")
  cat > system/decomposeParDict <<DEC
FoamFile { version 2.0; format ascii; class dictionary; object decomposeParDict; }
numberOfSubdomains $np;
method hierarchical;
coeffs { n ($n1); order xyz; }
hierarchicalCoeffs { n ($n1); order xyz; }
DEC
fi

# 計算機と OpenFOAM の記録
{
  echo "host: $host"; echo "date: $(date -u +%FT%TZ)"
  echo "uname: $(uname -a)"
  if command -v sysctl >/dev/null && sysctl -n machdep.cpu.brand_string >/dev/null 2>&1; then
    echo "cpu: $(sysctl -n machdep.cpu.brand_string)"
  else echo "cpu: $(grep -m1 'model name' /proc/cpuinfo 2>/dev/null | cut -d: -f2- || uname -m)"; fi
  echo "WM_PROJECT_VERSION: ${WM_PROJECT_VERSION:-?}"; echo "WM_OPTIONS: ${WM_OPTIONS:-?}"
  echo "WM_COMPILER: ${WM_COMPILER:-?}"; echo "solver: $solver"
  echo "iterations: $iters"; echo "np: $np"; echo "startTime: $start"; echo "endTime: $end"
  echo "src: $src"; echo "decompose_writeFormat: binary"
} > machine.txt

# メッシュを作り直すケース（Allrun でメッシュを作る）には対応しない。constant/polyMesh が要る
[ -d constant/polyMesh ] || { echo "constant/polyMesh が無い。メッシュを作ったケースを渡す"; exit 1; }

t0=$(date +%s)
if [ "$np" -gt 1 ]; then
  decomposePar -force > log.decomposePar 2>&1
  foamDictionary -entry writeFormat -set ascii system/controlDict >/dev/null
  # root で走らせる Docker では MPIRUN_ARGS="--allow-run-as-root" を付ける
  mpirun ${MPIRUN_ARGS:-} -np "$np" "$solver" -parallel > log.solver 2>&1 || { tail -20 log.solver; exit 1; }
  reconstructPar -latestTime > log.reconstructPar 2>&1
else
  foamDictionary -entry writeFormat -set ascii system/controlDict >/dev/null
  "$solver" > log.solver 2>&1 || { tail -20 log.solver; exit 1; }
fi
echo "wallclock_s: $(( $(date +%s) - t0 ))" >> machine.txt
rm -rf processor*
last=$(foamListTimes -latestTime 2>/dev/null | tail -1)
echo "latestTime: $last" >> machine.txt
cd ..
tar czf "$tag.tar.gz" "$tag/machine.txt" "$tag/log.solver" "$tag/$last"
echo "できた: $PWD/$tag.tar.gz（この 1 つを送る）"
