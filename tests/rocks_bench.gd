extends SceneTree
## What a `Sea.clear_of_rocks` call costs, beside the set pieces and in open water, against the
## old way (one 8 m square of floor, every sphere that could be felt from it), and whether the two
## agree. Headless:
##   godot --headless --path . --audio-driver Dummy -s res://tests/rocks_bench.gd
## (tools/PERF.md, "Decision: two grids for the rocks".)

var _scenery: Node


func _initialize() -> void:
	_scenery = Scenery.new()
	root.add_child(_scenery)
	_run.call_deferred()


func _old(p: Vector3, room: float) -> Vector3:
	var near: Variant = Sea._cells.get(Vector2i(floori(p.x / Sea.CELL), floori(p.z / Sea.CELL)))
	if near == null:
		return p
	for at: int in near:
		var rock := Sea.rocks[at]
		var from := p - Vector3(rock.x, rock.y, rock.z)
		var far := from.length()
		if far < rock.w + room:
			p = Vector3(rock.x, rock.y, rock.z) + (from / far if far > 0.001 else Vector3.UP) * (rock.w + room)
	return p


func _points(rng: RandomNumberGenerator, middle: Vector3, spread: float, n: int) -> PackedVector3Array:
	var out := PackedVector3Array()
	for i in n:
		var x := middle.x + rng.randf_range(-spread, spread)
		var z := middle.z + rng.randf_range(-spread, spread)
		var low := Sea.ground(x, z)
		out.append(Vector3(x, rng.randf_range(low + 0.2, maxf(low + 0.3, Sea.SURFACE - 0.5)), z))
	return out


func _run() -> void:
	await process_frame
	var most := 0
	for key: Variant in Sea._cells:
		most = maxi(most, (Sea._cells[key] as PackedInt32Array).size())
	var fine_most := 0
	for key: Variant in Sea._fine:
		fine_most = maxi(fine_most, (Sea._fine[key] as PackedFloat32Array).size() / 4)
	print("ROCKS %d spheres; at most %d in an 8 m square, %d in a %d m cube; %d cubes" % [Sea.rocks.size(), most, fine_most, int(Sea.FINE), Sea._fine.size()])
	var rng := RandomNumberGenerator.new()
	rng.seed = 3
	for spot: Array in [["liner", Sea.WRECK_AT, 30.0], ["pirate", Sea.PIRATE_AT, 22.0], ["ruins", Sea.RUINS_AT, 30.0], ["kelp", Vector3(53.0, 0.0, 42.0), 30.0], ["open", Vector3(-52.8, 0.0, -36.8), 20.0]]:
		var pts := _points(rng, spot[1], spot[2], 4000)
		var rooms := PackedFloat32Array()
		for i in pts.size():
			rooms.append(rng.randf_range(0.12, 0.6))
		var t0 := Time.get_ticks_usec()
		var a := PackedVector3Array()
		for i in pts.size():
			a.append(_old(pts[i], rooms[i]))
		var t1 := Time.get_ticks_usec()
		var b := PackedVector3Array()
		for i in pts.size():
			b.append(Sea.clear_of_rocks(pts[i], rooms[i]))
		var t2 := Time.get_ticks_usec()
		var moved := 0
		var differ := 0
		var worst := 0.0
		for i in pts.size():
			if a[i] != pts[i]:
				moved += 1
			var d := a[i].distance_to(b[i])
			if d > 0.01:
				differ += 1
			worst = maxf(worst, d)
		print("ROCKS %s: old %.2f us a call, new %.2f us; %d of %d pushed out; %d come out more than 1 cm apart (worst %.2f m)" % [
				spot[0], float(t1 - t0) / pts.size(), float(t2 - t1) / pts.size(), moved, pts.size(), differ, worst])
	quit()
