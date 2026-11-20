extends SceneTree
## For the bay editor (addons/bay_layout): the floor as the game makes it (`Bay.ground` on its 2 m
## grid, with the river, harbours, shelves, Atlantis's ledges and the dunes over the baked floor),
## the shore's distance and which biome each corner is in, written to one file the editor draws
## from. The game's own classes run here, in a quick process of their own: in the editor they are
## not tools and would not run. With --bake, the floor is baked first (data/monterey.bin).
##   godot --headless --path . --audio-driver Dummy -s res://addons/bay_layout/floor_dump.gd -- --out=<file> [--bake]
## The file: int32 cols, rows; float32 west, north, cell; cols*rows float32 heights (world y);
## cols*rows float32 shore distances; cols*rows bytes, the biome (0 none, else 1 + its place in
## BiomeRegions.ORDER). Prints FLOOR DUMP <ms>.

const BAKE := preload("res://addons/bay_layout/bay_bake.gd")


func _initialize() -> void:
	var out := ""
	var bake := false
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):
			out = arg.get_slice("=", 1)
		elif arg == "--bake":
			bake = true
	var t := Time.get_ticks_msec()
	if bake:
		var baked: Dictionary = (BAKE.new() as RefCounted).call(&"bake")
		if baked.is_empty():
			print("FLOOR DUMP FAILED (no bake)")
			quit(1)
			return
	var cols := int(round((Bay.EAST - Bay.WEST) / Bay.GRID)) + 1
	var rows := int(round((Bay.SOUTH - Bay.NORTH) / Bay.GRID)) + 1
	var heights := PackedFloat32Array()
	var shore := PackedFloat32Array()
	var biome := PackedByteArray()
	heights.resize(cols * rows)
	shore.resize(cols * rows)
	biome.resize(cols * rows)
	for r in rows:
		for c in cols:
			var x := Bay.WEST + c * Bay.GRID
			var z := Bay.NORTH + r * Bay.GRID
			var i := r * cols + c
			heights[i] = Bay.ground(x, z)
			shore[i] = Bay.shore_distance(Vector2(x, z))
			var b := BiomeRegions.at(x, z)
			biome[i] = 0 if b == "" else BiomeRegions.ORDER.find(b) + 1
	var f := FileAccess.open(out, FileAccess.WRITE)
	f.store_32(cols)
	f.store_32(rows)
	f.store_float(Bay.WEST)
	f.store_float(Bay.NORTH)
	f.store_float(Bay.GRID)
	f.store_buffer(heights.to_byte_array())
	f.store_buffer(shore.to_byte_array())
	f.store_buffer(biome)
	f.close()
	print("FLOOR DUMP %d" % (Time.get_ticks_msec() - t))
	quit()
