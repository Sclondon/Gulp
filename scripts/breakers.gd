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
## (Second round, 2026-11-18: both strips longer and both waves taller, so a tube spins along the beach
## for longer and reads from further off; the same peel times over a longer strip are a faster peel,
## 11 and 13 m/s, as a makeable point break's is.)
const SITES := [
	{"name": "steamer_lane", "from": Vector2(-58.0, -126.5), "to": Vector2(-20.0, -123.0), "height": 3.0, "peel": Vector2(0.4, 3.9)},
	{"name": "marina", "from": Vector2(88.8, -18.0), "to": Vector2(86.3, 28.0), "height": 2.9, "peel": Vector2(0.4, 3.9)},
]
## The shoulders: the wave is lower towards the strip's ends (to this share of its height), over this far
## from the end still to break (the shoulder, m) and from the end that broke first (the white water).
const SHOULDER_LOW := 0.4
const SHOULDER := Vector2(14.0, 7.0)
## The line the strip's sections stand on (m from the shore): the crest's shore distance is worked out
## along each section as if the distance fell evenly from here (true near a smooth coast).
const DEPTH_LINE := 8.0
## Metres between sections.
const STEP := 0.6
## Points down a section: the back piece (the water behind the crest), the breaking piece (the
## profile), the front piece (the water ahead, to the shore).
## (96 points, 72 of them round the curl: with 40 the lip's tip was a few points and its edge hard.)
const POINTS := 96
const PIECE := Vector2i(12, 83)
## How long a break takes, from the face standing up (stage 0) to the lip landing (stage 1) (s); the last
## stage drawn (white water settling back into the water's own bore). (A section carries its wave for one
## period, 7 s: the last section's peel time plus LAST_STAGE breaks must fit in it.)
const BREAK_TIME := 2.0
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
## (Shapes after barrel photographs and tools/art_src/concept_waves_shore.png. Second round: a taller
## face (the crest 1.2 heights up), a lip with real thickness (a quarter to a third of a height, Teahupo'o's
## is half) thrown out 1.6 to 1.85 heights, and a round tube, about 1.4 times as wide as it is high
## ("round" is 1 to 2), so it reads as a big dark hollow. The tip never quite meets the water below it:
## the profile must never cross itself, checks.gd counts it.)
const KEYS := [
	[0.0, [-1.6, -0.2, -1.15, -0.05, -0.8, 0.15, -0.5, 0.38, -0.25, 0.58, -0.05, 0.72, 0.12, 0.78, 0.27, 0.76, 0.38, 0.68, 0.45, 0.56, 0.48, 0.45, 0.5, 0.34, 0.53, 0.22, 0.57, 0.1, 0.62, -0.02, 0.75, -0.13, 1.3, -0.22, 2.6, -0.22]],
	[0.28, [-1.6, -0.2, -1.15, -0.03, -0.8, 0.2, -0.5, 0.45, -0.25, 0.7, 0.0, 0.88, 0.28, 0.98, 0.55, 0.95, 0.76, 0.84, 0.88, 0.66, 0.78, 0.6, 0.6, 0.6, 0.45, 0.53, 0.36, 0.38, 0.33, 0.18, 0.38, -0.06, 1.1, -0.22, 2.6, -0.22]],
	[0.55, [-1.6, -0.2, -1.15, -0.02, -0.8, 0.24, -0.5, 0.52, -0.22, 0.8, 0.08, 1.02, 0.45, 1.12, 0.88, 1.06, 1.22, 0.84, 1.42, 0.48, 1.25, 0.56, 0.96, 0.8, 0.55, 0.83, 0.25, 0.66, 0.1, 0.32, 0.12, -0.1, 1.0, -0.24, 2.6, -0.22]],
	[0.8, [-1.6, -0.2, -1.15, 0.0, -0.8, 0.28, -0.5, 0.58, -0.2, 0.88, 0.12, 1.1, 0.55, 1.2, 1.02, 1.08, 1.42, 0.74, 1.62, 0.1, 1.42, 0.4, 1.06, 0.8, 0.58, 0.9, 0.22, 0.72, 0.04, 0.36, 0.06, -0.12, 0.9, -0.26, 2.6, -0.24]],
	[0.95, [-1.6, -0.2, -1.15, -0.01, -0.8, 0.26, -0.5, 0.54, -0.2, 0.82, 0.12, 1.02, 0.55, 1.1, 1.05, 0.98, 1.5, 0.62, 1.74, -0.06, 1.52, 0.26, 1.12, 0.7, 0.62, 0.8, 0.24, 0.64, 0.07, 0.3, 0.09, -0.12, 1.3, -0.16, 2.6, -0.22]],
	[1.1, [-1.6, -0.2, -1.15, -0.04, -0.8, 0.16, -0.5, 0.38, -0.2, 0.56, 0.15, 0.68, 0.55, 0.72, 1.0, 0.66, 1.45, 0.46, 1.8, -0.02, 1.6, 0.12, 1.2, 0.36, 0.75, 0.42, 0.38, 0.34, 0.2, 0.16, 0.24, -0.06, 1.6, -0.1, 2.6, -0.2]],
	[1.35, [-1.6, -0.18, -1.15, -0.08, -0.8, 0.02, -0.5, 0.12, -0.2, 0.2, 0.15, 0.26, 0.55, 0.29, 1.0, 0.27, 1.45, 0.18, 1.85, -0.04, 1.65, 0.04, 1.25, 0.12, 0.85, 0.15, 0.5, 0.12, 0.3, 0.04, 0.3, -0.06, 1.6, -0.1, 2.6, -0.2]],
]
## How thin and lit through each point is (the lip), and how far inside the tube (the face and ceiling).
const LIP := [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.45, 0.85, 1.0, 0.85, 0.45, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0]
const INSIDE := [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.3, 0.9, 1.0, 1.0, 0.8, 0.4, 0.1, 0.0]
## The profile picture: columns along the piece, rows of stages (0 to LAST_STAGE).
const COLUMNS := 128
const ROWS := 48

static var _profile: ImageTexture
static var _pdata := PackedFloat32Array()
static var _sites: Array = []

var _meshes: Array[MeshInstance3D] = []
var _rogue_mesh: MeshInstance3D
var _spray: Array[Dictionary] = []
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
## {name, height, heights: [each section's, m], points: [base (x, z)], ways: [shoreward], u: [m along],
## tb: [s], fade: [0..1], long}.
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
		# (to the point on the line nearest `to`, which need not be on it; stopping once past it)
		var end := _onto_line(to)
		var heading := (end - p).normalized()
		var guard := 0
		while guard < 400:
			guard += 1
			bases.append(p)
			if p.distance_to(end) < STEP * 1.5 or heading.dot(end - p) < 0.0:
				break
			var way := _shoreward(p)
			var along := Vector2(-way.y, way.x)
			if along.dot(end - p) < 0.0:
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
		var heights := PackedFloat32Array()
		var peel: Vector2 = site.peel
		for i in bases.size():
			tb.append(lerpf(peel.x, peel.y, u[i] / run))
			# (the breaking shape fades out only in the last few metres; before that the wave itself gets
			# lower towards each end, the shoulder still to break and the white water behind, so a tube
			# tapers away along the beach instead of flattening into a twisted sliver)
			fade.append(smoothstep(0.8, 3.5, u[i]) * smoothstep(0.8, 3.5, run - u[i]))
			var taper := smoothstep(0.0, SHOULDER.x, run - u[i]) * smoothstep(0.0, SHOULDER.y, u[i])
			heights.append(float(site.height) * lerpf(SHOULDER_LOW, 1.0, taper))
		var lo := Vector2(INF, INF)
		var hi := Vector2(-INF, -INF)
		for b in bases:
			lo = lo.min(b)
			hi = hi.max(b)
		_sites.append({"name": site.name, "height": site.height, "heights": heights, "points": bases, "ways": ways, "u": u, "tb": tb, "fade": fade, "long": run,
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


## A breaker's share of its site's height with the sets (its crest's phase): 0.67 to 1 (the surf's own sets
## go lower, but a small set's barrel was too small to read; the shader's breaker_point has the same).
static func sets(phase: float) -> float:
	return (0.92 + 0.18 * sin(phase * 0.27 + 1.0)) / 1.1


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
	var hh: float = float(site.heights[i]) * sets(cr.z)
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


## The water's top over a point near a break, for something at height y (Sea.surface_height): where a
## lip curls over, the water there has three faces one above the other (the lip's top, its underside, the
## tube's floor); something in the tube is in air above the floor, something in the lip is under its top.
## So: the face that is the surface for y (the first above it, or the floor when the first above it is
## the lip's underside). NAN where no breaking shape stands (the caller uses the water's own sums).
## (Cheap: a box test per break, then one section's profile row, read off the profile picture's data.)
static func surface(x: float, z: float, y: float, t: float) -> float:
	var p := Vector2(x, z)
	for site: Dictionary in sites():
		if not (site.box as Rect2).has_point(p):
			continue
		var pts: PackedVector2Array = site.points
		var ways: PackedVector2Array = site.ways
		# (the nearest section, coarse then fine: the strip is in order along the coast)
		var near := -1
		var off := INF
		for i in range(0, pts.size(), 6):
			var rel := p - pts[i]
			var side := absf(rel.dot(Vector2(-ways[i].y, ways[i].x)))
			if side < off and absf(rel.dot(ways[i])) < 30.0:
				off = side
				near = i
		if near < 0:
			continue
		for i in range(maxi(near - 6, 0), mini(near + 7, pts.size())):
			var rel := p - pts[i]
			var side := absf(rel.dot(Vector2(-ways[i].y, ways[i].x)))
			if side < off:
				off = side
				near = i
		if off > STEP:
			continue
		var base: Vector2 = pts[near]
		var way: Vector2 = ways[near]
		var cr := crest(base, way, t)
		var hh: float = float(site.heights[near]) * sets(cr.z)
		var stage: float = (cr.y - float(site.tb[near])) / BREAK_TIME
		var wd := stage_weight(stage) * float(site.fade[near])
		if wd <= 0.01 or stage < 0.0:
			return NAN
		var d := DEPTH_LINE - (p - base).dot(way)
		var px := (d_of(cr.x) - d) / hh
		# (outside the breaking piece, or far under it, the water's own sums do: most asks end here)
		if px < -BACK or px > FRONT or y < Sea.SURFACE - 0.6 * hh - 0.5:
			return NAN
		# (the profile's row at this stage, and where its line crosses px)
		var gy := clampf(stage / LAST_STAGE, 0.0, 1.0) * (ROWS - 1)
		var r := mini(int(gy), ROWS - 2)
		var fy := gy - r
		profile()
		var ys := PackedFloat32Array()
		var ws := PackedFloat32Array()
		var prev := Vector3.INF
		for c in COLUMNS:
			var i0 := (r * COLUMNS + c) * 4
			var i1 := ((r + 1) * COLUMNS + c) * 4
			var q := Vector3(lerpf(_pdata[i0], _pdata[i1], fy), lerpf(_pdata[i0 + 1], _pdata[i1 + 1], fy), c / float(COLUMNS - 1))
			if prev != Vector3.INF and (prev.x - px) * (q.x - px) <= 0.0 and prev.x != q.x:
				var f := (px - prev.x) / (q.x - prev.x)
				ys.append(lerpf(prev.y, q.y, f))
				ws.append(piece_weight(lerpf(prev.z, q.z, f)))
			prev = q
		if ys.is_empty():
			return NAN
		var w: Array = water_at(base + (DEPTH_LINE - d) * way, t, 1.0)
		var plain: float = (w[0] as Vector3).y
		var level := Sea.SURFACE + float(w[1])
		# (the faces from the top down: the lip's top, its underside, the floor; mixed as the shader mixes)
		var faces := PackedFloat32Array()
		for k in ys.size():
			faces.append(lerpf(plain, level + ys[k] * hh, wd * ws[k]))
		faces.sort()
		faces.reverse()
		# (from the bottom: water to faces[n-1], air to faces[n-2], water to faces[n-3]...)
		for k in range(faces.size() - 1, -1, -1):
			if faces[k] > y:
				var from_bottom := faces.size() - 1 - k
				if from_bottom % 2 == 1:
					return faces[k + 1]
				return faces[k]
		return faces[0]
	return NAN


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
		_spray.append({"plume": _make_stream("plume"), "burst": _make_stream("burst"), "curtain": _make_stream("curtain")})
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
	material.set_shader_parameter(&"breaker_points", float(POINTS))


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
			custom.append_array(PackedFloat32Array([DEPTH_LINE, site.tb[i], site.heights[i], 7.0]))
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


## Spray (second round: painted puffs, not drops; tools/WATER_FX.md, "Barrels"). Three streams a break, each
## one CPUParticles3D of billboards cut from one small painted puff (`puff`), fed points along the lips
## every SPRAY_EVERY s from the CPU copy of the sums: the PLUME, mist feathering back off the crest as an
## offshore wind blows it (the tell of a breaking wave from out at sea) and spray thrown off the lip as it
## pitches; the BURST, an explosion of white where the lip lands; and the CURTAIN, a cloud of bubbles
## under the water where it lands, for the view from below.
const SPRAY_EVERY := 0.1
const SPRAY_SEEN := 90.0

static var _puff: ImageTexture


## The puff: a few round lobes with an edge cut by noise and the light in three flat tones from above,
## white over a blue-grey (a brush's dab, as the concept's spray is), made once.
static func puff() -> ImageTexture:
	if _puff:
		return _puff
	var n := 64
	var image := Image.create(n, n, false, Image.FORMAT_RGBA8)
	var noise := FastNoiseLite.new()
	noise.seed = 11
	noise.frequency = 0.09
	var lobes := [Vector3(0.5, 0.56, 0.3), Vector3(0.31, 0.62, 0.19), Vector3(0.69, 0.6, 0.2), Vector3(0.42, 0.36, 0.2), Vector3(0.62, 0.38, 0.17)]
	for y in n:
		for x in n:
			var p := Vector2((x + 0.5) / n, (y + 0.5) / n)
			var field := 0.0
			for l: Vector3 in lobes:
				field = maxf(field, 1.0 - p.distance_to(Vector2(l.x, l.y)) / l.z)
			var edge := field + (noise.get_noise_2d(x, y) * 0.5) * 0.45
			var alpha := smoothstep(0.0, 0.1, edge)
			# (lit from above: three flat tones, the shade low and on the right)
			var light := (1.0 - p.y) * 0.6 + (1.0 - p.x) * 0.15 + field * 0.5 + noise.get_noise_2d(x * 2.0 + 40.0, y * 2.0) * 0.15
			var tone := 0.8 if light < 0.45 else (0.92 if light < 0.7 else 1.0)
			image.set_pixel(x, y, Color(tone * 0.95, tone * 0.98, tone, alpha))
	image.generate_mipmaps()
	_puff = ImageTexture.create_from_image(image)
	return _puff


func _make_stream(stream: String) -> CPUParticles3D:
	var p := CPUParticles3D.new()
	p.name = "Breaker_" + stream
	p.local_coords = false
	p.emitting = false
	p.emission_shape = CPUParticles3D.EMISSION_SHAPE_DIRECTED_POINTS
	p.emission_points = PackedVector3Array([Vector3.ZERO])
	p.emission_normals = PackedVector3Array([Vector3.UP])
	p.angle_min = -180.0
	p.angle_max = 180.0
	p.angular_velocity_min = -40.0
	p.angular_velocity_max = 40.0
	var size := 1.0
	var curve := Curve.new()
	var ramp := Gradient.new()
	match stream:
		"plume":
			p.amount = 400
			p.lifetime = 1.3
			p.spread = 18.0
			p.initial_velocity_min = 2.5
			p.initial_velocity_max = 6.0
			p.gravity = Vector3(0.0, -1.0, 0.0)
			p.damping_min = 0.8
			p.damping_max = 1.8
			p.scale_amount_min = 0.45
			p.scale_amount_max = 1.0
			size = 1.3
			curve.add_point(Vector2(0.0, 0.35))
			curve.add_point(Vector2(0.4, 1.0))
			curve.add_point(Vector2(1.0, 1.4))
			ramp.set_color(0, Color(1.0, 1.0, 1.0, 0.0))
			ramp.set_color(1, Color(1.0, 1.0, 1.0, 0.0))
			ramp.add_point(0.12, Color(1.0, 1.0, 1.0, 0.6))
			ramp.add_point(0.45, Color(0.96, 0.98, 1.0, 0.3))
		"burst":
			p.amount = 180
			p.lifetime = 1.3
			p.spread = 38.0
			p.initial_velocity_min = 3.0
			p.initial_velocity_max = 7.5
			p.gravity = Vector3(0.0, -6.0, 0.0)
			p.damping_min = 1.0
			p.damping_max = 2.2
			p.scale_amount_min = 0.7
			p.scale_amount_max = 1.4
			size = 1.7
			curve.add_point(Vector2(0.0, 0.45))
			curve.add_point(Vector2(0.3, 1.0))
			curve.add_point(Vector2(1.0, 1.3))
			ramp.set_color(0, Color(1.0, 1.0, 1.0, 0.95))
			ramp.set_color(1, Color(1.0, 1.0, 1.0, 0.0))
			ramp.add_point(0.6, Color(0.97, 0.99, 1.0, 0.75))
		_:
			# (bubbles: pale, slow, drifting down and forward with the plunge, then rising)
			p.amount = 150
			p.lifetime = 2.4
			p.spread = 40.0
			p.initial_velocity_min = 0.6
			p.initial_velocity_max = 2.0
			p.gravity = Vector3(0.0, 0.9, 0.0)
			p.damping_min = 1.5
			p.damping_max = 2.5
			p.scale_amount_min = 0.5
			p.scale_amount_max = 1.1
			size = 1.2
			curve.add_point(Vector2(0.0, 0.5))
			curve.add_point(Vector2(0.5, 1.0))
			curve.add_point(Vector2(1.0, 1.2))
			ramp.set_color(0, Color(0.85, 0.95, 1.0, 0.75))
			ramp.set_color(1, Color(0.85, 0.95, 1.0, 0.0))
	p.scale_amount_curve = curve
	p.color_ramp = ramp
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	mat.vertex_color_use_as_albedo = true
	mat.albedo_texture = puff()
	mat.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	# (gone right at the eye, so a puff blown past the camera never fills the screen)
	mat.distance_fade_mode = BaseMaterial3D.DISTANCE_FADE_PIXEL_ALPHA
	mat.distance_fade_min_distance = 0.6
	mat.distance_fade_max_distance = 5.0
	var quad := QuadMesh.new()
	quad.size = Vector2(size, size)
	quad.material = mat
	p.mesh = quad
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
		for each: CPUParticles3D in (_spray[k] as Dictionary).values():
			each.visible = near < SPRAY_SEEN
	_rogue_mesh.visible = Surf.rogue_on
	_spray_wait -= delta
	if _spray_wait <= 0.0:
		_spray_wait = SPRAY_EVERY
		# (the puffs take the light of the hour, as the water's foam does: unshaded, so dimmed by hand)
		var water: ShaderMaterial = get_parent().get(&"_water")
		var lit := 1.0
		if water:
			var shallow: Variant = water.get_shader_parameter(&"shallow")
			if shallow is Color:
				lit = clampf(Vector3((shallow as Color).r, (shallow as Color).g, (shallow as Color).b).length() / 0.646, 0.3, 1.0)
		for k in all.size():
			_feed_spray(all[k], _spray[k], lit, bool(get_parent().get(&"above")))


# The streams' points: along the strip every other section, from where each section is in its break.
# (the plume and the burst are seen only from the air, the bubbles only from under the water: the surf's
# surface hides each from the other side, so only one side's streams are fed, which halves the cost)
func _feed_spray(site: Dictionary, streams: Dictionary, lit: float, above: bool) -> void:
	var plume: CPUParticles3D = streams.plume
	if not plume.visible:
		for each: CPUParticles3D in streams.values():
			each.emitting = false
		return
	var t := Surf.clock
	var pts: PackedVector2Array = site.points
	var tip_v := (PIECE.x + (PIECE.y - PIECE.x) * 9.0 / 17.0) / float(POINTS - 1)
	var top_v := (PIECE.x + (PIECE.y - PIECE.x) * 6.0 / 17.0) / float(POINTS - 1)
	var plume_at := PackedVector3Array()
	var plume_way := PackedVector3Array()
	var burst_at := PackedVector3Array()
	var burst_way := PackedVector3Array()
	var curtain_at := PackedVector3Array()
	var curtain_way := PackedVector3Array()
	for i in range(2, pts.size() - 2, 2):
		if float(site.fade[i]) < 0.5:
			continue
		var cr := crest(pts[i], site.ways[i], t)
		var stage: float = (cr.y - float(site.tb[i])) / BREAK_TIME
		if stage < 0.12 or stage > 1.25:
			continue
		if not above and (stage < 0.86 or stage > 1.2):
			continue
		var way: Vector2 = site.ways[i]
		var big: float = float(site.heights[i]) / 3.0
		var tip: Vector3 = point(site, i, tip_v, t).at
		if above and stage < 0.92:
			# (feathering back off the crest, the offshore wind's plume: up and back out to sea)
			var top: Vector3 = point(site, i, top_v, t).at
			plume_at.append(top + Vector3(0.0, 0.15, 0.0))
			plume_way.append(Vector3(-way.x * 0.4, 1.0, -way.y * 0.4).normalized())
			# (twice from a big crest, the second steeper up, so the plume stands over the crest from behind)
			if big > 0.75 and stage > 0.2:
				plume_at.append(top + Vector3(0.0, 0.3, 0.0))
				plume_way.append(Vector3(-way.x * 0.45, 1.0, -way.y * 0.45).normalized())
			if stage > 0.3 and stage < 0.6 and i % 4 == 2:
				# (and a little thrown off the lip as it pitches, forward and down with it: little, or it hides the
				# tube from the beach)
				plume_at.append(tip)
				plume_way.append(Vector3(way.x, 0.25, way.y).normalized())
		if stage > 0.86 and stage < 1.2:
			# (where the lip lands: an explosion of white up and back, and bubbles driven down under it)
			var n := 2 if big > 0.7 else 1
			for k in n if above else 0:
				burst_at.append(tip + Vector3(way.x * 0.3, 0.1, way.y * 0.3))
				# (up and forward, away from the tube, as a landing lip throws its water)
				burst_way.append(Vector3(way.x * 0.5, 1.0, way.y * 0.5).normalized())
			if not above:
				curtain_at.append(Vector3(tip.x, minf(tip.y, Sea.SURFACE) - 0.5 - 0.4 * big, tip.z))
				curtain_way.append(Vector3(way.x * 0.6, -0.8, way.y * 0.6).normalized())
	var feeds := {"plume": [plume_at, plume_way], "burst": [burst_at, burst_way], "curtain": [curtain_at, curtain_way]}
	for stream: String in streams:
		var p: CPUParticles3D = streams[stream]
		var where: PackedVector3Array = feeds[stream][0]
		if where.is_empty():
			p.emitting = false
			continue
		p.emission_points = where
		p.emission_normals = feeds[stream][1]
		p.emitting = true
		var mat := (p.mesh as QuadMesh).material as StandardMaterial3D
		mat.albedo_color = Color(lit, lit, lit)
