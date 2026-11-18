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
const SKY := preload("res://shaders/sky.gdshader")

## How high the water's surface is, and how far the sea runs: west (the open Pacific) to east
## (Moss Landing) along x, north (Santa Cruz) to south (Point Lobos) along z. The shape of the
## floor is Bay's (scripts/bay.gd; the layout is in tools/MONTEREY.md).
const SURFACE := 40.0
const WEST := Bay.WEST
const EAST := Bay.EAST
const NORTH := Bay.NORTH
const SOUTH := Bay.SOUTH
## (the larger of NORTH and SOUTH, for anything that wants one half-width)
const SIDE := 160.0
## Where the shelf ends and the floor drops away (x, wavering along z: see `edge_at`); the open
## ocean is to the west of it.
const EDGE := Bay.EDGE * Bay.K
## The places in it, each round a middle (x, z) out to a radius, and some with more patches
## (`also`: [middle, radius] each), at their real places in the bay (CLAUDE.md, "Decision: the real
## bay"; the user's layout of 2026-11-18 kept where the real floor allows). "open" is everything west
## of the shelf's edge (and the deep water over the canyon); "beach" is the strip of shallows all
## along the shore (`Bay.BEACH`); "trench" is the canyon's water deeper than `deeper`. World metres.
const ZONES := {
	"beach": {"at": Vector2(60.0, -125.0), "radius": 0.0},
	"river": {"at": Vector2(106.0, -38.0), "radius": 9.0},
	"kelp": {"at": Vector2(44.0, 55.0), "radius": 16.0, "also": [[Vector2(35.0, -130.0), 13.0]]},
	"docks": {"at": Vector2(66.0, 68.0), "radius": 16.0, "also": [[Vector2(3.0, -123.0), 12.0]]},
	"sand": {"at": Vector2(-10.0, -105.0), "radius": 22.0},
	"pirate": {"at": Vector2(-20.0, -62.0), "radius": 18.0},
	"trench": {"at": Vector2(30.0, -36.0), "radius": 45.0, "deeper": 45.0},
	"ruins": {"at": Vector2(-53.0, 26.0), "radius": 30.0},
	"grass": {"at": Vector2(82.0, 52.0), "radius": 12.0},
	"reef": {"at": Vector2(4.0, 122.0), "radius": 24.0},
	"open": {"at": Vector2(-95.0, 10.0), "radius": 24.0},
}
## The liner's wreck (scripts/wreck.gd, another agent's): where the middle of its keel rests on the
## bottom, and its turn (rotation.y; the hull's length lies along the node's own Z). Across the head of the Carmel
## Canyon like a bridge (the user, 2026-11-18: "The liner should sit across the carmel trench top like a
## bridge"): its ends rest on the rims 20 m down (Bay.WRECK_SHELF and WRECK_SEAT_SOUTH, two small seats), the
## canyon open under its middle down to about 50 m. Found by tools/bay_probe.gd --span.
const WRECK_AT := Vector3(4.0, 20.2, 122.0)
const WRECK_HEADING := 0.26
## Atlantis (scripts/ruins.gd, another agent's): the middle of its terrace on the bottom, and its
## turn (its front, the node's -Z, faces north-east, up the canyon). In the canyon's deep basin, 93 m down, on
## its flattest ground, at the floor's own depth (not a raised terrace: "atlantis shouldn't just be a giant crater").
const RUINS_AT := Vector3(-53.0, -53.0, 26.0)
const RUINS_HEADING := -0.93
## The pirate ship (scripts/pirate_wreck.gd, another agent's): the middle of its sandy hollow, and
## its turn (its length along the node's own Z). On the canyon's north rim, along it.
const PIRATE_AT := Vector3(-20.0, 19.0, -62.0)
const PIRATE_HEADING := 1.57
## The fish markets' landings (the user: "the fish markets should be at monteray, santa cruz, and carmel";
## the places are Claude's): the end of Monterey's commercial wharf, the end of the Santa Cruz wharf,
## the end of Carmel's pier at Stillwater Cove (world x, z). Selling there is another stage's.
const MARKETS := {"monterey": Vector2(82.0, 56.0), "santa_cruz": Vector2(-8.0, -107.0), "carmel": Vector2(27.0, 121.0)}
## Where a run starts (x, z): over the sand off Santa Cruz, by the pirate ship, with room east of it
## for the title boat's circle (45 m round a middle 45 m east: Title.COURSE).
const START := Vector2(-40.0, -55.0)

## The rocks, each as a sphere: x, y, z, radius (Scenery adds them: `add_rock`). They are kept
## twice (tools/PERF.md, "Decision: two grids for the rocks"): by the square of floor they could be
## felt from (`CELL` metres, their radius and REACH more: a quick "nothing here" for most of the
## sea), and in a fine grid of FINE-metre cubes, each holding the spheres that overlap it, so that
## a swimmer beside a wreck of a thousand spheres is tried against the few round it.
static var rocks: Array[Vector4] = []
const CELL := 8.0
const FINE := 2.0
## The most room a swimmer is given against a rock (m): more is asked of a big animal, but the
## rocks it is tried against are those within this of it.
const REACH := 3.0
static var _cells := {}
static var _fine := {}

var sand: SandGround
## Whatever the snow should hang round (the camera).
var eye: Node3D
var clock := 0.0
## The eye is out of the water (see `set_above`).
var above := false

var _env: Environment
var _sky: ShaderMaterial

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


## Adds a rock: a sphere nothing may swim into.
static func add_rock(rock: Vector4) -> void:
	var at := rocks.size()
	rocks.append(rock)
	# (into every square it could be felt from: its own radius and REACH of room)
	var reach := rock.w + REACH
	for cx in range(floori((rock.x - reach) / CELL), floori((rock.x + reach) / CELL) + 1):
		for cz in range(floori((rock.z - reach) / CELL), floori((rock.z + reach) / CELL) + 1):
			var key := Vector2i(cx, cz)
			var list: PackedInt32Array = _cells.get(key, PackedInt32Array())
			list.append(at)
			_cells[key] = list
	# (and into every fine cube it overlaps, as x, y, z, radius)
	for cx in range(floori((rock.x - rock.w) / FINE), floori((rock.x + rock.w) / FINE) + 1):
		for cy in range(floori((rock.y - rock.w) / FINE), floori((rock.y + rock.w) / FINE) + 1):
			for cz in range(floori((rock.z - rock.w) / FINE), floori((rock.z + rock.w) / FINE) + 1):
				var key := _fine_key(cx, cy, cz)
				var list: PackedFloat32Array = _fine.get(key, PackedFloat32Array())
				list.append_array(PackedFloat32Array([rock.x, rock.y, rock.z, rock.w]))
				_fine[key] = list


static func _fine_key(cx: int, cy: int, cz: int) -> int:
	return ((cx + 32768) << 32) | ((cy + 32768) << 16) | (cz + 32768)


## A point pushed out of any rock it is in, `room` metres clear.
static func clear_of_rocks(p: Vector3, room: float) -> Vector3:
	# (most of the sea has no rock within reach: one look at the coarse squares says so)
	if not _cells.has(Vector2i(floori(p.x / CELL), floori(p.z / CELL))):
		return p
	var reach := minf(room, REACH)
	var x0 := floori((p.x - reach) / FINE)
	var x1 := floori((p.x + reach) / FINE)
	var y0 := floori((p.y - reach) / FINE)
	var y1 := floori((p.y + reach) / FINE)
	var z0 := floori((p.z - reach) / FINE)
	var z1 := floori((p.z + reach) / FINE)
	for cx in range(x0, x1 + 1):
		for cy in range(y0, y1 + 1):
			for cz in range(z0, z1 + 1):
				var near: Variant = _fine.get(_fine_key(cx, cy, cz))
				if near == null:
					continue
				var list: PackedFloat32Array = near
				var k := 0
				var n := list.size()
				while k < n:
					var middle := Vector3(list[k], list[k + 1], list[k + 2])
					var clear := list[k + 3] + room
					var from := p - middle
					var far_sq := from.length_squared()
					if far_sq < clear * clear:
						var far := sqrt(far_sq)
						p = middle + (from / far if far > 0.001 else Vector3.UP) * clear
					k += 4
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
			# (the open ocean's water is deep: none of its kinds, the giants above all, over the
			# shallows round the canyon's basin; tools/BIOMES.md section 7)
			if deep > 2.0 * room + 0.6 and (zone != "beach" or deep < Bay.BEACH_DEEP + 1.0) and deep >= float(ZONES.get(zone, {}).get("deeper", 0.0)) \
					and (zone != "open" or deep >= 30.0):
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
			# (the real shelf is wide in the north: there the deep water does not reach the world's
			# west side at all, so a row of it is picked again)
			for tries in 8:
				if edge_at(z) - 10.0 > WEST + 6.0:
					return Vector2(rng.randf_range(WEST + 6.0, edge_at(z) - 10.0), z)
				z = rng.randf_range(NORTH + 6.0, SOUTH - 6.0)
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
	# (what the floor is made of, painted on the sand: scripts/floor_types.gd, tools/BIOMES.md)
	FloorTypes.paint(sand)
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
		# (a sky, not a flat colour: deeper overhead, pale at the horizon, sun and clouds. The fog
		# leaves it alone but for a haze at the horizon, which the sky draws itself. Claude's pick,
		# 2026-11-18: the user, "Whys the sky just gray")
		_env.background_mode = Environment.BG_SKY
		_env.fog_sky_affect = 0.0
		var overhead := Color(0.03, 0.05, 0.13).lerp(Color(0.12, 0.34, 0.86), day).lerp(Color(0.3, 0.32, 0.62), glow * 0.45)
		_sky.set_shader_parameter(&"zenith", overhead)
		_sky.set_shader_parameter(&"horizon", sky.lerp(Color(0.85, 0.92, 1.0), 0.35 * day))
		_sky.set_shader_parameter(&"sun_colour", lit.lerp(Color(1.0, 0.96, 0.88), 0.6 * day) * lerpf(0.35, 1.0, maxf(day, glow)))
		var cloud := Color(1.0, 1.0, 1.0).lerp(Color(1.0, 0.72, 0.55), glow * 0.7) * lerpf(0.18, 1.0, day)
		_sky.set_shader_parameter(&"cloud_lit", cloud)
		_sky.set_shader_parameter(&"cloud_shade", cloud * Color(0.68, 0.74, 0.86))
		_sky.set_shader_parameter(&"drift", Vector2(0.006, 0.002) * clock)
		_env.ambient_light_color = Color(0.8, 0.85, 0.9).lerp(sky, 0.35) * lerpf(0.6, 1.0, day)
	else:
		# (the liner's coral pocket is warmer and clearer water: a little more green-teal, less fog,
		# a warmer ambient, fading in over 50 to 30 m from the wreck. tools/BIOMES.md 5.9; Claude's
		# default for the user's question 6)
		var warm := 0.0
		if eye:
			warm = 1.0 - smoothstep(30.0, 50.0, Vector2(eye.global_position.x - WRECK_AT.x, eye.global_position.z - WRECK_AT.z).length())
		water = water.lerp(Color(0.03, 0.17, 0.19) * lerpf(0.5, 1.0, day), 0.35 * warm)
		_env.background_mode = Environment.BG_COLOR
		_env.fog_sky_affect = 1.0
		_env.background_color = water
		_env.fog_light_color = water
		_env.fog_density = lerpf(0.03, 0.04, down_far) * lerpf(1.0, 0.8, warm)
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
	# (and steep ground is rock painted from the sides, not sand stretched down it: WALL_ROCK)
	var walls := ["void fragment() {", "	float distance_off = length(VERTEX);"]
	if code.count(walls[0]) == 1 and code.count(walls[1]) == 1:
		code = code.replace(walls[0], WALL_ROCK + walls[0])
		code = code.replace(walls[1], WALL_MIX + walls[1])
	else:
		push_warning("Sea: the sand's shader has changed; no rock walls")
	# (and the sea floor's rock (the sand's sandstone kind, scripts/floor_types.gd) without the strong
	# beds of colour a desert's sandstone has: under the sea they read as stripes. Same program.)
	code = code.replace("stone_colour * mix(vec3(0.66, 0.58, 0.55), vec3(1.2, 1.17, 1.08)", "stone_colour * mix(vec3(0.88, 0.86, 0.84), vec3(1.07, 1.06, 1.04)")
	var shader := Shader.new()
	shader.code = code
	material.shader = shader
	material.set_shader_parameter(&"caustic_surface", SURFACE)
	_sand_look = material


## Rock walls (the user, 2026-11-18: "we need to work on a way to make the trench cliffs look good,
## stretched terrain looks bad"). The sand is painted from above (its x and z), so on a canyon wall
## its ripples and grain stretch into bands. Where the ground is steeper than `wall_from` (1 - the
## normal's y) it is rock instead, painted from the sides (triplanar: the x-y and z-y planes, blended
## by which way the wall faces): beds that run level along it and waver, each its own tone, with a
## lip of light over a shadowed foot; joints; blotches; silt on what faces up. The sand's ripples
## are taken out of its light there too. The usual cure for stretched heightfield cliffs (CLAUDE.md,
## "Decision: rock walls"); rock pieces over the steepest walls break their outline (Biomes' "walls").
const WALL_ROCK := """
uniform vec3 wall_colour : source_color = vec3(0.4, 0.38, 0.36);
uniform float wall_from = 0.32;
uniform float wall_to = 0.55;

// The rock at a point of a wall (p: along it, up it): its colour, and in .a how much its face there
// tips up (the lip of a bed, +) or under (its foot, -), for the light.
vec4 wall_rock(vec2 p) {
	float bed = p.y * 0.6 + (patches(p * vec2(0.035, 0.02)) - 0.5) * 2.6 + (patches(p * vec2(0.25, 0.1)) - 0.5) * 0.35;
	float layer = fract(bed);
	float lip = 1.0 - smoothstep(0.0, 0.14, layer);
	float foot = smoothstep(0.7, 1.0, layer);
	float tone = patches(vec2(floor(bed) * 3.1, 0.5));
	float blot = patches(p * 0.4 + 5.0);
	float fine = patches(p * vec2(2.2, 3.4) + 1.0);
	// (joints, thin and only here and there, mostly upright between the beds)
	float split = 1.0 - smoothstep(0.002, 0.012, cracks(p * vec2(0.55, 0.3) + 3.0));
	split *= smoothstep(0.35, 0.6, patches(p * 0.12 + 11.0));
	vec3 c = wall_colour * (0.75 + 0.45 * tone) * (0.82 + 0.3 * blot) * (0.9 + 0.2 * fine);
	// (pale silt lies on each lip, as in tools/art_src/concept_canyon_wall.png)
	c = mix(c, vec3(0.62, 0.62, 0.58), lip * 0.55 * smoothstep(0.3, 0.6, patches(p * vec2(0.3, 0.8) + 2.0)));
	c *= (1.0 + 0.2 * lip) * (1.0 - 0.45 * foot) * (1.0 - 0.4 * split);
	return vec4(c, lip - foot);
}

"""
const WALL_MIX := """	float wall = smoothstep(wall_from, wall_to, 1.0 - unrippled.y);
	if (wall > 0.001) {
		vec3 side = abs(unrippled);
		float across = side.x / max(side.x + side.z, 0.001);
		vec4 rock = wall_rock(vec2(at.z, at.y)) * across + wall_rock(vec2(at.x, at.y)) * (1.0 - across);
		vec3 stone = mix(rock.rgb, colour, smoothstep(0.45, 0.8, unrippled.y) * 0.6);
		colour = mix(colour, stone, wall);
		// (the ledges tip the light: a lip faces up, a foot faces down)
		up = normalize(mix(up, unrippled, wall) + vec3(0.0, rock.a * 0.9 * wall, 0.0));
	}
"""


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
	# (the sky, shown only from above the water: see _look. It lights nothing)
	_sky = ShaderMaterial.new()
	_sky.shader = SKY
	var sky := Sky.new()
	sky.sky_material = _sky
	sky.radiance_size = Sky.RADIANCE_SIZE_32
	sky.process_mode = Sky.PROCESS_MODE_AUTOMATIC
	env.sky = sky
	env.reflected_light_source = Environment.REFLECTION_SOURCE_DISABLED
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
	# (the user, later the same day: "The plankton sprites are too big and hd": a 16-pixel copy of each,
	# drawn with hard pixels as the rest of the half-size picture is, a third of the size. The
	# 1024-pixel sheet is kept, unused)
	speck.albedo_texture = load("res://textures/plankton_sheet_lo.png")
	speck.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
	speck.particles_anim_h_frames = 4
	speck.particles_anim_v_frames = 3
	speck.particles_anim_loop = false
	var quad := QuadMesh.new()
	quad.size = Vector2(0.06, 0.06)
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
