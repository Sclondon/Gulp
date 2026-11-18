extends SceneTree
## Cuts a generated picture of separate objects on a black background into one picture each,
## with the background made clear. Only the black that is joined to the picture's edge is taken
## for background, so dark places inside an object (a well, a shadow) are kept.
##   godot --headless --path . -s res://tools/cut_art.gd -- <picture.png> <out folder> <name> [dark=0.07] [gap=10] [least=40]
## Writes <out>/<name>_<n>.png, numbered left to right then top to bottom, and prints each one's
## place and size in the picture. `dark`: how bright a pixel may be and still count as background;
## `gap`: how many clear pixels apart two things must be to count as separate; `least`: the
## smallest thing kept (pixels across).


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var source: String = args[0]
	var out: String = args[1]
	var named: String = args[2]
	var dark := 0.07
	var gap := 10
	var least := 40
	for arg in args.slice(3):
		if arg.begins_with("dark="):
			dark = float(arg.get_slice("=", 1))
		elif arg.begins_with("gap="):
			gap = int(arg.get_slice("=", 1))
		elif arg.begins_with("least="):
			least = int(arg.get_slice("=", 1))
	var image := Image.load_from_file(source)
	image.convert(Image.FORMAT_RGBA8)
	var w := image.get_width()
	var h := image.get_height()
	# Flood the background in from every edge.
	var clear := PackedByteArray()
	clear.resize(w * h)
	var todo: Array[Vector2i] = []
	for x in w:
		todo.append(Vector2i(x, 0))
		todo.append(Vector2i(x, h - 1))
	for y in h:
		todo.append(Vector2i(0, y))
		todo.append(Vector2i(w - 1, y))
	while not todo.is_empty():
		var p: Vector2i = todo.pop_back()
		if p.x < 0 or p.y < 0 or p.x >= w or p.y >= h or clear[p.y * w + p.x] == 1:
			continue
		var c := image.get_pixel(p.x, p.y)
		if maxf(c.r, maxf(c.g, c.b)) > dark:
			continue
		clear[p.y * w + p.x] = 1
		todo.append(Vector2i(p.x + 1, p.y))
		todo.append(Vector2i(p.x - 1, p.y))
		todo.append(Vector2i(p.x, p.y + 1))
		todo.append(Vector2i(p.x, p.y - 1))
	# Clear it, softening the edge by a pixel (a pixel with clear neighbours is half clear).
	for y in h:
		for x in w:
			if clear[y * w + x] == 1:
				image.set_pixel(x, y, Color(0, 0, 0, 0))
			else:
				var open := 0
				for d: Vector2i in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
					var q := Vector2i(x, y) + d
					if q.x >= 0 and q.y >= 0 and q.x < w and q.y < h and clear[q.y * w + q.x] == 1:
						open += 1
				if open > 0:
					var c := image.get_pixel(x, y)
					image.set_pixel(x, y, Color(c.r, c.g, c.b, 1.0 - 0.22 * open))
	# The things in it: rows of things first (bands of the picture with something in), then each
	# row's things by the runs of columns with something in.
	var found: Array[Rect2i] = []
	for band: Vector2i in _runs(func(y: int) -> bool: return _row_has(clear, w, y, 0, w), h, gap):
		for run: Vector2i in _runs(func(x: int) -> bool: return _column_has(clear, w, x, band.x, band.y), w, gap):
			# (tighten the band to this thing)
			var top := band.x
			while top < band.y and not _row_has(clear, w, top, run.x, run.y):
				top += 1
			var bottom := band.y
			while bottom > top and not _row_has(clear, w, bottom - 1, run.x, run.y):
				bottom -= 1
			var box := Rect2i(run.x, top, run.y - run.x, bottom - top)
			if box.size.x >= least and box.size.y >= least:
				found.append(box)
	DirAccess.make_dir_recursive_absolute(out)
	for i in found.size():
		var box := found[i].grow(2).intersection(Rect2i(0, 0, w, h))
		var piece := image.get_region(box)
		var path := "%s/%s_%d.png" % [out, named, i + 1]
		piece.save_png(path)
		print("CUT %s at %d,%d size %dx%d" % [path.get_file(), box.position.x, box.position.y, box.size.x, box.size.y])
	print("CUT %d things from a picture %dx%d" % [found.size(), w, h])
	quit()


# The runs of lines for which `has` is true, joining runs less than `gap` apart: each [from, to).
func _runs(has: Callable, count: int, gap: int) -> Array[Vector2i]:
	var runs: Array[Vector2i] = []
	var start := -1
	var empty := 0
	for i in count:
		if has.call(i):
			if start < 0:
				start = i
			empty = 0
		elif start >= 0:
			empty += 1
			if empty >= gap:
				runs.append(Vector2i(start, i - empty + 1))
				start = -1
	if start >= 0:
		runs.append(Vector2i(start, count - empty))
	return runs


func _row_has(clear: PackedByteArray, w: int, y: int, from: int, to: int) -> bool:
	for x in range(from, to):
		if clear[y * w + x] == 0:
			return true
	return false


func _column_has(clear: PackedByteArray, w: int, x: int, from: int, to: int) -> bool:
	for y in range(from, to):
		if clear[y * w + x] == 0:
			return true
	return false
