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
	[0.95, [-1.6, -0.2, -1.15, -0.01, -0.8, 0.26, -0.5, 0.54, -0.2, 0.82, 0.12, 1.02, 0.55, 1.1, 1.05, 0.98, 1.5, 0.62, 1.74, -0.12, 1.52, 0.26, 1.12, 0.7, 0.62, 0.8, 0.24, 0.64, 0.07, 0.3, 0.09, -0.12, 1.3, -0.16, 2.6, -0.22]],
	[1.1, [-1.6, -0.2, -1.15, -0.04, -0.8, 0.16, -0.5, 0.38, -0.2, 0.56, 0.15, 0.68, 0.55, 0.72, 1.0, 0.66, 1.45, 0.46, 1.8, -0.08, 1.6, 0.12, 1.2, 0.36, 0.75, 0.42, 0.38, 0.34, 0.2, 0.16, 0.24, -0.06, 1.6, -0.1, 2.6, -0.2]],
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
var _crash: Array[MultiMeshInstance3D] = []
## each site's landings drawn now, one a sampled section (s on the water's clock)
var _landed: Array[PackedFloat32Array] = []


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


## The stage at which the lip's tip comes down on the water ahead of it (third pass, the crash; tools/WATER_FX.md),
## read off the profile itself: for each row, the tip's height over the floor straight under it (the last time the
## profile's line passes under the tip's x); the landing is the first stage after the lip is thrown at which that gap
## is within CONTACT_GAP heights of the least it ever gets (the tip never quite meets the water: the profile must not
## cross itself). Everything the crash does starts then, section by section (`_land`), and the shader's white water
## grows from there (`breaker_contact`).
const CONTACT_GAP := 0.03
static var _contact := -1.0


static func contact() -> float:
	if _contact >= 0.0:
		return _contact
	profile()
	var gaps := PackedFloat32Array()
	var stages := PackedFloat32Array()
	var least := INF
	for r in ROWS:
		var stage := LAST_STAGE * r / float(ROWS - 1)
		if stage < 0.6 or stage > 1.3:
			continue
		var gap := tip_gap(stage)
		gaps.append(gap)
		stages.append(stage)
		least = minf(least, gap)
	_contact = stages[stages.size() - 1]
	for k in gaps.size():
		if gaps[k] <= least + CONTACT_GAP:
			# (between this row and the one before, where the gap crossed the line)
			if k > 0 and gaps[k - 1] > gaps[k]:
				var f := clampf((gaps[k - 1] - (least + CONTACT_GAP)) / (gaps[k - 1] - gaps[k]), 0.0, 1.0)
				_contact = lerpf(stages[k - 1], stages[k], f)
			else:
				_contact = stages[k]
			break
	return _contact


## The lip's tip's height over the water under it at a stage (wave heights; profile_at's reading).
static func tip_gap(stage: float) -> float:
	var tip := Vector2(-INF, 0.0)
	for c in range(int(COLUMNS * 0.4), int(COLUMNS * 0.66)):
		var p := profile_at(c / float(COLUMNS - 1), stage)
		if p.x > tip.x:
			tip = Vector2(p.x, p.y)
	var floor_y := NAN
	var prev := profile_at(0.0, stage)
	for c in range(1, COLUMNS):
		var q := profile_at(c / float(COLUMNS - 1), stage)
		if c > int(COLUMNS * 0.66) and (prev.x - tip.x) * (q.x - tip.x) <= 0.0 and prev.x != q.x:
			floor_y = lerpf(prev.y, q.y, (tip.x - prev.x) / (q.x - prev.x))
		prev = q
	return tip.y - floor_y if not is_nan(floor_y) else INF


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
		_spray.append({"plume": _make_stream("plume")})
		_crash.append(_make_crash(site))
		var never := PackedFloat32Array()
		never.resize(_crash_sections(site))
		never.fill(-1.0e6)
		_landed.append(never)
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
	material.set_shader_parameter(&"breaker_contact", contact())


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


## Spray (second round: painted puffs, not drops; tools/WATER_FX.md, "Barrels"). The PLUME: one CPUParticles3D a
## break of billboards cut from one small painted puff (`puff`), fed points along the crests every SPRAY_EVERY s from
## the CPU copy of the sums: mist feathering back off the crest as an offshore wind blows it (the tell of a breaking
## wave from out at sea) and spray thrown off the lip as it pitches. The crash where the lip lands is below (`_land`).
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
	var curve := Curve.new()
	var ramp := Gradient.new()
	# (more than before: the plume has PLUME_SLOTS points, most hidden until the crest is fully feathering)
	p.amount = 560
	p.lifetime = 1.3
	p.spread = 18.0
	p.initial_velocity_min = 2.5
	p.initial_velocity_max = 6.0
	p.gravity = Vector3(0.0, -1.0, 0.0)
	p.damping_min = 0.8
	p.damping_max = 1.8
	p.scale_amount_min = 0.45
	p.scale_amount_max = 1.0
	curve.add_point(Vector2(0.0, 0.35))
	curve.add_point(Vector2(0.4, 1.0))
	curve.add_point(Vector2(1.0, 1.4))
	ramp.set_color(0, Color(1.0, 1.0, 1.0, 0.0))
	ramp.set_color(1, Color(1.0, 1.0, 1.0, 0.0))
	ramp.add_point(0.12, Color(1.0, 1.0, 1.0, 0.6))
	ramp.add_point(0.45, Color(0.96, 0.98, 1.0, 0.3))
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
	quad.size = Vector2(1.3, 1.3)
	quad.material = mat
	p.mesh = quad
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(p)
	return p


# ---------------------------------------------------------------- the crash (third pass)

## The crash where the lip lands (third pass, 2026-11-18; tools/WATER_FX.md, "Third pass: the crash"). The user:
## "the splash timing and effects when the wave crashes needs work". Every CRASH_EVERY-th section of a strip has a
## set of painted puffs of its own, one MultiMesh a break, drawn and moved entirely by shaders/crash.gdshader from
## the water's clock: the CPU only says, once a wave, WHEN and WHERE that section's lip comes down (`contact()`, the
## stage read off the profile, turned into a time on the section's own break, and the tip's place then from
## `point`), so each section's crash starts the moment its own lip touches the water and the explosion runs along
## the strip with the peel. Being a function of the clock, it is the same held still (the pictures) as running.
## The kinds of puff a landing throws, in this order (how many of each):
## 0 the SPLASH-UP, thrown up and forward over the falling lip, about as high as the wave;
## 1 a SECOND splash a moment later, ahead of the first and lower, curling forward (the "secondary jet");
## 2 MIST, big faint puffs that rise and hang for seconds, drifting back out to sea in the offshore wind;
## 3 the SPIT, a blast of air and spray shot along the tube and out of its open end (not every landing);
## 4 the BORE, the white water rolling on towards the beach as a tumbling heap for a few seconds, then thinning into
##   trails and gone;
## 5 the trapped air BURSTING out on the wave's back half a second later;
## 6 BUBBLES under the water, a white vortex driven down and forward, turning, fading (seen only from below).
const CRASH_KINDS := [18, 6, 6, 4, 10, 3, 12]
const CRASH_EVERY := 2
## How long one landing's puffs can live (s); the next wave's landing is drawn only once they are all gone.
const CRASH_LIFE := 5.5
## The share of landings that spit out of the tube.
const SPIT_SHARE := 0.45

static var _crash_shader: Shader


static func _crash_per() -> int:
	var n := 0
	for k: int in CRASH_KINDS:
		n += k
	return n


static func _crash_sections(site: Dictionary) -> int:
	return int(ceil((site.points as PackedVector2Array).size() / float(CRASH_EVERY)))


func _make_crash(site: Dictionary) -> MultiMeshInstance3D:
	if _crash_shader == null:
		_crash_shader = load("res://shaders/crash.gdshader")
	var mat := ShaderMaterial.new()
	mat.shader = _crash_shader
	mat.set_shader_parameter(&"puff", puff())
	var quad := QuadMesh.new()
	quad.size = Vector2.ONE
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = quad
	mm.instance_count = _crash_sections(site) * _crash_per()
	# (born long ago: nothing shows until a landing is written)
	var never := Transform3D(Basis(Vector3(0.0, 0.0, -1.0e6), Vector3.ZERO, Vector3.ZERO), Vector3.ZERO)
	for i in mm.instance_count:
		mm.set_instance_transform(i, never)
	var box: Rect2 = site.box
	mm.custom_aabb = AABB(Vector3(box.position.x, Sea.SURFACE - 8.0, box.position.y), Vector3(box.size.x, 20.0, box.size.y))
	var mi := MultiMeshInstance3D.new()
	mi.name = "Breaker_crash_%s" % site.name
	mi.multimesh = mm
	mi.material_override = mat
	mi.custom_aabb = mm.custom_aabb
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mi)
	return mi


# Each sampled section's landing: the one now playing, or the next one once the last has died away. Written
# only when it changes (once a wave a section), ahead of time; the shader starts it on the clock.
## When a section's lip lands (s on the water's clock): the landing now playing out (within CRASH_LIFE), or else the
## next. Exact (to a frame), or only near (within a tenth of a second, for the cheap test of whether it changed).
static func landing(site: Dictionary, i: int, t: float, exact := true) -> float:
	var pts: PackedVector2Array = site.points
	var ways: PackedVector2Array = site.ways
	var cr := crest(pts[i], ways[i], t)
	var stage: float = (cr.y - float(site.tb[i])) / BREAK_TIME
	var te := t + (contact() - stage) * BREAK_TIME
	# (the wave before's landing is still playing out)
	if te > t and t - (te - Surf.PERIOD) < CRASH_LIFE:
		te -= Surf.PERIOD
	if exact:
		# (a section's stage does not run exactly with the clock, its crest's phase drifting as it comes in: two
		# steps of Newton's on the stage at the guess put the landing within a frame)
		for step in 2:
			var at_te := crest(pts[i], ways[i], te)
			te += (contact() - (at_te.y - float(site.tb[i])) / BREAK_TIME) * BREAK_TIME
	return te


func _land(site: Dictionary, crash: MultiMeshInstance3D, landed: PackedFloat32Array) -> void:
	var t := Surf.clock
	var pts: PackedVector2Array = site.points
	var ways: PackedVector2Array = site.ways
	var mm := crash.multimesh
	var per := _crash_per()
	var tip_v := (PIECE.x + (PIECE.y - PIECE.x) * 9.0 / 17.0) / float(POINTS - 1)
	for n in landed.size():
		var i := mini(n * CRASH_EVERY + 1, pts.size() - 1)
		if float(site.fade[i]) < 0.5:
			continue
		var te := landing(site, i, t, false)
		if absf(te - landed[n]) < 0.3:
			continue
		te = landing(site, i, t, true)
		landed[n] = te
		var way: Vector2 = ways[i]
		var along := (pts[mini(i + 1, pts.size() - 1)] - pts[maxi(i - 1, 0)]).normalized()
		var hh: float = float(site.heights[i]) * sets(crest(pts[i], way, te).z)
		var at: Vector3 = point(site, i, tip_v, te).at
		var bed := Sea.ground(at.x, at.z)
		var heading := atan2(way.y, way.x)
		var seed := fposmod(te * 17.31 + n * 3.7, 97.0)
		var spits := fposmod(sin(seed * 12.9898) * 43758.5453, 1.0) < SPIT_SHARE
		var k := 0
		for kind in CRASH_KINDS.size():
			for m in int(CRASH_KINDS[kind]):
				var strength := 0.0 if kind == 3 and not spits else 1.0
				# (the basis is not a turn: it carries the landing's data to the shader, full floats)
				var data := Basis(Vector3(heading, bed, te), Vector3(along.x, along.y, hh), Vector3(kind, seed + k * 1.618, strength))
				mm.set_instance_transform(n * per + k, Transform3D(data, at))
				k += 1


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
		_crash[k].visible = near < SPRAY_SEEN
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
		var above := bool(get_parent().get(&"above"))
		for k in all.size():
			_feed_spray(all[k], _spray[k], lit, above)
			if _crash[k].visible:
				_land(all[k], _crash[k], _landed[k])
				var mat := _crash[k].material_override as ShaderMaterial
				mat.set_shader_parameter(&"lit", lit)
				mat.set_shader_parameter(&"under", 0.0 if above else 1.0)


## How strong a section's crest plume is at a stage of its break: none while the swell is still rounded, growing as
## the face stands up and the lip starts to feather (0.25 to 0.55), full while it pitches, gone just before it lands
## (the crash takes over there).
static func _plume_weight(stage: float) -> float:
	return smoothstep(0.25, 0.55, stage) * (1.0 - smoothstep(0.82, 0.96, stage))


## The plume stream's points: PLUME_PER at most a section, PLUME_SLOTS in all (the unused ones hidden).
const PLUME_PER := 3
const PLUME_SLOTS := 60


# The plume's points: along the strip every other section, from where each section is in its break (seen only
# from the air: the surf's surface hides it from below).
func _feed_spray(site: Dictionary, streams: Dictionary, lit: float, above: bool) -> void:
	var plume: CPUParticles3D = streams.plume
	if not plume.visible or not above:
		plume.emitting = false
		return
	var t := Surf.clock
	var pts: PackedVector2Array = site.points
	var tip_v := (PIECE.x + (PIECE.y - PIECE.x) * 9.0 / 17.0) / float(POINTS - 1)
	var top_v := (PIECE.x + (PIECE.y - PIECE.x) * 6.0 / 17.0) / float(POINTS - 1)
	# (the user, 2026-11-18: "The spray at the top of the crest all spawns in at once as well so it doesn't make
	# sense". It came on whole the moment a section passed stage 0.12, and a particle system's rate is the same
	# however many points it has, so the first section on got the whole stream at once. Now each section's spray
	# grows as its face steepens (`_plume_weight`) and the stream has PLUME_SLOTS points always: a section takes
	# slots by its weight, the rest are hidden far below, so each section's share of the stream is its own weight
	# and the plume builds along the crest as the wave peels, then dies off before the lip lands.)
	var plume_at := PackedVector3Array()
	var plume_way := PackedVector3Array()
	for i in range(2, pts.size() - 2, 2):
		if float(site.fade[i]) < 0.5:
			continue
		var cr := crest(pts[i], site.ways[i], t)
		var stage: float = (cr.y - float(site.tb[i])) / BREAK_TIME
		var weight := _plume_weight(stage) * float(site.fade[i])
		if weight <= 0.01:
			continue
		var way: Vector2 = site.ways[i]
		var big: float = float(site.heights[i]) / 3.0
		var top: Vector3 = point(site, i, top_v, t).at
		# (feathering back off the crest, the offshore wind's plume: up and back out to sea; one slot at a little
		# weight, up to PLUME_PER at full, the higher ones steeper up so a full plume stands over the crest)
		var slots := int(round(weight * PLUME_PER * clampf(big, 0.6, 1.0)))
		for s in slots:
			plume_at.append(top + Vector3(0.0, 0.15 + 0.12 * s, 0.0))
			plume_way.append(Vector3(-way.x * (0.4 + 0.03 * s), 1.0, -way.y * (0.4 + 0.03 * s)).normalized())
		if stage > 0.35 and stage < 0.6 and i % 4 == 2:
			# (and a little thrown off the lip as it pitches, forward and down with it: little, or it hides the
			# tube from the beach)
			plume_at.append(point(site, i, tip_v, t).at)
			plume_way.append(Vector3(way.x, 0.25, way.y).normalized())
	if plume_at.is_empty():
		plume.emitting = false
		return
	# (the rest of the slots far under the sand: what is emitted there is never seen)
	var hidden := Vector3(pts[0].x, -500.0, pts[0].y)
	while plume_at.size() < PLUME_SLOTS:
		plume_at.append(hidden)
		plume_way.append(Vector3.DOWN)
	plume.emission_points = plume_at
	plume.emission_normals = plume_way
	plume.emitting = true
	var mat := (plume.mesh as QuadMesh).material as StandardMaterial3D
	mat.albedo_color = Color(lit, lit, lit)
