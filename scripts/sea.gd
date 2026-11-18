class_name Sea
extends Node3D
## The sea the game is played in: a floor of GameCommon's sand with rocks standing in it
## (models/sea_floor.glb), under Salmon Run 2's water, dim and blue, with marine snow hanging
## in it. Taken from Moon Jellies' scripts/sea.gd (as of its 642f9bd) and made bigger and a
## little lighter, so that what is coming can be seen in time; the snow is CPU particles, not
## GPU ones, for GL Compatibility.
##
## It is a small Monterey Bay (see `ZONES`, scripts/bay.gd and tools/MONTEREY.md): beaches all
## round the shore, two kelp forests, docks at Monterey and Santa Cruz, Elkhorn Slough, sand off
## Santa Cruz, the canyon winding out from Moss Landing into a deep basin with Atlantis at its
## lower end, a pirate ship on its rim, sea grass and a sunken liner off the peninsula and Carmel,
## and to the west the shelf's edge, where the floor drops away into the open ocean.
## `ground` is the floor's height everywhere; `keep_in` holds a swimmer in the water and
## `clear_of_rocks` out of the rocks (each a sphere); `place` finds somewhere in a zone.

const WATER := preload("res://shaders/water.gdshader")
const FOAM := preload("res://textures/foam_noise.png")
const ROCK := preload("res://shaders/sea_floor.gdshader")

## How high the water's surface is, and how far the sea runs: west (the open Pacific) to east
## (Moss Landing) along x, north (Santa Cruz) to south (Point Lobos) along z. The shape of the
## floor is Bay's (scripts/bay.gd; the layout is in tools/MONTEREY.md).
const SURFACE := 40.0
const WEST := Bay.WEST
const EAST := Bay.EAST
const NORTH := Bay.NORTH
const SOUTH := Bay.SOUTH
## (the larger of NORTH and SOUTH, for anything that wants one half-width)
const SIDE := 194.0 * Bay.K
## Where the shelf ends and the floor drops away (x, wavering along z: see `edge_at`); the open
## ocean is to the west of it.
const EDGE := Bay.EDGE * Bay.K
## The places in it (the user's drawing, 2026-11-18), each round a middle (x, z) out to a radius,
## and some with more patches (`also`: [middle, radius] each). "open" is everything west of the
## shelf's edge (and the deep water over the canyon's basin); "beach" is the strip of shallows
## all along the shore (`Bay.BEACH`); "trench" is the canyon's water deeper than `deeper`.
## In world metres (the chart in scripts/bay.gd times Bay.K).
const ZONES := {
	"beach": {"at": Vector2(78.0, -56.0), "radius": 0.0},
	"river": {"at": Vector2(99.0, -19.0), "radius": 10.0},
	"kelp": {"at": Vector2(53.0, 42.0), "radius": 30.0, "also": [[Vector2(54.4, -64.0), 19.0]]},
	"docks": {"at": Vector2(35.2, 78.4), "radius": 14.0, "also": [[Vector2(-27.2, -107.2), 13.0]]},
	"sand": {"at": Vector2(-74.0, -78.0), "radius": 34.0},
	"pirate": {"at": Vector2(-80.0, -12.8), "radius": 20.0},
	"trench": {"at": Vector2(-40.0, 26.0), "radius": 38.0, "deeper": 45.0},
	"ruins": {"at": Vector2(-75.2, 73.6), "radius": 36.0},
	"grass": {"at": Vector2(-11.2, 78.4), "radius": 15.0},
	"reef": {"at": Vector2(-40.0, 129.6), "radius": 32.0},
	"open": {"at": Vector2(-138.0, -16.0), "radius": 24.0},
}
## The liner's wreck (scripts/wreck.gd, another agent's): where the middle of its keel rests on the
## bottom, and its turn (rotation.y; the hull's length lies along the node's own Z). On the shelf
## off Point Lobos at the head of the Carmel Canyon: the user's red X.
const WRECK_AT := Vector3(-40.0, 10.0, 129.6)
const WRECK_HEADING := 1.4
## Atlantis (scripts/ruins.gd, another agent's): the middle of its terrace on the bottom, and its
## turn (its front, the node's -Z, faces north-east, up the canyon). In the lower end of the canyon.
const RUINS_AT := Vector3(-75.2, -2.0, 73.6)
const RUINS_HEADING := -0.785
## The pirate ship (scripts/pirate_wreck.gd, another agent's): the middle of its sandy hollow, and
## its turn (its length along the node's own Z). On the canyon's western rim.
const PIRATE_AT := Vector3(-80.0, 19.0, -12.8)
const PIRATE_HEADING := 0.3
## Where a run starts (x, z): over the sand, between the north kelp and the pirate ship, with
## room east of it for the title boat's circle (45 m round a middle 45 m east: Title.COURSE).
const START := Vector2(-52.8, -36.8)

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
## Shafts of light hanging from the surface round the eye (scripts/light_shafts.gd).
var shafts: LightShafts
var _sun: DirectionalLight3D
var _water: ShaderMaterial
var _sand_look: ShaderMaterial
var _look_wait := 0.0
var _shaft_strength := 0.0


## The height of the sea floor at a point: Monterey Bay (scripts/bay.gd has the one sum; this
## reads it from a 2 m grid made the first time it is asked).
static func ground(x: float, z: float) -> float:
	return Bay.ground(x, z)


## Where the shelf's edge is (x) at a place along the coast (z): the open ocean is west of it.
static func edge_at(z: float) -> float:
	return Bay.edge_at(z)


## A zone's patches: each [middle, radius].
static func patches(zone: String) -> Array:
	var entry: Dictionary = ZONES[zone]
	return [[entry.at, float(entry.radius)]] + entry.get("also", [])


## Which zone a place is in ("" for the plain shelf between them).
static func zone_at(x: float, z: float) -> String:
	if x < edge_at(z):
		return "open"
	var deep := SURFACE - ground(x, z)
	for zone: String in ZONES:
		if zone == "open" or zone == "beach":
			continue
		for patch: Array in patches(zone):
			if Vector2(x, z).distance_to(patch[0]) < float(patch[1]) and deep >= float(ZONES[zone].get("deeper", 0.0)):
				return zone
	if deep > 0.0 and deep < Bay.BEACH_DEEP:
		return "beach"
	return ""


## A point held inside the sea, `room` metres clear of its floor, surface and edges. Where the
## water is too shallow for that it is moved out towards deeper water.
static func keep_in(p: Vector3, room: float) -> Vector3:
	var x := clampf(p.x, WEST + room, EAST - room)
	var z := clampf(p.z, NORTH + room, SOUTH - room)
	var low := ground(x, z) + room
	for attempt in 16:
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
		var flat := _spot(rng, zone)
		# (water deep enough to hold it; failing that, the last try is taken as it is)
		for again in 10:
			var deep := SURFACE - ground(flat.x, flat.y)
			if deep > 2.0 * room + 0.6 and (zone != "beach" or deep < Bay.BEACH_DEEP + 1.0) and deep >= float(ZONES.get(zone, {}).get("deeper", 0.0)):
				break
			flat = _spot(rng, zone)
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


# A spot (x, z) in a zone, at random, before it is tried for depth. The open ocean is the strip
# west of the shelf's edge or, as often, the water over the canyon's deep basin; the beach is
# anywhere near the shore; a zone of several patches picks one by its size.
static func _spot(rng: RandomNumberGenerator, zone: String) -> Vector2:
	var z := rng.randf_range(NORTH + 6.0, SOUTH - 6.0)
	if zone == "open":
		if rng.randf() < 0.5:
			return Vector2(rng.randf_range(WEST + 6.0, edge_at(z) - 10.0), z)
		zone = "trench"
	if zone == "beach":
		# (a point on the shelf, walked in to the shore's strip)
		var flat := Vector2(rng.randf_range(WEST + 30.0, EAST - 6.0), z)
		var d := Bay.shore_distance(flat)
		for step in 6:
			if d < Bay.BEACH * Bay.K:
				break
			var fall := Vector2(Bay.shore_distance(flat + Vector2(1.0, 0.0)) - d, Bay.shore_distance(flat + Vector2(0.0, 1.0)) - d)
			flat -= fall.normalized() * (d - rng.randf_range(2.5, Bay.BEACH * Bay.K - 2.5)) if fall.length() > 0.001 else Vector2.ZERO
			d = Bay.shore_distance(flat)
		return flat
	if not ZONES.has(zone):
		return Vector2(rng.randf_range(WEST + 6.0, EAST - 6.0), z)
	var all := patches(zone)
	var pick: Array = all[0]
	if all.size() > 1:
		var total := 0.0
		for patch: Array in all:
			total += pow(float(patch[1]), 2.0)
		var roll := rng.randf() * total
		for patch: Array in all:
			roll -= pow(float(patch[1]), 2.0)
			pick = patch
			if roll <= 0.0:
				break
	var turn := rng.randf() * TAU
	return pick[0] + Vector2(cos(turn), sin(turn)) * float(pick[1]) * sqrt(rng.randf())


func _ready() -> void:
	_light()
	_floor()
	_surface()
	_make_snow()
	# (the water's light: tools/WATER_FX.md)
	_caustics()
	shafts = LightShafts.new()
	add_child(shafts)
	_look()


func _process(delta: float) -> void:
	clock += delta
	RenderingServer.global_shader_parameter_set(&"water_clock", clock)
	if eye:
		_snow.global_position = eye.global_position - eye.global_basis.z * 4.0
	# (the time of day moves the light on, a few times a second; the shafts fade as the eye goes deep)
	Day.advance(delta)
	_look_wait -= delta
	if _look_wait <= 0.0:
		_look_wait = 0.25
		_look()
	shafts.eye = eye
	if eye:
		var deep := Sea.SURFACE - eye.global_position.y
		shafts.strength = 0.0 if above else _shaft_strength * (1.0 - smoothstep(14.0, 34.0, deep))


## Whether the eye is above the surface: there the air is clear and the sky pale; under it the
## water is blue and thick.
func set_above(to: bool) -> void:
	if to == above:
		return
	above = to
	_look()
	_snow.visible = not to


## The light of the hour (Day), in the air or under the water: the sun (or the moon), the sky,
## the water's colour and fog, the shafts and the caustics. Night is a moonlit blue, never
## black: the ambient light under water stays at about two thirds of midday's, so what is
## coming can still be seen.
func _look() -> void:
	var day := Day.light()
	var glow := Day.glow()
	var lit := Day.light_colour()
	var to := Day.sun_direction()
	_sun.global_basis = Basis.looking_at(-to, Vector3.UP if absf(to.y) < 0.99 else Vector3.FORWARD)
	_sun.light_color = lit
	_sun.light_energy = lerpf(0.6, 1.5, day) + 0.45 * glow * (1.0 - day)
	var water := Color(0.008, 0.042, 0.11).lerp(Color(0.012, 0.07, 0.17), day).lerp(Color(0.05, 0.06, 0.13), glow * 0.35)
	# (near the top the water is a green-blue, as coastal water is and as the concept pictures
	# are; it goes to the deep blue by about 35 m down. Claude's pick, 2026-11-18)
	var eye := get_viewport().get_camera_3d()
	var down_far := clampf((SURFACE - eye.global_position.y) / 35.0, 0.0, 1.0) if eye else 0.5
	water = (Color(0.02, 0.2, 0.22) * lerpf(0.45, 1.0, day)).lerp(water, smoothstep(0.0, 1.0, down_far))
	if above:
		var sky := Day.sky_colour()
		_env.background_color = sky
		_env.fog_light_color = sky.lerp(Color(0.62, 0.74, 0.9) * lerpf(0.3, 1.0, day), 0.5)
		_env.fog_density = 0.004
		_env.ambient_light_color = Color(0.8, 0.85, 0.9).lerp(sky, 0.35) * lerpf(0.6, 1.0, day)
	else:
		_env.background_color = water
		_env.fog_light_color = water
		_env.fog_density = lerpf(0.03, 0.04, down_far)
		_env.ambient_light_color = Color(0.22, 0.34, 0.62).lerp(Color(0.3, 0.5, 0.8), day).lerp(Color(0.42, 0.42, 0.62), glow * 0.3).lerp(Color(0.5, 0.72, 0.7) * lerpf(0.6, 1.0, day), 0.6 * (1.0 - down_far))
	# (the surface overhead dims at night; seen from under it, it is the brightest thing there is)
	var dim := lerpf(0.5, 1.0, maxf(day, glow * 0.7))
	_water.set_shader_parameter(&"deep", Color(0.02, 0.1, 0.28) * dim)
	_water.set_shader_parameter(&"shallow", Color(0.1, 0.3, 0.56).lerp(Color(0.4, 0.32, 0.42), glow * 0.15) * dim)
	# The shafts: the light comes down through the surface bent steeper (water bends it by 1.33).
	var down := -to
	var flat := Vector2(down.x, down.z)
	var bent := clampf(flat.length() / 1.33, 0.0, 0.95)
	var aside := flat.normalized() * bent if flat.length() > 0.001 else Vector2.ZERO
	shafts.slant = Vector3(aside.x, -sqrt(1.0 - bent * bent), aside.y)
	shafts.colour = lit.lerp(Color.WHITE, 0.3)
	_shaft_strength = 0.2 * lerpf(0.3, 1.0, day)
	if _sand_look:
		_sand_look.set_shader_parameter(&"caustics", 2.2 * lerpf(0.35, 1.0, day))


## Caustics: the rippling net of light the surface throws on the sea bed in the shallows. They
## are added to the sand's own shader (GameCommon's sand, whose copy in scripts/sand.gd is left as
## it is): a copy of its code is made with a few lines put in, and the sand is drawn with that
## instead (still one shader, made before anything is drawn). The net brightens only the light
## from above (the sun, or the moon), fades out between 5 and 12 m of water, and further off.
func _caustics() -> void:
	var material := sand.material()
	if material == null or material.shader == null:
		return
	var code := material.shader.code
	var anchors := ["varying vec3 plain;", "// Ground that has dried and split", "	ALBEDO = colour * (1.0 - veil);", "	DIFFUSE_LIGHT += lit * sun + (LIGHT_IS_DIRECTIONAL ? sky : vec3(0.0));"]
	for anchor: String in anchors:
		if code.count(anchor) != 1:
			push_warning("Sea: the sand's shader has changed; no caustics")
			return
	code = code.replace(anchors[0], anchors[0] + "\nvarying float caustic_k;\nuniform float caustics = 0.0;\nuniform float caustic_surface = 40.0;\nglobal uniform float water_clock;")
	code = code.replace(anchors[1], CAUSTIC_NET + anchors[1])
	code = code.replace(anchors[2], "	caustic_k = caustics * caustic_net(at) * (1.0 - smoothstep(5.0, 12.0, caustic_surface - at.y)) * (1.0 - smoothstep(16.0, 34.0, length(VERTEX)));\n" + anchors[2])
	code = code.replace(anchors[3], "	DIFFUSE_LIGHT += lit * sun * (LIGHT_IS_DIRECTIONAL ? 1.0 + caustic_k : 1.0) + (LIGHT_IS_DIRECTIONAL ? sky : vec3(0.0));")
	var shader := Shader.new()
	shader.code = code
	material.shader = shader
	material.set_shader_parameter(&"caustic_surface", SURFACE)
	_sand_look = material


## The net itself: two layers of wandering lines (where a smooth noise crosses its middle),
## warped by a slower noise and drifting different ways, brightest where they cross; in patches,
## so that some stretches of the shallows have more of it than others.
const CAUSTIC_NET := """
float caustic_line(vec2 p) {
	return 1.0 - smoothstep(0.0, 0.08, abs(patches(p) - 0.5));
}

float caustic_net(vec3 p) {
	float t = water_clock;
	vec2 q = p.xz * 0.85;
	vec2 warp = vec2(patches(q * 0.45 + vec2(t * 0.11, 0.0)), patches(q * 0.45 + vec2(3.7, t * 0.09))) - 0.5;
	float a = caustic_line(q + warp * 1.7 + vec2(t * 0.13, t * 0.07));
	float b = caustic_line(q * 1.37 + warp.yx * 1.3 + vec2(-t * 0.09, t * 0.12) + 9.1);
	float spread = 0.35 + 0.65 * smoothstep(0.3, 0.65, patches(p.xz * 0.035 + 4.0));
	return (max(a, b) * 0.6 + a * b * 0.9) * spread;
}

"""


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
	_sun = sun


## The sea floor: GameCommon's sand, pale and rippled, with the rocks standing in it.
func _floor() -> void:
	sand = SandGround.new()
	sand.name = "Sand"
	# (the whole bay, its corners on Bay's grid; the height is asked in the sand's own space)
	var middle := Vector3((WEST + EAST) * 0.5, 0.0, (NORTH + SOUTH) * 0.5)
	sand.position = middle
	sand.half = Vector2((EAST - WEST) * 0.5, (SOUTH - NORTH) * 0.5)
	sand.cell = Bay.GRID
	sand.colour = Color(0.62, 0.63, 0.6)
	sand.ripples = Sand.Ripples.MIXED
	sand.solid = false
	sand.casts_shadow = false
	sand.height = func(x: float, z: float) -> float: return Sea.ground(x + middle.x, z + middle.z)
	add_child(sand)


## The water overhead: Salmon Run 2's water (shaders/water.gdshader), on the kind of mesh its
## water_scene.gd builds (a few metres to a square, each corner's place in metres in its UVs).
## As Moon Jellies lays it.
func _surface() -> void:
	var water := ShaderMaterial.new()
	_water = water
	water.shader = WATER
	water.set_shader_parameter(&"foam_texture", FOAM)
	water.set_shader_parameter(&"deep", Color(0.02, 0.1, 0.28))
	water.set_shader_parameter(&"shallow", Color(0.1, 0.3, 0.56))
	water.set_shader_parameter(&"swell", 1.6)
	water.set_shader_parameter(&"whitecaps", 0.35)
	water.set_shader_parameter(&"flow", 0.05)  # (the user, 2026-11-18: "the foam on the water surface is moving wa ytoo fast")
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
