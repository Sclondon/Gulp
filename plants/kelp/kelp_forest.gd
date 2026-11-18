class_name KelpForest
extends Node3D
## A forest of giant kelp (Macrocystis pyrifera), cheap in the hundreds: each plant is a holdfast
## and a stack of one-metre pieces of frond bundle (three stipes and twelve blades on their
## floats: three variants and a light one for far off, built in Blender), drawn by a few
## MultiMeshes for each block of water `cell` metres across (and twice that tall). All of the moving is in
## kelp.gdshader: a slow surge that runs through the forest as a wave and swings the tops most,
## a lean down-current, blades fluttering, and fronds that reach the surface turning over and
## lying along it as a canopy.
##
##   var forest := KelpForest.new()
##   add_child(forest)
##   forest.plant(places, heights, surface_y)   # holdfasts, each plant's length in metres, the surface
##   forest.current = Vector2(0.4, 0.0)         # which way the water streams, and how hard
##   forest.sway = 1.0
##
## `places` are in the forest's own space: leave the node unturned and unscaled (it may be moved;
## `plant` again after moving it up or down). A plant longer than the water over it is deep lies
## its extra length along the surface.
##
## For thousands of plants, set `far_piece` (and `mid`, `far_cell`) before `plant`: beyond `mid`
## the plants are drawn by bigger blocks of the light piece stretched `far_piece` metres long (a
## third or less of its triangles, one draw a block, no holdfasts).
##
## The shader reads the global shader uniform `water_clock` (seconds). If the project declares
## none (Project Settings > Shader Globals), the first forest adds one and runs it; if it declares
## one, the game sets it.

const MODEL := "res://plants/kelp/models/kelp_%s.glb"
const SHADER := "res://plants/kelp/kelp.gdshader"
const CLOCK := &"water_clock"
const VARIANTS := ["a", "b", "c"]

## How far the surge swings the fronds: 1 about 12 degrees either way at the top, 0 still.
@export_range(0.0, 3.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Which way the water streams (world x, z) and how hard: at length 1 a frond's top leans about
## 14 degrees. The canopy streams this way; the surge swings along it.
@export var current := Vector2.ZERO:
	set(value):
		current = value
		_send(&"current", value)
## Blocks whose plants' middle lines (not their lean or canopy) are nearer the camera than this
## draw the full pieces, the rest the low one (metres).
@export var near := 8.0
## Blocks farther than this are not drawn (0: drawn however far).
@export var far := 0.0
## The side of a block of water whose pieces are drawn together (metres; blocks are twice as tall).
## Set it before `plant`.
@export var cell := 8.0
## The far level (0: none, every block draws the light piece out to `far`): how long each far piece
## is (metres; the light piece stretched, so 3 is a third of its triangles). Set before `plant`.
@export var far_piece := 0.0
## With a far level: the big blocks (`far_cell` across, the water's whole height) whose plants'
## middle lines are all farther than this draw the far pieces instead of their small blocks (metres).
@export var mid := 20.0
## With a far level: the side of its big blocks (metres; a whole number of `cell`s). Set before `plant`.
@export var far_cell := 24.0
## Changes which variant and which way round each piece is.
@export var seed := 1

static var _meshes := {}
static var _shader: Shader
## Whether this component added `water_clock` (and so must run it), and the frame it last did.
static var _runs_clock := false
static var _clock := 0.0
static var _clock_frame := -1

var _material: ShaderMaterial
var _surface_y := 0.0
var _blocks: Array = []
var _bigs: Array = []
var _pieces := 0
var _plants := 0


## The mesh of a piece: variant 0, 1 or 2 ("a", "b", "c"), or the low piece, or the holdfast
## (`KelpForest.mesh_of(-1)`).
static func mesh_of(variant := 0, low := false) -> Mesh:
	var path := MODEL % ("holdfast" if variant < 0 else ("lo" if low else VARIANTS[variant % 3]))
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]


## How many triangles a mesh has.
static func triangles_of(mesh: Mesh) -> int:
	var all := 0
	for surface in mesh.get_surface_count():
		var arrays := mesh.surface_get_arrays(surface)
		var index: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		all += (index.size() if not index.is_empty() else (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array).size()) / 3
	return all


## A new material wearing kelp.gdshader (the top of the shader lists its settings).
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


## Plants the forest (taking up whatever was planted before): a holdfast at each of `places`
## (the forest's own space), each plant `heights[i]` metres long (4 to 25 is what it is made
## for), under a surface at world height `surface_y`. `widths` (optional, 1 each if left out)
## makes a plant's bundle that many times as wide, its blades reaching that much farther out: a
## plant of many stipes.
func plant(places: PackedVector3Array, heights: PackedFloat32Array, surface_y: float, widths := PackedFloat32Array()) -> void:
	for block: Dictionary in _blocks:
		for part: Node in block.parts:
			part.queue_free()
	for big: Dictionary in _bigs:
		if big.part != null:
			big.part.queue_free()
	_blocks.clear()
	_bigs.clear()
	_surface_y = surface_y
	_material.set_shader_parameter(&"surface_y", surface_y)
	_send(&"sway", sway)
	_send(&"current", current)
	_plants = places.size()
	_pieces = 0
	var rng := RandomNumberGenerator.new()
	rng.seed = seed
	var lift := global_position.y if is_inside_tree() else position.y
	var found := {}
	var found_big := {}
	for i in places.size():
		var at := places[i]
		var tall := maxf(heights[i] if i < heights.size() else 10.0, 1.0)
		var wide := widths[i] if i < widths.size() else 1.0
		var count := maxi(roundi(tall), 1)
		var stretch := tall / count
		var depth := maxf(surface_y - 0.05 - (at.y + lift), 0.5)
		var turn := rng.randf() * TAU
		var own := rng.randf()
		# (how far its top may be carried: along the surface, and by the lean)
		var carried := 2.0 + 0.3 * minf(tall, depth)
		var big: Dictionary = {}
		if far_piece > 0.0:
			big = _big_at(found_big, at)
		for k in count:
			var base := k * stretch
			var rest := Vector3(at.x, at.y + minf(base + 0.5 * stretch, depth), at.z)
			var block := _block_at(found, rest)
			if not big.is_empty():
				big.blocks[block.id] = true
			var basis := Basis(Vector3.UP, turn + (rng.randi() % 3) * TAU / 3.0).scaled_local(Vector3(wide, stretch, wide))
			var piece := [Transform3D(basis, at + Vector3(0.0, base, 0.0)), Color(base, tall, own, 0.0)]
			(block.pieces[rng.randi() % 3] as Array).append(piece)
			_grow(block, rest, maxf(base + stretch - depth, 0.0) + carried * (base + stretch) / tall + 0.8 * wide, 1.3)
			block.core = (block.core as AABB).expand(rest)
			_pieces += 1
		if not big.is_empty():
			# (the far level: the same plant in fewer, longer pieces of the light one)
			var far_count := maxi(roundi(tall / far_piece), 1)
			var far_stretch := tall / far_count
			for k in far_count:
				var base := k * far_stretch
				var rest := Vector3(at.x, at.y + minf(base + 0.5 * far_stretch, depth), at.z)
				var basis := Basis(Vector3.UP, turn + k * TAU / 3.0).scaled_local(Vector3(wide, far_stretch, wide))
				(big.pieces as Array).append([Transform3D(basis, at + Vector3(0.0, base, 0.0)), Color(base, tall, own, 0.0)])
				_grow(big, rest, maxf(base + far_stretch - depth, 0.0) + carried * (base + far_stretch) / tall + 0.8 * wide, far_stretch * 0.5 + 0.3)
				big.core = (big.core as AABB).expand(rest)
		var low := _block_at(found, at)
		if not big.is_empty():
			big.blocks[low.id] = true
		var size := clampf(tall / 14.0, 0.7, 1.5) * sqrt(wide)
		(low.holdfasts as Array).append([Transform3D(Basis(Vector3.UP, turn).scaled(Vector3.ONE * size), at), Color(0.0, tall, own, 1.0)])
		_grow(low, at, 0.6 * size, 0.6)
	for block: Dictionary in found.values():
		var all: Array = []
		for v in 3:
			var some: Array = block.pieces[v]
			all.append_array(some)
			if not some.is_empty():
				(block.full as Array).append(_part(some, mesh_of(v), block.box))
		if not all.is_empty():
			block.low = _part(all, mesh_of(0, true), block.box)
			block.parts.append(block.low)
		block.parts.append_array(block.full)
		if not (block.holdfasts as Array).is_empty():
			block.holdfast = _part(block.holdfasts, mesh_of(-1), block.box)
			block.parts.append(block.holdfast)
		block.triangles_full = all.size() * triangles_of(mesh_of(0))
		block.triangles_low = all.size() * triangles_of(mesh_of(0, true))
		block.triangles_holdfast = (block.holdfasts as Array).size() * triangles_of(mesh_of(-1))
		block.erase("pieces")
		_blocks.append(block)
	for big: Dictionary in found_big.values():
		if not (big.pieces as Array).is_empty():
			big.part = _part(big.pieces, mesh_of(0, true), big.box)
			big.triangles = (big.pieces as Array).size() * triangles_of(mesh_of(0, true))
		big.erase("pieces")
		_bigs.append(big)
	_choose()


## How many plants and pieces there are, and what was sent to be drawn this frame (before the
## renderer leaves out blocks that are off screen): {plants, pieces, triangles, draws, blocks}.
func counts() -> Dictionary:
	var triangles := 0
	var draws := 0
	for block: Dictionary in _blocks:
		if block.shown == 0:
			continue
		if block.shown == 2:
			triangles += block.triangles_full
			draws += (block.full as Array).size()
		elif block.low != null:
			triangles += block.triangles_low
			draws += 1
		if block.holdfast != null:
			triangles += block.triangles_holdfast
			draws += 1
	for big: Dictionary in _bigs:
		if big.shown and big.part != null:
			triangles += big.triangles
			draws += 1
	return {"plants": _plants, "pieces": _pieces, "triangles": triangles, "draws": draws, "blocks": _blocks.size() + _bigs.size()}


## Sets one of the shader's settings (`surge_period`, `surge_length`, `flutter`, `teeth`, `eye_clear`,
## `translucency`, and the colours `blade`, `blade_amber`, `blade_lit`, `bulb`, `stipe`).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


func material() -> ShaderMaterial:
	return _material


func _process(delta: float) -> void:
	if _runs_clock and _clock_frame != Engine.get_process_frames():
		_clock_frame = Engine.get_process_frames()
		_clock += delta
		RenderingServer.global_shader_parameter_set(CLOCK, _clock)
	_choose()


## Each block draws its full pieces near the camera, its low ones farther off, nothing past `far`;
## with a far level, a big block wholly beyond `mid` draws its far pieces in place of its small ones.
func _choose() -> void:
	if not is_inside_tree():
		return
	var camera := get_viewport().get_camera_3d()
	var eye := to_local(camera.global_position) if camera != null else Vector3.ZERO
	var off := {}
	for big: Dictionary in _bigs:
		var gap := _gap(eye, big.core) if camera != null else 0.0
		# (a metre of give, so that a block on the line does not flicker between the two)
		var wanted: bool = gap > mid + (0.0 if big.shown else 1.0)
		if far > 0.0 and gap > far + (1.0 if big.shown else 0.0):
			wanted = false
		if wanted or (far > 0.0 and gap > far):
			for id: int in big.blocks:
				off[id] = true
		if wanted != big.shown:
			big.shown = wanted
			if big.part != null:
				big.part.visible = wanted
	for block: Dictionary in _blocks:
		var gap := _gap(eye, block.core) if camera != null else 0.0
		var shown: int = block.shown
		var wanted := 2 if gap < near - (0.0 if shown == 2 else 1.0) else 1
		if far > 0.0 and gap > far + (1.0 if shown != 0 else 0.0):
			wanted = 0
		if off.has(block.id):
			wanted = 0
		if wanted == shown:
			continue
		block.shown = wanted
		for part: MultiMeshInstance3D in block.full:
			part.visible = wanted == 2
		if block.low != null:
			block.low.visible = wanted == 1
		if block.holdfast != null:
			block.holdfast.visible = wanted != 0


func _gap(eye: Vector3, core: AABB) -> float:
	var box := core.grow(1.0)
	return eye.distance_to(eye.clamp(box.position, box.end))


func _block_at(found: Dictionary, at: Vector3) -> Dictionary:
	var key := Vector3i((at / Vector3(cell, cell * 2.0, cell)).floor())
	if not found.has(key):
		found[key] = {"id": found.size(), "pieces": [[], [], []], "holdfasts": [], "full": [], "low": null, "holdfast": null, "parts": [],
				"box": AABB(at, Vector3.ZERO), "core": AABB(at, Vector3.ZERO), "shown": -1, "triangles_full": 0, "triangles_low": 0, "triangles_holdfast": 0}
	return found[key]


func _big_at(found: Dictionary, at: Vector3) -> Dictionary:
	var key := Vector2i(floori(at.x / far_cell), floori(at.z / far_cell))
	if not found.has(key):
		found[key] = {"pieces": [], "blocks": {}, "part": null, "box": AABB(at, Vector3.ZERO), "core": AABB(at, Vector3.ZERO),
				"shown": false, "triangles": 0}
	return found[key]


func _grow(block: Dictionary, at: Vector3, wide: float, tall: float) -> void:
	var box: AABB = block.box
	block.box = box.merge(AABB(at - Vector3(wide, tall, wide), Vector3(wide, tall, wide) * 2.0))


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
