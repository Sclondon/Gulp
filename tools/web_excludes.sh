#!/bin/sh
# Rewrites the Web export preset's exclude list so that a web build leaves out every creature's
# FULL model where it has a game model (the game shows game models, `game = true`, which never
# load the full ones: they are about nine tenths of the models' weight), the retired panel art, the
# concept art and the retired rocks (models/sea_floor.glb).
#   sh tools/web_excludes.sh        (from the project folder; then export as usual)
# A full model is creatures/<x>/models/<name>.glb beside a <name>_game.glb.
set -e
# (addons/ and editor/: the bay editor, addons/bay_layout and editor/bay_layout.tscn; the game reads only data/layout.json)
list="tools/*,tests/*,addons/*,editor/*,shots/*,conceptart/*,textures/panel/retired_1/*,textures/controls/*,creatures/*/tools/*,models/sea_floor.glb,models/*_old.json"
# The figures being made (the boy, his brother, the captain, the townsfolk, their faces and hair) are
# not in the game: only the title's own copies (models/title_*) are drawn. About 35 MB of the pack
# (tools/PERF.md, "The web pack, 2026-11-19"). Take a figure out of this list when the game uses it.
list="$list,models/boy*,models/brother*,models/captain*,models/face/*,models/hair/*,models/npc/*"
list="$list,textures/boy/*,textures/brother/*,textures/captain/*,textures/tattoos/*,textures/face/*,textures/hair/*,textures/npc/*"
# (retired: the first, flat Atlantis with its atlases and table, the old rocks' table)
list="$list,models/atlantis_ruins*,textures/ruins_atlas.png,textures/ruins_atlas_statue.png,models/ruins_extra.json,models/sea_rocks.json"
# (the flat panel's pictures, retired when the panel became a model: tools/PERF.md)
for old in engine_module gauge_module helm_module knob lever needle plunger plunger_lit rivet spark switch_closed tube_lit; do
	list="$list,textures/panel/$old.png"
done
# The game and far models a creature's baked look stands in for (BakedLook primes the component's
# own cache with the baked meshes, so these are never loaded: tools/bake_looks.gd writes the list).
for primed in creatures/*/baked/*primed.txt; do
	[ -f "$primed" ] || continue
	for model in $(tr -d '\r' < "$primed"); do
		list="$list,$model"
	done
done
for game in creatures/*/models/*_game.glb; do
	full="${game%_game.glb}.glb"
	if [ -f "$full" ]; then
		list="$list,$full"
	fi
done
perl -pi -e 'BEGIN { $l = shift } s/^exclude_filter=.*/exclude_filter="$l"/' "$list" export_presets.cfg
echo "WEB excludes $(echo "$list" | tr ',' '\n' | wc -l) paths"
# The creatures' models are imported without automatic LODs (never used: Fish._wear sets lod_bias 64,
# since a body bent in its shader breaks on them) and without shadow meshes (nothing casts a
# shadow here): together they were half of each model's weight in the pack (tools/PERF.md). Newly
# installed creatures get Godot's defaults, so this is done again before every export; then
# `godot --headless --path . --import` before exporting.
changed=$(grep -l -E "^meshes/(generate_lods|create_shadow_meshes)=true" creatures/*/models/*.glb.import 2>/dev/null || true)
for file in $changed; do
	case "$file" in
	# (the meshes drawn hundreds at once by a MultiMesh, a school's or a cloud's, keep their LODs:
	# a far school is drawn with them, and without them the bait ball alone was 500,000 triangles)
	*_school.glb.import|*speck*.glb.import|*_colony.glb.import)
		perl -pi -e 's/^meshes\/create_shadow_meshes=true/meshes\/create_shadow_meshes=false/' "$file" ;;
	*)
		perl -pi -e 's/^meshes\/generate_lods=true/meshes\/generate_lods=false/; s/^meshes\/create_shadow_meshes=true/meshes\/create_shadow_meshes=false/' "$file" ;;
	esac
done
echo "WEB imports: $(echo "$changed" | grep -c . || true) creature models set to no shadow meshes (and, but for schools and clouds, no LODs)"
