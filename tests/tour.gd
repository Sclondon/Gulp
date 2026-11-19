extends Node
## A swim round the bay for finding freezes (`-- --tour[=<legs>]`, run by Main as a child, in a
## window, with the hitch logger on). It waits for the title's start (pass `--dive` too, so the run
## starts the moment the start button is live, as an eager player's does), then carries the fish
## along the legs at SPEED m/s, a few metres over the floor, and stops at each place for a moment;
## "leap" throws it out of the water. At the end: the hitches (scripts/hitches.gd) and the frame
## times. tools/PERF.md, "Hitches", says how it was used.
##
##   godot --path . --audio-driver Dummy --rendering-driver opengl3_angle --resolution 390x844 -- --dive --tour

const SPEED := 6.0
const LEGS := ["sand", "barrel", "leap", "beach", "trench", "river", "marina", "docks", "kelp", "reef", "ruins", "grass", "open", "crags", "pirate"]
const PLACES := {
	"sand": Vector2(-20.0, -80.0), "barrel": Vector2(-39.0, -122.0), "beach": Vector2(55.0, -118.0),
	"trench": Vector2(30.0, -36.0), "river": Vector2(120.0, -38.0), "marina": Vector2(84.0, 5.0),
	"docks": Vector2(66.0, 68.0), "kelp": Vector2(42.4, 48.6), "reef": Vector2(-37.0, 126.0),
	"ruins": Vector2(-64.0, 48.0), "grass": Vector2(-56.0, 2.0), "open": Vector2(-95.0, 10.0),
	"crags": Vector2(-82.0, -40.0), "pirate": Vector2(-65.0, -42.0),
}

var main: Node
var hitches: Hitches
var legs: PackedStringArray = []

var _times := PackedFloat32Array()
var _last := 0
var _leg := -1
var _goal := Vector3.ZERO
var _pause := 0.0
var _leaping := 0.0
var _started := false
var _leg_time := 0.0
var _best := INF
var _stuck := 0.0
# the way to the goal through the water (world points, the goal last)
var _route: Array[Vector3] = []


func _ready() -> void:
	process_priority = -1000
	if legs.is_empty():
		legs = PackedStringArray(LEGS)


func _process(delta: float) -> void:
	var player: Player = main.player
	if main._on_deck:
		hitches.stage = "title" if main._dive < 0.0 else "dive"
		return
	if not _started:
		_started = true
		main.life.hunting = false
		main.limited = false
		player.deepest = INF
		player.safe = 100000.0
		_last = Time.get_ticks_usec()
		_next()
		return
	var now := Time.get_ticks_usec()
	_times.append((now - _last) / 1000.0)
	_last = now
	player.safe = 100000.0
	var dt := minf(delta, 0.05)
	if _leaping > 0.0:
		_leaping -= dt
		if _leaping <= 0.0:
			_next()
		return
	if _pause > 0.0:
		_pause -= dt
		player.stick = Vector2.ZERO
		player.throttle = 0.0
		if _pause <= 0.0:
			_next()
		return
	var at := player.global_position
	while _route.size() > 1 and Vector2(_route[0].x - at.x, _route[0].z - at.z).length() < 3.0:
		_route.pop_front()
		_best = INF
	var to := (_route[0] if not _route.is_empty() else _goal) - at
	# (a goal it cannot reach (the fish is kept in the water) is given up after 4 s without getting nearer)
	_leg_time += dt
	if to.length() < _best - 0.5:
		_best = to.length()
		_stuck = 0.0
	else:
		_stuck += dt
	# (held back by something (a rock, the mangroves' roots): put on past it, to the next point)
	if _stuck > 2.0 and _route.size() > 1:
		player.global_position = _route.pop_front()
		_best = INF
		_stuck = 0.0
		return
	if (_route.size() <= 1 and to.length() < SPEED * dt * 1.5) or _stuck > 4.0 or _leg_time > 120.0:
		if _stuck > 4.0:
			print("GULP TOUR gave up on reaching %s, %.0f m off" % [legs[_leg], (_goal - at).length()])
		_pause = 1.5
		return
	var dir := to.normalized()
	var step := at + dir * SPEED * dt
	var floor_y := Sea.ground(step.x, step.z)
	step.y = clampf(step.y, floor_y + 2.5, Sea.SURFACE - 1.5) if floor_y < Sea.SURFACE - 4.0 else Sea.SURFACE - 1.5
	player.global_position = step
	player.heading = dir
	player.stick = Vector2.ZERO
	player.throttle = 0.0


func _next() -> void:
	_leg += 1
	if _leg >= legs.size():
		_finish()
		return
	var name := legs[_leg]
	hitches.stage = "tour:" + name
	var player: Player = main.player
	if name == "leap":
		player.global_position.y = Sea.SURFACE - 1.5
		player.pitch = 0.9
		player.boost_held = true
		_leaping = 3.0
		return
	player.boost_held = false
	var p: Vector2 = PLACES[name]
	var floor_y := Sea.ground(p.x, p.y)
	var y := clampf(floor_y + 4.0, floor_y + 2.0, Sea.SURFACE - 1.5)
	if name == "barrel":
		y = Sea.SURFACE - 1.5
	_goal = Sea.keep_in(Vector3(p.x, y, p.y), 1.0)
	_route = _water_route(player.global_position, _goal)
	_leg_time = 0.0
	_best = INF
	_stuck = 0.0
	print("GULP TOUR leg %s at %.0f s (from %s)" % [name, Time.get_ticks_msec() / 1000.0, player.global_position])


func _finish() -> void:
	var sorted := _times.duplicate()
	sorted.sort()
	var total := 0.0
	for t in _times:
		total += t
	var n := maxi(sorted.size(), 1)
	print("GULP TOUR frames %d, mean %.1f ms, median %.1f, 95th %.1f, 99th %.1f, worst %.0f" % [
			sorted.size(), total / n, sorted[n / 2], sorted[int(n * 0.95)], sorted[int(n * 0.99)], sorted[n - 1]])
	hitches.report()
	get_tree().quit()


# A way through the water from one point to another: a breadth-first search over 2 m squares of
# water (the floor at least 1.5 m under the surface), every fifth square a point, the goal last.
func _water_route(from: Vector3, to: Vector3) -> Array[Vector3]:
	const CELL := 2.0
	var nx := int((Sea.EAST - Sea.WEST) / CELL)
	var nz := int((Sea.SOUTH - Sea.NORTH) / CELL)
	var cell_of := func(p: Vector3) -> int:
		return clampi(int((p.z - Sea.NORTH) / CELL), 0, nz - 1) * nx + clampi(int((p.x - Sea.WEST) / CELL), 0, nx - 1)
	var wet := PackedByteArray()
	wet.resize(nx * nz)
	for k in nz:
		for i in nx:
			var x := Sea.WEST + (i + 0.5) * CELL
			var z := Sea.NORTH + (k + 0.5) * CELL
			wet[k * nx + i] = 1 if Sea.ground(x, z) < Sea.SURFACE - 1.5 else 0
	var start: int = cell_of.call(from)
	var goal: int = cell_of.call(to)
	var came := PackedInt32Array()
	came.resize(nx * nz)
	came.fill(-1)
	came[start] = start
	var queue := PackedInt32Array([start])
	var head := 0
	while head < queue.size():
		var c := queue[head]
		head += 1
		if c == goal:
			break
		var ci := c % nx
		var ck := c / nx
		for d: Vector2i in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
			var i := ci + d.x
			var k := ck + d.y
			if i < 0 or k < 0 or i >= nx or k >= nz:
				continue
			var n := k * nx + i
			if came[n] >= 0 or (wet[n] == 0 and n != goal):
				continue
			came[n] = c
			queue.append(n)
	var out: Array[Vector3] = []
	if came[goal] < 0:
		print("GULP TOUR no way through the water to %s: straight" % to)
		out.append(to)
		return out
	var cells: Array[int] = []
	var c := goal
	while c != start:
		cells.push_front(c)
		c = came[c]
	for j in range(4, cells.size(), 5):
		var x := Sea.WEST + (cells[j] % nx + 0.5) * CELL
		var z := Sea.NORTH + (cells[j] / nx + 0.5) * CELL
		var floor_y := Sea.ground(x, z)
		out.append(Vector3(x, clampf(floor_y + 4.0, floor_y + 2.0, Sea.SURFACE - 1.5), z))
	out.append(to)
	return out
