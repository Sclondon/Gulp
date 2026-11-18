#!/bin/sh
# Rewrites the Web export preset's exclude list so that a web build leaves out every creature's
# FULL model where it has a game model (the game shows game models, `game = true`, which never
# load the full ones: they are about nine tenths of the models' weight), and the retired panel art.
#   sh tools/web_excludes.sh        (from the project folder; then export as usual)
# A full model is creatures/<x>/models/<name>.glb beside a <name>_game.glb.
set -e
list="tools/*,tests/*,shots/*,textures/panel/retired_1/*,textures/controls/*,creatures/*/tools/*"
for game in creatures/*/models/*_game.glb; do
	full="${game%_game.glb}.glb"
	if [ -f "$full" ]; then
		list="$list,$full"
	fi
done
perl -pi -e 'BEGIN { $l = shift } s/^exclude_filter=.*/exclude_filter="$l"/' "$list" export_presets.cfg
echo "WEB excludes $(echo "$list" | tr ',' '\n' | wc -l) paths"
