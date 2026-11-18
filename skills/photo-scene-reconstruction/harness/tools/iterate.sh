#!/bin/bash
# build + preview render + compare sheets. FROZEN.
#   tools/iterate.sh <agent> <n> [width=960] [spp=24] [only=a,b] [cam=name] [clay] [x0 y0 x1 y1]
# Writes renders/<agent>_<n>.png, ovl_<agent>_<n>.jpg (target | render | 50% blend), edg_<agent>_<n>.jpg (target
# edges in red over the render, pixel grid), and with a box (target-image pixels) crop_<agent>_<n>.jpg
# (target crop | render crop | style-reference strip). cam=<name> renders an extra camera (no overlay).
set -e
cd "$(dirname "$0")/.."
A=$1; N=$2; Wd=${3:-960}; SPP=${4:-24}
ONLY=""; CAM=""; CLAY=""; BOX=()
i=0
for a in "$@"; do
  i=$((i+1))
  [ $i -le 4 ] && continue
  case "$a" in only=*) ONLY="$a";; cam=*) CAM="$a";; clay) CLAY="clay";; *) BOX+=("$a");; esac
done
B="/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"
FREE=$(df -k /c | tail -1 | awk '{print $4}')
if [ "$FREE" -lt 6000000 ]; then echo "ABORT: less than 6 GB free on C:"; exit 2; fi
mkdir -p work renders
"$B" -b --factory-startup -P blender/build_scene.py -- "$(pwd -W)/work/$A.blend" $ONLY > work/build_$A.log 2>&1 || true
if ! grep -q "\[saved\]" work/build_$A.log; then
  echo "BUILD FAILED:"; grep -nE "Error|Traceback|File \"|line [0-9]" work/build_$A.log | tail -14; exit 1
fi
grep -q "\[FAILED\]" work/build_$A.log && { echo "WARNING domain failed:"; grep -B8 "\[FAILED\]" work/build_$A.log | tail -24; }
rm -f work/$A.blend1
# one render at a time on the GPU (machine-wide lock shared by all three labs); stale after 8 minutes
LOCK=../.gpu_lock
until mkdir $LOCK 2>/dev/null; do
  if [ -n "$(find $LOCK -maxdepth 0 -mmin +8 2>/dev/null)" ]; then rmdir $LOCK 2>/dev/null || true; fi
  sleep 3
done
set +e
"$B" -b work/$A.blend -P blender/render.py -- "$(pwd -W)/renders/${A}_$N.png" $Wd $SPP "${BOX[@]}" $CAM $CLAY > work/render_$A.log 2>&1
RC=$?
rmdir $LOCK 2>/dev/null
set -e
if [ $RC -ne 0 ] || [ ! -f renders/${A}_$N.png ]; then echo "RENDER FAILED:"; tail -20 work/render_$A.log; exit 1; fi
if [ -z "$CAM" ]; then
  tools/py.sh tools/overlay.py ref/photo.jpg renders/${A}_$N.png renders/ovl_${A}_$N.jpg 2>/dev/null
  tools/py.sh tools/edges.py ref/photo.jpg renders/${A}_$N.png renders/edg_${A}_$N.jpg 2>/dev/null
  if [ ${#BOX[@]} -eq 4 ]; then
    tools/py.sh tools/pair.py ref/photo.jpg renders/${A}_$N.png renders/crop_${A}_$N.jpg "${BOX[@]}" 2>/dev/null
  fi
fi
echo "done ${A}_$N"
