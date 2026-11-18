extends SceneTree
## A preview of the sea built from Monterey Bay's real depths (GMRT's grid, which carries MBARI's
## multibeam of the bay), fitted to the game: the real bay squeezed to SCALE real metres a game
## metre, and the depths squeezed by `game_depth` (true in the shallows, then by a log curve, so the
## shelf stays swimmable and the canyon still drops to about 100 m). Nothing in the game uses it yet.
##
##   godot --path . --audio-driver Dummy --resolution 400x400 -s res://tools/bay_real.gd -- --grid=<bay.asc> --out=<png>
##
## The grid (ESRI ASCII) from:
##   https://www.gmrt.org/services/GridServer?north=37.02&west=-122.25&east=-121.75&south=36.45&layer=topo&format=esriascii&resolution=high

## Real metres to a game metre.
const SCALE := 180.0
## The part of the bay used (degrees).
const WEST_LON := -122.25
const EAST_LON := -121.75
const SOUTH_LAT := 36.48
const NORTH_LAT := 37.0
## Pixels a game metre in the preview.
const PX := 4.0

const PLACES := {
	"Santa Cruz wharf": Vector2(-122.017, 36.957),
	"Capitola": Vector2(-121.953, 36.972),
	"Moss Landing / Elkhorn Slough": Vector2(-121.788, 36.806),
	"Monterey wharf": Vector2(-121.893, 36.604),
	"Cannery Row": Vector2(-121.901, 36.617),
	"Point Pinos": Vector2(-121.936, 36.637),
	"Cypress Point": Vector2(-121.977, 36.581),
	"Carmel": Vector2(-121.925, 36.553),
	"Point Lobos": Vector2(-121.951, 36.518),
	"Monterey Canyon": Vector2(-121.96, 36.775),
	"Soquel Canyon": Vector2(-121.94, 36.875),
	"Carmel Canyon": Vector2(-121.99, 36.53),
}

var _cols := 0
var _rows := 0
var _x0 := 0.0
var _y0 := 0.0
var _cell := 0.0
var _z := PackedFloat32Array()


## How deep the game's floor is (m) for a real depth (m, positive down).
static func game_depth(real: float) -> float:
	if real <= 10.0:
		return real
	if real <= 100.0:
		return 10.0 + 15.0 * log(real / 10.0) / log(10.0)
	return 25.0 + 75.0 * log(real / 100.0) / log(20.0)


func _initialize() -> void:
	var grid := ""
	var out := ""
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--grid="):
			grid = arg.get_slice("=", 1)
		elif arg.begins_with("--out="):
			out = arg.get_slice("=", 1)
	_read(grid)
	_draw(out)


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
	print("BAY grid %d x %d, %d values" % [_cols, _rows, k])


# Height (m, + up) at a longitude and latitude, bilinear.
func _height(lon: float, lat: float) -> float:
	var gx := clampf((lon - _x0) / _cell - 0.5, 0.0, _cols - 1.001)
	var gy := clampf((_y0 + _rows * _cell - lat) / _cell - 0.5, 0.0, _rows - 1.001)
	var ix := int(gx)
	var iy := int(gy)
	var fx := gx - ix
	var fy := gy - iy
	var a := _z[iy * _cols + ix]
	var b := _z[iy * _cols + ix + 1]
	var c := _z[(iy + 1) * _cols + ix]
	var d := _z[(iy + 1) * _cols + ix + 1]
	return lerpf(lerpf(a, b, fx), lerpf(c, d, fx), fy)


func _metres_per_lon() -> float:
	return 111320.0 * cos(deg_to_rad((SOUTH_LAT + NORTH_LAT) * 0.5))


# Game height of the floor: below 0 is under water (the depth, game metres); land above 0 is kept low.
func _game(lon: float, lat: float) -> float:
	var h := _height(lon, lat)
	if h >= 0.0:
		return minf(h * 0.05, 8.0)
	return -game_depth(-h)


func _draw(out: String) -> void:
	var wide := (EAST_LON - WEST_LON) * _metres_per_lon() / SCALE
	var high := (NORTH_LAT - SOUTH_LAT) * 111320.0 / SCALE
	var w := int(wide * PX)
	var h := int(high * PX)
	print("BAY game size %.0f x %.0f m (real %.1f x %.1f km), picture %d x %d" % [wide, high, wide * SCALE / 1000.0, high * SCALE / 1000.0, w, h])
	var heights := PackedFloat32Array()
	heights.resize(w * h)
	for y in h:
		var lat := NORTH_LAT - (y + 0.5) / h * (NORTH_LAT - SOUTH_LAT)
		for x in w:
			var lon := WEST_LON + (x + 0.5) / w * (EAST_LON - WEST_LON)
			heights[y * w + x] = _game(lon, lat)
	var img := Image.create(w, h, false, Image.FORMAT_RGB8)
	var light := Vector3(-0.6, 0.7, -0.5).normalized()
	var deepest := 0.0
	for y in h:
		for x in w:
			var g := heights[y * w + x]
			deepest = minf(deepest, g)
			var gx := heights[y * w + mini(x + 1, w - 1)] - heights[y * w + maxi(x - 1, 0)]
			var gy := heights[mini(y + 1, h - 1) * w + x] - heights[maxi(y - 1, 0) * w + x]
			var n := Vector3(-gx * PX * 0.5, 1.0, -gy * PX * 0.5).normalized()
			var shade := clampf(n.dot(light), 0.0, 1.0) * 0.6 + 0.5
			var c: Color
			if g >= 0.0:
				c = Color(0.62, 0.58, 0.45).lerp(Color(0.45, 0.5, 0.32), clampf(g / 8.0, 0.0, 1.0))
			else:
				var t := clampf(-g / 100.0, 0.0, 1.0)
				c = Color(0.72, 0.93, 0.92).lerp(Color(0.22, 0.6, 0.78), smoothstep(0.0, 0.25, t)).lerp(Color(0.03, 0.1, 0.32), smoothstep(0.2, 1.0, t))
				# (a line every 5 game metres of depth, darker every 25)
				var band := fmod(-g, 5.0)
				if band < 0.35:
					c = c.darkened(0.35 if fmod(-g, 25.0) < 0.35 else 0.15)
			img.set_pixel(x, y, Color(c.r * shade, c.g * shade, c.b * shade))
	print("BAY deepest %.1f game m" % -deepest)
	await _label(img, out, w, h)
	quit()


func _label(img: Image, out: String, w: int, h: int) -> void:
	var sheet := SubViewport.new()
	sheet.size = Vector2i(w, h)
	sheet.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(sheet)
	var picture := TextureRect.new()
	picture.texture = ImageTexture.create_from_image(img)
	picture.size = Vector2(w, h)
	sheet.add_child(picture)
	for name: String in PLACES:
		var p: Vector2 = PLACES[name]
		var at := Vector2((p.x - WEST_LON) / (EAST_LON - WEST_LON) * w, (NORTH_LAT - p.y) / (NORTH_LAT - SOUTH_LAT) * h)
		var dot := ColorRect.new()
		dot.color = Color(1.0, 0.3, 0.2)
		dot.size = Vector2(8, 8)
		dot.position = at - Vector2(4, 4)
		sheet.add_child(dot)
		var label := Label.new()
		label.text = name
		label.add_theme_font_size_override(&"font_size", 22)
		label.add_theme_color_override(&"font_color", Color(1.0, 0.95, 0.5))
		label.add_theme_color_override(&"font_outline_color", Color.BLACK)
		label.add_theme_constant_override(&"outline_size", 6)
		label.position = at + Vector2(8, -14)
		sheet.add_child(label)
	var bar := ColorRect.new()
	bar.size = Vector2(50.0 * PX, 6.0)
	bar.position = Vector2(20.0, h - 30.0)
	sheet.add_child(bar)
	var note := Label.new()
	note.text = "50 game m (9 km real); lines every 5 game m of depth"
	note.add_theme_font_size_override(&"font_size", 20)
	note.add_theme_constant_override(&"outline_size", 6)
	note.add_theme_color_override(&"font_outline_color", Color.BLACK)
	note.position = Vector2(20.0, h - 62.0)
	sheet.add_child(note)
	for frame in 3:
		await process_frame
	await RenderingServer.frame_post_draw
	sheet.get_texture().get_image().save_png(out)
	print("BAY saved ", out)
