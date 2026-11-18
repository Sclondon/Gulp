extends SceneTree
## Bakes the sea floor from Monterey Bay's real depths into data/monterey.bin, which scripts/bay.gd
## reads. The grid is GMRT's (it carries MBARI's multibeam of the bay; about 60 m a sample):
##
##   curl -o bay.asc "https://www.gmrt.org/services/GridServer?north=37.02&west=-122.25&east=-121.75&south=36.45&layer=topo&format=esriascii&resolution=high"
##   godot --headless --path . -s res://tools/bake_bay.gd -- --grid=<bay.asc> [--places]
##
## The real bay is fitted to the game (CLAUDE.md, "Decision: the real bay"): SCALE real metres a
## game metre, centred on CENTRE; depths squeezed by `game_depth` (true to 10 m, then by log curves:
## 100 m real is 25 m, 2,000 m real is 100 m); then tuned for play: the narrow canyons widened by
## WIDEN metres, and the near-shore slope eased (`EASE_*`) so that beaches, kelp and harbours have
## room (the real bay is 10 m deep within a few hundred metres of the shore: two game metres).
##
## The file: int32 cols, rows; float32 west, north, cell; then cols*rows float32 depths (game m,
## positive down; land is negative, its height); then cols*rows float32 shore distances (game m
## from the nearest shore; negative on land). `--places` prints the game position and depth of the
## real places named in PLACES.

const SCALE := 180.0
const CENTRE := Vector2(-122.0, 36.74)
## The world's bounds (game m): Bay.WEST..EAST, NORTH..SOUTH.
const WEST := -122.0
const EAST := 122.0
const NORTH := -160.0
const SOUTH := 160.0
const CELL := 1.0
const WIDEN := 2.0
## Within EASE_BEACH of the shore the floor goes down to EASE_BEACH_DEEP; beyond, no steeper than
## EASE_SLOPE (m down a m out).
const EASE_BEACH := 14.0
const EASE_BEACH_DEEP := 5.0
const EASE_SLOPE := 0.6
## The easing is whole within the first of these from the shore (m) and gone by the second.
const EASE_NEAR := Vector2(25.0, 40.0)
const OUT := "res://data/monterey.bin"
## Skinnier canyons (see _narrow): below NARROW_FROM metres, the first LIFT metres of each wall are lifted
## to NARROW_FROM, and what is deeper is stretched back down to DEEPEST, so a canyon keeps its course and
## its floor but its gentle upper walls become shelf.
const NARROW_FROM := 24.0
const LIFT := 14.0
const DEEPEST := 106.0
## The user's drawn trench (see _trench), over the whole map. The user went back and forth (traced from the
## drawing; then "I didnt want it to be based exactly on my rough drawing just meant trench needs to be
## skinnier", so _narrow; then, of the traced one: "This had the best layout"). On. _narrow is kept, unused.
const USE_TRENCH_MASK := true
## ...but round Carmel (east of x and south of z, world m, blended over 8 m) the drawn mask shapes the
## Carmel Canyon: the user asked for it there.
const CARMEL_DRAWN := Vector2(-82.0, 66.0)
const TRENCH := "res://data/trench_mask.png"
const SHELF := 26.0
const SHELF_EASE := 5.0
const WALL := 3.0
const TRENCH_SHORE := 12.0
## Terraces down the trench's walls (see _steps): every TERRACE_WIDE metres in from its edge the floor
## steps down TERRACE_STEP metres: flat for the first TERRACE_TREAD of each, then a steep riser.
const TERRACE_WIDE := 6.0
const TERRACE_STEP := 14.0
const TERRACE_TREAD := 0.6
## The smoothing: box blurs this many cells round, this many times (about a Gaussian).
const BLUR := 2
const BLUR_PASSES := 3

const PLACES := {
	"santa_cruz_wharf": Vector2(-122.017, 36.957), "lighthouse_point": Vector2(-122.027, 36.951),
	"natural_bridges": Vector2(-122.058, 36.951), "capitola": Vector2(-121.953, 36.972),
	"aptos": Vector2(-121.905, 36.968), "moss_landing": Vector2(-121.788, 36.806),
	"monterey_wharf": Vector2(-121.893, 36.604), "cannery_row": Vector2(-121.901, 36.617),
	"lovers_point": Vector2(-121.915, 36.626), "point_pinos": Vector2(-121.936, 36.637),
	"cypress_point": Vector2(-121.977, 36.581), "pescadero_point": Vector2(-121.951, 36.561),
	"carmel_beach": Vector2(-121.928, 36.553), "point_lobos": Vector2(-121.951, 36.518),
	"del_monte": Vector2(-121.87, 36.605), "canyon_head": Vector2(-121.81, 36.80),
	"canyon_mid": Vector2(-121.92, 36.785), "canyon_bend": Vector2(-122.02, 36.75),
	"soquel_canyon": Vector2(-121.94, 36.86), "carmel_canyon": Vector2(-121.97, 36.54),
	"mid_bay_north": Vector2(-121.98, 36.88), "mid_bay_south": Vector2(-121.88, 36.70),
	"shelf_break_north": Vector2(-122.1, 36.9), "portuguese_ledge": Vector2(-121.98, 36.71),
	"sand_off_santa_cruz": Vector2(-122.0, 36.92),
}

var _cols := 0
var _rows := 0
var _x0 := 0.0
var _y0 := 0.0
var _cell := 0.0
var _z := PackedFloat32Array()


static func game_depth(real: float) -> float:
	if real <= 10.0:
		return real
	if real <= 100.0:
		return 10.0 + 15.0 * log(real / 10.0) / log(10.0)
	return 25.0 + 75.0 * log(real / 100.0) / log(20.0)


static func to_game(lon_lat: Vector2) -> Vector2:
	var per_lon := 111320.0 * cos(deg_to_rad(CENTRE.y))
	return Vector2((lon_lat.x - CENTRE.x) * per_lon / SCALE, (CENTRE.y - lon_lat.y) * 111320.0 / SCALE)


static func to_lon_lat(p: Vector2) -> Vector2:
	var per_lon := 111320.0 * cos(deg_to_rad(CENTRE.y))
	return Vector2(CENTRE.x + p.x * SCALE / per_lon, CENTRE.y - p.y * SCALE / 111320.0)


func _initialize() -> void:
	var grid := ""
	var places := false
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--grid="):
			grid = arg.get_slice("=", 1)
		elif arg == "--places":
			places = true
	_read(grid)
	var cols := int(round((EAST - WEST) / CELL)) + 1
	var rows := int(round((SOUTH - NORTH) / CELL)) + 1
	var raw := PackedFloat32Array()
	raw.resize(cols * rows)
	for r in rows:
		for c in cols:
			var ll := to_lon_lat(Vector2(WEST + c * CELL, NORTH + r * CELL))
			var h := _height(ll.x, ll.y)
			raw[r * cols + c] = game_depth(-h) if h < 0.0 else -clampf(h * 0.04, 0.0, 4.0)
	# Widened: each wet point as deep as the deepest wet point within WIDEN of it.
	var reach := int(ceil(WIDEN / CELL))
	var wide := raw.duplicate()
	for r in rows:
		for c in cols:
			var i := r * cols + c
			if raw[i] <= 0.0:
				continue
			var best := raw[i]
			for dr in range(-reach, reach + 1):
				for dc in range(-reach, reach + 1):
					if dr * dr + dc * dc > reach * reach:
						continue
					var rr := r + dr
					var cc := c + dc
					if rr < 0 or cc < 0 or rr >= rows or cc >= cols:
						continue
					best = maxf(best, raw[rr * cols + cc])
			wide[i] = best
	# Smoothed (GMRT joins surveys of different detail: their seams showed as straight steps and
	# ovals once the depths were squeezed), wet points only, so the shore stays where it is.
	for blur_pass in BLUR_PASSES:
		wide = _blur(wide, cols, rows, BLUR)
	if USE_TRENCH_MASK:
		wide = _trench(wide, cols, rows)
	else:
		wide = _narrow(wide)
		# (and the Carmel Canyon as the user drew it, there only: "There should be a canyone leading up to
		# carmel like the overlay I drew": a narrow canyon from Carmel west, the shelf either side of it)
		var drawn := _trench(wide, cols, rows)
		for r in rows:
			for c in cols:
				var i := r * cols + c
				var k := smoothstep(CARMEL_DRAWN.x, CARMEL_DRAWN.x + 8.0, WEST + c * CELL) * smoothstep(CARMEL_DRAWN.y, CARMEL_DRAWN.y + 8.0, NORTH + r * CELL)
				wide[i] = lerpf(wide[i], drawn[i], k)
	var shore := _shore_distance(wide, cols, rows)
	# The near shore eased.
	# (only near the shore, EASE_NEAR; and a canyon that drops far below the eased slope keeps its
	# depth, but for its last metres to the shore: the Monterey Canyon's head is real)
	for i in wide.size():
		if wide[i] <= 0.0:
			continue
		var d := shore[i]
		var most := maxf(d * EASE_BEACH_DEEP / EASE_BEACH if d < EASE_BEACH else EASE_BEACH_DEEP + (d - EASE_BEACH) * EASE_SLOPE, 0.3)
		var near := 1.0 - smoothstep(EASE_NEAR.x, EASE_NEAR.y, d)
		var canyon := 0.0 if d < 8.0 else smoothstep(10.0, 20.0, wide[i] - most)
		wide[i] = lerpf(wide[i], minf(wide[i], most), near * (1.0 - canyon))
	var out := FileAccess.open(OUT, FileAccess.WRITE)
	# (and once more, lightly, after the easing, whose bands follow the chamfer's octagons)
	wide = _blur(wide, cols, rows, 1)
	out.store_32(cols)
	out.store_32(rows)
	out.store_float(WEST)
	out.store_float(NORTH)
	out.store_float(CELL)
	out.store_buffer(wide.to_byte_array())
	out.store_buffer(shore.to_byte_array())
	out.close()
	var deepest := 0.0
	var wet := 0
	for v in wide:
		deepest = maxf(deepest, v)
		wet += int(v > 0.0)
	print("BAKE %d x %d, %.0f%% water, deepest %.1f m: %s" % [cols, rows, 100.0 * wet / wide.size(), deepest, OUT])
	if places:
		for name: String in PLACES:
			var p := to_game(PLACES[name])
			var c := clampi(int(round((p.x - WEST) / CELL)), 0, cols - 1)
			var r := clampi(int(round((p.y - NORTH) / CELL)), 0, rows - 1)
			print("PLACE %s: (%.1f, %.1f) depth %.1f, shore %.1f" % [name, p.x, p.y, wide[r * cols + c], shore[r * cols + c]])
	quit()


# Skinnier canyons: the real floor's canyons, their upper walls lifted to the shelf (see NARROW_FROM).
func _narrow(src: PackedFloat32Array) -> PackedFloat32Array:
	var out := src.duplicate()
	var stretch := (DEEPEST - NARROW_FROM) / (DEEPEST - NARROW_FROM - LIFT)
	for i in src.size():
		var over := src[i] - NARROW_FROM
		if over > 0.0:
			out[i] = NARROW_FROM + maxf(over - LIFT, 0.0) * stretch
	return out


# The deepest the floor may be `inside` metres in from the trench's edge: its walls as terraces (the user,
# 2026-11-18: "the trench needs to be carved out with terrace like steps, no just one huge cliff"). Steps
# by distance, not by depth: the real walls drop 60 m in a few metres, where depth-steps would be too
# narrow to see on the 2 m floor grid. The treads follow the trench's (drawn, wavering) edge.
func _steps(inside: float) -> float:
	var band := inside / TERRACE_WIDE
	var whole := floorf(band)
	return SHELF + TERRACE_STEP * (whole + smoothstep(TERRACE_TREAD, 1.0, band - whole))


# (unused: steps by depth, the first try) The trench's walls in steps (the user, 2026-11-18: "the trench needs to be carved out with terrace like
# steps, no just one huge cliff"): below SHELF, each TERRACE_STEP metres of depth is a flat tread for its
# first TERRACE_TREAD and a smooth steep riser down to the next. The treads follow the floor's own contours,
# so they wind along the walls; where a wall is gentle they are wide, where steep, narrow. Everything deeper
# than SHELF is in the trench (outside it the floor is raised to SHELF), so the whole trench is stepped.
func _terrace(src: PackedFloat32Array) -> PackedFloat32Array:
	var out := src.duplicate()
	for i in src.size():
		var over := src[i] - SHELF
		if over <= 0.0:
			continue
		var band := over / TERRACE_STEP
		var whole := floorf(band)
		out[i] = SHELF + TERRACE_STEP * (whole + smoothstep(TERRACE_TREAD, 1.0, band - whole))
	return out


# The trench where the user drew it (data/trench_mask.png, tools/trench_mask.gd: "The trench area needs to
# be skinner, just showing roughish boundaries"): outside it the floor is raised to the shelf (no deeper
# than SHELF, eased in over SHELF_EASE m from its edge); inside, it is at least as deep as a wall going
# down WALL m a metre from the edge would make it (so a branch the real floor has shallow, as the Soquel
# Canyon, is cut), but never within TRENCH_SHORE of a shore (the slough, Carmel Cove and the canyon's head
# at Moss Landing keep their own floors).
func _trench(src: PackedFloat32Array, cols: int, rows: int) -> PackedFloat32Array:
	if not FileAccess.file_exists(TRENCH):
		print("BAKE no trench mask: the floor as it is")
		return src
	var mask := Image.load_from_file(TRENCH)
	var inside := PackedFloat32Array()
	inside.resize(cols * rows)
	for r in rows:
		for c in cols:
			var m := mask.get_pixel(mini(c, mask.get_width() - 1), mini(r, mask.get_height() - 1)).r > 0.5
			inside[r * cols + c] = 1.0 if m else -1.0
	var to_out := _chamfer(inside, cols, rows, true)
	var to_in := _chamfer(inside, cols, rows, false)
	var shore := _shore_distance(src, cols, rows)
	var out := src.duplicate()
	for i in src.size():
		if src[i] <= 0.0:
			continue
		if inside[i] > 0.0:
			var cut := SHELF + clampf(to_out[i] * WALL, 0.0, 70.0)
			# (and its walls in steps, inward from its edge: see _steps)
			var stepped := minf(maxf(src[i], cut), _steps(to_out[i]))
			out[i] = lerpf(src[i], stepped, smoothstep(TRENCH_SHORE * 0.5, TRENCH_SHORE, shore[i]))
		else:
			# (right up to the edge: the steps inside start at SHELF, so they meet; an ease here left a moat)
			out[i] = minf(src[i], SHELF)
	return out


# A box blur `r` cells round, of the wet points among wet points (land is left as it is).
func _blur(src: PackedFloat32Array, cols: int, rows: int, r: int) -> PackedFloat32Array:
	var mid := src.duplicate()
	for row in rows:
		for c in cols:
			var i := row * cols + c
			if src[i] <= 0.0:
				continue
			var sum := 0.0
			var n := 0
			for k in range(maxi(c - r, 0), mini(c + r, cols - 1) + 1):
				var v := src[row * cols + k]
				if v > 0.0:
					sum += v
					n += 1
			mid[i] = sum / n
	var out := mid.duplicate()
	for row in rows:
		for c in cols:
			var i := row * cols + c
			if src[i] <= 0.0:
				continue
			var sum := 0.0
			var n := 0
			for k in range(maxi(row - r, 0), mini(row + r, rows - 1) + 1):
				var v := mid[k * cols + c]
				if v > 0.0:
					sum += v
					n += 1
			out[i] = sum / n
	return out


# Signed distance to the shore (game m): two-pass chamfer over the grid, from water to land and back.
func _shore_distance(depth: PackedFloat32Array, cols: int, rows: int) -> PackedFloat32Array:
	var to_land := _chamfer(depth, cols, rows, true)
	var to_water := _chamfer(depth, cols, rows, false)
	var out := PackedFloat32Array()
	out.resize(depth.size())
	for i in depth.size():
		out[i] = (to_land[i] - 0.5 * CELL) if depth[i] > 0.0 else -(to_water[i] - 0.5 * CELL)
	return out


func _chamfer(depth: PackedFloat32Array, cols: int, rows: int, wet: bool) -> PackedFloat32Array:
	var d := PackedFloat32Array()
	d.resize(depth.size())
	for i in depth.size():
		# (distance from each point of one kind to the nearest of the other)
		d[i] = INF if (depth[i] > 0.0) == wet else 0.0
	var a := CELL
	var b := CELL * 1.41421356
	for r in rows:
		for c in cols:
			var i := r * cols + c
			if d[i] == 0.0:
				continue
			var v := d[i]
			if c > 0: v = minf(v, d[i - 1] + a)
			if r > 0:
				v = minf(v, d[i - cols] + a)
				if c > 0: v = minf(v, d[i - cols - 1] + b)
				if c < cols - 1: v = minf(v, d[i - cols + 1] + b)
			d[i] = v
	for r in range(rows - 1, -1, -1):
		for c in range(cols - 1, -1, -1):
			var i := r * cols + c
			if d[i] == 0.0:
				continue
			var v := d[i]
			if c < cols - 1: v = minf(v, d[i + 1] + a)
			if r < rows - 1:
				v = minf(v, d[i + cols] + a)
				if c < cols - 1: v = minf(v, d[i + cols + 1] + b)
				if c > 0: v = minf(v, d[i + cols - 1] + b)
			d[i] = v
	for i in d.size():
		if d[i] == INF:
			d[i] = 999.0
	return d


func _read(path: String) -> void:
	var f := FileAccess.open(path, FileAccess.READ)
	var head := {}
	for i in 6:
		var parts := f.get_line().split(" ", false)
		head[parts[0].to_lower()] = parts[1]
	_cols = int(head.ncols)
	_rows = int(head.nrows)
	_x0 = float(head.xllcorner)
	_y0 = float(head.yllcorner)
	_cell = float(head.cellsize)
	_z.resize(_cols * _rows)
	var k := 0
	while not f.eof_reached() and k < _z.size():
		for v in f.get_line().split(" ", false):
			if k < _z.size():
				_z[k] = float(v)
				k += 1


func _height(lon: float, lat: float) -> float:
	var gx := clampf((lon - _x0) / _cell - 0.5, 0.0, _cols - 1.001)
	var gy := clampf((_y0 + _rows * _cell - lat) / _cell - 0.5, 0.0, _rows - 1.001)
	var ix := int(gx)
	var iy := int(gy)
	var fx := gx - ix
	var fy := gy - iy
	return lerpf(lerpf(_z[iy * _cols + ix], _z[iy * _cols + ix + 1], fx), lerpf(_z[(iy + 1) * _cols + ix], _z[(iy + 1) * _cols + ix + 1], fx), fy)
