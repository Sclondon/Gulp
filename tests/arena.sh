#!/bin/sh
# The shared sea, tested with two copies of the game on a local stand-in for the site's server:
# a tuna (a) swims into a sardine (b) and eats it. Prints each copy's ARENA line.
#   sh tests/arena.sh <path to scareathon-v3/server (with node_modules)> [out dir]
cd "$(dirname "$0")/.."
GODOT="${GODOT:-/c/Program Files (x86)/Steam/steamapps/common/Godot Engine/godot.windows.opt.tools.64.exe}"
SERVER_DIR="${1:?path to scareathon-v3/server}"
OUT="${2:-${TMPDIR:-/tmp}/gulp-arena-test}"
PORT=3117
mkdir -p "$OUT"
node tools/dev_relay.mjs "$SERVER_DIR" $PORT > "$OUT/relay.log" 2>&1 &
RELAY=$!
sleep 2
timeout 60 "$GODOT" --headless --path . --audio-driver Dummy --max-fps 60 -- --server=http://127.0.0.1:$PORT --role=b --name=BRAVO > "$OUT/b.log" 2>&1 < /dev/null &
B=$!
sleep 1
timeout 60 "$GODOT" --headless --path . --audio-driver Dummy --max-fps 60 -- --server=http://127.0.0.1:$PORT --role=a --as=tuna --name=ALPHA > "$OUT/a.log" 2>&1 < /dev/null &
A=$!
wait $A $B
kill $RELAY 2> /dev/null
grep -h "ARENA\|SCRIPT ERROR" "$OUT/a.log" "$OUT/b.log" | awk '!seen[$0]++'
grep -v "Gulp arena on" "$OUT/relay.log"
if grep -q "ARENA PASS a" "$OUT/a.log" && grep -q "ARENA PASS b" "$OUT/b.log"; then echo PASSED; else echo FAILED; exit 1; fi
