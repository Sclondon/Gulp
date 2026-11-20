@tool
extends MeshInstance3D
## The bay editor's sea floor: the floor as the game makes it (read from floor_dump.gd's file), coloured
## by depth (a darker line every 5 m) and tinted by biome, with the shore drawn in cyan; plus the floor's
## hand edits (the brushes: raise, lower, smooth), kept on the bake's 1 m grid in
## tools/bay_src/floor_adjust.bin and shown at once (what changed since the last bake is added to the
## picture; Rebake makes it real).

const BAKE := preload("res://addons/bay_layout/bay_bake.gd")
const SURFACE := 40.0
## Each biome's tint (as tests/overhead.gd --biomes), in BiomeRegions.ORDER.
const ORDER := ["river", "reef", "trench", "beach", "crags", "kelp", "grass", "dunes"]
const TINTS := {"kelp": Color(0.1, 0.9, 0.2), "dunes": Color(1.0, 0.9, 0.1), "grass": Color(1.0, 0.25, 0.25), "crags": Color(0.9, 0.2, 0.9),
		"trench": Color(0.3, 0.3, 1.0), "beach": Color(0.2, 0.95, 0.95), "river": Color(0.65, 0.4, 0.15), "reef": Color(1.0, 0.55, 0.1)}
## How much of a biome's tint is laid over the depth's colour.
const TINT := 0.3

## Biomes tinted on the floor.
@export var show_biomes := true:
	set(v):
		show_biomes = v
		rebuild()

var cols := 0
var rows := 0
var west := 0.0
var north := 0.0
var cell := 2.0
## The floor as the game made it at the last refresh (world y), the shore's distance, the biomes.
var heights := PackedFloat32Array()
var shore := PackedFloat32Array()
var biomes := PackedByteArray()
## The hand edits now (metres raised, 1 m grid) and as they were when the floor was last baked.
var adjust := PackedFloat32Array()
var adjust_baked := PackedFloat32Array()
## The hand edits differ from the file (not saved yet).
var adjust_dirty := false
var _adj_size := Vector2i.ZERO
var _shore_line: MeshInstance3D
var _ring: MeshInstance3D
var _rebuild_queued := false


## Reads the floor's file (floor_dump.gd's) and the hand edits; false if the file is not there.
func load_dump(path: String) -> bool:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return false
	cols = f.get_32()
	rows = f.get_32()
	west = f.get_float()
	north = f.get_float()
	cell = f.get_float()
	heights = f.get_buffer(cols * rows * 4).to_float32_array()
	shore = f.get_buffer(cols * rows * 4).to_float32_array()
	biomes = f.get_buffer(cols * rows)
	_adj_size = BAKE.grid_size()
	adjust = BAKE.read_adjust()
	if adjust.is_empty():
		adjust.resize(_adj_size.x * _adj_size.y)
	adjust_baked = BAKE.read_adjust(BAKE.ADJUST_BAKED)
	if adjust_baked.is_empty():
		adjust_baked.resize(_adj_size.x * _adj_size.y)
	adjust_dirty = false
	rebuild()
	return true


## The floor's height at a point as shown (world y): the game's, with the edits since the last bake.
func height_at(x: float, z: float) -> float:
	if heights.is_empty():
		return 0.0
	var gx := clampf((x - west) / cell, 0.0, cols - 1.001)
	var gz := clampf((z - north) / cell, 0.0, rows - 1.001)
	var c := int(gx)
	var r := int(gz)
	var fx := gx - c
	var fz := gz - r
	var top := lerpf(_shown(r * cols + c), _shown(r * cols + c + 1), fx)
	var bottom := lerpf(_shown((r + 1) * cols + c), _shown((r + 1) * cols + c + 1), fx)
	return lerpf(top, bottom, fz)


func _shown(i: int) -> float:
	var r := i / cols
	var c := i % cols
	var k := _adj_index(west + c * cell, north + r * cell)
	return heights[i] + (adjust[k] - adjust_baked[k] if k >= 0 else 0.0)


func _adj_index(x: float, z: float) -> int:
	var c := int(round(x - BAKE.WEST))
	var r := int(round(z - BAKE.NORTH))
	if c < 0 or r < 0 or c >= _adj_size.x or r >= _adj_size.y:
		return -1
	return r * _adj_size.x + c


## Where a ray from the camera meets the floor (Vector3.INF if it misses).
func hit(from: Vector3, way: Vector3) -> Vector3:
	if heights.is_empty():
		return Vector3.INF
	way = way.normalized()
	var t := 0.0
	var was := from
	while t < 3000.0:
		var p := from + way * t
		if p.y < height_at(p.x, p.z):
			var a := was
			var b := p
			for k in 12:
				var m := (a + b) * 0.5
				if m.y < height_at(m.x, m.z):
					b = m
				else:
					a = m
			return b
		was = p
		t += 1.0
	return Vector3.INF


## One dab of a brush at `at` (world x, z): "raise", "lower" or "smooth", `radius` metres, `strength`
## metres (at the middle; less towards the edge).
func dab(mode: String, at: Vector2, radius: float, strength: float) -> void:
	var before := adjust.duplicate() if mode == "smooth" else PackedFloat32Array()
	for r in range(int(floor(at.y - radius - BAKE.NORTH)), int(ceil(at.y + radius - BAKE.NORTH)) + 1):
		for c in range(int(floor(at.x - radius - BAKE.WEST)), int(ceil(at.x + radius - BAKE.WEST)) + 1):
			if c < 0 or r < 0 or c >= _adj_size.x or r >= _adj_size.y:
				continue
			var x := BAKE.WEST + c
			var z := BAKE.NORTH + r
			var d := Vector2(x, z).distance_to(at)
			if d > radius:
				continue
			var fall := smoothstep(radius, radius * 0.4, d)
			var i := r * _adj_size.x + c
			match mode:
				"raise":
					adjust[i] += strength * fall
				"lower":
					adjust[i] -= strength * fall
				"smooth":
					# (towards the average of the floor 2 m round, as it is shown)
					var sum := 0.0
					var n := 0
					for dr in range(-2, 3):
						for dc in range(-2, 3):
							var rr := r + dr
							var cc := c + dc
							if rr < 0 or cc < 0 or rr >= _adj_size.y or cc >= _adj_size.x:
								continue
							sum += _final(rr, cc, before)
							n += 1
					adjust[i] += (sum / n - _final(r, c, before)) * clampf(strength, 0.0, 1.0) * fall
	adjust_dirty = true
	_queue_rebuild()


# The floor as shown at a 1 m cell, with the edits `edits`.
func _final(r: int, c: int, edits: PackedFloat32Array) -> float:
	var i := r * _adj_size.x + c
	var x := BAKE.WEST + c
	var z := BAKE.NORTH + r
	var gx := clampf((x - west) / cell, 0.0, cols - 1.001)
	var gz := clampf((z - north) / cell, 0.0, rows - 1.001)
	var gc := int(gx)
	var gr := int(gz)
	var fx := gx - gc
	var fz := gz - gr
	var base := lerpf(lerpf(heights[gr * cols + gc], heights[gr * cols + gc + 1], fx), lerpf(heights[(gr + 1) * cols + gc], heights[(gr + 1) * cols + gc + 1], fx), fz)
	return base + edits[i] - adjust_baked[i]


## Puts the edits back (undo, redo).
func set_adjust(values: PackedFloat32Array) -> void:
	adjust = values.duplicate()
	adjust_dirty = true
	rebuild()


## Writes the edits (tools/bay_src/floor_adjust.bin) if they changed.
func save_adjust() -> bool:
	if not adjust_dirty:
		return false
	var any := false
	for v in adjust:
		if v != 0.0:
			any = true
			break
	if any or FileAccess.file_exists(BAKE.ADJUST):
		BAKE.write_adjust(adjust)
	adjust_dirty = false
	return true


## Whether the edits differ from what was last baked (a rebake would change the floor).
func needs_bake() -> bool:
	return adjust != adjust_baked


## Shows the brush's ring on the floor (radius 0: hidden).
func show_ring(at: Vector2, radius: float) -> void:
	if _ring == null:
		_ring = MeshInstance3D.new()
		_ring.name = "BrushRing"
		_ring.mesh = ImmediateMesh.new()
		_ring.material_override = _line_material(Color(1.0, 1.0, 1.0))
		add_child(_ring)
	var im := _ring.mesh as ImmediateMesh
	im.clear_surfaces()
	if radius <= 0.0:
		return
	im.surface_begin(Mesh.PRIMITIVE_LINE_STRIP)
	for k in 49:
		var a := TAU * k / 48.0
		var p := at + Vector2(cos(a), sin(a)) * radius
		im.surface_add_vertex(Vector3(p.x, height_at(p.x, p.y) + 0.3, p.y))
	im.surface_end()


# (once a frame at most, while a brush is dragged)
func _queue_rebuild() -> void:
	if not _rebuild_queued:
		_rebuild_queued = true
		rebuild.call_deferred()


## Builds the floor's mesh and the shore's line from the heights.
func rebuild() -> void:
	_rebuild_queued = false
	if heights.is_empty():
		return
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var colours := PackedColorArray()
	verts.resize(cols * rows)
	normals.resize(cols * rows)
	colours.resize(cols * rows)
	var shown := PackedFloat32Array()
	shown.resize(cols * rows)
	for i in cols * rows:
		shown[i] = _shown(i)
	for r in rows:
		for c in cols:
			var i := r * cols + c
			var h := shown[i]
			verts[i] = Vector3(west + c * cell, h, north + r * cell)
			var hx := shown[r * cols + mini(c + 1, cols - 1)] - shown[r * cols + maxi(c - 1, 0)]
			var hz := shown[mini(r + 1, rows - 1) * cols + c] - shown[maxi(r - 1, 0) * cols + c]
			normals[i] = Vector3(-hx, 2.0 * cell, -hz).normalized()
			var colour := _depth_colour(SURFACE - h)
			if show_biomes and biomes.size() > i and biomes[i] > 0:
				colour = colour.lerp(TINTS[ORDER[biomes[i] - 1]], TINT)
			colours[i] = colour
	var index := PackedInt32Array()
	index.resize((cols - 1) * (rows - 1) * 6)
	var k := 0
	for r in rows - 1:
		for c in cols - 1:
			var a := r * cols + c
			var b := a + 1
			var d := a + cols
			var e := d + 1
			# (wound so that each faces up: (c - a) x (b - a) is +Y, Godot's front)
			index[k] = a
			index[k + 1] = b
			index[k + 2] = d
			index[k + 3] = b
			index[k + 4] = e
			index[k + 5] = d
			k += 6
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_COLOR] = colours
	arrays[Mesh.ARRAY_INDEX] = index
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.roughness = 1.0
	m.surface_set_material(0, mat)
	mesh = m
	_build_shore()


func _depth_colour(d: float) -> Color:
	var colour: Color
	if d < 0.0:
		colour = Color(0.42, 0.5, 0.3).lerp(Color(0.6, 0.55, 0.4), clampf(-d / 4.0, 0.0, 1.0))
	else:
		var stops := [[0.0, Color(0.92, 0.86, 0.66)], [8.0, Color(0.6, 0.78, 0.66)], [26.0, Color(0.32, 0.56, 0.66)],
				[50.0, Color(0.16, 0.32, 0.58)], [100.0, Color(0.05, 0.08, 0.3)]]
		colour = stops[-1][1]
		for s in stops.size() - 1:
			if d < float(stops[s + 1][0]):
				colour = (stops[s][1] as Color).lerp(stops[s + 1][1], (d - float(stops[s][0])) / (float(stops[s + 1][0]) - float(stops[s][0])))
				break
		# (a darker line every 5 m of depth)
		if fmod(d, 5.0) < 0.35:
			colour = colour.darkened(0.25)
	return colour


# The shore (where the shore distance crosses 0), as lines just over the water, by marching squares.
func _build_shore() -> void:
	if _shore_line == null:
		_shore_line = MeshInstance3D.new()
		_shore_line.name = "Shore"
		_shore_line.material_override = _line_material(Color(0.2, 1.0, 1.0))
		add_child(_shore_line)
	var lines := PackedVector3Array()
	var level := SURFACE + 0.4
	for r in rows - 1:
		for c in cols - 1:
			var v := [shore[r * cols + c], shore[r * cols + c + 1], shore[(r + 1) * cols + c + 1], shore[(r + 1) * cols + c]]
			var p := [Vector2(c, r), Vector2(c + 1, r), Vector2(c + 1, r + 1), Vector2(c, r + 1)]
			var cuts := []
			for e in 4:
				var a: float = v[e]
				var b: float = v[(e + 1) % 4]
				if (a > 0.0) != (b > 0.0):
					var t := a / (a - b)
					var q: Vector2 = (p[e] as Vector2).lerp(p[(e + 1) % 4], t)
					cuts.append(Vector3(west + q.x * cell, level, north + q.y * cell))
			if cuts.size() >= 2:
				lines.append(cuts[0])
				lines.append(cuts[1])
			if cuts.size() == 4:
				lines.append(cuts[2])
				lines.append(cuts[3])
	var m := ArrayMesh.new()
	if not lines.is_empty():
		var arrays := []
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX] = lines
		m.add_surface_from_arrays(Mesh.PRIMITIVE_LINES, arrays)
	_shore_line.mesh = m


static func _line_material(colour: Color) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = colour
	mat.no_depth_test = true
	mat.render_priority = 2
	return mat
