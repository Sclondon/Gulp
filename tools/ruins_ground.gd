extends SceneTree
## Writes the sea floor round Atlantis (Sea.ground, with the ledges Bay cuts from data/ruins_layout.json)
## in the ruins' own space, for tools/build_atlantis_canyon.py: its footings reach down to this floor, its
## facades and stairs sink into it, its bake is shadowed by it and its rubble lies on it.
##   godot --headless --path . --audio-driver Dummy -s res://tools/ruins_ground.gd
## Run it again whenever the floor (data/monterey.bin, Bay) or the layout changes, then build the model.
## Writes tools/ruins_ground.json: x0, z0 (the ruins' own x, z of the first point), step, cols, rows,
## heights (the ruins' own y, rows along z).

const OUT := "res://tools/ruins_ground.json"
const X0 := -48.0
const Z0 := -44.0
const X1 := 52.0
const Z1 := 40.0
const STEP := 1.0


func _initialize() -> void:
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(Bay.RUINS_LAYOUT))
	var origin := Vector3(float(data.origin[0]), Sea.SURFACE - float(data.origin_depth), float(data.origin[1]))
	var cols := int(round((X1 - X0) / STEP)) + 1
	var rows := int(round((Z1 - Z0) / STEP)) + 1
	var heights := []
	for r in rows:
		for c in cols:
			var x := origin.x + X0 + c * STEP
			var z := origin.z + Z0 + r * STEP
			heights.append(snappedf(Sea.ground(x, z) - origin.y, 0.001))
	var f := FileAccess.open(OUT, FileAccess.WRITE)
	f.store_string(JSON.stringify({"about": "Sea.ground round Atlantis in the ruins' own space (tools/ruins_ground.gd)", "origin": [origin.x, origin.y, origin.z],
			"x0": X0, "z0": Z0, "step": STEP, "cols": cols, "rows": rows, "heights": heights}))
	f.close()
	print("RUINS GROUND written: %d x %d, origin %s" % [cols, rows, origin])
	quit()
