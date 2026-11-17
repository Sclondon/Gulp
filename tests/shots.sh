#!/bin/sh
# Pictures of the key screens at phone and desktop sizes, into a folder (a new one each time:
# nothing is deleted). Short silent windows open off to one side.
#   sh tests/shots.sh <folder>
cd "$(dirname "$0")/.."
GODOT="${GODOT:-/c/Program Files (x86)/Steam/steamapps/common/Godot Engine/godot.windows.opt.tools.64.exe}"
out="${1:?give a folder for the pictures}"
mkdir -p "$out"
out=$(cygpath -m "$out" 2>/dev/null || echo "$out")
shot() {
	name=$1; size=$2; shift 2
	timeout 60 "$GODOT" --path . --audio-driver Dummy --resolution "$size" --position 2600,60 -- "$@" --out="$out/$name.png" </dev/null 2>&1 | grep -E "GULP SHOT|SCRIPT ERROR|Parse Error|ERROR"
}
shot play_phone 390x844 --bot --shot=6
shot play_short 720x1170 --bot --stage=1 --shot=8
shot play_landscape 844x390 --bot --stage=2 --shot=8
shot play_desktop 1280x720 --bot --stage=4 --shot=8
shot over_phone 390x844 --stage=3 --over --shot=2
shot over_desktop 1280x720 --stage=3 --over --shot=2
shot jelly 720x720 --near=jelly --shot=1.2
