class_name MangroveStand
extends Node3D
## A stand of red mangroves (Rhizophora mangle) standing in shallow water, cheap in the dozens:
## four trees (root spreads about 3, 4, 5 and 6 m, canopies 3.6 to 6.3 m over the water) and two
## root clusters (a low bough 2.8 or 3.4 m long dropping roots to both sides, to thicken a bank), each with a light piece for far off, built in
## Blender. Each is drawn by a MultiMesh per piece for each square of water `cell` metres across.
## Each piece's y = 0 is the WATERLINE: its prop roots arch down through the surface into mud at
## y = -3 (they go on 0.5 m below that), its trunk and canopy stand above.
##
##   var stand := MangroveStand.new()
##   add_child(stand)
##   stand.plant(places, turns, sizes)        # points on the waterline, turns (radians), sizes (1 as built)
##   for s in stand.spheres(): ...            # where fish may not go (the root tangles), the stand's own space
##
## `places` are in the stand's own space: leave the node unturned and unscaled (it may be moved).
## A piece of size s has its mud line at -3 s: put its place s * 3 m over the mud.
##
## The shader reads the global shader uniform `water_clock` (seconds) to stir the canopy. If the
## project declares none (Project Settings > Shader Globals), the first stand adds one and runs it;
## if it declares one, the game sets it.

const MODEL := "res://plants/mangrove/models/mangrove_%s.glb"
const SHADER := "res://plants/mangrove/mangrove.gdshader"
const SHAPES := preload("res://plants/mangrove/mangrove_shapes.gd")
const CLOCK := &"water_clock"
## The pieces: four trees, then two root clusters.
const VARIANTS := ["a", "b", "c", "d", "roots_a", "roots_b"]
const TREES := 4
## The mud line in a piece's own space at size 1 (metres under the waterline).
const MUD := -3.0
## How far each piece reaches from its middle line (roots and canopy, any way round) and how high
## its canopy stands over the water, at size 1 (metres).
const REACH := [3.6, 4.5, 5.4, 6.0, 3.1, 3.4]
const TOP := [3.8, 4.7, 5.4, 6.3, 3.3, 3.3]

## How much the canopy stirs (0 still).
@export_range(0.0, 3.0) var stir := 1.0:
	set(value):
		stir = value
		if _material != null:
			_material.set_shader_parameter(&"stir", value)
## Squares nearer the camera than this draw the full pieces, the rest the light ones (metres).
@export var near := 22.0
## Squares farther than this are not drawn (0: drawn however far).
@export var far := 0.0
## The side of a square of water whose pieces are drawn together (metres). Set it before `plant`.
@export var cell := 16.0
## Changes which tree each place gets when `plant` is not told.
@export var seed := 1

static var _meshes := {}
static var _shader: Shader
static var _runs_clock := false
static var _clock := 0.0
static var _clock_frame := -1

var _material: ShaderMaterial
var _blocks: Array = []
var _spheres: Array[Vector4] = []
var _count := 0


## The mesh of a piece: 0..3 the trees "a".."d", 4 and 5 the root clusters; `low` its light one.
static func mesh_of(variant := 0, low := false) -> Mesh:
	var path := MODEL % (VARIANTS[clampi(variant, 0, VARIANTS.size() - 1)] + ("_lo" if low else ""))
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]


## The spheres (x, y, z, radius: the piece's own space, size 1) that roughly fill a piece's root
## tangles under the water, with room between its clusters for a 0.3 m fish to thread through.
static func spheres_of(variant: int) -> Array[Vector4]:
	var found: Array[Vector4] = []
	found.assign(SHAPES.SPHERES[VARIANTS[clampi(variant, 0, VARIANTS.size() - 1)]])
	return found


## How many triangles a mesh has.
static func triangles_of(mesh: Mesh) -> int:
	var all := 0
	for surface in mesh.get_surface_count():
		var arrays := mesh.surface_get_arrays(surface)
		var index: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		all += (index.size() if not index.is_empty() else (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array).size()) / 3
	return all


## A new material wearing mangrove.gdshader (the top of the shader lists its settings).
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


## Plants the stand (taking up whatever was planted before): a piece at each of `places` (points on
## the waterline, the stand's own space), turned `turns[i]` radians about the up axis, scaled
## `sizes[i]` (1 as built; 0.7 to 1.4 look right). `variants[i]` picks the piece (0..3 trees,
## 4 and 5 root clusters); without it each place gets a tree at random.
func plant(places: PackedVector3Array, turns: PackedFloat32Array, sizes: PackedFloat32Array, variants := PackedInt32Array()) -> void:
	for block: Dictionary in _blocks:
		for part: Node in block.parts:
			part.queue_free()
	_blocks.clear()
	_spheres.clear()
	_material.set_shader_parameter(&"stir", stir)
	_count = places.size()
	var rng := RandomNumberGenerator.new()
	rng.seed = seed
	var found := {}
	for i in places.size():
		var at := places[i]
		var turn := turns[i] if i < turns.size() else rng.randf() * TAU
		var size := maxf(sizes[i] if i < sizes.size() else 1.0, 0.05)
		var variant := clampi(variants[i], 0, VARIANTS.size() - 1) if i < variants.size() else rng.randi() % TREES
		var basis := Basis(Vector3.UP, turn).scaled(Vector3.ONE * size)
		var key := Vector2i(floori(at.x / cell), floori(at.z / cell))
		if not found.has(key):
			found[key] = {"pieces": [], "full": [], "low": [], "parts": [], "core": AABB(at, Vector3.ZERO),
					"box": AABB(at, Vector3.ZERO), "shown": -1, "triangles_full": 0, "triangles_low": 0}
			for v in VARIANTS.size():
				(found[key].pieces as Array).append([])
		var block: Dictionary = found[key]
		(block.pieces[variant] as Array).append([Transform3D(basis, at), Color(rng.randf(), size, 0.0, 0.0)])
		block.core = (block.core as AABB).expand(at)
		var reach: float = REACH[variant] * size
		block.box = (block.box as AABB).merge(AABB(at + Vector3(-reach, (MUD - 0.6) * size, -reach),
				Vector3(reach * 2.0, (TOP[variant] - MUD + 0.6) * size, reach * 2.0)))
		for s in spheres_of(variant):
			var c := basis * Vector3(s.x, s.y, s.z) + at
			_spheres.append(Vector4(c.x, c.y, c.z, s.w * size))
	for block: Dictionary in found.values():
		for v in VARIANTS.size():
			var some: Array = block.pieces[v]
			if some.is_empty():
				continue
			(block.full as Array).append(_part(some, mesh_of(v), block.box))
			(block.low as Array).append(_part(some, mesh_of(v, true), block.box))
			block.triangles_full += some.size() * triangles_of(mesh_of(v))
			block.triangles_low += some.size() * triangles_of(mesh_of(v, true))
		block.parts.append_array(block.full)
		block.parts.append_array(block.low)
		block.erase("pieces")
		_blocks.append(block)
	_choose()


## Every planted piece's spheres (x, y, z, radius), in the stand's own space: the root tangles
## under the water, for a game that keeps its fish out of solid things with spheres.
func spheres() -> Array[Vector4]:
	return _spheres


## How many pieces there are, and what was sent to be drawn this frame (before the renderer leaves
## out squares that are off screen): {pieces, triangles, draws, squares}.
func counts() -> Dictionary:
	var triangles := 0
	var draws := 0
	for block: Dictionary in _blocks:
		if block.shown == 2:
			triangles += block.triangles_full
			draws += (block.full as Array).size()
		elif block.shown == 1:
			triangles += block.triangles_low
			draws += (block.low as Array).size()
	return {"pieces": _count, "triangles": triangles, "draws": draws, "squares": _blocks.size()}


## Sets one of the shader's settings (`stir`, `barnacles`, and the colours `bark`, `bark_stain`,
## `crust_oyster`, `crust_algae`, `barnacle`, `root_tip`, `leaf_top`, `leaf_under`, `leaf_clump`,
## `pod`, `pod_tip`, `leaf_fallen`, `leaf_rotting`).
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


## Each square draws its full pieces near the camera, its light ones farther off, nothing past `far`.
func _choose() -> void:
	if not is_inside_tree():
		return
	var camera := get_viewport().get_camera_3d()
	var eye := to_local(camera.global_position) if camera != null else Vector3.ZERO
	for block: Dictionary in _blocks:
		var box: AABB = (block.core as AABB).grow(2.0)
		var nearest := eye.clamp(box.position, box.end)
		var gap := eye.distance_to(nearest) if camera != null else 0.0
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
		for part: MultiMeshInstance3D in block.low:
			part.visible = wanted == 1


func _part(list: Array, mesh: Mesh, box: AABB) -> MultiMeshInstance3D:
	var many := MultiMesh.new()
	many.transform_format = MultiMesh.TRANSFORM_3D
	# (the shader reads the pieces' vertex colours: under Compatibility COLOR comes out black
	# unless the MultiMesh has colours, so each instance's is white)
	many.use_colors = true
	many.use_custom_data = true
	many.mesh = mesh
	many.instance_count = list.size()
	for i in list.size():
		many.set_instance_transform(i, list[i][0])
		many.set_instance_color(i, Color.WHITE)
		many.set_instance_custom_data(i, list[i][1])
	many.custom_aabb = box
	var part := MultiMeshInstance3D.new()
	part.multimesh = many
	part.material_override = _material
	part.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	part.visible = false
	add_child(part)
	return part
