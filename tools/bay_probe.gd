extends SceneTree
## Prints the floor's depth and the distance to shore at points (world x,z), for placing things:
##   godot --headless --path . -s res://tools/bay_probe.gd -- 10,-40 -30,-25 ...
## With `--raw` the baked floor only (no slough, harbours or shelves).

func _initialize() -> void:
	var raw := OS.get_cmdline_user_args().has("--raw")
	for arg in OS.get_cmdline_user_args():
		if not "," in arg:
			continue
		var p := Vector2(float(arg.get_slice(",", 0)), float(arg.get_slice(",", 1)))
		var deep := Bay._sample(Bay._depth, p.x, p.y) if raw else Bay.SURFACE - Bay.ground(p.x, p.y)
		print("PROBE %s: depth %.1f, shore %.1f" % [p, deep, Bay.shore_distance(p)])
	quit()
