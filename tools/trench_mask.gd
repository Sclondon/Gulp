extends SceneTree
## Where the trench is: the user's own lines (2026-11-18, drawn in red over the overhead chart, 1600 x 2000,
## 6.25 pixels a metre from (Bay.WEST, Bay.NORTH): tools/art_src/user_trench_lines.png; "The trench area
## needs to be skinner, just showing roughish boundaries") made into a mask of the deep water, which
## tools/bake_bay.gd reads: outside it the floor is raised to the shelf, inside the canyon keeps its depth.
##
##   godot --headless --path . -s res://tools/trench_mask.gd -- [--preview=<png>]
##
## The lines' loose ends are joined to the shore or the map's edge (CLOSE: Claude's reading of where
## each was going), the land stops the fill too, and the deep places are filled from SEEDS. Writes
## data/trench_mask.png: one pixel a metre over the bake's grid, white in the trench.

const LINES := "res://tools/art_src/user_trench_lines.png"
const OUT := "res://data/trench_mask.png"
const PER_M := 6.25
## Segments (pixels) that close the lines' ends: to the map's edge, to the shore, over a gap in a dash.
const CLOSE := [
	[Vector2(30, 190), Vector2(0, 160)],
	[Vector2(1325, 720), Vector2(1470, 700)],
	[Vector2(1190, 825), Vector2(1330, 788)],
	[Vector2(1325, 790), Vector2(1470, 815)],
	[Vector2(900, 1720), Vector2(990, 1716)],
	[Vector2(878, 1795), Vector2(990, 1800)],
	[Vector2(118, 1765), Vector2(0, 1690)],
]
## Points in the deep water (pixels): the canyon by Moss Landing, the Soquel branch, the open water
## in the west, the deep south of the old Atlantis, the Carmel Canyon.
const SEEDS := [Vector2(1000, 880), Vector2(840, 700), Vector2(50, 600), Vector2(300, 1400), Vector2(700, 1745)]
## How far the deep water is spread over the lines themselves (pixels: the lines are about 14 wide).
const OVER := 9


func _initialize() -> void:
	Bay._load()
	var preview := ""
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--preview="):
			preview = arg.get_slice("=", 1)
	var src := Image.load_from_file(LINES)
	var w := src.get_width()
	var h := src.get_height()
	var wall := PackedByteArray()
	wall.resize(w * h)
	for y in h:
		for x in w:
			var c := src.get_pixel(x, y)
			if c.r > 0.75 and c.g < 0.4 and c.b < 0.4 and c.r - c.g > 0.45:
				wall[y * w + x] = 1
	for seg: Array in CLOSE:
		var a: Vector2 = seg[0]
		var b: Vector2 = seg[1]
		var steps := int(a.distance_to(b)) + 1
		for s in steps + 1:
			var p := a.lerp(b, float(s) / steps)
			for dy in range(-6, 7):
				for dx in range(-6, 7):
					var x := int(p.x) + dx
					var y := int(p.y) + dy
					if x >= 0 and y >= 0 and x < w and y < h:
						wall[y * w + x] = 1
	# (the land stops it too)
	for y in range(0, h, 1):
		for x in range(0, w, 1):
			if Bay.shore_distance(Vector2(Bay.WEST + (x + 0.5) / PER_M, Bay.NORTH + (y + 0.5) / PER_M)) < 0.0:
				wall[y * w + x] = 1
	# The fill, from each seed.
	var deep := PackedByteArray()
	deep.resize(w * h)
	var queue := PackedInt32Array()
	for seed: Vector2 in SEEDS:
		var i := int(seed.y) * w + int(seed.x)
		if wall[i] == 0 and deep[i] == 0:
			deep[i] = 1
			queue.append(i)
	var head := 0
	while head < queue.size():
		var i := queue[head]
		head += 1
		var x := i % w
		var y := i / w
		for n: int in [i - 1 if x > 0 else -1, i + 1 if x < w - 1 else -1, i - w if y > 0 else -1, i + w if y < h - 1 else -1]:
			if n >= 0 and wall[n] == 0 and deep[n] == 0:
				deep[n] = 1
				queue.append(n)
	# Over the lines (so two deep places either side of one line meet; a line with the shelf on its
	# other side keeps its edge where it was drawn, give or take half its width).
	var spread := deep.duplicate()
	for pass_k in OVER:
		var next := spread.duplicate()
		for y in range(1, h - 1):
			for x in range(1, w - 1):
				var i := y * w + x
				if spread[i] == 0 and wall[i] == 1 and (spread[i - 1] == 1 or spread[i + 1] == 1 or spread[i - w] == 1 or spread[i + w] == 1):
					next[i] = 1
		spread = next
	# (not up the slough at Moss Landing: the canyon's head ends at the shore; east of x 100 m, none)
	for y in h:
		for x in range(int((100.0 - Bay.WEST) * PER_M), w):
			spread[y * w + x] = 0
	print("MASK filled %d of %d pixels" % [queue.size(), w * h])
	# At a metre a pixel, over the bake's grid.
	var cols := int(round((Bay.EAST - Bay.WEST))) + 1
	var rows := int(round((Bay.SOUTH - Bay.NORTH))) + 1
	var out := Image.create(cols, rows, false, Image.FORMAT_L8)
	for r in rows:
		for c in cols:
			var px := clampi(int(c * PER_M), 0, w - 1)
			var py := clampi(int(r * PER_M), 0, h - 1)
			out.set_pixel(c, r, Color.WHITE if spread[py * w + px] == 1 else Color.BLACK)
	out.save_png(OUT)
	print("MASK saved %s (%d x %d)" % [OUT, cols, rows])
	if preview != "":
		var view := Image.create(w, h, false, Image.FORMAT_RGB8)
		for y in h:
			for x in w:
				var i := y * w + x
				var base := src.get_pixel(x, y)
				view.set_pixel(x, y, base.lerp(Color(0.1, 0.3, 1.0), 0.45) if spread[i] == 1 else base)
		view.save_png(preview)
	quit()
