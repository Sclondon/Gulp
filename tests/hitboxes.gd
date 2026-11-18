extends SceneTree
## Hit boxes against what is drawn (tools/QUALITY.md). For every kind in Species.ALL (and the
## player's kinds), a Fish is dressed as the game dresses it, and its drawn model is measured in the
## fish's own space (nose at -z, the fish's middle at 0):
## - drawn: the model's length nose to tail, against the length the game uses (`length`);
## - nose: where the drawn nose is against where the game puts it (-length/2), in body lengths;
## - mouth: where the game's mouth point is (Fish.mouth: 0.42 of a length ahead of the middle)
##   against the drawn mouth, taken as where the head begins (the first slice from the nose whose
##   girth is 30% of the body's greatest: a bill, a tusk or reaching arms come before it), in
##   body lengths;
## - wide, high: the drawn body's greatest width and height, in body lengths (what a touch is
##   measured against).
## Anything off by more than LIMIT is flagged.
##
## godot --headless --path . --audio-driver Dummy -s res://tests/hitboxes.gd
## (-- --kind=a,b only those; -- --slices prints a kind's girth profile)

const LIMIT := 0.08
const SLICES := 60
const CORE := 0.15

var _only := []
var _profile := false


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--kind="):
			_only = arg.trim_prefix("--kind=").split(",")
		elif arg == "--slices":
			_profile = true
	_run.call_deferred()


func _run() -> void:
	var fish_script: GDScript = load("res://scripts/fish.gd")
	var species: GDScript = load("res://scripts/species.gd")
	var all: Dictionary = species.ALL
	var made := {}
	var x := 0.0
	for kind: String in all:
		if not _only.is_empty() and not _only.has(kind):
			continue
		if not species.has(kind):
			continue
		var f: Node3D = fish_script.new()
		root.add_child(f)
		f.global_position = Vector3(x, 0.0, 0.0)
		x += 80.0
		var size: Array = all[kind].size
		f.length = (float(size[0]) + float(size[1])) * 0.5
		f.set_kind(kind)
		made[kind] = f
	# (some looks build their meshes in _ready or on their first frames)
	for i in 3:
		await process_frame
	print("HB kind | game m | drawn m (all) | body m | body/game | tip ahead | mouth err | wide | high | flags | fix: long front")
	var flagged := 0
	var rows := 0
	for kind: String in made:
		var f: Node3D = made[kind]
		f.global_basis = Basis.IDENTITY
		var r := measure(f)
		if r.is_empty():
			print("HB %s | no mesh drawn" % kind)
			continue
		rows += 1
		var length: float = f.length
		var flags := []
		var body: float = r.body
		var upright: bool = r.high > 1.5 * r.drawn
		if upright:
			# (a seahorse or a sea lily stands up: its length is its height)
			body = r.high
			flags.append("upright")
		if absf(body / length - 1.0) > LIMIT:
			flags.append("LENGTH")
		# (how far the drawn tip, feelers and all, is ahead of the game's nose: information only)
		var tip_ahead: float = (-length * 0.5 - r.nose) / length
		# The game's mouth point (Fish.mouth) against a point a little inside the body's front.
		var game_mouth: float = f.to_local(f.mouth()).z
		var mouth_err: float = (game_mouth - (r.head + 0.08 * length)) / length
		if all[kind].has("mouth"):
			# (set by hand from its girth: a bill's root, a squid's beak among its arms)
			flags.append("mouth-by-hand")
		elif not upright and absf(mouth_err) > LIMIT:
			flags.append("MOUTH")
		if flags.has("LENGTH") or flags.has("MOUTH"):
			flagged += 1
		# What `long` and `front` would make the body the game's length with its front at the nose.
		var s: float = length / f._long
		var origin: float = (f._front - f._long * 0.5) * s
		var fix := "%.3f %.3f" % [r.body / s, -(r.head - origin) / s]
		print("HB %s | %.2f | %.2f | %.2f | %.2f | %+.3f | %+.3f | %.2f | %.2f | %s | %s" % [kind, length, r.drawn, body,
			body / length, tip_ahead, mouth_err, r.wide / length, r.high / length, " ".join(flags), fix])
		if _profile:
			print("   girth by slice from the nose: ", r.girth)
	print("HB SUMMARY %d kinds measured, %d flagged (limit %.0f%%)" % [rows, flagged, LIMIT * 100.0])
	# The set-piece giants (Scenery places them, not Species): their drawn boxes, in their own space.
	if _only.is_empty():
		for named in ["old_one/old_one", "reef_back/reef_back"]:
			var path := "res://creatures/%s.gd" % named
			if not ResourceLoader.exists(path):
				continue
			var g: Node3D = (load(path) as GDScript).new()
			g.set(&"game", true)
			root.add_child(g)
			await process_frame
			await process_frame
			var lo := Vector3.INF
			var hi := -Vector3.INF
			for mi: MeshInstance3D in g.find_children("*", "MeshInstance3D", true, false):
				if not mi.is_visible_in_tree() or mi.mesh == null:
					continue
				var box: AABB = g.global_transform.affine_inverse() * mi.global_transform * mi.mesh.get_aabb()
				lo = lo.min(box.position)
				hi = hi.max(box.end)
			print("HB GIANT %s box from %s to %s" % [named, lo, hi])
	quit(0)


## The drawn model of a fish in its own space: nose (min z), tail (max z), drawn length, the
## head's start (see above), greatest width and height.
func measure(f: Node3D) -> Dictionary:
	var to_local: Transform3D = f.global_transform.affine_inverse()
	var points := PackedVector3Array()
	for mi: MeshInstance3D in f.find_children("*", "MeshInstance3D", true, false):
		if not mi.is_visible_in_tree() or mi.mesh == null:
			continue
		# (a submarine's lamp beams are light, not body)
		if String(mi.name).begins_with("Beam"):
			continue
		var t := to_local * mi.global_transform
		for s in mi.mesh.get_surface_count():
			var arrays := mi.mesh.surface_get_arrays(s)
			var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			for v in verts:
				points.append(t * v)
	if points.is_empty():
		return {}
	var lo := points[0]
	var hi := points[0]
	for p in points:
		lo = lo.min(p)
		hi = hi.max(p)
	var drawn := hi.z - lo.z
	# Girth by slice: the greater of a slice's width and height.
	var min_x := PackedFloat32Array()
	var max_x := PackedFloat32Array()
	var min_y := PackedFloat32Array()
	var max_y := PackedFloat32Array()
	for arr in [min_x, min_y]:
		arr.resize(SLICES)
		arr.fill(INF)
	for arr in [max_x, max_y]:
		arr.resize(SLICES)
		arr.fill(-INF)
	for p in points:
		var k := clampi(int((p.z - lo.z) / maxf(drawn, 0.0001) * SLICES), 0, SLICES - 1)
		min_x[k] = minf(min_x[k], p.x)
		max_x[k] = maxf(max_x[k], p.x)
		min_y[k] = minf(min_y[k], p.y)
		max_y[k] = maxf(max_y[k], p.y)
	var girth := PackedFloat32Array()
	var most := 0.0
	for k in SLICES:
		var g := -1.0
		if max_x[k] > -INF:
			g = maxf(max_x[k] - min_x[k], max_y[k] - min_y[k])
		girth.append(g)
		most = maxf(most, g)
	# (a low model has rings of points far apart: a slice with none takes the lesser of the nearest
	# on either side)
	for k in SLICES:
		if girth[k] < 0.0:
			var before := 0.0
			var after := 0.0
			for j in range(k - 1, -1, -1):
				if girth[j] >= 0.0:
					before = girth[j]
					break
			for j in range(k + 1, SLICES):
				if girth[j] >= 0.0:
					after = girth[j]
					break
			girth[k] = minf(before, after)
	# The body: from the first to the last slice of at least CORE of the greatest girth (a bill,
	# a tusk, feelers, a whip tail or reaching arms are outside it). The mouth is taken at its front.
	var first := 0
	var last := SLICES - 1
	while first < SLICES - 1 and girth[first] < most * CORE:
		first += 1
	while last > first and girth[last] < most * CORE:
		last -= 1
	var head := lo.z + drawn * (float(first) / SLICES)
	var core_back := lo.z + drawn * (float(last + 1) / SLICES)
	var shown := []
	for k in SLICES:
		shown.append(snappedf(girth[k] / maxf(most, 0.0001), 0.01))
	return {"nose": lo.z, "tail": hi.z, "drawn": drawn, "head": head, "body": core_back - head, "wide": hi.x - lo.x,
		"high": hi.y - lo.y, "girth": shown}
