class_name Breakers
extends Node3D
## Curling barrels at a few surf breaks, and the rogue wave's curl (tools/WATER_FX.md, "Barrels").
##
## A heightfield has one height for each x, z, so it cannot curl over. Here each break has its own
## sheet of water: a strip of sections laid along the coast, each section a line of points running in
## to the shore. Every section carries ONE wave at a time (the one between ZONE's entry and the next,
## so the strip never shows two at once), and draws it with the water's own sums (the swell, the surf,
## the rogue wave: exactly what the water mesh would draw) except round the crest, where it takes a
## breaking profile from `profile` (a picture: one row a stage, from a steep face through the lip
## thrown forward, the open tube, the lip landing, to a collapsing mound of white water). The profile
## is blended in by height only, so it never folds through itself. The water mesh is cut away
## (discarded) wherever a sheet stands for it (the shore map's fourth channel, `zone`), and the sheet
## is cut away everywhere else: the two meet at one line on one surface. Both draw with the same
## material, the water's (water.gdshader's breaker path, chosen by the mesh's CUSTOM0.w).
##
## The barrels break at the SITES (a point break at Santa Cruz, west of the wharf, and the long beach
## on the east shore); the break moves along each one as the wave comes in at an angle (the "peel"):
## `tb` is when each section breaks, so at any moment one end is white water, the middle an open
## tube and the far end still standing up. The same sums are here for the CPU (`point`), for the
## spray and for the checks; keep them like water.gdshader's `breaker_point`.

## The shore breaks: where along the coast (from, to: world x, z; the strip follows the line DEPTH_LINE
## metres from the shore between them), the wave height at a full set (m), and when the first and the
## last section break (s after the wave comes into the zone): the break peels from `from` to `to`.
const SITES := [
	{"name": "steamer_lane", "from": Vector2(-50.0, -125.5), "to": Vector2(-22.0, -123.0), "height": 2.6, "peel": Vector2(0.5, 3.1)},
	{"name": "marina", "from": Vector2(88.5, -10.0), "to": Vector2(86.5, 24.0), "height": 2.3, "peel": Vector2(0.5, 3.1)},
]
## The line the strip's sections stand on (m from the shore): the crest's shore distance is worked out
## along each section as if the distance fell evenly from here (true near a smooth coast).
const DEPTH_LINE := 8.0
## Metres between sections.
const STEP := 0.6
## Points down a section: the back piece (the water behind the crest), the breaking piece (the
## profile), the front piece (the water ahead, to the shore).
const POINTS := 64
const PIECE := Vector2i(12, 51)
## How long a break takes, from the face standing up (stage 0) to the lip landing (stage 1) (s); the last
## stage drawn (white water settling back into the water's own bore).
const BREAK_TIME := 2.2
const LAST_STAGE := 1.5
## The zone: a wave comes in at this shore distance (m) and the next one replaces it a wavelength later;
## each section reaches WINDOW wavelengths either side of its crest, so the zone the water mesh gives
## up (ZONE_S, in the surf's s: a wave's travel) is always covered.
const ENTRY := 12.0
const WINDOW := 1.7
## The breaking piece reaches this far behind the crest and ahead of it (wave heights).
const BACK := 1.6
const FRONT := 2.6
## Drawn within this far of the eye (m); the water mesh draws everything beyond.
const SEEN := 110.0
## The rogue wave's sheet: across its width every ROGUE_STEP m out to ROGUE_REACH of its width either
## side; it reaches ROGUE_WINDOW of its lengths either side of the crest. Its curl: stage 0 at this share
## of its life, a stage every ROGUE_STAGE of it.
const ROGUE_STEP := 1.0
const ROGUE_REACH := 1.4
const ROGUE_WINDOW := 6.0
const ROGUE_FROM := 0.42
const ROGUE_STAGE := 0.22

## The profile's keyframes (x shoreward from the crest, y up from the still water, in wave heights): 18
## points from the back end over the crest, the lip and its tip, back under it (the ceiling of the
## tube), down the face and along the floor (the trough under the lip) on past the lip to the front end. Every key has its tip at point 9.
## (Shapes after barrel photographs and tools/art_src/concept_waves_shore.png: a thin lip thrown out
## about one and a half heights, a round tube about as high as it is deep.)
const KEYS := [
	[0.0, [-1.6, -0.2, -1.2, -0.07, -0.85, 0.12, -0.55, 0.33, -0.3, 0.5, -0.1, 0.63, 0.08, 0.69, 0.22, 0.67, 0.33, 0.6, 0.41, 0.5, 0.46, 0.39, 0.5, 0.28, 0.54, 0.17, 0.59, 0.06, 0.75, -0.08, 1.32, -0.21, 1.9, -0.22, 2.6, -0.22]],
	[0.28, [-1.6, -0.2, -1.2, -0.05, -0.85, 0.16, -0.55, 0.4, -0.3, 0.6, -0.08, 0.74, 0.15, 0.83, 0.38, 0.84, 0.57, 0.78, 0.68, 0.68, 0.58, 0.6, 0.45, 0.54, 0.36, 0.42, 0.32, 0.2, 0.42, -0.05, 1.16, -0.21, 1.9, -0.22, 2.6, -0.22]],
	[0.55, [-1.6, -0.2, -1.2, -0.03, -0.85, 0.2, -0.55, 0.45, -0.28, 0.68, 0.0, 0.85, 0.35, 0.93, 0.72, 0.88, 1.02, 0.72, 1.18, 0.45, 1.03, 0.52, 0.72, 0.68, 0.36, 0.6, 0.14, 0.3, 0.24, -0.1, 1.07, -0.21, 1.9, -0.22, 2.6, -0.22]],
	[0.8, [-1.6, -0.2, -1.2, -0.03, -0.85, 0.2, -0.55, 0.46, -0.25, 0.72, 0.05, 0.88, 0.45, 0.95, 0.88, 0.88, 1.25, 0.62, 1.45, 0.14, 1.28, 0.3, 0.92, 0.66, 0.42, 0.7, 0.07, 0.38, 0.13, -0.1, 1.01, -0.21, 1.9, -0.22, 2.6, -0.22]],
	[0.95, [-1.6, -0.2, -1.2, -0.04, -0.85, 0.18, -0.55, 0.42, -0.25, 0.66, 0.05, 0.8, 0.48, 0.86, 0.95, 0.78, 1.38, 0.5, 1.6, -0.12, 1.42, 0.12, 1.02, 0.54, 0.48, 0.6, 0.1, 0.33, 0.14, -0.1, 1.02, -0.21, 1.9, -0.22, 2.6, -0.22]],
	[1.1, [-1.6, -0.2, -1.2, -0.06, -0.85, 0.1, -0.55, 0.28, -0.25, 0.44, 0.05, 0.54, 0.48, 0.58, 0.95, 0.52, 1.35, 0.34, 1.68, -0.1, 1.48, 0.06, 1.08, 0.3, 0.55, 0.36, 0.18, 0.2, 0.16, -0.08, 1.03, -0.21, 1.9, -0.22, 2.6, -0.22]],
	[1.35, [-1.6, -0.18, -1.2, -0.08, -0.85, 0.02, -0.55, 0.12, -0.25, 0.2, 0.05, 0.26, 0.48, 0.29, 0.95, 0.26, 1.35, 0.16, 1.7, -0.06, 1.5, 0.02, 1.1, 0.1, 0.6, 0.12, 0.24, 0.06, 0.2, -0.06, 1.05, -0.21, 1.9, -0.22, 2.6, -0.22]],
]
## How thin and lit through each point is (the lip), and how far inside the tube (the face and ceiling).
const LIP := [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.15, 0.5, 0.85, 1.0, 0.85, 0.4, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0]
const INSIDE := [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.3, 0.9, 1.0, 1.0, 0.6, 0.25, 0.1, 0.0]
## The profile picture: columns along the piece, rows of stages (0 to LAST_STAGE).
const COLUMNS := 64
const ROWS := 48

static var _profile: ImageTexture
static var _pdata := PackedFloat32Array()
static var _sites: Array = []

var _meshes: Array[MeshInstance3D] = []
var _rogue_mesh: MeshInstance3D
var _spray: Array[CPUParticles3D] = []
var _spray_wait := 0.0


# The surf's travel s at a shore distance (Surf.wave's), and back.
static func s_of(d: float) -> float:
	var dd := maxf(d, 0.25)
	return dd + Surf.FLAT if dd >= Surf.FLAT else 2.0 * sqrt(dd * Surf.FLAT)


static func d_of(s: float) -> float:
	return s - Surf.FLAT if s >= 2.0 * Surf.FLAT else s * s / (4.0 * Surf.FLAT)


## The zone's ends in s: the water mesh gives it up between these (full 1.5 inside them).
## (A section's crest is between s_in - LENGTH and s_in, and it reaches WINDOW wavelengths either side,
## so it always covers s_in - WINDOW LENGTH to s_in + (WINDOW - 1) LENGTH; the zone keeps 2 m inside that,
## and fades over 1.5 m outside its ends.)
static func zone_s() -> Vector2:
	var s_in := s_of(ENTRY)
	return Vector2(s_in - WINDOW * Surf.LENGTH + 3.5, s_in + (WINDOW - 1.0) * Surf.LENGTH - 3.5)


# ---------------------------------------------------------------- the profile


## The breaking profile as a picture (made once): x, y (wave heights), lip, inside.
static func profile() -> ImageTexture:
	if _profile:
		return _profile
	var image := Image.create(COLUMNS, ROWS, false, Image.FORMAT_RGBAF)
	_pdata.resize(COLUMNS * ROWS * 4)
	for r in ROWS:
		var stage := LAST_STAGE * r / float(ROWS - 1)
		var pts := _key_points(stage)
		for c in COLUMNS:
			var v := _curve(pts, c / float(COLUMNS - 1))
			image.set_pixel(c, r, Color(v.x, v.y, v.z, v.w))
			var i := (r * COLUMNS + c) * 4
			_pdata[i] = v.x
			_pdata[i + 1] = v.y
			_pdata[i + 2] = v.z
			_pdata[i + 3] = v.w
	_profile = ImageTexture.create_from_image(image)
	return _profile


# The 18 points at a stage: each between its two keys, eased.
static func _key_points(stage: float) -> PackedVector2Array:
	var a: Array = KEYS[0]
	var b: Array = KEYS[0]
	for k in KEYS.size():
		if float(KEYS[k][0]) <= stage:
			a = KEYS[k]
			b = KEYS[mini(k + 1, KEYS.size() - 1)]
	var f := 0.0
	if b != a:
		f = smoothstep(0.0, 1.0, (stage - float(a[0])) / (float(b[0]) - float(a[0])))
	var out := PackedVector2Array()
	var pa: Array = a[1]
	var pb: Array = b[1]
	for i in 18:
		out.append(Vector2(lerpf(pa[i * 2], pb[i * 2], f), lerpf(pa[i * 2 + 1], pb[i * 2 + 1], f)))
	return out


# A point along the 18 (Catmull-Rom through them), t 0..1: x, y, lip, inside.
static func _curve(pts: PackedVector2Array, t: float) -> Vector4:
	var n := pts.size()
	var at := clampf(t, 0.0, 1.0) * (n - 1)
	var i := mini(int(at), n - 2)
	var f := at - i
	var p0 := pts[maxi(i - 1, 0)]
	var p1 := pts[i]
	var p2 := pts[i + 1]
	var p3 := pts[mini(i + 2, n - 1)]
	var p := 0.5 * ((2.0 * p1) + (-p0 + p2) * f + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * f * f + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * f * f * f)
	return Vector4(p.x, p.y, lerpf(LIP[i], LIP[i + 1], f), lerpf(INSIDE[i], INSIDE[i + 1], f))


## The profile at a share t of the breaking piece and a stage, read from the picture as the shader
## reads it (bilinear between texel middles).
static func profile_at(t: float, stage: float) -> Vector4:
	profile()
	var gx := clampf(t, 0.0, 1.0) * (COLUMNS - 1)
	var gy := clampf(stage / LAST_STAGE, 0.0, 1.0) * (ROWS - 1)
	var c := mini(int(gx), COLUMNS - 2)
	var r := mini(int(gy), ROWS - 2)
	var fx := gx - c
	var fy := gy - r
	var out := Vector4.ZERO
	for k in 4:
		var a := _pdata[(r * COLUMNS + c) * 4 + k]
		var b := _pdata[(r * COLUMNS + c + 1) * 4 + k]
		var cc := _pdata[((r + 1) * COLUMNS + c) * 4 + k]
		var d := _pdata[((r + 1) * COLUMNS + c + 1) * 4 + k]
		out[k] = lerpf(lerpf(a, b, fx), lerpf(cc, d, fx), fy)
	return out


## How much of the breaking shape there is at a stage (none before the face stands up, none once the
## white water has settled into the water's own bore), and along the piece (none at its two ends).
static func stage_weight(stage: float) -> float:
	return smoothstep(-0.05, 0.2, stage) * (1.0 - smoothstep(1.2, 1.5, stage))


static func piece_weight(t: float) -> float:
	return smoothstep(0.0, 0.05, t) * (1.0 - smoothstep(0.94, 1.0, t))


# ---------------------------------------------------------------- the sites


## Each site's sections (made once, from Bay: never from Surf, whose map is baked from these):
## {name, height, points: [base (x, z)], ways: [shoreward], u: [m along], tb: [s], fade: [0..1], long}.
static func sites() -> Array:
	if not _sites.is_empty():
		return _sites
	# (`-- --no-breakers` leaves them out, for costs and pictures: the water is drawn as before)
	if OS.get_cmdline_user_args().has("--no-breakers"):
		return _sites
	for site: Dictionary in SITES:
		var bases := PackedVector2Array()
		var from: Vector2 = site.from
		var to: Vector2 = site.to
		var p := _onto_line(from)
		var guard := 0
		while guard < 400:
			guard += 1
			bases.append(p)
			if p.distance_to(to) < STEP * 1.5:
				break
			var way := _shoreward(p)
			var along := Vector2(-way.y, way.x)
			if along.dot(to - p) < 0.0:
				along = -along
			p = _onto_line(p + along * STEP)
		# (each section's way in to the shore: the shore's own way there, smoothed over its neighbours,
		# so that the sections do not cross)
		var ways := PackedVector2Array()
		var u := PackedFloat32Array()
		var run := 0.0
		for i in bases.size():
			var sum := Vector2.ZERO
			for k in range(-4, 5):
				sum += _shoreward(bases[clampi(i + k, 0, bases.size() - 1)])
			ways.append(sum.normalized())
			if i > 0:
				run += bases[i].distance_to(bases[i - 1])
			u.append(run)
		var tb := PackedFloat32Array()
		var fade := PackedFloat32Array()
		var peel: Vector2 = site.peel
		for i in bases.size():
			tb.append(lerpf(peel.x, peel.y, u[i] / run))
			fade.append(smoothstep(2.5, 8.0, u[i]) * smoothstep(2.5, 8.0, run - u[i]))
		var lo := Vector2(INF, INF)
		var hi := Vector2(-INF, -INF)
		for b in bases:
			lo = lo.min(b)
			hi = hi.max(b)
		_sites.append({"name": site.name, "height": site.height, "points": bases, "ways": ways, "u": u, "tb": tb, "fade": fade, "long": run,
				"box": Rect2(lo - Vector2(30.0, 30.0), hi - lo + Vector2(60.0, 60.0))})
	return _sites


# The point on the DEPTH_LINE nearest a point (moved along the shore's way).
static func _onto_line(p: Vector2) -> Vector2:
	for k in 6:
		p += _shoreward(p) * (Bay.shore_distance(p) - DEPTH_LINE)
	return p


static func _shoreward(p: Vector2) -> Vector2:
	var g := Vector2(Bay.shore_distance(p - Vector2(2.0, 0.0)) - Bay.shore_distance(p + Vector2(2.0, 0.0)),
			Bay.shore_distance(p - Vector2(0.0, 2.0)) - Bay.shore_distance(p + Vector2(0.0, 2.0)))
	return g.normalized() if g.length_squared() > 0.000001 else Vector2(1.0, 0.0)


## How much of the water at a point (x, z; `d` its shore distance) a breaker's sheet stands for (Surf
## bakes it into its map's fourth channel; the water mesh is cut away where it is over 0.5).
static func zone(p: Vector2, d: float) -> float:
	var band := zone_s()
	var s := s_of(d)
	var across := smoothstep(band.x - 1.5, band.x, s) * (1.0 - smoothstep(band.y, band.y + 1.5, s))
	if across <= 0.0:
		return 0.0
	var best := 0.0
	for site: Dictionary in sites():
		if not (site.box as Rect2).has_point(p):
			continue
		var pts: PackedVector2Array = site.points
		var ways: PackedVector2Array = site.ways
		# (the section whose line passes nearest the point; then how far along the strip that is)
		var near := -1
		var off := INF
		for i in pts.size():
			var rel := p - pts[i]
			if absf(rel.dot(ways[i])) > 40.0:
				continue
			var side := absf(rel.dot(Vector2(-ways[i].y, ways[i].x)))
			if side < off:
				off = side
				near = i
		if near < 0 or off > STEP * 2.0:
			continue
		var u: float = site.u[near]
		var long: float = site.long
		best = maxf(best, smoothstep(0.8, 2.0, u) * smoothstep(0.8, 2.0, long - u))
	return best * across


# ---------------------------------------------------------------- the sums (the shader's)


## The crest a shore section carries now: its s, how long since it came in (s), its phase.
static func crest(base: Vector2, way: Vector2, t: float) -> Vector3:
	var k0 := TAU / Surf.LENGTH
	var om := TAU / Surf.PERIOD
	var s_in := s_of(ENTRY)
	var j := Surf._jitter(base.x, base.y)
	var sc := s_in
	for n in 3:
		var s0 := (j - om * t - PI * 0.5) / k0
		sc = s_in - fposmod(s_in - s0, Surf.LENGTH)
		if n < 2:
			var q := base + (DEPTH_LINE - d_of(sc)) * way
			j = Surf._jitter(q.x, q.y)
	var tau := (s_in - sc) / Surf.LENGTH * Surf.PERIOD
	return Vector3(sc, tau, -(k0 * sc + om * t) + j)


## The water's own surface at an undisplaced point (water.gdshader's surface_at): its place (world),
## and the level the breaking shape rides on (the swell and the rogue wave).
static func water_at(still: Vector2, t: float, fine: float) -> Array:
	var surf := Surf.wave(still.x, still.y, t)
	var r := Surf.rogue(still.x, still.y)
	var level := Surf.swell(still.x, still.y, t) * (1.0 - 0.6 * surf[7]) + r.x
	var xz := still
	var pushed := 1.0 - smoothstep(0.0, 0.5, Surf.zone_at(still.x, still.y))
	if surf[7] > 0.0:
		xz += Surf.shoreward(still.x, still.y) * surf[1] * fine * pushed
	xz += Surf.rogue_dir * r.y * pushed
	return [Vector3(xz.x, Sea.SURFACE + level + surf[0] * fine, xz.y), level]


## A point of a shore section at v (0..1 down it), at time t (water.gdshader's breaker_point): its place
## (world) and [weight of the breaking shape, stage, lip, inside], and the undisplaced water it stands for.
static func point(site: Dictionary, i: int, v: float, t: float, fine := 1.0) -> Dictionary:
	var base: Vector2 = site.points[i]
	var way: Vector2 = site.ways[i]
	var cr := crest(base, way, t)
	var sets := 0.8 + 0.3 * sin(cr.z * 0.27 + 1.0)
	var hh: float = site.height * sets / 1.1
	var stage: float = (cr.y - site.tb[i]) / BREAK_TIME
	var dc := d_of(cr.x)
	var win := WINDOW * Surf.LENGTH
	var vb := PIECE.x / float(POINTS - 1)
	var vf := PIECE.y / float(POINTS - 1)
	var d: float
	var b := Vector4.ZERO
	var wd := 0.0
	var info := Vector4(0.0, stage, 0.0, 0.0)
	if v < vb:
		d = d_of(lerpf(cr.x + win, s_of(dc + BACK * hh), v / vb))
	elif v > vf:
		d = d_of(lerpf(s_of(maxf(dc - FRONT * hh, 0.25)), maxf(cr.x - win, s_of(0.25)), (v - vf) / (1.0 - vf)))
	else:
		var tt := (v - vb) / (vf - vb)
		b = profile_at(tt, maxf(stage, 0.0))
		d = dc - b.x * hh
		wd = piece_weight(tt) * stage_weight(stage) * float(site.fade[i]) * fine
		info = Vector4(wd, stage, b.z, b.w)
	var still := base + (DEPTH_LINE - d) * way
	var w: Array = water_at(still, t, fine)
	var g: Vector3 = w[0]
	var bp := Vector3(still.x, Sea.SURFACE + float(w[1]) + b.y * hh, still.y)
	# (the breaking shape blended in by height alone, where the water is not pushed sideways: so it never
	# folds through itself)
	var at := Vector3(g.x, lerpf(g.y, bp.y, wd), g.z)
	return {"at": at, "info": info, "still": still, "height": hh}


# ---------------------------------------------------------------- the node


func _ready() -> void:
	var water: ShaderMaterial = get_parent().get(&"_water")
	for site: Dictionary in sites():
		var mesh := MeshInstance3D.new()
		mesh.name = "Breaker_%s" % site.name
		mesh.mesh = _site_mesh(site)
		mesh.material_override = water
		mesh.position = Vector3(0.0, Sea.SURFACE, 0.0)
		mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		var pts: PackedVector2Array = site.points
		var lo := Vector2(INF, INF)
		var hi := Vector2(-INF, -INF)
		for p in pts:
			lo = lo.min(p)
			hi = hi.max(p)
		mesh.custom_aabb = AABB(Vector3(lo.x - 40.0, -8.0, lo.y - 40.0), Vector3(hi.x - lo.x + 80.0, 16.0, hi.y - lo.y + 80.0))
		add_child(mesh)
		_meshes.append(mesh)
		_spray.append(_make_spray())
	_rogue_mesh = MeshInstance3D.new()
	_rogue_mesh.name = "Breaker_rogue"
	_rogue_mesh.mesh = _rogue_sheet()
	_rogue_mesh.material_override = water
	_rogue_mesh.position = Vector3(0.0, Sea.SURFACE, 0.0)
	_rogue_mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_rogue_mesh.custom_aabb = AABB(Vector3(-400.0, -10.0, -400.0), Vector3(800.0, 20.0, 800.0))
	_rogue_mesh.visible = false
	add_child(_rogue_mesh)


## What the water's material needs for the breakers (Sea calls it with Surf.dress).
static func dress(material: ShaderMaterial) -> void:
	material.set_shader_parameter(&"breaker_profile", profile())
	material.set_shader_parameter(&"breaker_a", Vector4(BREAK_TIME, LAST_STAGE, s_of(ENTRY), WINDOW))
	var vb := PIECE.x / float(POINTS - 1)
	var vf := PIECE.y / float(POINTS - 1)
	material.set_shader_parameter(&"breaker_b", Vector4(BACK, FRONT, vb, vf))
	material.set_shader_parameter(&"breaker_rogue", Vector4(ROGUE_FROM, ROGUE_STAGE, ROGUE_WINDOW, 0.0))
	material.set_shader_parameter(&"breaker_seen", SEEN)


# A site's strip: POINTS points down each section, the sections side by side. Each point carries its
# section's base (VERTEX, x and z), its share down the section and the section's fade (UV), its way in
# (UV2), and (DEPTH_LINE, tb, height, 7: a shore breaker) in CUSTOM0.
func _site_mesh(site: Dictionary) -> ArrayMesh:
	var pts: PackedVector2Array = site.points
	var ways: PackedVector2Array = site.ways
	var verts := PackedVector3Array()
	var uvs := PackedVector2Array()
	var uv2s := PackedVector2Array()
	var custom := PackedFloat32Array()
	for i in pts.size():
		for j in POINTS:
			verts.append(Vector3(pts[i].x, 0.0, pts[i].y))
			uvs.append(Vector2(j / float(POINTS - 1), site.fade[i]))
			uv2s.append(ways[i])
			custom.append_array(PackedFloat32Array([DEPTH_LINE, site.tb[i], site.height, 7.0]))
	return _strip(verts, uvs, uv2s, custom, pts.size(), _faces_up(pts, ways))


# The rogue wave's sheet: sections across its way, every ROGUE_STEP m; CUSTOM0 (across, 0, 0, 9).
func _rogue_sheet() -> ArrayMesh:
	var n := int(ROGUE_REACH * Surf.ROGUE_WIDTH * 2.0 / ROGUE_STEP) + 1
	var verts := PackedVector3Array()
	var uvs := PackedVector2Array()
	var uv2s := PackedVector2Array()
	var custom := PackedFloat32Array()
	for i in n:
		var across := -ROGUE_REACH * Surf.ROGUE_WIDTH + i * ROGUE_STEP
		for j in POINTS:
			verts.append(Vector3.ZERO)
			uvs.append(Vector2(j / float(POINTS - 1), 1.0))
			uv2s.append(Vector2(1.0, 0.0))
			custom.append_array(PackedFloat32Array([across, 0.0, 0.0, 9.0]))
	# (laid out as on a heading of +x, the sections stepping along +z, for the faces' order)
	var pts := PackedVector2Array()
	var ways := PackedVector2Array()
	for i in n:
		pts.append(Vector2(0.0, i))
		ways.append(Vector2(1.0, 0.0))
	# (the rogue's sections run along -its way's left, (-way.y, way.x): +z for a way of +x)
	return _strip(verts, uvs, uv2s, custom, n, _faces_up(pts, ways))


# Which way round the triangles go so that they face up (Godot's front faces: clockwise as seen) on
# still water: section i+1 lies along the strip from section i, each section runs in along its way.
static func _faces_up(pts: PackedVector2Array, ways: PackedVector2Array) -> bool:
	var a := Vector3(pts[0].x, 0.0, pts[0].y)
	var b := Vector3(pts[1].x, 0.0, pts[1].y)
	var c := a + Vector3(ways[0].x, 0.0, ways[0].y)
	return (b - a).cross(c - a).y < 0.0


static func _strip(verts: PackedVector3Array, uvs: PackedVector2Array, uv2s: PackedVector2Array, custom: PackedFloat32Array, sections: int, up: bool) -> ArrayMesh:
	var indices := PackedInt32Array()
	for i in sections - 1:
		for j in POINTS - 1:
			var a := i * POINTS + j
			var b := (i + 1) * POINTS + j
			var c := a + 1
			var d := b + 1
			if up:
				indices.append_array([a, b, c, c, b, d])
			else:
				indices.append_array([a, c, b, c, d, b])
	var normals := PackedVector3Array()
	var colours := PackedColorArray()
	var tangents := PackedFloat32Array()
	for v in verts:
		normals.append(Vector3.UP)
		colours.append(Color(0.0, 1.0, 0.0))
		tangents.append_array(PackedFloat32Array([1.0, 0.0, 0.0, 1.0]))
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_TANGENT] = tangents
	arrays[Mesh.ARRAY_COLOR] = colours
	arrays[Mesh.ARRAY_TEX_UV] = uvs
	arrays[Mesh.ARRAY_TEX_UV2] = uv2s
	arrays[Mesh.ARRAY_CUSTOM0] = custom
	arrays[Mesh.ARRAY_INDEX] = indices
	var mesh := ArrayMesh.new()
	var format := Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {}, format)
	return mesh


## Spray: one stream of drops a site, fed points along the lips each few frames.
func _make_spray() -> CPUParticles3D:
	var p := CPUParticles3D.new()
	p.name = "BreakerSpray"
	p.amount = 320
	p.lifetime = 1.1
	p.local_coords = false
	p.emitting = false
	p.emission_shape = CPUParticles3D.EMISSION_SHAPE_DIRECTED_POINTS
	p.emission_points = PackedVector3Array([Vector3.ZERO])
	p.emission_normals = PackedVector3Array([Vector3.UP])
	p.spread = 18.0
	p.initial_velocity_min = 2.5
	p.initial_velocity_max = 6.0
	p.gravity = Vector3(0.0, -9.0, 0.0)
	p.damping_min = 0.6
	p.damping_max = 1.4
	p.scale_amount_min = 0.5
	p.scale_amount_max = 1.3
	var curve := Curve.new()
	curve.add_point(Vector2(0.0, 0.6))
	curve.add_point(Vector2(0.25, 1.0))
	curve.add_point(Vector2(1.0, 0.0))
	p.scale_amount_curve = curve
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = Color(0.93, 0.98, 0.97)
	var drop := SphereMesh.new()
	drop.radius = 0.045
	drop.height = 0.09
	drop.radial_segments = 6
	drop.rings = 3
	drop.material = mat
	p.mesh = drop
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(p)
	return p


func _process(delta: float) -> void:
	var cam := get_viewport().get_camera_3d()
	if cam == null:
		return
	var eye := Vector2(cam.global_position.x, cam.global_position.z)
	var all := sites()
	for k in all.size():
		var site: Dictionary = all[k]
		var pts: PackedVector2Array = site.points
		var near := INF
		for i in range(0, pts.size(), 8):
			near = minf(near, eye.distance_to(pts[i]))
		_meshes[k].visible = near < SEEN + 40.0
		_spray[k].visible = near < 70.0
	_rogue_mesh.visible = Surf.rogue_on
	_spray_wait -= delta
	if _spray_wait <= 0.0:
		_spray_wait = 0.1
		for k in all.size():
			_feed_spray(all[k], _spray[k])


# The spray's points: off the tip of each lip being thrown (forward and up), and up off the water where a
# lip lands (the curtain's splash), along the strip every few sections.
func _feed_spray(site: Dictionary, spray: CPUParticles3D) -> void:
	if not spray.visible:
		spray.emitting = false
		return
	var t := Surf.clock
	var pts: PackedVector2Array = site.points
	var at := PackedVector3Array()
	var ways := PackedVector3Array()
	var tip_v := (PIECE.x + (PIECE.y - PIECE.x) * 9.0 / 17.0) / float(POINTS - 1)
	var top_v := (PIECE.x + (PIECE.y - PIECE.x) * 6.5 / 17.0) / float(POINTS - 1)
	for i in range(3, pts.size() - 3, 2):
		if float(site.fade[i]) < 0.5:
			continue
		var cr := crest(pts[i], site.ways[i], t)
		var stage: float = (cr.y - float(site.tb[i])) / BREAK_TIME
		if stage < 0.25 or stage > 1.12:
			continue
		var tip := point(site, i, tip_v, t)
		var way: Vector2 = site.ways[i]
		var p: Vector3 = tip.at
		if stage < 0.85:
			# (thrown off the lip as it pitches: forward and up)
			at.append(p)
			ways.append(Vector3(way.x * 0.8, 0.6, way.y * 0.8).normalized())
			# (and blown back off the top of the crest, as an offshore wind does)
			var top: Vector3 = point(site, i, top_v, t).at
			at.append(top + Vector3(0.0, 0.1, 0.0))
			ways.append(Vector3(-way.x * 0.7, 1.0, -way.y * 0.7).normalized())
		else:
			# (where it lands: a burst straight up, and back)
			at.append(p + Vector3(0.0, 0.1, 0.0))
			ways.append(Vector3(-way.x * 0.35, 1.0, -way.y * 0.35).normalized())
	if at.is_empty():
		spray.emitting = false
		return
	spray.emission_points = at
	spray.emission_normals = ways
	spray.emitting = true
