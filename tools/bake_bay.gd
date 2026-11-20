extends SceneTree
## Bakes the sea floor into data/monterey.bin (scripts/bay.gd reads it). The bake itself is
## addons/bay_layout/bay_bake.gd, which the bay editor's Rebake button runs too; its numbers, the
## trench's outline and the floor's hand edits come from the layout (data/layout.json,
## tools/bay_src/floor_adjust.bin). It reads GMRT's grid from tools/bay_src/gmrt.bin; to start from a
## fresh download instead (and keep it there):
##
##   curl -o bay.asc "https://www.gmrt.org/services/GridServer?north=37.02&west=-122.25&east=-121.75&south=36.45&layer=topo&format=esriascii&resolution=high"
##   godot --headless --path . --audio-driver Dummy -s res://tools/bake_bay.gd -- [--grid=<bay.asc>] [--out=<file>] [--places]
##
## `--places` prints the game position and depth of the real places named in the bake's PLACES;
## `--out=` writes somewhere else than data/monterey.bin (to compare).

const BAKE := preload("res://addons/bay_layout/bay_bake.gd")


func _initialize() -> void:
	var grid := ""
	var out: String = BAKE.OUT
	var places := false
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--grid="):
			grid = arg.get_slice("=", 1)
		elif arg.begins_with("--out="):
			out = arg.get_slice("=", 1)
		elif arg == "--places":
			places = true
	var bake: RefCounted = BAKE.new()
	if grid != "":
		bake.read_grid(grid, true)
	bake.bake(out, places)
	quit()
