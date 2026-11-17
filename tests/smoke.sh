#!/bin/sh
# Smoke test: the game loads and runs its checks (tests/checks.gd), headless and silent, with no
# script errors. Prints each CHECK line and PASSED or FAILED.
cd "$(dirname "$0")/.."
GODOT="${GODOT:-/c/Program Files (x86)/Steam/steamapps/common/Godot Engine/godot.windows.opt.tools.64.exe}"
out=$(timeout 120 "$GODOT" --headless --path . --audio-driver Dummy --fixed-fps 60 -- --check </dev/null 2>&1)
echo "$out" | grep -E "CHECK|GULP|SCRIPT ERROR|Parse Error|ERROR"
if echo "$out" | grep -qE "SCRIPT ERROR|Parse Error" || ! echo "$out" | grep -q "GULP SMOKE PASSED"; then
	echo FAILED
	exit 1
fi
echo PASSED
