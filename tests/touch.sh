#!/bin/sh
# Touch test: fingers sent to a real window (headless puts touches in the wrong place) work the
# stick, the burst button and the start-again button. A small silent window opens for a few
# seconds at phone size. Prints each CHECK line and PASSED or FAILED.
cd "$(dirname "$0")/.."
GODOT="${GODOT:-/c/Program Files (x86)/Steam/steamapps/common/Godot Engine/godot.windows.opt.tools.64.exe}"
out=$(timeout 60 "$GODOT" --path . --audio-driver Dummy --resolution 390x844 --position 2600,60 -- --check=touch </dev/null 2>&1)
echo "$out" | grep -E "CHECK|GULP|SCRIPT ERROR|Parse Error|ERROR"
if echo "$out" | grep -qE "SCRIPT ERROR|Parse Error" || ! echo "$out" | grep -q "GULP TOUCH PASSED"; then
	echo FAILED
	exit 1
fi
echo PASSED
