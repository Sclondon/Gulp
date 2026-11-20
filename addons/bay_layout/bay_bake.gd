@tool
extends RefCounted
## Bakes the sea floor from Monterey Bay's real depths into data/monterey.bin, which scripts/bay.gd
## reads. Run from the command line by tools/bake_bay.gd, or from the bay editor's Rebake button
## (addons/bay_layout). The numbers it is tuned with, the trench's outline and the floor's hand
## edits come from the layout (data/layout.json: "bake", "trench"; tools/bay_src/floor_adjust.bin).
##
## The grid is GMRT's (it carries MBARI's multibeam of the bay; about 60 m a sample), kept in
## tools/bay_src/gmrt.bin (packed from the download: `--grid=<bay.asc>` reads a fresh one):
##
##   curl -o bay.asc "https://www.gmrt.org/services/GridServer?north=37.02&west=-122.25&east=-121.75&south=36.45&layer=topo&format=esriascii&resolution=high"
##
## The real bay is fitted to the game (CLAUDE.md, "Decision: the real bay"): SCALE real metres a
## game metre, centred on CENTRE; depths squeezed by `game_depth` (true to 10 m, then by log curves:
## 100 m real is 25 m, 2,000 m real is 100 m); then tuned for play: the narrow canyons widened by
## `widen` metres, and the near-shore slope eased (`ease_*`) so that beaches, kelp and harbours have
## room (the real bay is 10 m deep within a few hundred metres of the shore: two game metres).
## Last, the floor's hand edits (raised or lowered by the editor's brushes) are added, and the
## shore's distances worked out again if they changed anything.
##
## The file: int32 cols, rows; float32 west, north, cell; then cols*rows float32 depths (game m,
## positive down; land is negative, its height); then cols*rows float32 shore distances (game m
## from the nearest shore; negative on land).

const SCALE := 180.0
const CENTRE := Vector2(-122.0, 36.74)
## The world's bounds (game m): Bay.WEST..EAST, NORTH..SOUTH.
const WEST := -122.0
const EAST := 162.0
const NORTH := -160.0
const SOUTH := 160.0
const CELL := 1.0
const OUT := "res://data/monterey.bin"
## GMRT's grid, packed (zstd): float64 x0, y0, cell; int32 cols, rows; int32 heights in centimetres, each
## less the one before it.
const GMRT := "res://tools/bay_src/gmrt.bin"
## The floor's hand edits (the editor's brushes): int32 cols, rows; float32 west, north, cell; then
## cols*rows float32, metres the floor is raised (less than 0: lowered). Zstd. On CELL's grid.
const ADJUST := "res://tools/bay_src/floor_adjust.bin"
## A copy of the edits as last baked (the editor shows the floor as baked plus what changed since).
const ADJUST_BAKED := "res://tools/bay_src/floor_adjust_baked.bin"
## Skinnier canyons (see _narrow; unused while the drawn trench is on).
const NARROW_FROM := 24.0
const LIFT := 14.0
const DEEPEST := 106.0
const USE_TRENCH_MASK := true
const CARMEL_DRAWN := Vector2(-82.0, 66.0)
## (the even coast offset that ruined the peninsula: off)
const PENINSULA_GROW := 0.0
const PENINSULA := Vector2(58.0, 56.0)
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

# The layout's numbers (data/layout.json "bake"), read at the start of `bake`.
var widen := 2.0
var shelf := 26.0
var wall := 3.0
var trench_shore := 12.0
var terrace_wide := 6.0
var terrace_step := 14.0
var terrace_tread := 0.6
var pen_scale := 1.15
var pen_root := Vector2(58.0, 110.0)
var pen_middle := Vector2(30.0, 108.0)
var pen_radii := Vector2(36.0, 56.0)
var pen_fade := 1.4
var ease_beach := 14.0
var ease_beach_deep := 5.0
var ease_slope := 0.6
var ease_near := Vector2(25.0, 40.0)

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


## The size of the 1 m grid the bake writes (and the hand edits are kept on).
static func grid_size() -> Vector2i:
	return Vector2i(int(round((EAST - WEST) / CELL)) + 1, int(round((SOUTH - NORTH) / CELL)) + 1)


## The hand edits (metres raised, per cell of the 1 m grid), or an empty array if there are none.
static func read_adjust(path := ADJUST) -> PackedFloat32Array:
	if not FileAccess.file_exists(path):
		return PackedFloat32Array()
	var f := FileAccess.open_compressed(path, FileAccess.READ, FileAccess.COMPRESSION_ZSTD)
	if f == null:
		return PackedFloat32Array()
	var size := Vector2i(f.get_32(), f.get_32())
	f.get_float()
	f.get_float()
	f.get_float()
	if size != grid_size():
		push_warning("Bay bake: %s is for another grid size; left out" % path)
		return PackedFloat32Array()
	return f.get_buffer(size.x * size.y * 4).to_float32_array()


static func write_adjust(values: PackedFloat32Array, path := ADJUST) -> void:
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var size := grid_size()
	var f := FileAccess.open_compressed(path, FileAccess.WRITE, FileAccess.COMPRESSION_ZSTD)
	f.store_32(size.x)
	f.store_32(size.y)
	f.store_float(WEST)
	f.store_float(NORTH)
	f.store_float(CELL)
	f.store_buffer(values.to_byte_array())
	f.close()


func _read_layout() -> void:
	var b: Dictionary = Layout.value("bake", {})
	widen = float(b.get("widen", widen))
	shelf = float(b.get("shelf", shelf))
	wall = float(b.get("wall", wall))
	trench_shore = float(b.get("trench_shore", trench_shore))
	terrace_wide = float(b.get("terrace_wide", terrace_wide))
	terrace_step = float(b.get("terrace_step", terrace_step))
	terrace_tread = float(b.get("terrace_tread", terrace_tread))
	pen_scale = float(b.get("pen_scale", pen_scale))
	pen_root = Layout.v2(b.get("pen_root", [pen_root.x, pen_root.y]))
	pen_middle = Layout.v2(b.get("pen_middle", [pen_middle.x, pen_middle.y]))
	pen_radii = Layout.v2(b.get("pen_radii", [pen_radii.x, pen_radii.y]))
	pen_fade = float(b.get("pen_fade", pen_fade))
	ease_beach = float(b.get("ease_beach", ease_beach))
	ease_beach_deep = float(b.get("ease_beach_deep", ease_beach_deep))
	ease_slope = float(b.get("ease_slope", ease_slope))
	ease_near = Layout.v2(b.get("ease_near", [ease_near.x, ease_near.y]))


## Reads GMRT's grid: from an ESRI ASCII download if `asc` is given (and packs it into GMRT for next
## time when `keep`), else from the packed copy. False if there is none.
func read_grid(asc := "", keep := false) -> bool:
	if asc != "":
		_read_asc(asc)
		if keep:
			# (as centimetres, each the step from the one before it: GMRT gives heights to the centimetre, and
			# small steps pack to a third of the size of plain floats; they read back as the same floats)
			var steps := PackedInt32Array()
			steps.resize(_z.size())
			var was := 0
			for i in _z.size():
				var cm := int(round(_z[i] * 100.0))
				if float(PackedFloat32Array([cm / 100.0])[0]) != _z[i]:
					push_error("Bay bake: a height is not to the centimetre (%f): not packed" % _z[i])
					return true
				steps[i] = cm - was
				was = cm
			DirAccess.make_dir_recursive_absolute(GMRT.get_base_dir())
			var f := FileAccess.open_compressed(GMRT, FileAccess.WRITE, FileAccess.COMPRESSION_ZSTD)
			f.store_double(_x0)
			f.store_double(_y0)
			f.store_double(_cell)
			f.store_32(_cols)
			f.store_32(_rows)
			f.store_buffer(steps.to_byte_array())
			f.close()
		return true
	if not _z.is_empty():
		return true
	var f := FileAccess.open_compressed(GMRT, FileAccess.READ, FileAccess.COMPRESSION_ZSTD)
	if f == null:
		return false
	_x0 = f.get_double()
	_y0 = f.get_double()
	_cell = f.get_double()
	_cols = f.get_32()
	_rows = f.get_32()
	var steps := f.get_buffer(_cols * _rows * 4).to_int32_array()
	_z.resize(steps.size())
	var cm := 0
	for i in steps.size():
		cm += steps[i]
		_z[i] = cm / 100.0
	return true


## Bakes the floor into `out`. Returns what it did: {"cols", "rows", "wet", "deepest", "ms"}; with
## `places`, also prints where PLACES are in the game.
func bake(out := OUT, places := false) -> Dictionary:
	var started := Time.get_ticks_msec()
	_read_layout()
	if not read_grid():
		push_error("Bay bake: no grid (%s): run tools/bake_bay.gd with --grid=<bay.asc>" % GMRT)
		return {}
	var size := grid_size()
	var cols := size.x
	var rows := size.y
	var raw := PackedFloat32Array()
	raw.resize(cols * rows)
	for r in rows:
		for c in cols:
			var ll := to_lon_lat(peninsula_source(Vector2(WEST + c * CELL, NORTH + r * CELL)))
			var h := _height(ll.x, ll.y)
			raw[r * cols + c] = game_depth(-h) if h < 0.0 else -clampf(h * 0.04, 0.0, 4.0)
	raw = _grow_peninsula(raw, cols, rows)
	# Widened: each wet point as deep as the deepest wet point within `widen` of it.
	var reach := int(ceil(widen / CELL))
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
		var drawn := _trench(wide, cols, rows)
		for r in rows:
			for c in cols:
				var i := r * cols + c
				var k := smoothstep(CARMEL_DRAWN.x, CARMEL_DRAWN.x + 8.0, WEST + c * CELL) * smoothstep(CARMEL_DRAWN.y, CARMEL_DRAWN.y + 8.0, NORTH + r * CELL)
				wide[i] = lerpf(wide[i], drawn[i], k)
	var shore := _shore_distance(wide, cols, rows)
	# The near shore eased.
	# (only near the shore, ease_near; and a canyon that drops far below the eased slope keeps its
	# depth, but for its last metres to the shore: the Monterey Canyon's head is real)
	for i in wide.size():
		if wide[i] <= 0.0:
			continue
		var d := shore[i]
		var most := maxf(d * ease_beach_deep / ease_beach if d < ease_beach else ease_beach_deep + (d - ease_beach) * ease_slope, 0.3)
		var near := 1.0 - smoothstep(ease_near.x, ease_near.y, d)
		var canyon := 0.0 if d < 8.0 else smoothstep(10.0, 20.0, wide[i] - most)
		wide[i] = lerpf(wide[i], minf(wide[i], most), near * (1.0 - canyon))
	# (and once more, lightly, after the easing, whose bands follow the chamfer's octagons)
	wide = _blur(wide, cols, rows, 1)
	# The hand edits (the editor's brushes), and the shore again where they moved it.
	var adjust := read_adjust()
	var edited := false
	if adjust.size() == wide.size():
		for i in wide.size():
			if adjust[i] != 0.0:
				wide[i] -= adjust[i]
				edited = true
	if edited:
		shore = _shore_distance(wide, cols, rows)
	var file := FileAccess.open(out, FileAccess.WRITE)
	file.store_32(cols)
	file.store_32(rows)
	file.store_float(WEST)
	file.store_float(NORTH)
	file.store_float(CELL)
	file.store_buffer(wide.to_byte_array())
	file.store_buffer(shore.to_byte_array())
	file.close()
	# (what was baked in, for the editor's picture of the floor)
	if out == OUT:
		if edited:
			write_adjust(adjust, ADJUST_BAKED)
		else:
			_forget_baked()
	var deepest := 0.0
	var wet := 0
	for v in wide:
		deepest = maxf(deepest, v)
		wet += int(v > 0.0)
	var ms := Time.get_ticks_msec() - started
	print("BAKE %d x %d, %.0f%% water, deepest %.1f m, %d ms: %s" % [cols, rows, 100.0 * wet / wide.size(), deepest, ms, out])
	if places:
		for name: String in PLACES:
			var p := to_game(PLACES[name])
			var c := clampi(int(round((p.x - WEST) / CELL)), 0, cols - 1)
			var r := clampi(int(round((p.y - NORTH) / CELL)), 0, rows - 1)
			print("PLACE %s: (%.1f, %.1f) depth %.1f, shore %.1f" % [name, p.x, p.y, wide[r * cols + c], shore[r * cols + c]])
	return {"cols": cols, "rows": rows, "wet": wet, "deepest": deepest, "ms": ms}


func _forget_baked() -> void:
	if FileAccess.file_exists(ADJUST_BAKED):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(ADJUST_BAKED))


# Skinnier canyons: the real floor's canyons, their upper walls lifted to the shelf (see NARROW_FROM).
func _narrow(src: PackedFloat32Array) -> PackedFloat32Array:
	var out := src.duplicate()
	var stretch := (DEEPEST - NARROW_FROM) / (DEEPEST - NARROW_FROM - LIFT)
	for i in src.size():
		var over := src[i] - NARROW_FROM
		if over > 0.0:
			out[i] = NARROW_FROM + maxf(over - LIFT, 0.0) * stretch
	return out


# The Monterey Peninsula bigger, its own shape scaled up (the user, 2026-11-18: "The peninsula needs to be a
# little bigger"; then, of an even coast offset that filled Carmel Bay: "you totally ruined the shape"; then
# "Yes I want the peninsula bigger"). Where the floor at a world point is read from: inside the ellipse
# pen_middle / pen_radii, from pen_root + (p - pen_root) / pen_scale (a copy pen_scale times as big, growing out
# from where the peninsula joins the land); outside it the real place; between (out to pen_fade times the
# ellipse), a smooth blend. `peninsula_target` is the other way: where something placed by the real coast
# goes.
func peninsula_source(p: Vector2) -> Vector2:
	var w := _pen_weight(p)
	if w <= 0.0:
		return p
	return p.lerp(pen_root + (p - pen_root) / pen_scale, w)


func peninsula_target(q: Vector2) -> Vector2:
	var p := pen_root + (q - pen_root) * pen_scale
	# (a few rounds to undo the blend near the edge)
	for k in 6:
		p += q - peninsula_source(p)
	return p


func _pen_weight(p: Vector2) -> float:
	var d := ((p - pen_middle) / pen_radii).length()
	return 1.0 - smoothstep(1.0, pen_fade, d)


# (unused: the even coast offset that ruined the shape)
func _grow_peninsula(src: PackedFloat32Array, cols: int, rows: int) -> PackedFloat32Array:
	if PENINSULA_GROW <= 0.0:
		return src
	var shore := _shore_distance(src, cols, rows)
	var out := src.duplicate()
	for r in rows:
		for c in cols:
			var i := r * cols + c
			if src[i] <= 0.0:
				continue
			var x := WEST + c * CELL
			var z := NORTH + r * CELL
			var k := (1.0 - smoothstep(PENINSULA.x - 10.0, PENINSULA.x, x)) * smoothstep(PENINSULA.y, PENINSULA.y + 10.0, z)
			var grow := PENINSULA_GROW * k
			if shore[i] < grow:
				out[i] = -0.6 * (1.0 - shore[i] / maxf(grow, 0.01)) - 0.2
	return out


# The deepest the floor may be `inside` metres in from the trench's edge: its walls as terraces (the user,
# 2026-11-18: "the trench needs to be carved out with terrace like steps, no just one huge cliff"). Steps
# by distance, not by depth: the real walls drop 60 m in a few metres, where depth-steps would be too
# narrow to see on the 2 m floor grid. The treads follow the trench's (drawn, wavering) edge.
func _steps(inside: float) -> float:
	var band := inside / terrace_wide
	var whole := floorf(band)
	return shelf + terrace_step * (whole + smoothstep(terrace_tread, 1.0, band - whole))


## Which cells of the 1 m grid are inside the trench (1) or not (-1): the layout's outlines
## ("trench" "shapes") if it has them, else the user's drawn mask (data/trench_mask.png,
## tools/trench_mask.gd) and the outlines added to it since ("trench" "add").
static func trench_inside(cols: int, rows: int) -> PackedFloat32Array:
	var t: Dictionary = Layout.value("trench", {})
	var shapes := []
	for s: Variant in t.get("shapes", []):
		shapes.append(PackedVector2Array(Layout.line(s)))
	var mask: Image = null
	if shapes.is_empty():
		for s: Variant in t.get("add", []):
			shapes.append(PackedVector2Array(Layout.line(s)))
		var path := String(t.get("mask", ""))
		if path != "" and FileAccess.file_exists(path):
			# (read as a file, not as the imported texture: the bake wants its pixels as drawn)
			mask = Image.new()
			mask.load_png_from_buffer(FileAccess.get_file_as_bytes(path))
	var inside := PackedFloat32Array()
	inside.resize(cols * rows)
	inside.fill(-1.0)
	if mask != null:
		var mw := mask.get_width()
		var mh := mask.get_height()
		for r in rows:
			for c in cols:
				if mask.get_pixel(mini(c, mw - 1), mini(r, mh - 1)).r > 0.5:
					inside[r * cols + c] = 1.0
	# (each outline only over its own box)
	for shape: PackedVector2Array in shapes:
		var box := Rect2(shape[0], Vector2.ZERO)
		for p in shape:
			box = box.expand(p)
		for r in range(maxi(int(floor((box.position.y - NORTH) / CELL)), 0), mini(int(ceil((box.end.y - NORTH) / CELL)) + 1, rows)):
			for c in range(maxi(int(floor((box.position.x - WEST) / CELL)), 0), mini(int(ceil((box.end.x - WEST) / CELL)) + 1, cols)):
				if Geometry2D.is_point_in_polygon(Vector2(WEST + c * CELL, NORTH + r * CELL), shape):
					inside[r * cols + c] = 1.0
	return inside


# The trench where the layout has it (see trench_inside): outside it the floor is raised to the shelf (no
# deeper than `shelf`); inside, it is at least as deep as a wall going down `wall` m a metre from the edge
# would make it (so a branch the real floor has shallow, as the Soquel Canyon, is cut), but never within
# trench_shore of a shore (the slough, Carmel Cove and the canyon's head at Moss Landing keep their own
# floors).
func _trench(src: PackedFloat32Array, cols: int, rows: int) -> PackedFloat32Array:
	var inside := trench_inside(cols, rows)
	var to_out := _chamfer(inside, cols, rows, true)
	var shore := _shore_distance(src, cols, rows)
	var out := src.duplicate()
	for i in src.size():
		if src[i] <= 0.0:
			continue
		if inside[i] > 0.0:
			var cut := shelf + clampf(to_out[i] * wall, 0.0, 70.0)
			# (and its walls in steps, inward from its edge: see _steps)
			var stepped := minf(maxf(src[i], cut), _steps(to_out[i]))
			out[i] = lerpf(src[i], stepped, smoothstep(trench_shore * 0.5, trench_shore, shore[i]))
		else:
			# (right up to the edge: the steps inside start at the shelf, so they meet; an ease here left a moat)
			out[i] = minf(src[i], shelf)
	return out


# A box blur `r` cells round, of the wet points among wet points (land is left as it is).
static func _blur(src: PackedFloat32Array, cols: int, rows: int, r: int) -> PackedFloat32Array:
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
static func _shore_distance(depth: PackedFloat32Array, cols: int, rows: int) -> PackedFloat32Array:
	var to_land := _chamfer(depth, cols, rows, true)
	var to_water := _chamfer(depth, cols, rows, false)
	var out := PackedFloat32Array()
	out.resize(depth.size())
	for i in depth.size():
		out[i] = (to_land[i] - 0.5 * CELL) if depth[i] > 0.0 else -(to_water[i] - 0.5 * CELL)
	return out


static func _chamfer(depth: PackedFloat32Array, cols: int, rows: int, wet: bool) -> PackedFloat32Array:
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


func _read_asc(path: String) -> void:
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
