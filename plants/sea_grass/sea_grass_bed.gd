class_name SeaGrassBed
extends Node3D
## A bed of eelgrass (Zostera marina), cheap in the hundreds or thousands: each tuft is two to
## four shoots of long flat ribbon leaves (three variants and a light one for far off, built in
## Blender), drawn by a few MultiMeshes for each square of sea floor `cell` metres across. All of
## the moving is in sea_grass.gdshader: the leaves bend over together down-current, a slow surge
## runs through the bed as a wave and swings them to and fro, a ripple runs up each leaf, and up
## to four pushers lay the grass aside.
##
## Two ways to fill it:
##
##   # A meadow over an area, filled square by square as the camera nears (GameCommon `grass`'s way):
##   SeaGrassBed.field(self, Rect2(-40, -40, 80, 80), 1.0, {
##       "mask": func(p: Vector2) -> float: return ...,      # 0..1, the chance of a tuft there
##       "height": func(p: Vector2) -> float: return ...,    # the floor's height there (world y)
##       "tall": func(p: Vector2) -> Vector2: return ...})   # the tufts' height there, least and most (m)
##   SeaGrassBed.set_quality(SeaGrassBed.Quality.LOW)        # for a phone: rebuilds every field
##
##   # Or a list of tufts, all at once:
##   var bed := SeaGrassBed.new()
##   add_child(bed)
##   bed.plant(places, heights)                 # tufts' feet, each tuft's height (0.4 to 1.2 m)
##
##   bed.current = Vector2(0.3, 0.0)            # which way the water streams, and how hard
##   bed.pushers = PackedVector3Array([fish.global_position])   # each frame: up to four
##   SeaGrassBed.push(fish, 0.8)                # or: it pushes every field by itself, nearest four to the camera
##
## `places` and a field's `area` are in the bed's own space: leave the node unturned and unscaled (a
## planted bed may be moved; a field stays at the origin: its area is in world metres).
##
## The shader reads the global shader uniform `water_clock` (seconds). If the project declares
## none (Project Settings > Shader Globals), the first bed adds one and runs it; if it declares
## one, the game sets it.

enum Quality { LOW, MEDIUM, HIGH }

const MODEL := "res://plants/sea_grass/models/sea_grass_%s.glb"
const SHADER := "res://plants/sea_grass/sea_grass.gdshader"
const CLOCK := &"water_clock"
const VARIANTS := ["a", "b", "c"]
const MOST_PUSHERS := 4
## The group of nodes that push every bed (`push`), and the group of fields (`set_quality`).
const PUSHERS := &"sea_grass_pushers"
const FIELDS := &"sea_grass_fields"
## How long a frame may spend filling a field's squares with tufts, microseconds (all fields
## together). A square's filling is carried over to the next frame when this runs out.
const FILL_BUDGET := 1200

## Per quality, for fields: tufts per square metre at full density, how far full density reaches, where
## the grass has gone entirely, the least share kept far off, and past where squares draw the light
## tuft (metres). Between `lod_near` and `fade_end` the tufts thin as 1 / distance (down to `keep_min`)
## and those still drawn sink into the floor over the last half, so the meadow has no edge where it ends.
const PRESETS := {
	Quality.LOW: {"tufts": 2.5, "lod_near": 10.0, "fade_end": 30.0, "keep_min": 0.45, "far_mesh": 7.0},
	Quality.MEDIUM: {"tufts": 4.0, "lod_near": 14.0, "fade_end": 40.0, "keep_min": 0.45, "far_mesh": 10.0},
	Quality.HIGH: {"tufts": 5.0, "lod_near": 18.0, "fade_end": 50.0, "keep_min": 0.45, "far_mesh": 14.0},
}

## The quality every field builds at. Change it with set_quality() to rebuild fields already made.
static var quality: int = Quality.MEDIUM

## Filling cost, all fields together: microseconds spent filling squares in the last frame that filled
## any, the most in one frame so far, and how many squares have been filled (for a game's perf counter).
static var fill_usec := 0
static var fill_usec_most := 0
static var squares_filled := 0

## How far the surge swings the leaves: 1 about 30 degrees either way at the tip, 0 still.
@export_range(0.0, 3.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Which way the water streams (world x, z) and how hard: at length 1 the tips bend over about
## 80 degrees down-current; the surge swings along it.
@export var current := Vector2.ZERO:
	set(value):
		current = value
		_send(&"current", value)
## Up to four world points that lay the grass aside (a fish, a diver); more are left out. Ignored
## while anything is in the PUSHERS group (`push`).
@export var pushers := PackedVector3Array():
	set(value):
		pushers = value
		_send_pushers()
## How far from a pusher the grass is laid aside (metres).
@export var push_radius := 0.8:
	set(value):
		push_radius = value
		_send_pushers()
## Planted beds: squares nearer the camera than this draw the full tufts, the rest the light one
## (metres). Fields use their quality's `far_mesh`.
@export var near := 10.0
## Planted beds: squares farther than this are not drawn (0: drawn however far). Fields fade out by
## their quality's `fade_end`.
@export var far := 0.0
## The side of a square of sea floor whose tufts are drawn together (metres). Set it before `plant`
## or `build`.
@export var cell := 8.0
## Changes which variant and which way round each tuft is (and, in a field, where each stands).
@export var seed := 1

# --- Fields only (see `field`) -------------------------------------------------------------
## The rectangle (world x, z) the field covers.
@export var area := Rect2(-20, -20, 40, 40)
## A multiplier on the quality's tufts per square metre (1 a full meadow, 0.3 sparse; up to 3).
@export_range(0.0, 3.0) var density := 1.0
## Optional: Vector2 world xz -> 0..1, the chance of a tuft there (0 keeps grass out).
var mask: Callable
## Optional: Vector2 world xz -> float, the floor's height there (default flat at y = 0).
var height: Callable
## Optional: Vector2 world xz -> Vector2, the least and most a tuft is tall there (metres; default
## `tall_range`). A tuft's own height is picked between them.
var tall: Callable
@export var tall_range := Vector2(0.4, 1.2)
## How far down into the floor a tuft's foot is set (metres), so it never stands on a slope's air.
@export var sink_feet := 0.03
## Metres between the points `mask`, `height` and `tall` are called at when a square is filled, read
## between them (0: called for every tuft). For a mask that is slow to work out; its edges soften
## over this distance.
@export_range(0.0, 8.0) var sample_step := 1.0
## How far the grass reaches before it has faded out, as a share of the quality's own distance.
@export_range(0.5, 3.0) var reach := 1.0
## How far it is drawn at full density before it starts to thin, as a share of the quality's own.
@export_range(0.5, 3.0) var full_reach := 1.0

static var _meshes := {}
static var _shader: Shader
## Whether this component added `water_clock` (and so must run it), and the frame it last did.
static var _runs_clock := false
static var _clock := 0.0
static var _clock_frame := -1
## The frame the fill budget was last started, and what is left of it (shared by every field).
static var _budget_frame := -1
static var _budget_left := 0
static var _pushers_frame := -1
static var _group_pushers := PackedVector4Array()

var _material: ShaderMaterial
var _blocks: Array = []
var _tufts := 0
# Fields: the squares ({rect, filled, job, full, low, low_y, high_y, shown, share}), how many
# across, the preset as scaled by reach, where the camera was when they were last thinned, the
# squares still to be filled (nearest first) and those showing now.
var _is_field := false
var _chunks: Array = []
var _across := 0
var _preset := {}
var _thinned_for := Vector3.INF
var _unfilled: Array[int] = []
var _showing := {}


## Makes a field over `area_xz` (world x, z) under `parent` and builds it. `settings` sets any
## property by name: "mask", "height", "tall" (callables), "current", "cell", "seed", "sample_step"...
static func field(parent: Node, area_xz: Rect2, density_scale := 1.0, settings := {}) -> SeaGrassBed:
	var made := SeaGrassBed.new()
	made.area = area_xz
	made.density = density_scale
	for key: String in settings:
		made.set(key, settings[key])
	parent.add_child(made)
	made.build()
	return made


## Lets `node` lay aside the grass of every bed (the four nearest the camera are used). `radius` in metres.
static func push(node: Node3D, radius := 0.8) -> void:
	node.set_meta(&"sea_grass_radius", radius)
	node.add_to_group(PUSHERS)


static func unpush(node: Node3D) -> void:
	node.remove_from_group(PUSHERS)


## Sets the quality for every field from now on and rebuilds those already made.
static func set_quality(level: int) -> void:
	quality = clampi(level, Quality.LOW, Quality.HIGH)
	var tree := Engine.get_main_loop() as SceneTree
	if tree != null:
		for made in tree.get_nodes_in_group(FIELDS):
			(made as SeaGrassBed).build()


## Fills every field's squares within `radius` of `point` now, all at once (where a round begins, or
## before a picture is taken).
static func fill_all_near(point: Vector3, radius: float) -> void:
	var tree := Engine.get_main_loop() as SceneTree
	if tree != null:
		for made in tree.get_nodes_in_group(FIELDS):
			(made as SeaGrassBed).fill_near(point, radius)


## The mesh of a tuft: variant 0, 1 or 2 ("a", "b", "c"), or the light one.
static func mesh_of(variant := 0, low := false) -> Mesh:
	var path := MODEL % ("lo" if low else VARIANTS[variant % 3])
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]


## How many triangles a mesh has.
static func triangles_of(mesh: Mesh) -> int:
	var key := "triangles %d" % mesh.get_instance_id()
	if _meshes.has(key):
		return _meshes[key]
	var all := 0
	for surface in mesh.get_surface_count():
		var arrays := mesh.surface_get_arrays(surface)
		var index: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		all += (index.size() if not index.is_empty() else (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array).size()) / 3
	_meshes[key] = all
	return all


## A new material wearing sea_grass.gdshader (the top of the shader lists its settings).
static func new_material() -> ShaderMaterial:
	if _shader == null:
		# (the shader names the clock, so the clock must be there before the shader is read;
		# asking the RenderingServer for its list is for the editor only, so ask the project,
		# and whether another component has added it already)
		if not ProjectSettings.has_setting("shader_globals/" + CLOCK) and not Engine.has_meta(CLOCK):
			RenderingServer.global_shader_parameter_add(CLOCK, RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.0)
			Engine.set_meta(CLOCK, true)
			_runs_clock = true
		_shader = load(SHADER)
	var made := ShaderMaterial.new()
	made.shader = _shader
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	if _is_field:
		add_to_group(FIELDS)


func _clear() -> void:
	for block: Dictionary in _blocks:
		for part: Node in block.parts:
			part.queue_free()
	_blocks.clear()
	for c: Dictionary in _chunks:
		for part: Node in c.full:
			part.queue_free()
		if c.low != null:
			(c.low as Node).queue_free()
	_chunks.clear()
	_unfilled.clear()
	_showing.clear()
	_thinned_for = Vector3.INF
	_tufts = 0


## Plants the bed (taking up whatever was planted before): a tuft at each of `places` (the bed's
## own space), each `heights[i]` metres tall (0.4 to 1.2 is what it is made for).
func plant(places: PackedVector3Array, heights: PackedFloat32Array) -> void:
	_clear()
	_is_field = false
	_send_all()
	_material.set_shader_parameter(&"fade_end", 0.0)
	_tufts = places.size()
	var rng := RandomNumberGenerator.new()
	rng.seed = seed
	var found := {}
	for i in places.size():
		var at := places[i]
		var tall_m := clampf(heights[i] if i < heights.size() else 0.8, 0.05, 4.0)
		var wide := rng.randf_range(0.85, 1.1)
		var basis := Basis(Vector3.UP, rng.randf() * TAU).scaled_local(Vector3(wide, tall_m, wide))
		var key := Vector2i(floori(at.x / cell), floori(at.z / cell))
		if not found.has(key):
			found[key] = {"tufts": [[], [], []], "full": [], "low": null, "parts": [], "core": AABB(at, Vector3.ZERO),
					"box": AABB(at, Vector3.ZERO), "shown": -1, "triangles_full": 0, "triangles_low": 0}
		var block: Dictionary = found[key]
		(block.tufts[rng.randi() % 3] as Array).append([Transform3D(basis, at), Color(rng.randf(), 0.0, 0.0, 0.0)])
		block.core = (block.core as AABB).expand(at)
		# (a leaf may lie over as far as it is long, and be pushed a little farther)
		var reach_m := tall_m * 1.1 + 0.1
		block.box = (block.box as AABB).merge(AABB(at - Vector3(reach_m, 0.1, reach_m), Vector3(reach_m * 2.0, tall_m + 0.2, reach_m * 2.0)))
	for block: Dictionary in found.values():
		var all: Array = []
		for v in 3:
			var some: Array = block.tufts[v]
			all.append_array(some)
			if not some.is_empty():
				(block.full as Array).append(_part(some, mesh_of(v), block.box))
				block.triangles_full += some.size() * triangles_of(mesh_of(v))
		block.low = _part(all, mesh_of(0, true), block.box)
		block.parts.append(block.low)
		block.parts.append_array(block.full)
		block.triangles_low = all.size() * triangles_of(mesh_of(0, true))
		block.erase("tufts")
		_blocks.append(block)
	_choose()


## (Re)builds a field from its settings at the current quality: its squares are laid out, and each is
## filled with tufts only when the camera first comes near it (a few a frame, nearest first).
func build() -> void:
	_clear()
	_is_field = true
	if is_inside_tree():
		add_to_group(FIELDS)
	_preset = (PRESETS[quality] as Dictionary).duplicate()
	_preset.fade_end *= reach
	_preset.lod_near *= full_reach
	_send_all()
	_material.set_shader_parameter(&"lod_near", _preset.lod_near)
	_material.set_shader_parameter(&"fade_end", _preset.fade_end)
	_material.set_shader_parameter(&"keep_min", _preset.keep_min)
	if _preset.tufts * density <= 0.0:
		return
	# (the tufts' models are read now, not when the first square fills: that was a 20 ms frame)
	for v in 3:
		triangles_of(mesh_of(v))
	triangles_of(mesh_of(0, true))
	_across = ceili(area.size.x / cell)
	var down := ceili(area.size.y / cell)
	for cz in down:
		for cx in _across:
			var rect := Rect2(area.position + Vector2(cx, cz) * cell, Vector2(cell, cell)).intersection(area)
			_chunks.append({"rect": rect, "filled": false, "job": null, "full": [], "low": null, "low_y": 0.0, "high_y": 0.0,
					"shown": -1, "count": 0, "share": 0.0})


## Fills the squares within `radius` metres of `point` with their tufts now, all at once.
func fill_near(point: Vector3, radius: float) -> void:
	for i in _chunks.size():
		var c: Dictionary = _chunks[i]
		if not c.filled and _distance_to(c, point) <= radius:
			while not _fill_step(i, 1 << 30):
				pass
	_thinned_for = Vector3.INF


## How many tufts there are, and what was sent to be drawn this frame (before the renderer leaves
## out squares that are off screen): {tufts, triangles, draws, squares} (and for a field, `filled`:
## squares filled so far).
func counts() -> Dictionary:
	var triangles := 0
	var draws := 0
	if _is_field:
		var filled := 0
		for c: Dictionary in _chunks:
			if c.filled:
				filled += 1
			var parts: Array = c.full if c.shown == 2 else ([c.low] if c.shown == 1 else [])
			for part: MultiMeshInstance3D in parts:
				var n := part.multimesh.visible_instance_count
				if n > 0:
					draws += 1
					triangles += n * triangles_of(part.multimesh.mesh)
		return {"tufts": _tufts, "triangles": triangles, "draws": draws, "squares": _chunks.size(), "filled": filled}
	for block: Dictionary in _blocks:
		if block.shown == 2:
			triangles += block.triangles_full
			draws += (block.full as Array).size()
		elif block.shown == 1:
			triangles += block.triangles_low
			draws += 1
	return {"tufts": _tufts, "triangles": triangles, "draws": draws, "squares": _blocks.size()}


## Sets one of the shader's settings (`surge_period`, `surge_length`, `flutter`, `push_bend`,
## `translucency`, and the colours `grass_deep`, `grass_bright`, `tip_pale`, `grass_lit`).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


func material() -> ShaderMaterial:
	return _material


## Up to four pushers with a radius each (world x, y, z, radius in metres), for a game that sets
## its own each frame with different sizes (instead of `pushers` and `push_radius`).
func set_pushers(points: PackedVector4Array) -> void:
	var packed := PackedVector4Array()
	for i in MOST_PUSHERS:
		packed.append(points[i] if i < points.size() else Vector4.ZERO)
	_material.set_shader_parameter(&"pushers", packed)


func _process(delta: float) -> void:
	if _runs_clock and _clock_frame != Engine.get_process_frames():
		_clock_frame = Engine.get_process_frames()
		_clock += delta
		RenderingServer.global_shader_parameter_set(CLOCK, _clock)
	if _is_field:
		_field_process()
	else:
		_choose()
	_group_push()


## Planted beds: each square draws its full tufts near the camera, its light ones farther off, nothing past `far`.
func _choose() -> void:
	if not is_inside_tree():
		return
	var camera := get_viewport().get_camera_3d()
	var eye := to_local(camera.global_position) if camera != null else Vector3.ZERO
	for block: Dictionary in _blocks:
		var box: AABB = (block.core as AABB).grow(0.5)
		var gap := eye.distance_to(eye.clamp(box.position, box.end)) if camera != null else 0.0
		var shown: int = block.shown
		# (a metre of give, so that a square on the line does not flicker between the two)
		var wanted := 2 if gap < near - (0.0 if shown == 2 else 1.0) else 1
		if far > 0.0 and gap > far + (1.0 if shown != 0 else 0.0):
			wanted = 0
		if wanted == shown:
			continue
		block.shown = wanted
		for part: MultiMeshInstance3D in block.full:
			part.visible = wanted == 2
		block.low.visible = wanted == 1


# --- Fields ----------------------------------------------------------------------------------

func _field_process() -> void:
	if _chunks.is_empty() or not is_inside_tree():
		return
	var camera := get_viewport().get_camera_3d()
	if camera == null:
		return
	var eye := camera.global_position
	# (thinned again only once the camera has moved a metre: a big field has hundreds of squares)
	if eye.distance_squared_to(_thinned_for) > 1.0:
		_thinned_for = eye
		var looked := {}
		var reach_n := ceili(_preset.fade_end / cell) + 1
		var at := Vector2i(((Vector2(eye.x, eye.z) - area.position) / cell).floor())
		var down := _chunks.size() / maxi(_across, 1)
		for y in range(maxi(at.y - reach_n, 0), mini(at.y + reach_n + 1, down)):
			for x in range(maxi(at.x - reach_n, 0), mini(at.x + reach_n + 1, _across)):
				looked[y * _across + x] = true
		# (squares not filled yet that are near enough to show are filled over the next frames, nearest first)
		_unfilled.clear()
		for i: int in looked:
			if not _chunks[i].filled and _distance_to(_chunks[i], eye) < _preset.fade_end:
				_unfilled.append(i)
		_unfilled.sort_custom(func(a: int, b: int) -> bool: return _distance_to(_chunks[a], eye) < _distance_to(_chunks[b], eye))
		for i: int in _showing:
			looked[i] = true
		_showing.clear()
		for i: int in looked:
			_thin(i, eye)
	if not _unfilled.is_empty():
		var frame := Engine.get_process_frames()
		if _budget_frame != frame:
			_budget_frame = frame
			_budget_left = FILL_BUDGET
			fill_usec = 0
		var started := Time.get_ticks_usec()
		while not _unfilled.is_empty() and Time.get_ticks_usec() - started < _budget_left:
			var i: int = _unfilled[0]
			if _fill_step(i, _budget_left - (Time.get_ticks_usec() - started)):
				_unfilled.pop_front()
				_thin(i, eye)
		var spent := Time.get_ticks_usec() - started
		_budget_left -= spent
		fill_usec += spent
		fill_usec_most = maxi(fill_usec_most, fill_usec)


func _distance_to(c: Dictionary, point: Vector3) -> float:
	var rect: Rect2 = c.rect
	return Vector2(point.x, point.z).distance_to(Vector2(clampf(point.x, rect.position.x, rect.end.x), clampf(point.z, rect.position.y, rect.end.y)))


## The share of tufts kept at a distance: all near, then falling as 1 / distance, none by fade_end.
## sea_grass.gdshader keeps the same sum to grow each tuft up out of the floor as it is let in.
func _keep(d: float) -> float:
	var near_m: float = _preset.lod_near
	var k := 1.0 if d <= near_m else maxf(near_m / d, _preset.keep_min)
	var end: float = _preset.fade_end
	return k * (1.0 - smoothstep(end * 0.72, end, d))


## Thins square `i` for a camera at `eye`: fewer tufts the farther it is, the light tuft far off,
## none past the fade.
func _thin(i: int, eye: Vector3) -> void:
	var c: Dictionary = _chunks[i]
	if not c.filled or c.low == null:
		return
	var rect: Rect2 = c.rect
	var nearest := Vector3(clampf(eye.x, rect.position.x, rect.end.x), clampf(eye.y, c.low_y, c.high_y), clampf(eye.z, rect.position.y, rect.end.y))
	var dist := eye.distance_to(nearest)
	var share := minf(_keep(dist) * 1.15, 1.0)
	var shown: int = c.shown
	# (a metre of give, so that a square on the line does not flicker between the two)
	var wanted := 2 if dist < _preset.far_mesh - (0.0 if shown == 2 else 1.0) else 1
	if share <= 0.0:
		wanted = 0
	if wanted != shown:
		c.shown = wanted
		for part: MultiMeshInstance3D in c.full:
			part.visible = wanted == 2
		(c.low as MultiMeshInstance3D).visible = wanted == 1
	if wanted == 0:
		return
	for part: MultiMeshInstance3D in (c.full if wanted == 2 else [c.low]):
		var count := ceili(part.multimesh.instance_count * share)
		if part.multimesh.visible_instance_count != count:
			part.multimesh.visible_instance_count = count
	_showing[i] = true


## Carries on filling square `i` for up to `budget` microseconds; true when it is done. A square is
## filled in two steps, each a row at a time: the mask, floor and tuft heights sampled on a lattice
## `sample_step` apart, then the tufts on a jittered grid (each kept by the mask's chance); then its
## MultiMeshes are made. The same tufts whenever it is filled (its own seed).
func _fill_step(i: int, budget: int) -> bool:
	var c: Dictionary = _chunks[i]
	if c.filled:
		return true
	var started := Time.get_ticks_usec()
	var rect: Rect2 = c.rect
	if c.job == null:
		var rng := RandomNumberGenerator.new()
		rng.seed = hash([seed, i])
		var lattice := sample_step > 0.0 and (mask.is_valid() or height.is_valid() or tall.is_valid())
		var lx := ceili(rect.size.x / sample_step) + 1 if lattice else 0
		var lz := ceili(rect.size.y / sample_step) + 1 if lattice else 0
		var step := 1.0 / sqrt(_preset.tufts * density)
		c.job = {"rng": rng, "lattice": lattice, "lx": lx, "lz": lz, "row": 0, "masks": PackedFloat32Array(),
				"floors": PackedFloat32Array(), "lows": PackedFloat32Array(), "highs": PackedFloat32Array(), "any": not lattice,
				"step": step, "gz": floori(rect.position.y / step), "tufts": [[], [], []], "low_y": INF, "high_y": -INF, "most": 0.0}
	var job: Dictionary = c.job
	# The lattice, a row at a time.
	# (packed arrays are copied on write: worked on here and put back in the job)
	if job.lattice and job.row < job.lz:
		var sampled: PackedFloat32Array = job.masks
		var floored: PackedFloat32Array = job.floors
		var least: PackedFloat32Array = job.lows
		var most: PackedFloat32Array = job.highs
		var out_of_time := false
		while job.row < job.lz:
			var zi: int = job.row
			for xi in int(job.lx):
				var q := rect.position + Vector2(xi, zi) * sample_step
				var m: float = mask.call(q) if mask.is_valid() else 1.0
				sampled.append(m)
				if m > 0.0:
					job.any = true
				floored.append(float(height.call(q)) if height.is_valid() and m > 0.0 else 0.0)
				var range_m: Vector2 = tall.call(q) if tall.is_valid() and m > 0.0 else tall_range
				least.append(range_m.x)
				most.append(range_m.y)
			job.row = zi + 1
			if Time.get_ticks_usec() - started > budget:
				out_of_time = true
				break
		job.masks = sampled
		job.floors = floored
		job.lows = least
		job.highs = most
		if out_of_time:
			return false
	# The tufts, a row of the jittered grid at a time.
	var rng: RandomNumberGenerator = job.rng
	var step: float = job.step
	var lx: int = job.lx
	var masks: PackedFloat32Array = job.masks
	var floors: PackedFloat32Array = job.floors
	var lows: PackedFloat32Array = job.lows
	var highs: PackedFloat32Array = job.highs
	var lists: Array = job.tufts
	var gx := floori(rect.position.x / step)
	while job.any and float(job.gz) * step < rect.end.y:
		var gz: int = job.gz
		var x := gx
		while x * step < rect.end.x:
			var p := Vector2((x + rng.randf()) * step, (gz + rng.randf()) * step)
			x += 1
			var roll := rng.randf()
			if not rect.has_point(p):
				continue
			var chance := 1.0
			var y := 0.0
			var lo := tall_range.x
			var hi := tall_range.y
			if job.lattice:
				var f := (p - rect.position) / sample_step
				var xi := mini(int(f.x), lx - 2)
				var zi := mini(int(f.y), int(job.lz) - 2)
				var tx := f.x - xi
				var tz := f.y - zi
				var k := zi * lx + xi
				var w00 := (1.0 - tx) * (1.0 - tz)
				var w10 := tx * (1.0 - tz)
				var w01 := (1.0 - tx) * tz
				var w11 := tx * tz
				chance = masks[k] * w00 + masks[k + 1] * w10 + masks[k + lx] * w01 + masks[k + lx + 1] * w11
				if chance <= 0.0 or roll >= chance:
					continue
				# (the floor and the heights from the lattice's corners that have grass: a corner with
				# none was never asked, and its zero would pull the floor down)
				if masks[k] <= 0.0:
					w00 = 0.0
				if masks[k + 1] <= 0.0:
					w10 = 0.0
				if masks[k + lx] <= 0.0:
					w01 = 0.0
				if masks[k + lx + 1] <= 0.0:
					w11 = 0.0
				var ws := maxf(w00 + w10 + w01 + w11, 0.000001)
				y = (floors[k] * w00 + floors[k + 1] * w10 + floors[k + lx] * w01 + floors[k + lx + 1] * w11) / ws
				lo = (lows[k] * w00 + lows[k + 1] * w10 + lows[k + lx] * w01 + lows[k + lx + 1] * w11) / ws
				hi = (highs[k] * w00 + highs[k + 1] * w10 + highs[k + lx] * w01 + highs[k + lx + 1] * w11) / ws
				if not height.is_valid():
					y = 0.0
			else:
				if mask.is_valid():
					chance = mask.call(p)
				if chance <= 0.0 or roll >= chance:
					continue
				if height.is_valid():
					y = height.call(p)
				if tall.is_valid():
					var range_m: Vector2 = tall.call(p)
					lo = range_m.x
					hi = range_m.y
			var tall_m := clampf(lerpf(lo, hi, rng.randf()), 0.05, 4.0)
			y -= sink_feet
			job.low_y = minf(job.low_y, y)
			job.high_y = maxf(job.high_y, y)
			job.most = maxf(job.most, tall_m)
			# (x, y, z, turn, width, height, own number)
			(lists[rng.randi() % 3] as Array).append(PackedFloat32Array([p.x, y, p.y, rng.randf() * TAU, rng.randf_range(0.85, 1.1), tall_m, rng.randf()]))
		job.gz = gz + 1
		if Time.get_ticks_usec() - started > budget:
			return false
	# Then its MultiMeshes, one a step (three variants near, the light tuft of all of them far off).
	var made := (lists[0] as Array).size() + (lists[1] as Array).size() + (lists[2] as Array).size()
	if made > 0:
		if not job.has("box"):
			var spread: float = job.most * 1.1 + 0.2
			job.box = AABB(Vector3(rect.position.x - spread, job.low_y - 0.2, rect.position.y - spread),
					Vector3(rect.size.x + spread * 2.0, job.high_y - job.low_y + job.most + 0.4, rect.size.y + spread * 2.0))
			job.part = 0
			if Time.get_ticks_usec() - started > budget:
				return false
		while job.part < 4:
			var v: int = job.part
			if v < 3:
				if not (lists[v] as Array).is_empty():
					(c.full as Array).append(_field_part(lists[v], mesh_of(v), job.box, rng))
			else:
				var all: Array = []
				for k in 3:
					all.append_array(lists[k])
				c.low = _field_part(all, mesh_of(0, true), job.box, rng)
			job.part = v + 1
			if job.part < 4 and Time.get_ticks_usec() - started > budget:
				return false
		c.low_y = job.low_y
		c.high_y = job.high_y
		c.count = made
		_tufts += made
	c.filled = true
	c.job = null
	squares_filled += 1
	return true


# A MultiMesh of a square's tufts, shuffled, each given its rank (0..1) in its custom data so that
# the first `visible_instance_count` are an even thinning of the square and the shader grows them in
# as the rank comes within the share kept.
func _field_part(list: Array, mesh: Mesh, box: AABB, rng: RandomNumberGenerator) -> MultiMeshInstance3D:
	var order := range(list.size())
	for k in range(order.size() - 1, 0, -1):
		var j := rng.randi_range(0, k)
		var keep: int = order[k]
		order[k] = order[j]
		order[j] = keep
	var buffer := PackedFloat32Array()
	buffer.resize(list.size() * 16)
	var count := float(list.size())
	for n in order.size():
		var one: PackedFloat32Array = list[order[n]]
		var o := n * 16
		var cs := cos(one[3]) * one[4]
		var sn := sin(one[3]) * one[4]
		# (the transform's rows: Basis(UP, turn) scaled by (width, height, width), then where)
		buffer[o] = cs
		buffer[o + 2] = sn
		buffer[o + 3] = one[0]
		buffer[o + 5] = one[5]
		buffer[o + 7] = one[1]
		buffer[o + 8] = -sn
		buffer[o + 10] = cs
		buffer[o + 11] = one[2]
		buffer[o + 12] = one[6]
		buffer[o + 13] = (n + 0.5) / count
	var many := MultiMesh.new()
	many.transform_format = MultiMesh.TRANSFORM_3D
	many.use_custom_data = true
	many.mesh = mesh
	many.instance_count = list.size()
	many.buffer = buffer
	many.visible_instance_count = 0
	many.custom_aabb = box
	var part := MultiMeshInstance3D.new()
	part.multimesh = many
	part.material_override = _material
	part.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	part.visible = false
	add_child(part)
	return part


func _part(list: Array, mesh: Mesh, box: AABB) -> MultiMeshInstance3D:
	var many := MultiMesh.new()
	many.transform_format = MultiMesh.TRANSFORM_3D
	many.use_custom_data = true
	many.mesh = mesh
	many.instance_count = list.size()
	for i in list.size():
		many.set_instance_transform(i, list[i][0])
		many.set_instance_custom_data(i, list[i][1])
	many.custom_aabb = box
	var part := MultiMeshInstance3D.new()
	part.multimesh = many
	part.material_override = _material
	part.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	part.visible = false
	add_child(part)
	return part


func _send(setting: StringName, value: Variant) -> void:
	if _material != null:
		_material.set_shader_parameter(setting, value)


func _send_all() -> void:
	_send(&"sway", sway)
	_send(&"current", current)
	_send_pushers()


func _send_pushers() -> void:
	if _material == null:
		return
	var packed := PackedVector4Array()
	for i in MOST_PUSHERS:
		if i < pushers.size():
			packed.append(Vector4(pushers[i].x, pushers[i].y, pushers[i].z, push_radius))
		else:
			packed.append(Vector4.ZERO)
	_material.set_shader_parameter(&"pushers", packed)


# The PUSHERS group's four nearest the camera (found once a frame for every bed), sent if there are any.
func _group_push() -> void:
	var tree := get_tree()
	if tree == null or not tree.has_group(PUSHERS):
		return
	var frame := Engine.get_process_frames()
	if _pushers_frame != frame:
		_pushers_frame = frame
		var camera := get_viewport().get_camera_3d()
		var eye := camera.global_position if camera != null else Vector3.ZERO
		var near_ones: Array = []
		for node in tree.get_nodes_in_group(PUSHERS):
			if node is Node3D and (node as Node3D).is_inside_tree():
				near_ones.append([(node as Node3D).global_position.distance_squared_to(eye), node])
		near_ones.sort_custom(func(a: Array, b: Array) -> bool: return a[0] < b[0])
		_group_pushers = PackedVector4Array()
		for k in mini(near_ones.size(), MOST_PUSHERS):
			var node: Node3D = near_ones[k][1]
			var at := node.global_position
			_group_pushers.append(Vector4(at.x, at.y, at.z, float(node.get_meta(&"sea_grass_radius", push_radius))))
	if not _group_pushers.is_empty():
		set_pushers(_group_pushers)
