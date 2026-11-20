@tool
class_name Layout
## The bay's layout, in one file: data/layout.json (CLAUDE.md, "Decision: the bay's layout in one
## file, edited in the Godot editor"). Every place (the start, the wrecks, the outcrops, Atlantis,
## the docks...), the biomes' outlines, the river's course, the harbours and shelves, the trench's
## outline, the bake's numbers, the spawn zones and where each kind of animal and each school lives.
## The game reads it here (Sea, Scenery, Bay, BiomeRegions, Life, Species keep their old names for
## the values, filled from this); tools/bake_bay.gd reads it to bake the floor; the editor
## (addons/bay_layout, editor/bay_layout.tscn) reads and writes it.
##
## World metres: x east, z south. A point is [x, z] (or [x, y, z]); depths are metres below the
## surface (40).

const PATH := "res://data/layout.json"

static var _data := {}


## The whole table (read the first time it is asked).
static func data() -> Dictionary:
	if _data.is_empty():
		var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(PATH))
		if parsed is Dictionary:
			_data = parsed
		else:
			push_error("Layout: %s could not be read" % PATH)
	return _data


## Forgets what was read (the editor, after saving).
static func reload() -> void:
	_data = {}


## A value by its path ("places.start"), or `fallback`.
static func value(path: String, fallback: Variant = null) -> Variant:
	var at: Variant = data()
	for key in path.split("."):
		if not at is Dictionary or not (at as Dictionary).has(key):
			return fallback
		at = at[key]
	return at


static func v2(a: Variant) -> Vector2:
	return Vector2(float(a[0]), float(a[1]))


static func v3(a: Variant) -> Vector3:
	return Vector3(float(a[0]), float(a[1]), float(a[2]))


## A list of points.
static func line(a: Variant) -> Array:
	var out := []
	for p: Variant in a:
		out.append(v2(p))
	return out


static func point(path: String) -> Vector2:
	return v2(value(path))


static func number(path: String) -> float:
	return float(value(path))


## Sea.ZONES as Sea had it: each {at: Vector2, radius, also: [[Vector2, radius]...], ...}.
static func zones() -> Dictionary:
	var out := {}
	var all: Dictionary = value("zones", {})
	for name: String in all:
		var e: Dictionary = (all[name] as Dictionary).duplicate(true)
		e.at = v2(e.at)
		if e.has("also"):
			var also := []
			for p: Dictionary in e.also:
				also.append([v2(p.at), float(p.radius)])
			e.also = also
		out[name] = e
	return out


## Bay's shelves: [middle, flat, out, depth, slope, (long), (fill only)].
static func shelf(name: String) -> Array:
	var s: Dictionary = value("shelves." + name)
	var out := [v2(s.at), float(s.flat), float(s.out), float(s.deep), v2(s.slope)]
	if s.has("long"):
		out.append(v2(s.long))
	if s.has("fill_only"):
		out.append(bool(s.fill_only))
	return out


## Bay's harbours: [middle, radius, depth] each.
static func harbours() -> Array:
	var out := []
	for h: Dictionary in value("harbours", []):
		out.append([v2(h.at), float(h.radius), float(h.deep)])
	return out


## BiomeRegions' drawn outlines: name -> [[Vector2...]...].
static func shapes() -> Dictionary:
	var out := {}
	var all: Dictionary = value("biomes.shapes", {})
	for name: String in all:
		var list := []
		for shape: Variant in all[name]:
			list.append(line(shape))
		out[name] = list
	return out


## Where a school lives: the zone of the `i`th school of a kind (they take the list in turn).
static func school_zone(kind: String, i: int) -> String:
	var list: Array = value("schools." + kind, [""])
	return String(list[i % list.size()]) if not list.is_empty() else ""


## A kind's own zones and count, as the layout has them (empty if it has none).
static func kind(name: String) -> Dictionary:
	return value("kinds." + name, {})


## The table written out as text: one key a line, short lists of numbers and points on one line,
## numbers as short as they can be and still read back the same.
static func to_text(d: Variant, indent := "") -> String:
	if d is Dictionary:
		var lines := PackedStringArray()
		for key: Variant in d:
			lines.append("%s\t%s: %s" % [indent, JSON.stringify(str(key)), to_text(d[key], indent + "\t")])
		return "{}" if lines.is_empty() else "{\n%s\n%s}" % [",\n".join(lines), indent]
	if d is Array:
		if _flat(d):
			var parts := PackedStringArray()
			for e: Variant in d:
				parts.append(to_text(e, indent))
			return "[%s]" % ", ".join(parts)
		var lines := PackedStringArray()
		for e: Variant in d:
			lines.append("%s\t%s" % [indent, to_text(e, indent + "\t")])
		return "[]" if lines.is_empty() else "[\n%s\n%s]" % [",\n".join(lines), indent]
	if d is float:
		return num(d)
	if d is int:
		return str(d)
	return JSON.stringify(d)


## A number written as short as it can be and still be the same float32 (a Vector2's) when read back.
static func num(v: float) -> String:
	if v == roundf(v) and absf(v) < 1e9:
		return "%.1f" % v
	for places in range(1, 10):
		var s := String.num(v, places)
		var back := float(s)
		if back == v or Vector2(back, 0.0).x == Vector2(v, 0.0).x:
			return s
	return str(v)


# A list written on one line: numbers, strings, or points (lists of up to three numbers).
static func _flat(a: Array) -> bool:
	for e: Variant in a:
		if e is Array:
			if (e as Array).size() > 3:
				return false
			for n: Variant in e:
				if not (n is float or n is int):
					return false
		elif e is Dictionary:
			return false
	return true
