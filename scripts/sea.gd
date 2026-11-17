class_name Sea
extends Node3D
## The sea the game is played in: a floor of GameCommon's sand with rocks standing in it
## (models/sea_floor.glb), under Salmon Run 2's water, dim and blue, with marine snow hanging
## in it. Taken from Moon Jellies' scripts/sea.gd (as of its 642f9bd) and made bigger and a
## little lighter, so that what is coming can be seen in time; the snow is CPU particles, not
## GPU ones, for GL Compatibility.
##
## It is a round bowl: `RADIUS` across the middle, the sand banking up all round its edge, the
## surface `SURFACE` metres up. `keep_in` holds a swimmer inside it and `clear_of_rocks` out of
## the rocks (each rock is a sphere in models/sea_rocks.json, written by the Blender build).

const WATER := preload("res://shaders/water.gdshader")
const FOAM := preload("res://textures/foam_noise.png")
const ROCK := preload("res://shaders/sea_floor.gdshader")

## How far out a swimmer can go from the middle, and how high the water's surface is.
const RADIUS := 44.0
const SURFACE := 16.0

## The rocks, each as a sphere: x, y, z, radius.
static var rocks: Array[Vector4] = []

var sand: SandGround
## Whatever the snow should hang round (the camera).
var eye: Node3D
var clock := 0.0

var _snow: CPUParticles3D


## The height of the sand at a point. (tools/build_sea_floor.py has the same sum, to stand the
## rocks in it: change one, change the other, and build the rocks again.)
static func ground(x: float, z: float) -> float:
	var h := 0.6 * sin(x * 0.07 + 1.3) * cos(z * 0.06) + 0.2 * sin(x * 0.21 + z * 0.17)
	var far := Vector2(x, z).length()
	# (banks rising all round the edge of the sea)
	return h + pow(maxf(far - 34.0, 0.0), 1.5) * 0.09


## A point held inside the sea, `room` metres clear of its floor, surface and edge.
static func keep_in(p: Vector3, room: float) -> Vector3:
	var out := Vector2(p.x, p.z)
	if out.length() > RADIUS - room:
		out = out.normalized() * (RADIUS - room)
	var low := ground(out.x, out.y) + room
	return Vector3(out.x, clampf(p.y, low, maxf(low, SURFACE - room)), out.y)


## A point pushed out of any rock it is in, `room` metres clear.
static func clear_of_rocks(p: Vector3, room: float) -> Vector3:
	for rock in rocks:
		var from := p - Vector3(rock.x, rock.y, rock.z)
		var far := from.length()
		if far < rock.w + room:
			p = Vector3(rock.x, rock.y, rock.z) + (from / far if far > 0.001 else Vector3.UP) * (rock.w + room)
	return p


## A place in open water, at random, no nearer than `apart` to `from` if that can be had.
static func open_water(rng: RandomNumberGenerator, room: float, from := Vector3.INF, apart := 0.0) -> Vector3:
	var best := Vector3.ZERO
	var best_far := -1.0
	for attempt in 12:
		var turn := rng.randf() * TAU
		var reach := (RADIUS - 4.0) * sqrt(rng.randf())
		var p := Vector3(cos(turn) * reach, rng.randf_range(1.0, SURFACE - 1.5), sin(turn) * reach)
		p = clear_of_rocks(keep_in(p, room), room)
		if from == Vector3.INF:
			return p
		var far := p.distance_to(from)
		if far >= apart:
			return p
		if far > best_far:
			best_far = far
			best = p
	return best


func _ready() -> void:
	if rocks.is_empty():
		for each: Array in (load("res://models/sea_rocks.json") as JSON).data:
			rocks.append(Vector4(each[0], each[1], each[2], each[3]))
	_light()
	_floor()
	_surface()
	_make_snow()


func _process(delta: float) -> void:
	clock += delta
	RenderingServer.global_shader_parameter_set(&"water_clock", clock)
	if eye:
		_snow.global_position = eye.global_position - eye.global_basis.z * 4.0


## Dim blue water, lighter than Moon Jellies' (there the jellies are the only light; here a
## hunter has to be seen coming).
func _light() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.012, 0.07, 0.17)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.3, 0.5, 0.8)
	env.ambient_light_energy = 0.55
	env.fog_enabled = true
	env.fog_light_color = Color(0.012, 0.07, 0.17)
	env.fog_density = 0.04
	# (the background must be fogged too: its own colour draws far darker than fogged ground)
	env.fog_sky_affect = 1.0
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.glow_enabled = true
	env.glow_intensity = 0.8
	env.glow_bloom = 0.1
	env.glow_hdr_threshold = 0.8
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_SCREEN
	var world := WorldEnvironment.new()
	world.environment = env
	add_child(world)
	var sun := DirectionalLight3D.new()
	sun.light_color = Color(0.55, 0.78, 1.0)
	sun.light_energy = 0.9
	sun.rotation_degrees = Vector3(-72.0, 25.0, 0.0)
	sun.shadow_enabled = false
	add_child(sun)


## The sea floor: GameCommon's sand, pale and rippled, with the rocks standing in it.
func _floor() -> void:
	sand = SandGround.new()
	sand.name = "Sand"
	sand.half = Vector2(60.0, 60.0)
	sand.cell = 1.0
	sand.colour = Color(0.62, 0.63, 0.6)
	sand.ripples = Sand.Ripples.MIXED
	sand.solid = false
	sand.casts_shadow = false
	sand.height = Sea.ground
	add_child(sand)
	var made := (load("res://models/sea_floor.glb") as PackedScene).instantiate()
	add_child(made)
	for mesh: MeshInstance3D in made.find_children("*", "MeshInstance3D", true, false):
		var material := ShaderMaterial.new()
		material.shader = ROCK
		material.set_shader_parameter(&"rock", true)
		material.set_shader_parameter(&"caustics", 0.5)
		mesh.material_override = material
		mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


## The water overhead: Salmon Run 2's water (shaders/water.gdshader), on the kind of mesh its
## water_scene.gd builds (a few metres to a square, each corner's place in metres in its UVs).
## As Moon Jellies lays it.
func _surface() -> void:
	var water := ShaderMaterial.new()
	water.shader = WATER
	water.set_shader_parameter(&"foam_texture", FOAM)
	water.set_shader_parameter(&"deep", Color(0.02, 0.1, 0.28))
	water.set_shader_parameter(&"shallow", Color(0.1, 0.3, 0.56))
	water.set_shader_parameter(&"swell", 1.6)
	water.set_shader_parameter(&"whitecaps", 0.35)
	water.set_shader_parameter(&"flow", 0.25)
	var size := Vector2(400.0, 400.0)
	var cell := Vector2(4.0, 4.0)
	var cols := int(size.x / cell.x)
	var rows := int(size.y / cell.y)
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var colours := PackedColorArray()
	var uvs := PackedVector2Array()
	var uv2s := PackedVector2Array()
	var tangents := PackedFloat32Array()
	var indices := PackedInt32Array()
	for r in rows + 1:
		var s := size.y * r / rows
		for c in cols + 1:
			var x := size.x * (float(c) / cols - 0.5)
			verts.append(Vector3(x, 0.0, size.y * 0.5 - s))
			normals.append(Vector3.UP)
			colours.append(Color(0.0, 1.0, 0.0))
			uvs.append(Vector2(0.5 + x / 26.8, s))
			uv2s.append(Vector2(x, 1.0))
			tangents.append_array(PackedFloat32Array([1.0, 0.0, 0.0, 1.0]))
	for r in rows:
		for c in cols:
			var a := r * (cols + 1) + c
			var b := a + 1
			var d := a + cols + 1
			var e := d + 1
			indices.append_array(PackedInt32Array([a, e, b, a, d, e]))
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_COLOR] = colours
	arrays[Mesh.ARRAY_TEX_UV] = uvs
	arrays[Mesh.ARRAY_TEX_UV2] = uv2s
	arrays[Mesh.ARRAY_TANGENT] = tangents
	arrays[Mesh.ARRAY_INDEX] = indices
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var surface := MeshInstance3D.new()
	surface.name = "Water"
	surface.mesh = mesh
	surface.material_override = water
	surface.position = Vector3(0.0, SURFACE, 0.0)
	surface.extra_cull_margin = 4.0
	surface.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(surface)


## Marine snow: specks hanging in the water round the camera, sinking very slowly.
func _make_snow() -> void:
	var speck := StandardMaterial3D.new()
	speck.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	speck.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	speck.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	speck.albedo_color = Color(0.25, 0.38, 0.6)
	var quad := QuadMesh.new()
	quad.size = Vector2(0.025, 0.025)
	quad.material = speck
	_snow = CPUParticles3D.new()
	_snow.name = "Snow"
	_snow.amount = 500
	_snow.lifetime = 12.0
	_snow.preprocess = 12.0
	_snow.local_coords = false
	_snow.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	_snow.emission_box_extents = Vector3(8.0, 5.0, 8.0)
	_snow.gravity = Vector3(0.0, -0.012, 0.0)
	_snow.initial_velocity_min = 0.0
	_snow.initial_velocity_max = 0.03
	_snow.spread = 180.0
	_snow.scale_amount_min = 0.4
	_snow.scale_amount_max = 1.6
	_snow.mesh = quad
	_snow.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_snow)
