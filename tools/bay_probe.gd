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
		if arg.begins_with("--fit="):
			_fit(arg.get_slice("=", 1).split(","))
		elif arg.begins_with("--grid="):
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


# `--fit=x0,z0,x1,z1,step,length,width,deep_from,deep_to,steepest`: for a long thing (a hull) at each point of
# that grid and each heading (every 15 degrees), the plane that best fits the raw floor under it
# (least squares over points 3 m apart), how steep that plane is, how far the floor strays from it,
# and its depth at the middle; all of it in water at least 4 m from a shore. The best (least astray,
# no steeper than the tenth number) first. Headings are as Sea's rotation.y (its length along sin, cos).
func _fit(v: PackedStringArray) -> void:
	var long := float(v[5]) * 0.5
	var wide := float(v[6]) * 0.5
	var found := []
	var z := float(v[1])
	while z <= float(v[3]):
		var x := float(v[0])
		while x <= float(v[2]):
			for k in 12:
				var turn := k * PI / 12.0
				var along := Vector2(sin(turn), cos(turn))
				var across := along.orthogonal()
				var pts := []
				var dry := false
				var a := -long
				while a <= long:
					var b := -wide
					while b <= wide:
						var p := Vector2(x, z) + along * a + across * b
						if Bay.shore_distance(p) < 4.0:
							dry = true
						pts.append([p.x - x, p.y - z, _depth(p, true)])
						b += 3.0
					a += 3.0
				if dry:
					continue
				var plane := _plane(pts)
				var worst := 0.0
				for q: Array in pts:
					worst = maxf(worst, absf(q[2] - (plane.x + plane.y * q[0] + plane.z * q[1])))
				var steep := Vector2(plane.y, plane.z).length()
				if steep <= float(v[9]) and plane.x >= float(v[7]) and plane.x <= float(v[8]):
					found.append([worst, Vector2(x, z), turn, plane])
			x += float(v[4])
		z += float(v[4])
	found.sort_custom(func(p: Array, q: Array) -> bool: return p[0] < q[0])
	for k in mini(found.size(), 12):
		var f: Array = found[k]
		var plane: Vector3 = f[3]
		print("FIT %s heading %.2f: depth %.1f, slope (x %.3f, z %.3f), strays %.1f m" % [f[1], f[2], plane.x, plane.y, plane.z, f[0]])


# Least squares of depth = c + sx * x + sz * z over [x, z, depth] points: Vector3(c, sx, sz).
func _plane(pts: Array) -> Vector3:
	var n := float(pts.size())
	var sx := 0.0
	var sz := 0.0
	var sxx := 0.0
	var szz := 0.0
	var sxz := 0.0
	var sd := 0.0
	var sxd := 0.0
	var szd := 0.0
	for q: Array in pts:
		sx += q[0]; sz += q[1]; sd += q[2]
		sxx += q[0] * q[0]; szz += q[1] * q[1]; sxz += q[0] * q[1]
		sxd += q[0] * q[2]; szd += q[1] * q[2]
	var m := Basis(Vector3(n, sx, sz), Vector3(sx, sxx, sxz), Vector3(sz, sxz, szz))
	return m.inverse() * Vector3(sd, sxd, szd)


func _depth(p: Vector2, raw: bool) -> float:
	return Bay._sample(Bay._depth, p.x, p.y) if raw else Bay.SURFACE - Bay.ground(p.x, p.y)
