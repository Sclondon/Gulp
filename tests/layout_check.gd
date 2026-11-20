extends SceneTree
## Fingerprints the bay's layout as the game sees it, so that moving the layout's numbers somewhere
## else (data/layout.json, 2026-11-20) can be shown to change nothing: the floor (`Bay.ground` and
## the shore distance on the 2 m grid), the biomes (`BiomeRegions.at` and `weight`), the zones
## (`Sea.zone_at`, and places drawn in each with a fixed seed), the places, and every kind's zones
## and count. Prints one line per part and an ALL line; with --out=<file> also writes every value.
##   godot --headless --path . --audio-driver Dummy -s res://tests/layout_check.gd -- [--out=<file>]

var _parts := {}
var _dump := PackedStringArray()


func _initialize() -> void:
	var out := ""
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):
			out = arg.get_slice("=", 1)
	var t := Time.get_ticks_msec()
	_floor()
	_biomes()
	_zones()
	_places()
	_kinds()
	var all := ""
	for part: String in _parts:
		print("LAYOUT %s %s" % [part, _parts[part]])
		all += _parts[part]
	print("LAYOUT ALL %s (%d ms)" % [all.md5_text(), Time.get_ticks_msec() - t])
	if out != "":
		var f := FileAccess.open(out, FileAccess.WRITE)
		f.store_string("\n".join(_dump))
	quit()


func _add(part: String, lines: PackedStringArray) -> void:
	_parts[part] = "\n".join(lines).md5_text()
	for line in lines:
		_dump.append(part + " " + line)


func _floor() -> void:
	var lines := PackedStringArray()
	var z := Bay.NORTH
	while z <= Bay.SOUTH:
		var row := PackedStringArray()
		var x := Bay.WEST
		while x <= Bay.EAST:
			row.append("%.4f/%.3f" % [Bay.ground(x, z), Bay.shore_distance(Vector2(x, z))])
			x += Bay.GRID
		lines.append(" ".join(row))
		z += Bay.GRID
	_add("floor", lines)


func _biomes() -> void:
	var lines := PackedStringArray()
	var z := Bay.NORTH
	while z <= Bay.SOUTH:
		var row := PackedStringArray()
		var x := Bay.WEST
		while x <= Bay.EAST:
			var b := BiomeRegions.at(x, z)
			row.append("%s:%.3f" % [b, BiomeRegions.weight(b, x, z) if b != "" else 0.0])
			x += Bay.GRID
		lines.append(" ".join(row))
		z += Bay.GRID
	_add("biomes", lines)


func _zones() -> void:
	var lines := PackedStringArray()
	var z := Bay.NORTH
	while z <= Bay.SOUTH:
		var row := PackedStringArray()
		var x := Bay.WEST
		while x <= Bay.EAST:
			row.append(Sea.zone_at(x, z))
			x += 4.0
		lines.append(" ".join(row))
		z += 4.0
	var rng := RandomNumberGenerator.new()
	rng.seed = 11
	for zone: String in Sea.ZONES:
		lines.append("%s %s" % [zone, Sea.ZONES[zone]])
		for i in 6:
			lines.append("%s %s" % [zone, Sea.place(rng, zone, 0.5)])
	_add("zones", lines)


func _places() -> void:
	var lines := PackedStringArray()
	for each: Array in [["start", Sea.START], ["liner", Sea.WRECK_AT], ["liner_heading", Sea.WRECK_HEADING],
			["pirate", Sea.PIRATE_AT], ["pirate_heading", Sea.PIRATE_HEADING], ["atlantis", Sea.RUINS_AT],
			["markets", Sea.MARKETS], ["outcrop", Scenery.OUTCROP], ["outcrop_south", Scenery.OUTCROP_SOUTH],
			["docks_monterey", Scenery.MONTEREY], ["docks_santa_cruz", Scenery.SANTA_CRUZ], ["arch", Scenery.ARCH],
			["carmel_pier", Scenery.CARMEL_PIER], ["old_one", Scenery.OLD_ONE_AT], ["reef_back", Scenery.REEF_BACK_LOOP],
			["eels", Scenery.EEL_COLONIES], ["anchors", Scenery.DUNE_ANCHORS], ["slough", Bay.SLOUGH],
			["slough_size", [Bay.SLOUGH_HALF, Bay.SLOUGH_DEEP, Bay.SLOUGH_BANK]], ["harbours", Bay.HARBOURS],
			["seats", [Bay.WRECK_SHELF, Bay.WRECK_SEAT_SOUTH, Bay.PIRATE_HOLLOW]], ["shapes", BiomeRegions.SHAPES],
			["estuary", BiomeRegions.ESTUARY], ["ruins_clear", BiomeRegions.RUINS_CLEAR], ["fishers_start", Fishers.START],
			["home", [Life.HOME_ROOM, Life.HOME_DEPTH]]]:
		lines.append("%s %s" % [each[0], each[1]])
	_add("places", lines)


func _kinds() -> void:
	var lines := PackedStringArray()
	for kind: String in Species.ALL:
		var entry := Species.of(kind)
		lines.append("%s %s %d" % [kind, entry.get("zones", []), int(entry.get("count", 0))])
	_add("kinds", lines)
