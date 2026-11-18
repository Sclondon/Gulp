class_name Sea
extends Node3D
## The sea the game is played in: a floor of GameCommon's sand with rocks standing in it
## (models/sea_floor.glb), under Salmon Run 2's water, dim and blue, with marine snow hanging
## in it. Taken from Moon Jellies' scripts/sea.gd (as of its 642f9bd) and made bigger and a
## little lighter, so that what is coming can be seen in time; the snow is CPU particles, not
## GPU ones, for GL Compatibility.
##
## It is a stretch of coast (see `ZONES`): a shore to the west with a river mouth among mangroves,
## a sea grass bed and sand flats in the shallows, a kelp forest on rock and a small coral reef on
## the shelf, and to the east the shelf's edge, where the floor drops away into the open ocean.
## `ground` is the floor's height everywhere; `keep_in` holds a swimmer in the water and
## `clear_of_rocks` out of the rocks (each a sphere); `place` finds somewhere in a zone.

const WATER := preload("res://shaders/water.gdshader")
const FOAM := preload("res://textures/foam_noise.png")
const ROCK := preload("res://shaders/sea_floor.gdshader")

## How high the water's surface is, and how far the sea runs: west (the shore) to east (open
## ocean) along x, and north and south along z.
const SURFACE := 40.0
const WEST := -150.0
const EAST := 175.0
const SIDE := 105.0
## Where the shelf ends and the floor drops away (x, wavering along z: see `edge_at`).
const EDGE := 58.0
## The places in it, each round a middle (x, z) out to a radius; "open" is everything beyond the
## shelf's edge. Depths are `ground`'s business.
const ZONES := {
	"river": {"at": Vector2(-128.0, -30.0), "radius": 20.0},
	"grass": {"at": Vector2(-82.0, -48.0), "radius": 30.0},
	"sand": {"at": Vector2(-62.0, 48.0), "radius": 34.0},
	"kelp": {"at": Vector2(0.0, -34.0), "radius": 40.0},
	"reef": {"at": Vector2(12.0, 56.0), "radius": 24.0},
	"open": {"at": Vector2(118.0, 0.0), "radius": 55.0},
	"trench": {"at": Vector2(140.0, 55.0), "radius": 24.0},
}

## The rocks, each as a sphere: x, y, z, radius (Scenery adds them: `add_rock`). They are kept
## by the square of floor they stand on (`CELL` metres), so that a swimmer is only tried against
## the few near it.
static var rocks: Array[Vector4] = []
const CELL := 8.0
static var _cells := {}

var sand: SandGround
## Whatever the snow should hang round (the camera).
var eye: Node3D
var clock := 0.0
## The eye is out of the water (see `set_above`).
var above := false

var _env: Environment

var _snow: CPUParticles3D


## The height of the sand at a point. (tools/build_sea_floor.py has the same sum, to stand the
## rocks in it: change one, change the other, and build the rocks again.)
static func ground(x: float, z: float) -> float:
	var bumps := 0.6 * sin(x * 0.07 + 1.3) * cos(z * 0.06) + 0.2 * sin(x * 0.21 + z * 0.17)
	# How deep the water is, going out from the shore: a beach, the shallows, the shelf.
	var deep := 0.0
	if x < -100.0:
		deep = remap(x, -140.0, -100.0, -3.0, 6.0)
	elif x < -30.0:
		deep = remap(x, -100.0, -30.0, 6.0, 16.0)
	else:
		deep = remap(minf(x, EDGE), -30.0, EDGE, 16.0, 24.0)
	# The river: a channel cut through the shore, running out west.
	var river: Vector2 = ZONES.river.at
	var across := absf(z - river.y - 6.0 * sin(x * 0.05))
	var channel := (1.0 - smoothstep(9.0, 16.0, across)) * (1.0 - smoothstep(-110.0, -92.0, x))
	deep = lerpf(deep, maxf(deep, 5.0), channel)
	# The reef: a mound.
	var reef: Vector2 = ZONES.reef.at
	deep -= 5.0 * (1.0 - smoothstep(6.0, float(ZONES.reef.radius), Vector2(x, z).distance_to(reef)))
	# Past the shelf's edge the floor falls away.
	var over := x - edge_at(z)
	deep += 36.0 * smoothstep(0.0, 14.0, over) + 0.05 * maxf(over, 0.0)
	# The trench: a long cleft in the ocean floor, far deeper still.
	var trench: Vector2 = ZONES.trench.at
	deep += 60.0 * (1.0 - smoothstep(5.0, 16.0, absf(x - trench.x - 0.3 * (z - trench.y)))) * (1.0 - smoothstep(18.0, 34.0, absf(z - trench.y)))
	return SURFACE - deep + bumps * clampf(deep * 0.15, 0.0, 1.0)


## Where the shelf's edge is (x) at a place along the coast (z).
static func edge_at(z: float) -> float:
	return EDGE + 7.0 * sin(z * 0.035) + 3.0 * sin(z * 0.11 + 1.0)


## Which zone a place is in ("" for the plain shelf between them).
static func zone_at(x: float, z: float) -> String:
	if x > edge_at(z):
		return "open"
	for zone: String in ZONES:
		if zone != "open" and zone != "trench" and Vector2(x, z).distance_to(ZONES[zone].at) < float(ZONES[zone].radius):
			return zone
	return ""


## A point held inside the sea, `room` metres clear of its floor, surface and edges. Where the
## water is too shallow for that it is moved out towards deeper water.
static func keep_in(p: Vector3, room: float) -> Vector3:
	var x := clampf(p.x, WEST, EAST - room)
	var z := clampf(p.z, -SIDE + room, SIDE - room)
	var low := ground(x, z) + room
	for attempt in 8:
		if low <= SURFACE - room:
			break
		# (downhill: the way the floor falls)
		var fall := Vector2(ground(x - 0.5, z) - ground(x + 0.5, z), ground(x, z - 0.5) - ground(x, z + 0.5))
		if fall.length() < 0.0001:
			fall = Vector2.RIGHT
		fall = fall.normalized() * 0.6
		x += fall.x
		z += fall.y
		low = ground(x, z) + room
	return Vector3(x, clampf(p.y, low, maxf(low, SURFACE - room)), z)


## A point pushed out of any rock it is in, `room` metres clear.
## Adds a rock: a sphere nothing may swim into.
static func add_rock(rock: Vector4) -> void:
	var at := rocks.size()
	rocks.append(rock)
	# (into every square it could be felt from: its own radius and 3 m of room)
	var reach := rock.w + 3.0
	for cx in range(floori((rock.x - reach) / CELL), floori((rock.x + reach) / CELL) + 1):
		for cz in range(floori((rock.z - reach) / CELL), floori((rock.z + reach) / CELL) + 1):
			var key := Vector2i(cx, cz)
			var list: PackedInt32Array = _cells.get(key, PackedInt32Array())
			list.append(at)
			_cells[key] = list


static func clear_of_rocks(p: Vector3, room: float) -> Vector3:
	var near: Variant = _cells.get(Vector2i(floori(p.x / CELL), floori(p.z / CELL)))
	if near == null:
		return p
	for at: int in near:
		var rock := rocks[at]
		var from := p - Vector3(rock.x, rock.y, rock.z)
		var far := from.length()
		if far < rock.w + room:
			p = Vector3(rock.x, rock.y, rock.z) + (from / far if far > 0.001 else Vector3.UP) * (rock.w + room)
	return p


## A place in the water of a zone ("" for anywhere), at random, no nearer than `apart` to `from`
## if that can be had.
static func place(rng: RandomNumberGenerator, zone: String, room: float, from := Vector3.INF, apart := 0.0) -> Vector3:
	var best := Vector3.ZERO
	var best_far := -1.0
	for attempt in 12:
		var flat := Vector2(rng.randf_range(WEST + 30.0, EAST - 6.0), rng.randf_range(-SIDE + 6.0, SIDE - 6.0))
		if zone == "open":
			flat.x = rng.randf_range(EDGE + 16.0, EAST - 6.0)
		elif ZONES.has(zone):
			var turn := rng.randf() * TAU
			flat = ZONES[zone].at + Vector2(cos(turn), sin(turn)) * float(ZONES[zone].radius) * sqrt(rng.randf())
		var p := Vector3(flat.x, 0.0, flat.y)
		p.y = rng.randf_range(ground(p.x, p.z) + 1.0, SURFACE - 1.5)
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


static func open_water(rng: RandomNumberGenerator, room: float, from := Vector3.INF, apart := 0.0) -> Vector3:
	return place(rng, "", room, from, apart)


func _ready() -> void:
	_light()
	_floor()
	_surface()
	_make_snow()


func _process(delta: float) -> void:
	clock += delta
	RenderingServer.global_shader_parameter_set(&"water_clock", clock)
	if eye:
		_snow.global_position = eye.global_position - eye.global_basis.z * 4.0


## Whether the eye is above the surface: there the air is clear and the sky pale; under it the
## water is blue and thick.
func set_above(to: bool) -> void:
	if to == above:
		return
	above = to
	_env.background_color = Color(0.55, 0.75, 0.95) if to else Color(0.012, 0.07, 0.17)
	_env.fog_light_color = Color(0.7, 0.82, 0.95) if to else Color(0.012, 0.07, 0.17)
	_env.fog_density = 0.004 if to else 0.04
	_env.ambient_light_color = Color(0.8, 0.85, 0.9) if to else Color(0.3, 0.5, 0.8)
	_snow.visible = not to


## Dim blue water, lighter than Moon Jellies' (there the jellies are the only light; here a
## hunter has to be seen coming).
func _light() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.012, 0.07, 0.17)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.3, 0.5, 0.8)
	env.ambient_light_energy = 0.95
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
	_env = env
	var world := WorldEnvironment.new()
	world.environment = env
	add_child(world)
	var sun := DirectionalLight3D.new()
	sun.light_color = Color(0.55, 0.78, 1.0)
	sun.light_energy = 1.5
	sun.rotation_degrees = Vector3(-72.0, 25.0, 0.0)
	sun.shadow_enabled = false
	add_child(sun)


## The sea floor: GameCommon's sand, pale and rippled, with the rocks standing in it.
func _floor() -> void:
	sand = SandGround.new()
	sand.name = "Sand"
	sand.half = Vector2(180.0, 112.0)
	sand.cell = 2.0
	sand.colour = Color(0.62, 0.63, 0.6)
	sand.ripples = Sand.Ripples.MIXED
	sand.solid = false
	sand.casts_shadow = false
	sand.height = Sea.ground
	add_child(sand)


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
	# (the user, 2026-11-18: "the little particles that drift by shouldnt all just be squares, but
	# little sprites of plankton": twelve kinds on one sheet, textures/plankton_sheet.png, made with
	# an image generator; each speck is one of them, turned at random, drawn as light)
	speck.albedo_color = Color(0.8, 0.95, 1.15)
	speck.albedo_texture = load("res://textures/plankton_sheet.png")
	speck.particles_anim_h_frames = 4
	speck.particles_anim_v_frames = 3
	speck.particles_anim_loop = false
	var quad := QuadMesh.new()
	quad.size = Vector2(0.16, 0.16)
	quad.material = speck
	_snow = CPUParticles3D.new()
	_snow.name = "Snow"
	_snow.amount = 200
	_snow.anim_offset_min = 0.0
	_snow.anim_offset_max = 1.0
	_snow.angle_min = -180.0
	_snow.angle_max = 180.0
	_snow.angular_velocity_min = -8.0
	_snow.angular_velocity_max = 8.0
	_snow.lifetime = 12.0
	_snow.preprocess = 12.0
	_snow.local_coords = false
	_snow.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	_snow.emission_box_extents = Vector3(8.0, 5.0, 8.0)
	_snow.gravity = Vector3(0.0, -0.012, 0.0)
	_snow.initial_velocity_min = 0.0
	_snow.initial_velocity_max = 0.03
	_snow.spread = 180.0
	_snow.scale_amount_min = 0.5
	_snow.scale_amount_max = 1.3
	_snow.mesh = quad
	_snow.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_snow)
