extends SceneTree
## Hit boxes of the set pieces against what is drawn (tools/QUALITY.md). Builds the sea as the
## game does (Scenery, as tests/rocks_bench.gd), then for each set piece samples points over its
## drawn surfaces and over its collision spheres (`Sea.add_rock`):
## - SWIM-THROUGH: the share of drawn surface whose nearest rock sphere's skin is more than
##   0.15 m (CLIP) and more than 0.4 m (HOLE) away: a small fish's middle (room 0.12) can reach it.
## - PROUD: spheres of the piece itself standing out in open water: more than 0.3 m from any drawn
##   surface (and not inside another sphere, nor under the floor) over a quarter of their skin.
## Headless:
##   godot --headless --path . --audio-driver Dummy -s res://tests/setpiece_hits.gd [-- --only=liner,pirate,ruins,kit,docks]
## Prints one table row a piece (HITS ...), the worst places (WORST ...) and the proud spheres (PROUD ...).

const CLIP := 0.15
const HOLE := 0.4
const PROUD := 0.3
const SPACING := 0.17
const MOST := 260000
## Parts drawn but meant to be swum through or round (not solid): left out of SWIM-THROUGH.
const SOFT := ["kelp", "grass", "weed", "eel", "anemone", "jelly", "net", "rope", "sail", "rigging", "flag",
		"chain", "glass", "glow", "wire", "line", "school", "plankton", "snow", "fan", "sponge", "coral",
		"anemones", "sea_rods", "mussel", "star", "urchin", "light", "shaft", "water", "sand", "dust", "bubble"]

var _scenery: Node
var _only := PackedStringArray()
var _worst := 12


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--only="):
			_only = arg.substr(7).split(",")
		elif arg.begins_with("--worst="):
			_worst = int(arg.substr(8))
	_scenery = Scenery.new()
	root.add_child(_scenery)
	_run.call_deferred()


func _wants(what: String) -> bool:
	return _only.is_empty() or _only.has(what)


func _run() -> void:
	await process_frame
	await process_frame
	print("HITS rocks in the sea: %d" % Sea.rocks.size())
	var liner: Node3D = null
	var pirate: Node3D = null
	var ruins: Node3D = null
	for child in _scenery.get_children():
		var s: Script = child.get_script()
		if s == null:
			continue
		match s.resource_path:
			"res://scripts/wreck.gd": liner = child
			"res://scripts/pirate_wreck.gd": pirate = child
			"res://scripts/ruins.gd": ruins = child
	if OS.get_cmdline_user_args().has("--fit-ruins"):
		_fit_ruins(ruins)
		quit()
		return
	print("HITS piece | drawn m2 | clip %>0.15 | hole %>0.4 | own spheres | proud | proud % of spheres")
	if liner and _wants("liner"):
		var own: Array = liner.call(&"spheres")
		_piece("liner", _meshes_under(liner.get_node("Liner")), own)
	if pirate and _wants("pirate"):
		_piece("pirate", _meshes_under(pirate.get_node("Model")), pirate.get(&"_rocks"))
	if ruins and _wants("ruins"):
		var own: Array = []
		for r: Vector4 in ruins.call(&"rocks"):
			var m: Vector3 = ruins.global_transform * Vector3(r.x, r.y, r.z)
			own.append(Vector4(m.x, m.y, m.z, r.w * ruins.global_basis.get_scale().x))
		_piece("ruins", _meshes_under(ruins.get_node("Model")), own)
	if _wants("kit"):
		_kit()
	if _wants("docks"):
		_others(liner, pirate, ruins)
	quit()


# Every MeshInstance3D under a node, as [label, mesh, world transform].
func _meshes_under(node: Node) -> Array:
	var out := []
	for m: MeshInstance3D in node.find_children("*", "MeshInstance3D", true, false):
		if m.mesh:
			out.append([String(m.name), m.mesh, m.global_transform])
	return out


func _soft(label: String) -> bool:
	var low := label.to_lower().replace("sailboat", "boat")
	for word: String in SOFT:
		if low.contains(word):
			return true
	return false


# Area-weighted points over the drawn surfaces: [points, normals, labels (index into names)].
func _sample(drawn: Array, names: PackedStringArray, skip_soft := true) -> Array:
	var pts := PackedVector3Array()
	var nrm := PackedVector3Array()
	var lab := PackedInt32Array()
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	var area_all := 0.0
	for each: Array in drawn:
		if skip_soft and _soft(each[0]):
			continue
		var mesh: Mesh = each[1]
		var xf: Transform3D = each[2]
		var li := names.find(each[0])
		if li < 0:
			names.append(each[0])
			li = names.size() - 1
		for s in mesh.get_surface_count():
			var arrays := mesh.surface_get_arrays(s)
			var v: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var vn: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL] if arrays[Mesh.ARRAY_NORMAL] != null else PackedVector3Array()
			var idx: PackedInt32Array = arrays[Mesh.ARRAY_INDEX] if arrays[Mesh.ARRAY_INDEX] != null else PackedInt32Array()
			var tris := idx.size() / 3 if idx.size() > 0 else v.size() / 3
			for t in tris:
				var ia := idx[t * 3] if idx.size() > 0 else t * 3
				var ib := idx[t * 3 + 1] if idx.size() > 0 else t * 3 + 1
				var ic := idx[t * 3 + 2] if idx.size() > 0 else t * 3 + 2
				var a := xf * v[ia]
				var b := xf * v[ib]
				var c := xf * v[ic]
				var cr := (b - a).cross(c - a)
				var area := cr.length() * 0.5
				if area < 1e-6:
					continue
				area_all += area
				var n := Vector3.ZERO
				if vn.size() > 0:
					n = (xf.basis * (vn[ia] + vn[ib] + vn[ic])).normalized()
				else:
					n = -cr.normalized()
				var want := area / (SPACING * SPACING)
				var k := int(want)
				if rng.randf() < want - k:
					k += 1
				for j in k:
					var u := rng.randf()
					var w := rng.randf()
					if u + w > 1.0:
						u = 1.0 - u
						w = 1.0 - w
					pts.append(a + (b - a) * u + (c - a) * w)
					nrm.append(n)
					lab.append(li)
	# (too many: thinned evenly, each then standing for more area)
	if pts.size() > MOST:
		var keep := float(MOST) / pts.size()
		var p2 := PackedVector3Array()
		var n2 := PackedVector3Array()
		var l2 := PackedInt32Array()
		for i in pts.size():
			if rng.randf() < keep:
				p2.append(pts[i])
				n2.append(nrm[i])
				l2.append(lab[i])
		pts = p2
		nrm = n2
		lab = l2
	return [pts, nrm, lab, area_all]


# How far a point is outside the nearest rock sphere's skin (negative: inside), capped at `cap`.
func _gap(p: Vector3, spheres_extra: Array, cap := 0.6) -> float:
	var best := cap
	for cx in range(floori((p.x - cap) / Sea.FINE), floori((p.x + cap) / Sea.FINE) + 1):
		for cy in range(floori((p.y - cap) / Sea.FINE), floori((p.y + cap) / Sea.FINE) + 1):
			for cz in range(floori((p.z - cap) / Sea.FINE), floori((p.z + cap) / Sea.FINE) + 1):
				var near: Variant = Sea._fine.get(Sea._fine_key(cx, cy, cz))
				if near == null:
					continue
				var list: PackedFloat32Array = near
				var k := 0
				while k < list.size():
					var d := p.distance_to(Vector3(list[k], list[k + 1], list[k + 2])) - list[k + 3]
					if d < best:
						best = d
					k += 4
	for s: Vector4 in spheres_extra:
		best = minf(best, p.distance_to(Vector3(s.x, s.y, s.z)) - s.w)
	return best


func _inside_any(p: Vector3, except: Vector4) -> bool:
	var near: Variant = Sea._fine.get(Sea._fine_key(floori(p.x / Sea.FINE), floori(p.y / Sea.FINE), floori(p.z / Sea.FINE)))
	if near == null:
		return false
	var list: PackedFloat32Array = near
	var k := 0
	while k < list.size():
		var c := Vector3(list[k], list[k + 1], list[k + 2])
		if list[k + 3] != except.w or c.distance_squared_to(Vector3(except.x, except.y, except.z)) > 1e-6:
			if p.distance_to(c) < list[k + 3] - 0.02:
				return true
		k += 4
	return false


# A grid of surface samples (cells of 0.5 m) for nearest-surface questions.
func _grid(pts: PackedVector3Array) -> Dictionary:
	var g := {}
	for i in pts.size():
		var key := Vector3i(floori(pts[i].x * 2.0), floori(pts[i].y * 2.0), floori(pts[i].z * 2.0))
		if not g.has(key):
			g[key] = PackedInt32Array()
		var l: PackedInt32Array = g[key]
		l.append(i)
		g[key] = l
	return g


# The nearest surface sample to a point within 0.5..1 m: [distance, index] (INF, -1 when none).
func _nearest(q: Vector3, g: Dictionary, pts: PackedVector3Array) -> Array:
	var best := INF
	var at := -1
	var kx := floori(q.x * 2.0)
	var ky := floori(q.y * 2.0)
	var kz := floori(q.z * 2.0)
	for dx in range(-1, 2):
		for dy in range(-1, 2):
			for dz in range(-1, 2):
				var l: Variant = g.get(Vector3i(kx + dx, ky + dy, kz + dz))
				if l == null:
					continue
				for i: int in l:
					var d := q.distance_squared_to(pts[i])
					if d < best:
						best = d
						at = i
	return [sqrt(best), at]


# Every fourth surface sample in cells of 2 m, for "which way is the nearest surface" further off.
func _coarse(pts: PackedVector3Array) -> Dictionary:
	var g := {}
	for i in range(0, pts.size(), 4):
		var key := Vector3i(floori(pts[i].x * 0.5), floori(pts[i].y * 0.5), floori(pts[i].z * 0.5))
		if not g.has(key):
			g[key] = PackedInt32Array()
		var l: PackedInt32Array = g[key]
		l.append(i)
		g[key] = l
	return g


func _nearest_coarse(q: Vector3, g: Dictionary, pts: PackedVector3Array) -> int:
	var best := INF
	var at := -1
	var kx := floori(q.x * 0.5)
	var ky := floori(q.y * 0.5)
	var kz := floori(q.z * 0.5)
	for dx in range(-1, 2):
		for dy in range(-1, 2):
			for dz in range(-1, 2):
				var l: Variant = g.get(Vector3i(kx + dx, ky + dy, kz + dz))
				if l == null:
					continue
				for i: int in l:
					var d := q.distance_squared_to(pts[i])
					if d < best:
						best = d
						at = i
	return at


func _piece(label: String, drawn: Array, own: Array, extra_spheres := [], rows := -1) -> void:
	var show := _worst if rows < 0 else rows
	var t0 := Time.get_ticks_msec()
	var names := PackedStringArray()
	var got := _sample(drawn, names)
	var pts: PackedVector3Array = got[0]
	var nrm: PackedVector3Array = got[1]
	var lab: PackedInt32Array = got[2]
	var per := float(got[3]) / maxf(pts.size(), 1)
	if pts.is_empty():
		print("HITS %s: nothing drawn" % label)
		return
	var clip := 0
	var hole := 0
	var low_holes := 0
	var cells := {}
	for i in pts.size():
		# (under the sea floor nothing can reach it anyway)
		if pts[i].y < Sea.ground(pts[i].x, pts[i].z) + 0.05 or pts[i].y > Sea.SURFACE:
			continue
		var g := _gap(pts[i], extra_spheres)
		if g > CLIP:
			clip += 1
		if g > HOLE:
			hole += 1
			var key := Vector3i(floori(pts[i].x / 2.0), floori(pts[i].y / 2.0), floori(pts[i].z / 2.0))
			if not cells.has(key):
				cells[key] = {"n": 0, "parts": {}, "at": Vector3.ZERO, "up": 0.0, "low": 0}
			cells[key].n += 1
			cells[key].at += pts[i]
			cells[key].up += nrm[i].y
			if pts[i].y < Sea.ground(pts[i].x, pts[i].z) + 0.6:
				cells[key].low += 1
				low_holes += 1
			cells[key].parts[names[lab[i]]] = int(cells[key].parts.get(names[lab[i]], 0)) + 1
	# Proud spheres.
	var g := _grid(pts)
	var proud := []
	var coarse := _coarse(pts)
	var dirs := _dirs(32)
	for s: Vector4 in own:
		var c := Vector3(s.x, s.y, s.z)
		var out := 0
		var most := 0.0
		for d in dirs:
			var q := c + d * s.w
			if q.y < Sea.ground(q.x, q.z) + 0.02 or _inside_any(q, s):
				continue
			var n: Array = _nearest(q, g, pts)
			if n[1] < 0:
				# (no surface within half a metre: in open water, or deep inside a thick part: the nearest
				# surface further off says which, by its facing)
				var far := _nearest_coarse(q, coarse, pts)
				if far < 0 or (q - pts[far]).dot(nrm[far]) > 0.0:
					out += 1
					most = maxf(most, 1.0 if far < 0 else q.distance_to(pts[far]))
			elif float(n[0]) > PROUD and (q - pts[n[1]]).dot(nrm[n[1]]) > 0.0:
				out += 1
				most = maxf(most, float(n[0]))
		if out >= dirs.size() / 4:
			proud.append([s, out, most])
	var counted := 0
	for i in pts.size():
		if pts[i].y >= Sea.ground(pts[i].x, pts[i].z) + 0.05 and pts[i].y <= Sea.SURFACE:
			counted += 1
	print("HITS %s | %.0f | %.1f | %.1f | %d | %d | %.1f   (%d samples, %.0f s)" % [label, float(got[3]),
			100.0 * clip / maxf(counted, 1), 100.0 * hole / maxf(counted, 1), own.size(), proud.size(),
			100.0 * proud.size() / maxf(own.size(), 1), pts.size(), (Time.get_ticks_msec() - t0) / 1000.0])
	print("HITS %s: of the holes, %.0f%% are within 0.6 m of the floor (low debris, paving: a fish sinks in only so far)" % [label, 100.0 * low_holes / maxf(hole, 1)])
	var keys := cells.keys()
	keys.sort_custom(func(a, b): return cells[a].n > cells[b].n)
	for k in mini(keys.size(), show):
		var cell: Dictionary = cells[keys[k]]
		var parts: Array = cell.parts.keys()
		parts.sort_custom(func(a, b): return cell.parts[a] > cell.parts[b])
		print("WORST %s %.1f m2 open at %s (%d%% within 0.6 m of the floor, facing up %.2f) parts %s" % [label, cell.n * per, str((cell.at / cell.n).snapped(Vector3.ONE * 0.1)), 100 * cell.low / cell.n, cell.up / cell.n, str(parts.slice(0, 3))])
	proud.sort_custom(func(a, b): return a[1] * a[0].w > b[1] * b[0].w)
	for k in mini(proud.size(), maxi(show, 12)):
		var s: Vector4 = proud[k][0]
		print("PROUD %s sphere at %s r %.2f: %d of %d points of its skin stand off (most %.2f m)" % [label,
				str(Vector3(s.x, s.y, s.z).snapped(Vector3.ONE * 0.1)), s.w, proud[k][1], dirs.size(), proud[k][2]])


func _dirs(n: int) -> PackedVector3Array:
	var out := PackedVector3Array()
	var golden := PI * (3.0 - sqrt(5.0))
	for i in n:
		var y := 1.0 - (i + 0.5) / n * 2.0
		var r := sqrt(1.0 - y * y)
		out.append(Vector3(cos(golden * i) * r, y, sin(golden * i) * r))
	return out


# The sea floor kit's pieces, each alone in its own space against its own spheres (the drawn
# model: the full one, or the light one for the cliffs, which Scenery draws light near too).
func _kit() -> void:
	var props: GDScript = load(Scenery.PROPS)
	var placed: Dictionary = _scenery.get(&"_placed")
	var counts := {}
	for piece: String in placed:
		counts[piece] = (placed[piece][0] as Array).size()
	print("HITS kit: one row a piece (alone, at scale 1; its count in the sea after the name)")
	for piece: String in props.call(&"names", ""):
		var spheres: Array = props.call(&"spheres_of", piece)
		if spheres.is_empty():
			continue
		var mesh: Mesh = props.call(&"mesh_of", piece, piece.begins_with("cliff"))
		if mesh == null:
			continue
		_alone("kit %s x%d" % [piece, int(counts.get(piece, 0))], [[piece, mesh, Transform3D()]], spheres)


# A piece in its own space against a list of spheres (not the sea's).
func _alone(label: String, drawn: Array, spheres: Array) -> void:
	var names := PackedStringArray()
	var got := _sample(drawn, names, false)
	var pts: PackedVector3Array = got[0]
	var nrm: PackedVector3Array = got[1]
	var clip := 0
	var hole := 0
	var low := INF
	for p in pts:
		low = minf(low, p.y)
	var counted := 0
	for p in pts:
		# (its foot is in the floor)
		if p.y < low + 0.1:
			continue
		counted += 1
		var best := INF
		for s: Vector4 in spheres:
			best = minf(best, p.distance_to(Vector3(s.x, s.y, s.z)) - s.w)
		if best > CLIP:
			clip += 1
		if best > HOLE:
			hole += 1
	var g := _grid(pts)
	var proud := 0
	var dirs := _dirs(32)
	for s: Vector4 in spheres:
		var out := 0
		for d in dirs:
			var q := Vector3(s.x, s.y, s.z) + d * s.w
			if q.y < low + 0.05:
				continue
			var inside := false
			for o: Vector4 in spheres:
				if o != s and q.distance_to(Vector3(o.x, o.y, o.z)) < o.w - 0.02:
					inside = true
					break
			if inside:
				continue
			var n: Array = _nearest(q, g, pts)
			if n[1] < 0 or (float(n[0]) > PROUD and (q - pts[n[1]]).dot(nrm[n[1]]) > 0.0):
				out += 1
		if out >= dirs.size() / 4:
			proud += 1
	print("HITS %s | %.1f | %.1f | %.1f | %d | %d | %.1f" % [label, float(got[3]), 100.0 * clip / maxf(counted, 1),
			100.0 * hole / maxf(counted, 1), spheres.size(), proud, 100.0 * proud / maxf(spheres.size(), 1)])


# What else Scenery draws whole (docks, piles, floats, moored boats, the outcrop, mangroves, the
# giants): every MultiMesh and mesh under it that is not a set piece's or the kit's LodField,
# grouped by node name, against all the sea's rocks; and every rock not of the three set pieces
# nor of the kit as placed, checked for standing proud of all of that.
func _others(liner: Node, pirate: Node, ruins: Node) -> void:
	var drawn := []
	for node in _scenery.find_children("*", "GeometryInstance3D", true, false):
		if (liner and liner.is_ancestor_of(node)) or (pirate and pirate.is_ancestor_of(node)) or (ruins and ruins.is_ancestor_of(node)):
			continue
		var p := node.get_parent()
		var in_field := false
		while p and p != _scenery:
			if p is LodField:
				in_field = true
			p = p.get_parent()
		if in_field:
			continue
		# (named by what it draws: the docks' and kit's meshes keep their names from their models)
		var shown: Mesh = (node as MultiMeshInstance3D).multimesh.mesh if node is MultiMeshInstance3D and (node as MultiMeshInstance3D).multimesh else (node as MeshInstance3D).mesh if node is MeshInstance3D else null
		var label := String(node.get_parent().name) + "/" + (shown.resource_name if shown and shown.resource_name != "" else String(node.name))
		if node is MultiMeshInstance3D:
			var mm := (node as MultiMeshInstance3D).multimesh
			if mm == null or mm.mesh == null or mm.instance_count == 0:
				continue
			var xf := (node as Node3D).global_transform
			for i in mm.instance_count:
				drawn.append([label, mm.mesh, xf * mm.get_instance_transform(i)])
		elif node is MeshInstance3D and (node as MeshInstance3D).mesh:
			drawn.append([label, (node as MeshInstance3D).mesh, (node as Node3D).global_transform])
	# Which are which, by name: one row each.
	var by := {}
	for each: Array in drawn:
		var key: String = each[0]
		if not by.has(key):
			by[key] = []
		by[key].append(each)
	var keys := by.keys()
	keys.sort()
	print("HITS other drawn things (grouped by node name; soft ones listed, not counted): %s" % str(keys))
	# The rocks not owned by the set pieces or the kit's placements.
	var known := {}
	var props: GDScript = load(Scenery.PROPS)
	var placed: Dictionary = _scenery.get(&"_placed")
	for piece: String in placed:
		var sph: Array = props.call(&"spheres_of", piece)
		for where: Transform3D in placed[piece][0]:
			for s: Vector4 in sph:
				var m := where * Vector3(s.x, s.y, s.z)
				known[Vector3(m.x, m.y, m.z).snapped(Vector3.ONE * 0.01)] = true
	var owned := []
	if liner:
		owned.append_array(liner.call(&"spheres"))
	if pirate:
		owned.append_array(pirate.get(&"_rocks"))
	if ruins:
		for r: Vector4 in ruins.call(&"rocks"):
			var m: Vector3 = ruins.global_transform * Vector3(r.x, r.y, r.z)
			owned.append(Vector4(m.x, m.y, m.z, 0))
	for s: Vector4 in owned:
		known[Vector3(s.x, s.y, s.z).snapped(Vector3.ONE * 0.01)] = true
	var rest := []
	for s: Vector4 in Sea.rocks:
		if not known.has(Vector3(s.x, s.y, s.z).snapped(Vector3.ONE * 0.01)):
			rest.append(s)
	# The kit's pieces as placed are drawn too: added so that a dock pile's spheres beside a rock are judged fairly.
	var kit_drawn := []
	for piece: String in placed:
		var mesh: Mesh = props.call(&"mesh_of", piece, piece.begins_with("cliff"))
		if mesh == null or (props.call(&"spheres_of", piece) as Array).is_empty():
			continue
		for where: Transform3D in placed[piece][0]:
			kit_drawn.append(["kit_" + piece, mesh, where])
	for key: String in keys:
		if _soft(key):
			continue
		_piece("other " + key, by[key], [], [], 2)
	_piece("other: the rest of the rocks (piles, floats, boats, outcrop, mangroves, giants) against all drawn", drawn + kit_drawn, rest, [], 30)


# --- Atlantis' extra spheres (models/ruins_canyon_extra.json; models/ruins_extra.json was the first, flat Atlantis', retired): its build fits spheres only to pieces thick enough
# for them, so its thin paving slabs over the falling floor and many tops were open to a fish passing through.
# Run with the extra ones left out (`--no-ruins-extra`, read by Ruins), it adds, greediest first, a sphere of
# FIT_R a little inside each part of the drawn surface still more than FIT_GAP from every rock, kept out of
# the swim routes, and writes them in the ruins' own space:
#   godot --headless --path . --audio-driver Dummy -s res://tests/setpiece_hits.gd -- --fit-ruins --no-ruins-extra
const FIT_GAP := 0.3
const FIT_R := 0.45
const FIT_IN := 0.2


func _fit_ruins(ruins: Node3D) -> void:
	var names := PackedStringArray()
	var got := _sample(_meshes_under(ruins.get_node("Model")), names)
	var pts: PackedVector3Array = got[0]
	var nrm: PackedVector3Array = got[1]
	var open := []
	for i in pts.size():
		if pts[i].y < Sea.ground(pts[i].x, pts[i].z) + 0.05 or pts[i].y > Sea.SURFACE:
			continue
		var g := _gap(pts[i], [])
		if g > FIT_GAP:
			open.append([g, i])
	open.sort_custom(func(a, b): return a[0] > b[0])
	# the routes in the world: segments with their room
	var segs := []
	var to_world := ruins.global_transform
	var routes: Dictionary = ruins.get_script().call(&"routes")
	for name: String in routes:
		var p: PackedVector3Array = routes[name][0]
		for k in p.size() - 1:
			segs.append([to_world * p[k], to_world * p[k + 1], float(routes[name][1]) * to_world.basis.get_scale().x])
	var g := _grid(pts)
	var covered := {}
	var made := []
	for each: Array in open:
		var i: int = each[1]
		if covered.has(i):
			continue
		var c := pts[i] - nrm[i] * FIT_IN
		var r := FIT_R
		for s: Array in segs:
			var on := Geometry3D.get_closest_point_to_segment(c, s[0], s[1])
			r = minf(r, c.distance_to(on) - float(s[2]) - 0.08)
		if r < FIT_IN + 0.08:
			covered[i] = true
			continue
		made.append(Vector4(c.x, c.y, c.z, r))
		# (what it now covers: samples whose gap to it is under FIT_GAP)
		var reach := r + FIT_GAP
		for dx in range(-2, 3):
			for dy in range(-2, 3):
				for dz in range(-2, 3):
					var l: Variant = g.get(Vector3i(floori(c.x * 2.0) + dx, floori(c.y * 2.0) + dy, floori(c.z * 2.0) + dz))
					if l == null:
						continue
					for j: int in l:
						if pts[j].distance_to(c) < reach:
							covered[j] = true
	var back := to_world.affine_inverse()
	var grow := to_world.basis.get_scale().x
	var out := []
	for s: Vector4 in made:
		var m := back * Vector3(s.x, s.y, s.z)
		out.append([snappedf(m.x, 0.001), snappedf(m.y, 0.001), snappedf(m.z, 0.001), snappedf(s.w / grow, 0.001)])
	var f := FileAccess.open(Ruins.EXTRA, FileAccess.WRITE)
	f.store_string(JSON.stringify({"about": "Atlantis' extra collision spheres (its own space: x, y, z, radius), made by tests/setpiece_hits.gd --fit-ruins over the surface its build's spheres left open; read by Ruins", "spheres": out}))
	f.close()
	print("FIT ruins: %d open samples, %d extra spheres written to %s" % [open.size(), made.size(), Ruins.EXTRA])
