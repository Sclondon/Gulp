extends SceneTree
## Do the animals that keep to the floor stand on it, not in it or over it? (tools/QUALITY.md.) The
## sea is built and stocked (Scenery, Life; nothing hunts), every animal that keeps to the floor is
## dressed and left to go about for a while, then the bottom corners of each one's drawn box (in its
## own space, turned as it is) are measured against the floor under them: "sunk" how far the lowest
## goes into the floor, "over" how far the highest of the four bottom corners... no: how far the
## body's lowest corner is above the floor at its middle (hovering). Per kind, the worst of each.
##   godot --headless --path . --audio-driver Dummy --fixed-fps 60 -s res://tests/floor_clip.gd

const SECONDS := 8.0

var _life: Life
var _player: Player


func _initialize() -> void:
	root.add_child(Scenery.new())
	_player = Player.new()
	root.add_child(_player)
	_player.begin(Vector3(Sea.START.x, Sea.SURFACE - 5.0, Sea.START.y), "sardine")
	_life = Life.new()
	_life.player = _player
	_life.hunting = false
	root.add_child(_life)
	_run.call_deferred()


func _box(c: Creature) -> AABB:
	var to_me := c.global_transform.affine_inverse()
	var box := AABB()
	var first := true
	for mesh: MeshInstance3D in c.find_children("*", "MeshInstance3D", true, false):
		if mesh.mesh == null or not mesh.visible:
			continue
		var b: AABB = to_me * mesh.global_transform * mesh.mesh.get_aabb()
		box = b if first else box.merge(b)
		first = false
	return box


func _run() -> void:
	await process_frame
	var floor_ones: Array[Creature] = []
	for c: Creature in _life.creatures:
		if c.on_floor:
			c.dress()
			floor_ones.append(c)
	var frames := int(SECONDS * 60.0)
	for i in frames:
		# (the player is kept still, high up, out of the way)
		_player.global_position = Vector3(Sea.START.x, Sea.SURFACE - 1.0, Sea.START.y)
		_life.step(1.0 / 60.0)
		await process_frame
	var worst := {}
	for c in floor_ones:
		if c.away > 0.0:
			continue
		# (one resting on a rock stands on the rock, not the sand: left out)
		if Sea.clear_of_rocks(c.global_position, c.length * 0.5 + 0.1).distance_squared_to(c.global_position) > 0.0001:
			continue
		var box := _box(c)
		var t := c.global_transform
		var lowest := INF
		var sunk := 0.0
		for corner in [Vector3(box.position.x, box.position.y, box.position.z), Vector3(box.end.x, box.position.y, box.position.z),
				Vector3(box.position.x, box.position.y, box.end.z), Vector3(box.end.x, box.position.y, box.end.z)]:
			var w: Vector3 = t * corner
			sunk = maxf(sunk, Sea.ground(w.x, w.z) - w.y)
			lowest = minf(lowest, w.y)
		var middle := c.global_position
		var over := lowest - Sea.ground(middle.x, middle.z)
		var row: Array = worst.get(c.kind, [0.0, -INF, 0, c.length, box.size.y, 0, 0])
		var tol := maxf(0.03, box.size.y * 0.3)
		row[5] += int(sunk > tol)
		row[6] += int(over > tol)
		if over > tol and OS.get_cmdline_user_args().has("--why"):
			print("WHY %s at %s ground %.2f stands %.3f mode %d away %.1f zone %s dressed %s" % [c.kind, c.global_position, Sea.ground(middle.x, middle.z), c._stands(), c.mode, c.away, Sea.zone_at(middle.x, middle.z), c.dressed])
		row[0] = maxf(row[0], sunk)
		row[1] = maxf(row[1], over)
		row[2] += 1
		worst[c.kind] = row
	print("FLOOR kind | n | length m | drawn height m | worst sunk m (corners into the floor) | worst hover m (lowest point over the floor) | how many sunk, hovering")
	for kind: String in worst:
		var r: Array = worst[kind]
		var flag := ""
		if r[0] > maxf(0.05, r[4] * 0.3):
			flag += " SUNK"
		if r[1] > maxf(0.03, r[4] * 0.3):
			flag += " HOVERS"
		print("FLOOR %s | %d | %.2f | %.2f | %.3f | %.3f | %d, %d |%s" % [kind, r[2], r[3], r[4], r[0], r[1], r[5], r[6], flag])
	quit(0)
