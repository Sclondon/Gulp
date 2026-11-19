class_name Surf
## The sea's surface as a shape, for everything that floats, leaps or splashes on it: the open swell,
## the surf along every shore and, now and then, a rogue wave. shaders/surf.gdshaderinc draws the same
## sums (keep the two alike: every number the shader needs is sent to it from here by `dress`).
## tools/WATER_FX.md, "Surf and rogue waves", has the research, the decision and the numbers.
##
## - The swell: water.gdshader's four trains of waves (height only), as before.
## - The surf: one train of waves running in to every shore at once. Their phase is the distance to the
##   shore (so their crests lie along the coastline, as real waves bend round to it), squeezed where the
##   water shoals so the waves shorten as they slow; their height grows as the water shoals (Green's
##   law, depth^-1/4) until it reaches 0.78 of the depth (McCowan's breaking limit), where they break and
##   go on as broken water no higher than that. They are Gerstner waves (trochoids: points move in
##   orbits, bunching at the crests), steeper as they shoal, the crest thrown forward over the face as
##   it breaks (after Fournier and Reeves' tilted orbits). Over the sand they run up and draw back.
## - A rogue wave: a single swell travelling across part of the sea, far taller than the sea round it,
##   growing as it comes (a wave group focusing) and fading after, breaking at its top, with a deep
##   trough before it. `start_rogue` sends one (Sea starts them by chance: `Sea.rogue_wave`).
##
## Where the shores are is baked once from Bay into `map` (a picture, a texel every GRID metres: shore
## distance, depth, how open the shore is to the sea), sampled here and in the shader the same way.

## The surf. How high the waves are out past the surf (m, amplitude), how long and how often they come
## (m, s), and how far from the shore they reach (m).
const HEIGHT := 0.85
const LENGTH := 14.0
const PERIOD := 7.0
const REACH := 28.0
## Within FLAT metres of the shore the waves shoal (the beach strip, Bay.BEACH, eased to DEEP metres).
const FLAT := Bay.BEACH
const DEEP := Bay.BEACH_DEEP
## McCowan's limit: a wave breaks when its height is this much of the depth.
const BREAK := 0.78
## Broken water still runs up the sand this high (m) at the waterline: the swash.
const SWASH := 0.3

## A rogue wave: its highest (m, from the mean surface to its crest), how long it lasts (s), how fast it
## goes (m/s), its length (m: the half-width of its hump) and width across (m), and how often one
## comes by itself (s, at random between the two).
const ROGUE_HEIGHT := 4.5
const ROGUE_LIFE := 30.0
const ROGUE_SPEED := 5.5
const ROGUE_LENGTH := 6.5
const ROGUE_WIDTH := 30.0
const ROGUE_EVERY := Vector2(240.0, 480.0)
## Its push on what swims near the top (m/s at the crest), and how fast that fades with depth (m).
const ROGUE_PUSH := 1.6
const ROGUE_DECAY := 4.0

## The open swell (water.gdshader's swell_at, with Sea's settings: swell 1.6, swell_height 0.18,
## swell_length 12, swell_speed 1).
const SWELL_LONG := 12.0 * (0.4 + 0.6 * 1.6)
const SWELL_HIGH := 0.18 * 1.6
const TRAINS := [Vector4(0.34, -0.94, 1.0, 1.0), Vector4(-0.78, -0.62, 0.62, 0.55), Vector4(0.97, 0.26, 0.37, 0.3), Vector4(-0.57, 0.82, 0.23, 0.16)]

const GRID := 2.0

## The water's clock (Sea sets it each frame; the shader's water_clock).
static var clock := 0.0
## The rogue wave under way, if any.
static var rogue_on := false
static var rogue_at := Vector2.ZERO
static var rogue_dir := Vector2(1.0, 0.0)
static var rogue_age := 0.0

static var map: ImageTexture
static var _d := PackedFloat32Array()
static var _h := PackedFloat32Array()
static var _open := PackedFloat32Array()
static var _zone := PackedFloat32Array()
static var _cols := 0
static var _rows := 0


## Bakes the shores into `map` (once): shore distance, depth and openness every GRID metres.
static func bake() -> void:
	if map:
		return
	# (Bay loads its baked floor on the first call to ground: shore_distance alone does not)
	Sea.ground(0.0, 0.0)
	_cols = int((Bay.EAST - Bay.WEST) / GRID) + 1
	_rows = int((Bay.SOUTH - Bay.NORTH) / GRID) + 1
	_d.resize(_cols * _rows)
	_h.resize(_cols * _rows)
	_open.resize(_cols * _rows)
	_zone.resize(_cols * _rows)
	var image := Image.create(_cols, _rows, false, Image.FORMAT_RGBAH)
	for r in _rows:
		var z := Bay.NORTH + r * GRID
		for c in _cols:
			var x := Bay.WEST + c * GRID
			var p := Vector2(x, z)
			var d := Bay.shore_distance(p)
			var h := Sea.SURFACE - Sea.ground(x, z)
			# (no surf up the slough, nor inside the harbours: sheltered water)
			var open := 1.0
			if d < REACH + 4.0:
				open = smoothstep(Bay.SLOUGH_HALF + 2.0, Bay.SLOUGH_HALF + 16.0, Bay._line_distance(p, Bay.SLOUGH))
				for harbour: Array in Bay.HARBOURS:
					open = minf(open, smoothstep(float(harbour[1]) * 0.7, float(harbour[1]) + 10.0, p.distance_to(harbour[0])))
			var i := r * _cols + c
			_d[i] = d
			_h[i] = h
			_open[i] = open
			# (the fourth: how much a breaker's sheet stands for the water here, scripts/breakers.gd)
			_zone[i] = Breakers.zone(p, d) if d > -2.0 and d < REACH else 0.0
			image.set_pixel(c, r, Color(d, h, open, _zone[i]))
	map = ImageTexture.create_from_image(image)


## What the shader needs, from these numbers (Sea calls it on the water's material).
static func dress(material: ShaderMaterial) -> void:
	bake()
	material.set_shader_parameter(&"shore_map", map)
	material.set_shader_parameter(&"shore_rect", Vector4(Bay.WEST, Bay.NORTH, GRID, GRID))
	material.set_shader_parameter(&"shore_texel", Vector2(1.0 / _cols, 1.0 / _rows))
	material.set_shader_parameter(&"surf_a", Vector4(HEIGHT, LENGTH, PERIOD, REACH))
	material.set_shader_parameter(&"surf_b", Vector4(FLAT, DEEP, BREAK, SWASH))
	material.set_shader_parameter(&"rogue_c", Vector4(ROGUE_LENGTH, ROGUE_WIDTH, ROGUE_LIFE, ROGUE_HEIGHT))
	Breakers.dress(material)


## The rogue wave's state for the shader, each frame.
static func dress_rogue(material: ShaderMaterial) -> void:
	material.set_shader_parameter(&"rogue_a", Vector4(rogue_at.x, rogue_at.y, rogue_dir.x, rogue_dir.y))
	material.set_shader_parameter(&"rogue_b", Vector2(rogue_age if rogue_on else -1.0, ROGUE_SPEED))


# The baked shore at a point (bilinear, as the shader's texture is): distance, depth, openness.
static func _shore(x: float, z: float) -> Vector3:
	if _d.is_empty():
		bake()
	# (texel centres: the shader's UV maps the first and last texel's middles onto the map's edges)
	var gx := clampf((x - Bay.WEST) / GRID, 0.0, _cols - 1.001)
	var gz := clampf((z - Bay.NORTH) / GRID, 0.0, _rows - 1.001)
	var c := int(gx)
	var r := int(gz)
	var fx := gx - c
	var fz := gz - r
	var i := r * _cols + c
	var j := i + _cols
	return Vector3(
			lerpf(lerpf(_d[i], _d[i + 1], fx), lerpf(_d[j], _d[j + 1], fx), fz),
			lerpf(lerpf(_h[i], _h[i + 1], fx), lerpf(_h[j], _h[j + 1], fx), fz),
			lerpf(lerpf(_open[i], _open[i + 1], fx), lerpf(_open[j], _open[j + 1], fx), fz))


## Which way the surf runs here (towards the shore, flat).
static func shoreward(x: float, z: float) -> Vector2:
	var g := Vector2(_shore(x - GRID, z).x - _shore(x + GRID, z).x, _shore(x, z - GRID).x - _shore(x, z + GRID).x)
	return g.normalized() if g.length_squared() > 0.000001 else Vector2.ZERO


# A slow wander in where along the coast each crest is, so they do not come in as one straight line
# and break in sections. (The shader has the same sum.)
static func _jitter(x: float, z: float) -> float:
	return 1.2 * sin(x * 0.045 + 1.3) * sin(z * 0.037 + 0.4) + 0.8 * sin((x + z) * 0.021 + 2.0)


## The surf at a point (undisplaced), at time t: [height, push along shoreward, phase, height of the
## wave, breaking 0..1, steepness, wavenumber here, weight]. The shader's surf_wave.
static func wave(x: float, z: float, t: float, shore := Vector3.INF) -> PackedFloat32Array:
	if shore == Vector3.INF:
		shore = _shore(x, z)
	var d := shore.x
	var h := shore.y
	var w := shore.z * (1.0 - smoothstep(REACH * 0.6, REACH, d)) * (1.0 - smoothstep(9.0, 16.0, h)) * smoothstep(-6.0, -2.5, d)
	if w <= 0.0:
		return PackedFloat32Array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0])
	var dd := maxf(d, 0.25)
	# (the phase runs with the distance to the shore, squeezed over the shoals: 2 sqrt(d FLAT), the
	# travel time of a wave over a beach sloping evenly, as it slows by the root of the depth)
	var s := dd + FLAT if dd >= FLAT else 2.0 * sqrt(dd * FLAT)
	var squeeze := 1.0 if dd >= FLAT else minf(sqrt(FLAT / dd), 3.0)
	var k0 := TAU / LENGTH
	var phase := -(k0 * s + TAU / PERIOD * t) + _jitter(x, z)
	# (sets: every few waves bigger)
	var sets := 0.8 + 0.3 * sin(phase * 0.27 + 1.0)
	var hh := maxf(h, 0.05)
	var shoal := HEIGHT * sets * pow(clampf(DEEP / maxf(hh, 0.5), 0.6, 3.0), 0.25)
	var limit := BREAK * 0.5 * hh
	var ratio := shoal / maxf(limit, 0.01)
	var breaking := smoothstep(0.85, 1.25, ratio)
	# (broken, it goes on no higher than the limit; at the waterline it still runs up the sand: the swash)
	var a := minf(shoal, maxf(limit * 1.2, SWASH))
	var kl := k0 * squeeze
	var steep := lerpf(0.3, 1.0, smoothstep(0.45, 1.05, ratio))
	var across := minf(steep / kl, 2.5 * a)
	var up := sin(phase)
	var push := across * cos(phase) + breaking * a * 1.4 * pow(maxf(up, 0.0), 3.0)
	return PackedFloat32Array([a * up * w, push * w, phase, a, breaking, across * kl, kl, w])


static func _sech2(v: float) -> float:
	var c := cosh(clampf(v, -20.0, 20.0))
	return 1.0 / (c * c)


## The rogue wave at a point: (height, push along its way, breaking), all 0 with none under way.
static func rogue(x: float, z: float) -> Vector3:
	if not rogue_on:
		return Vector3.ZERO
	var rel := Vector2(x, z) - rogue_at
	var along := rel.dot(rogue_dir) - ROGUE_SPEED * rogue_age
	var across := rel.dot(Vector2(-rogue_dir.y, rogue_dir.x))
	var grow := pow(sin(PI * clampf(rogue_age / ROGUE_LIFE, 0.0, 1.0)), 1.5)
	var lat := exp(-pow(across / ROGUE_WIDTH, 2.0))
	var crest := _sech2(along / ROGUE_LENGTH)
	var trough := _sech2((along - 1.7 * ROGUE_LENGTH) / (1.3 * ROGUE_LENGTH))
	var high := ROGUE_HEIGHT * grow * lat
	var breaking := smoothstep(0.7, 0.92, grow) * lat
	var push := high * (0.3 * crest * -tanh(along / ROGUE_LENGTH) + 0.35 * breaking * pow(crest, 4.0))
	return Vector3(high * (crest - 0.3 * trough), push, breaking)


## The open swell's height at a point (water.gdshader's swell_at), less near the shore.
static func swell(x: float, z: float, t: float) -> float:
	var p := Vector2(x, 200.0 - z)
	var sum := 0.0
	for i in TRAINS.size():
		var train: Vector4 = TRAINS[i]
		var k := TAU / (SWELL_LONG * train.z)
		sum += SWELL_HIGH * train.w * sin(k * Vector2(train.x, train.y).dot(p) - sqrt(9.8 * k) * t + float(i) * 1.7)
	return sum


## Where the surface is at a point (world y), as drawn. The surf and the rogue wave move the water
## sideways as well: one step back along that push finds the water that is over the point now.
static func height(x: float, z: float) -> float:
	var t := clock
	var shore := _shore(x, z)
	var surf := wave(x, z, t, shore)
	var r := rogue(x, z)
	# (no sideways push where a breaker's sheet draws the water: scripts/breakers.gd)
	var pushed := 1.0 - smoothstep(0.0, 0.5, zone_at(x, z))
	var sx := x
	var sz := z
	if surf[7] > 0.0:
		var way := shoreward(x, z)
		sx -= way.x * surf[1] * pushed
		sz -= way.y * surf[1] * pushed
	if r.y != 0.0:
		sx -= rogue_dir.x * r.y * pushed
		sz -= rogue_dir.y * r.y * pushed
	if sx != x or sz != z:
		shore = _shore(sx, sz)
		surf = wave(sx, sz, t, shore)
		r = rogue(sx, sz)
	return Sea.SURFACE + swell(sx, sz, t) * (1.0 - 0.6 * surf[7]) + surf[0] + r.x


## Sends a rogue wave from `at` (x, z) along `heading`: it grows as it comes, is highest halfway
## through its life (ROGUE_SPEED x ROGUE_LIFE / 2 metres on), and fades after.
static func start_rogue(at: Vector2, heading: Vector2) -> void:
	rogue_on = true
	rogue_at = at
	rogue_dir = heading.normalized() if heading.length_squared() > 0.0 else Vector2(1.0, 0.0)
	rogue_age = 0.0


## Moves the rogue wave on (Sea, each frame).
static func advance(delta: float) -> void:
	if rogue_on:
		rogue_age += delta
		if rogue_age >= ROGUE_LIFE:
			rogue_on = false


## The rogue wave's push on something swimming at a point (m/s): along its way under the crest, up
## its front face and down its back (the water's own motion: dh/dt at the surface), fading with depth.
## Gentle: at most ROGUE_PUSH along, 1.8 m/s up the front of the crest.
static func surge(at: Vector3) -> Vector3:
	if not rogue_on:
		return Vector3.ZERO
	var r := rogue(at.x, at.z)
	if r.x == 0.0:
		return Vector3.ZERO
	var top := Sea.SURFACE + r.x
	var fade := exp(-maxf(top - at.y, 0.0) / ROGUE_DECAY)
	if fade < 0.02:
		return Vector3.ZERO
	# (the height a moment later, here: how fast the surface rises)
	var ahead := rogue(at.x - rogue_dir.x * ROGUE_SPEED * 0.1, at.z - rogue_dir.y * ROGUE_SPEED * 0.1)
	var rise := (ahead.x - r.x) / 0.1
	var along := ROGUE_PUSH * clampf(r.x / ROGUE_HEIGHT, -0.4, 1.0)
	return Vector3(rogue_dir.x * along, clampf(rise, -1.5, 1.8), rogue_dir.y * along) * fade


## How much a breaker's sheet stands for the water at a point (the map's fourth channel, bilinear as the
## shader reads it): there the water is not pushed sideways (scripts/breakers.gd).
static func zone_at(x: float, z: float) -> float:
	if _d.is_empty():
		bake()
	var gx := clampf((x - Bay.WEST) / GRID, 0.0, _cols - 1.001)
	var gz := clampf((z - Bay.NORTH) / GRID, 0.0, _rows - 1.001)
	var c := int(gx)
	var r := int(gz)
	var i := r * _cols + c
	var j := i + _cols
	return lerpf(lerpf(_zone[i], _zone[i + 1], gx - c), lerpf(_zone[j], _zone[j + 1], gx - c), gz - r)
