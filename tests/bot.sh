#!/bin/sh
# Bot run: the game plays itself (scripts/bot.gd) for some minutes of game time, headless and
# silent, faster than real time, starting again whenever it is eaten. Passes if it ate its way
# up at least one stage and there were no script errors.
#   sh tests/bot.sh [seconds of game time, default 240]
cd "$(dirname "$0")/.."
GODOT="${GODOT:-/c/Program Files (x86)/Steam/steamapps/common/Godot Engine/godot.windows.opt.tools.64.exe}"
out=$(timeout 240 "$GODOT" --headless --path . --audio-driver Dummy --fixed-fps 60 -- --bot --seconds="${1:-240}" </dev/null 2>&1)
echo "$out" | grep -E "GULP|SCRIPT ERROR|Parse Error|ERROR"
if echo "$out" | grep -qE "SCRIPT ERROR|Parse Error" || ! echo "$out" | grep -q "GULP BOT PASSED"; then
	echo FAILED
	exit 1
fi
echo PASSED
