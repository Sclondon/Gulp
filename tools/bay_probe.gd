extends SceneTree
## Prints the floor's depth and the distance to shore at points (world x,z), for placing things:
##   godot --headless --path . -s res://tools/bay_probe.gd -- 10,-40 -30,-25 ...
## With `--raw` the baked floor only (no slough, harbours or shelves).
## `--grid=x0,z0,x1,z1,step` prints a table of depths (rows z, columns x; `--raw` applies).
## `--flat=x0,z0,x1,z1,step,radius` prints, for each point of that grid, the mean depth and the spread
## (highest to lowest) of the raw floor within `radius`: the flattest spots first.

func _initialize() -> void:
	Bay._load()
	var raw := OS.get_cmdline_user_args().has("--raw")
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--grid="):
			var v := arg.get_slice("=", 1).split(",")
			var head := "z\\x  "
			var x := float(v[0])
			while x <= float(v[2]):
				head += "%5d" % int(x)
				x += float(v[4])
			print(head)
			var z := float(v[1])
			while z <= float(v[3]):
				var row := "%5d" % int(z)
				x = float(v[0])
				while x <= float(v[2]):
					row += "%5.0f" % _depth(Vector2(x, z), raw)
					x += float(v[4])
				print(row)
				z += float(v[4])
		elif arg.begins_with("--flat="):
			var v := arg.get_slice("=", 1).split(",")
			var radius := float(v[5])
			var found := []
			var z := float(v[1])
			while z <= float(v[3]):
				var x := float(v[0])
				while x <= float(v[2]):
					var lo := INF
					var hi := -INF
					var sum := 0.0
					var n := 0
					for dz in range(-int(radius), int(radius) + 1, 2):
						for dx in range(-int(radius), int(radius) + 1, 2):
							if dx * dx + dz * dz > radius * radius:
								continue
							var d := _depth(Vector2(x + dx, z + dz), true)
							lo = minf(lo, d)
							hi = maxf(hi, d)
							sum += d
							n += 1
					found.append([hi - lo, Vector2(x, z), sum / n])
					x += float(v[4])
				z += float(v[4])
			found.sort_custom(func(a: Array, b: Array) -> bool: return a[0] < b[0])
			for k in found.size():
				print("FLAT %s: mean %.1f, spread %.1f" % [found[k][1], found[k][2], found[k][0]])
		elif "," in arg:
			var p := Vector2(float(arg.get_slice(",", 0)), float(arg.get_slice(",", 1)))
			print("PROBE %s: depth %.1f, shore %.1f" % [p, _depth(p, raw), Bay.shore_distance(p)])
	quit()


func _depth(p: Vector2, raw: bool) -> float:
	return Bay._sample(Bay._depth, p.x, p.y) if raw else Bay.SURFACE - Bay.ground(p.x, p.y)
