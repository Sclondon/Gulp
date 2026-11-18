class_name SeaGrassBed
extends Node3D
## A bed of eelgrass (Zostera marina), cheap in the hundreds or thousands: each tuft is two to
## four shoots of long flat ribbon leaves (three variants and a light one for far off, built in
## Blender), drawn by a few MultiMeshes for each square of sea floor `cell` metres across. All of
## the moving is in sea_grass.gdshader: the leaves bend over together down-current, a slow surge
## runs through the bed as a wave and swings them to and fro, a ripple runs up each leaf, and up
## to four pushers lay the grass aside.
##
##   var bed := SeaGrassBed.new()
##   add_child(bed)
##   bed.plant(places, heights)                 # tufts' feet, each tuft's height (0.4 to 1.2 m)
##   bed.current = Vector2(0.3, 0.0)            # which way the water streams, and how hard
##   bed.pushers = PackedVector3Array([fish.global_position])   # each frame: up to four
##
## `places` are in the bed's own space: leave the node unturned and unscaled (it may be moved).
##
## The shader reads the global shader uniform `water_clock` (seconds). If the project declares
## none (Project Settings > Shader Globals), the first bed adds one and runs it; if it declares
## one, the game sets it.

const MODEL := "res://plants/sea_grass/models/sea_grass_%s.glb"
const SHADER := "res://plants/sea_grass/sea_grass.gdshader"
const CLOCK := &"water_clock"
const VARIANTS := ["a", "b", "c"]
const MOST_PUSHERS := 4

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
## Up to four world points that lay the grass aside (a fish, a diver); more are left out.
@export var pushers := PackedVector3Array():
	set(value):
		pushers = value
		_send_pushers()
## How far from a pusher the grass is laid aside (metres).
@export var push_radius := 0.8:
	set(value):
		push_radius = value
		_send_pushers()
## Squares nearer the camera than this draw the full tufts, the rest the light one (metres).
@export var near := 10.0
## Squares farther than this are not drawn (0: drawn however far).
@export var far := 0.0
## The side of a square of sea floor whose tufts are drawn together (metres). Set it before `plant`.
@export var cell := 8.0
## Changes which variant and which way round each tuft is.
@export var seed := 1

static var _meshes := {}
static var _shader: Shader
## Whether this component added `water_clock` (and so must run it), and the frame it last did.
static var _runs_clock := false
static var _clock := 0.0
static var _clock_frame := -1

var _material: ShaderMaterial
var _blocks: Array = []
var _tufts := 0


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
	var all := 0
	for surface in mesh.get_surface_count():
		var arrays := mesh.surface_get_arrays(surface)
		var index: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		all += (index.size() if not index.is_empty() else (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array).size()) / 3
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


## Plants the bed (taking up whatever was planted before): a tuft at each of `places` (the bed's
## own space), each `heights[i]` metres tall (0.4 to 1.2 is what it is made for).
func plant(places: PackedVector3Array, heights: PackedFloat32Array) -> void:
	for block: Dictionary in _blocks:
		for part: Node in block.parts:
			part.queue_free()
	_blocks.clear()
	_send(&"sway", sway)
	_send(&"current", current)
	_send_pushers()
	_tufts = places.size()
	var rng := RandomNumberGenerator.new()
	rng.seed = seed
	var found := {}
	for i in places.size():
		var at := places[i]
		var tall := clampf(heights[i] if i < heights.size() else 0.8, 0.05, 4.0)
		var wide := rng.randf_range(0.85, 1.1)
		var basis := Basis(Vector3.UP, rng.randf() * TAU).scaled_local(Vector3(wide, tall, wide))
		var key := Vector2i(floori(at.x / cell), floori(at.z / cell))
		if not found.has(key):
			found[key] = {"tufts": [[], [], []], "full": [], "low": null, "parts": [], "core": AABB(at, Vector3.ZERO),
					"box": AABB(at, Vector3.ZERO), "shown": -1, "triangles_full": 0, "triangles_low": 0}
		var block: Dictionary = found[key]
		(block.tufts[rng.randi() % 3] as Array).append([Transform3D(basis, at), Color(rng.randf(), 0.0, 0.0, 0.0)])
		block.core = (block.core as AABB).expand(at)
		# (a leaf may lie over as far as it is long, and be pushed a little farther)
		var reach := tall * 1.1 + 0.1
		block.box = (block.box as AABB).merge(AABB(at - Vector3(reach, 0.1, reach), Vector3(reach * 2.0, tall + 0.2, reach * 2.0)))
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


## How many tufts there are, and what was sent to be drawn this frame (before the renderer leaves
## out squares that are off screen): {tufts, triangles, draws, squares}.
func counts() -> Dictionary:
	var triangles := 0
	var draws := 0
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


func _process(delta: float) -> void:
	if _runs_clock and _clock_frame != Engine.get_process_frames():
		_clock_frame = Engine.get_process_frames()
		_clock += delta
		RenderingServer.global_shader_parameter_set(CLOCK, _clock)
	_choose()


## Each square draws its full tufts near the camera, its light ones farther off, nothing past `far`.
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
