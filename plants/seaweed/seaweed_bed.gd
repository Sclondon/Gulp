class_name SeaweedBed
extends Node3D
## Seaweed of six kinds, cheap in the hundreds: sea lettuce, rockweed, a feathery red weed, feather
## boa kelp, sea palm, and sargassum floating at the surface. Each plant is built in Blender (a full
## model and a very light one for far off) and drawn by one MultiMesh for each kind in the bed (or
## in each square of it, when `cell` is set). All of the moving is in seaweed.gdshader: plants on
## the floor bend over together down-current, a slow surge runs through the bed as a wave and swings
## them to and fro, blades flap, and sargassum bobs and rocks on the swell.
##
##   var bed := SeaweedBed.new()
##   add_child(bed)
##   bed.current = Vector2(0.3, 0.0)            # which way the water streams, and how hard
##   bed.plant(places, sizes, kinds, surface_y) # feet, heights (m), SeaweedBed.Kind each, the surface
##
## `places` are in the bed's own space: leave the node unturned and unscaled (it may be moved, but
## plant again after moving it up or down: sargassum is put on the surface then).
##
## The shader reads the global shader uniform `water_clock` (seconds). If the project declares
## none (Project Settings > Shader Globals), the first bed adds one and runs it; if it declares
## one, the game sets it.

enum Kind { SEA_LETTUCE, ROCKWEED, RED_ALGAE, FEATHER_BOA, SEA_PALM, SARGASSUM }

const NAMES := ["sea_lettuce", "rockweed", "red_algae", "feather_boa", "sea_palm", "sargassum"]
## Each kind's size at scale 1 (metres): its height, or for sargassum the width of its mat. A plant
## planted with another size is that model scaled evenly (half to twice this looks right).
const SIZE := [0.35, 0.32, 0.22, 2.5, 0.5, 1.0]
const MODEL := "res://plants/seaweed/models/seaweed_%s%s.glb"
const SHADER := "res://plants/seaweed/seaweed.gdshader"
const CLOCK := &"water_clock"
## Each kind's shader settings (the top of seaweed.gdshader says what each does).
const LOOK := [
	{   # sea lettuce: bright, thin, translucent, floppy
		"bendy": 1.2, "flap": 0.025, "translucency": 0.9, "midrib": 0.0,
		"colour_foot": Color(0.16, 0.42, 0.1), "colour_tip": Color(0.45, 0.8, 0.22),
		"colour_stem": Color(0.16, 0.42, 0.1), "colour_float": Color(0.45, 0.8, 0.22), "colour_lit": Color(0.6, 1.0, 0.35),
	},
	{   # rockweed: olive, tough, golden swollen tips
		"bendy": 0.7, "flap": 0.006, "translucency": 0.35, "midrib": 1.0,
		"colour_foot": Color(0.2, 0.19, 0.06), "colour_tip": Color(0.5, 0.43, 0.14),
		"colour_stem": Color(0.22, 0.2, 0.07), "colour_float": Color(0.42, 0.37, 0.12), "colour_lit": Color(0.6, 0.5, 0.2),
	},
	{   # red algae: crimson, deep at the foot, rosy at the tips
		"bendy": 0.8, "flap": 0.008, "translucency": 0.6, "midrib": -0.3,
		"colour_foot": Color(0.3, 0.02, 0.05), "colour_tip": Color(0.78, 0.14, 0.2),
		"colour_stem": Color(0.3, 0.02, 0.05), "colour_float": Color(0.6, 0.1, 0.15), "colour_lit": Color(0.95, 0.3, 0.35),
	},
	{   # feather boa kelp: dark olive-brown, long and streaming
		"bendy": 1.4, "flap": 0.02, "snake": 1.0, "translucency": 0.45, "midrib": 0.6,
		"colour_foot": Color(0.27, 0.2, 0.06), "colour_tip": Color(0.56, 0.43, 0.14),
		"colour_stem": Color(0.27, 0.2, 0.06), "colour_float": Color(0.62, 0.5, 0.17), "colour_lit": Color(0.75, 0.55, 0.2),
	},
	{   # sea palm: an olive stalk that whips over, yellow-brown blades
		"bendy": 1.0, "flap": 0.012, "translucency": 0.4, "midrib": 0.5,
		"colour_foot": Color(0.3, 0.24, 0.07), "colour_tip": Color(0.55, 0.44, 0.15),
		"colour_stem": Color(0.32, 0.27, 0.1), "colour_float": Color(0.42, 0.35, 0.12), "colour_lit": Color(0.6, 0.5, 0.2),
	},
	{   # sargassum: golden, floating
		"floating": 1.0, "bob": 0.03, "flap": 0.006, "translucency": 1.0, "midrib": 0.5,
		"colour_foot": Color(0.55, 0.38, 0.08), "colour_tip": Color(0.78, 0.58, 0.16),
		"colour_stem": Color(0.45, 0.3, 0.07), "colour_float": Color(0.62, 0.44, 0.1), "colour_lit": Color(0.95, 0.75, 0.3),
	},
]

## How far the surge swings the plants: 1 about 25 degrees either way at the top, 0 still.
@export_range(0.0, 3.0) var sway := 1.0:
	set(value):
		sway = value
		_send_all(&"sway", value)
## Which way the water streams (world x, z) and how hard: at length 1 plants bend over about 70
## degrees down-current; the surge swings along it.
@export var current := Vector2.ZERO:
	set(value):
		current = value
		_send_all(&"current", value)
## Squares nearer the camera than this draw the full plants, the rest the light ones (metres).
@export var near := 12.0
## Squares farther than this are not drawn (0: drawn however far).
@export var far := 0.0
## Always the light plants, however near (a phone's lowest setting).
@export var low := false
## The side of a square of sea floor whose plants are drawn together (metres); 0: the whole bed is
## one square, one draw for each kind in it. Set it before `plant`.
@export var cell := 0.0
## Changes which way round each plant is.
@export var seed := 1

static var _meshes := {}
static var _shader: Shader
## Whether this component added `water_clock` (and so must run it), and the frame it last did.
static var _runs_clock := false
static var _clock := 0.0
static var _clock_frame := -1

var _materials: Array[ShaderMaterial] = []
var _blocks: Array = []
var _plants := 0


## The mesh of a kind (Kind), full or light.
static func mesh_of(kind: int, light := false) -> Mesh:
	var path := MODEL % [NAMES[kind], "_lo" if light else ""]
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


## A new material for a kind, wearing seaweed.gdshader with that kind's LOOK.
static func new_material(kind: int) -> ShaderMaterial:
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
	made.set_shader_parameter(&"model_tall", SIZE[kind])
	var look: Dictionary = LOOK[kind]
	for setting: String in look:
		made.set_shader_parameter(setting, look[setting])
	return made


func _init() -> void:
	for kind in NAMES.size():
		_materials.append(new_material(kind))


## Plants the bed (taking up whatever was planted before): a plant of `kinds[i]` (Kind) at each of
## `places` (the bed's own space), `sizes[i]` metres tall (for sargassum: its mat's width; 0 or
## missing: the kind's SIZE). Sargassum floats with its waterline at `surface_y` (world height),
## wherever its place's own height is.
func plant(places: PackedVector3Array, sizes: PackedFloat32Array, kinds: PackedInt32Array, surface_y := 0.0) -> void:
	for block: Dictionary in _blocks:
		for part: Node in block.parts:
			part.queue_free()
	_blocks.clear()
	_send_all(&"sway", sway)
	_send_all(&"current", current)
	_plants = places.size()
	var rng := RandomNumberGenerator.new()
	rng.seed = seed
	var lift := global_position.y if is_inside_tree() else position.y
	var found := {}
	for i in places.size():
		var kind := clampi(kinds[i] if i < kinds.size() else 0, 0, NAMES.size() - 1)
		var size: float = sizes[i] if i < sizes.size() and sizes[i] > 0.0 else SIZE[kind]
		var at := places[i]
		if kind == Kind.SARGASSUM:
			at.y = surface_y - lift
		var grow: float = size / SIZE[kind]
		var basis := Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3.ONE * grow)
		var key := Vector2i(floori(at.x / cell), floori(at.z / cell)) if cell > 0.0 else Vector2i.ZERO
		if not found.has(key):
			var lists: Array = []
			for k in NAMES.size():
				lists.append([])
			found[key] = {"lists": lists, "full": [], "light": [], "parts": [], "core": AABB(at, Vector3.ZERO),
					"box": AABB(at, Vector3.ZERO), "shown": -1, "triangles_full": 0, "triangles_light": 0}
		var block: Dictionary = found[key]
		(block.lists[kind] as Array).append([Transform3D(basis, at), Color(rng.randf(), 0.0, 0.0, 0.0)])
		block.core = (block.core as AABB).expand(at)
		# (how far it may reach: bent over, or a mat bobbing)
		var reach := size * (0.65 if kind == Kind.SARGASSUM else 1.15) + 0.1
		var low_y := -0.2 * size if kind == Kind.SARGASSUM else -0.1
		block.box = (block.box as AABB).merge(AABB(at + Vector3(-reach, low_y, -reach),
				Vector3(reach * 2.0, size * 1.1 - low_y + 0.1, reach * 2.0)))
	for block: Dictionary in found.values():
		for kind in NAMES.size():
			var some: Array = block.lists[kind]
			if some.is_empty():
				continue
			(block.full as Array).append(_part(some, mesh_of(kind), kind, block.box))
			(block.light as Array).append(_part(some, mesh_of(kind, true), kind, block.box))
			block.triangles_full += some.size() * triangles_of(mesh_of(kind))
			block.triangles_light += some.size() * triangles_of(mesh_of(kind, true))
		(block.parts as Array).append_array(block.full)
		(block.parts as Array).append_array(block.light)
		block.erase("lists")
		_blocks.append(block)
	_choose()


## How many plants there are, and what was sent to be drawn this frame (before the renderer leaves
## out squares that are off screen): {plants, triangles, draws, squares}.
func counts() -> Dictionary:
	var triangles := 0
	var draws := 0
	for block: Dictionary in _blocks:
		if block.shown == 2:
			triangles += block.triangles_full
			draws += (block.full as Array).size()
		elif block.shown == 1:
			triangles += block.triangles_light
			draws += (block.light as Array).size()
	return {"plants": _plants, "triangles": triangles, "draws": draws, "squares": _blocks.size()}


## Sets one of the shader's settings for one kind (Kind), or for every kind (-1): `surge_period`,
## `surge_length`, `flutter`, a kind's `bendy`, `flap`, `snake`, `bob`, `translucency`, `midrib`,
## and its colours `colour_foot`, `colour_tip`, `colour_stem`, `colour_float`, `colour_lit`.
func set_shader_parameter(setting: StringName, value: Variant, kind := -1) -> void:
	if kind >= 0:
		_materials[kind].set_shader_parameter(setting, value)
	else:
		_send_all(setting, value)


## The material a kind is drawn with.
func material(kind: int) -> ShaderMaterial:
	return _materials[kind]


func _process(delta: float) -> void:
	if _runs_clock and _clock_frame != Engine.get_process_frames():
		_clock_frame = Engine.get_process_frames()
		_clock += delta
		RenderingServer.global_shader_parameter_set(CLOCK, _clock)
	_choose()


## Each square draws its full plants near the camera, its light ones farther off, nothing past `far`.
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
		var wanted := 2 if not low and gap < near - (0.0 if shown == 2 else 1.0) else 1
		if far > 0.0 and gap > far + (1.0 if shown != 0 else 0.0):
			wanted = 0
		if wanted == shown:
			continue
		block.shown = wanted
		for part: MultiMeshInstance3D in block.full:
			part.visible = wanted == 2
		for part: MultiMeshInstance3D in block.light:
			part.visible = wanted == 1


func _part(list: Array, mesh: Mesh, kind: int, box: AABB) -> MultiMeshInstance3D:
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
	part.material_override = _materials[kind]
	part.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	part.visible = false
	add_child(part)
	return part


func _send_all(setting: StringName, value: Variant) -> void:
	for made in _materials:
		made.set_shader_parameter(setting, value)
