@tool
extends Node3D
## The bay editor (editor/bay_layout.tscn; README, "Editing the bay"): the whole layout of the bay as
## things to drag in the Godot editor, read from data/layout.json when the scene opens and written back
## when it is saved (ctrl+S, or the Save button of the bay bar). Nothing of the game runs here: the floor
## is a picture of the game's floor made by a quick separate process (floor_dump.gd), the set pieces
## are light stand-ins. Everything it makes is kept out of the scene file itself (the scene holds only
## this node): the layout file is the one source.
##
## CLAUDE.md, "Decision: the bay's layout in one file, edited in the Godot editor".

const BAKE := preload("res://addons/bay_layout/bay_bake.gd")
const FLOOR := preload("res://addons/bay_layout/bay_floor.gd")
const PLACE := preload("res://addons/bay_layout/bay_place.gd")
const CIRCLE := preload("res://addons/bay_layout/bay_circle.gd")
const OUTLINE := preload("res://addons/bay_layout/bay_outline.gd")
const DATA := preload("res://addons/bay_layout/bay_data.gd")
const RUINS_LAYOUT := "res://data/ruins_layout.json"
## The picture of the floor (floor_dump.gd's file), kept with the editor's own files.
const DUMP := "res://.godot/editor/bay_layout_floor.bin"
## Where outlines and rings are drawn (world y: over the water and the land).
const HIGH := 44.5
## How closely the trench's outline follows the drawn mask it is traced from (m).
const TRACE := 0.6
const BIOME_COLOURS := {"kelp": Color(0.1, 0.9, 0.2), "dunes": Color(1.0, 0.9, 0.1), "grass": Color(1.0, 0.3, 0.3),
		"crags": Color(0.95, 0.3, 0.95), "reef": Color(1.0, 0.55, 0.1)}
## The places: key, name, stand-in shape, size, colour, keeps its height, turns.
const PLACES := [
	["start", "Start", "sphere", Vector3(2.0, 2.0, 2.0), Color(1.0, 1.0, 0.6), false, false],
	["liner", "Liner", "box", Vector3(14.0, 10.0, 64.0), Color(0.6, 0.35, 0.25), true, true],
	["pirate", "Pirate ship", "box", Vector3(12.0, 8.0, 34.0), Color(0.45, 0.3, 0.18), true, true],
	["atlantis", "Atlantis", "box", Vector3(40.0, 6.0, 40.0), Color(0.85, 0.85, 0.75), true, false],
	["outcrop", "Seal rock", "cylinder", Vector3(16.0, 40.0, 16.0), Color(0.45, 0.42, 0.4), false, false],
	["outcrop_south", "South islet", "cylinder", Vector3(14.0, 40.0, 14.0), Color(0.45, 0.42, 0.4), false, false],
	["docks_monterey", "Monterey docks", "box", Vector3(18.0, 4.0, 18.0), Color(0.55, 0.4, 0.25), false, false],
	["docks_santa_cruz", "Santa Cruz docks", "box", Vector3(18.0, 4.0, 18.0), Color(0.55, 0.4, 0.25), false, false],
	["arch", "Kelp arch", "box", Vector3(10.0, 8.0, 3.0), Color(0.5, 0.45, 0.4), false, false],
	["carmel_pier", "Carmel pier", "box", Vector3(3.0, 4.0, 12.0), Color(0.55, 0.4, 0.25), false, false],
	["old_one", "Old one (asleep)", "sphere", Vector3(10.0, 10.0, 10.0), Color(0.2, 0.25, 0.2), false, false],
]

var floor_node: MeshInstance3D
## The layout as read (what is saved is this, with what the nodes say written over it).
var _layout := {}
var _made: Array[Node] = []
var _traced := ""
var _atlantis_was := Vector2.ZERO
var _pid := -1
var _after_refresh: Callable
## What the last refresh of the floor said (shown in the bay bar).
var status := ""


func _ready() -> void:
	build()


## Makes every handle from the layout file (anything made before is dropped).
func build() -> void:
	var t := Time.get_ticks_msec()
	for node in _made:
		if is_instance_valid(node):
			node.free()
	_made.clear()
	Layout.reload()
	_layout = Layout.data().duplicate(true)
	floor_node = _add(self, FLOOR.new(), "Floor")
	floor_node.load_dump(_dump_path())
	var places := _add(self, Node3D.new(), "Places")
	var by_key := {}
	for spec: Array in PLACES:
		by_key[spec[0]] = _make_place(places, spec)
	var p: Dictionary = _layout.places
	_set_xz(by_key.start, Layout.v2(p.start))
	for key: String in ["liner", "pirate", "atlantis"]:
		var node: Node3D = by_key[key]
		node.position = Layout.v3(p[key].at)
		node.rotation.y = float(p[key].get("heading", 0.0))
	_atlantis_was = Layout.v2([p.atlantis.at[0], p.atlantis.at[2]])
	for key: String in ["outcrop", "outcrop_south", "docks_monterey", "docks_santa_cruz", "arch", "carmel_pier", "old_one"]:
		_set_xz(by_key[key], Layout.v2(p[key]))
	var home: Dictionary = _layout.get("home", {})
	(by_key.start as Node).set(&"extra", {"room": Layout.v2(home.get("room", [6, 14])), "depth": Layout.v2(home.get("depth", [4, 9]))})
	for market: String in p.markets:
		var node := _make_place(places, ["market:" + market, "Market " + market.capitalize(), "cylinder", Vector3(3.0, 6.0, 3.0), Color(1.0, 0.8, 0.2), false, false])
		_set_xz(node, Layout.v2(p.markets[market]))
	var back: Dictionary = p.reef_back
	_make_circle(places, "reef_back", "Reef-back's walk", Layout.v2(back.at), float(back.radius), 0.0, Color(0.6, 0.8, 0.5))
	var n := 0
	for a: Dictionary in _layout.get("dune_anchors", []):
		n += 1
		var node := _make_place(places, ["dune_anchor", "Dune anchor %d" % n, "box", Vector3(2.0, 3.0, 1.0), Color(0.25, 0.22, 0.2), false, true])
		_set_xz(node, Layout.v2(a.at))
		node.rotation.y = float(a.turn)
		node.set(&"extra", {"size": float(a.size)})
	n = 0
	for c: Dictionary in _layout.get("eel_colonies", []):
		n += 1
		var o := _make_outline(places, "eels", "Garden eels %d" % n, [Layout.v2(c.from), Layout.v2(c.to)], false, Color(0.95, 0.95, 0.8))
		o.set(&"extra", {"count": int(c.count)})
	# Shelves, zones, harbours and areas that belong to a set piece are its children: they move with it.
	var shelves: Dictionary = _layout.shelves
	for name: String in shelves:
		var s: Dictionary = shelves[name]
		var owner_node: Node3D = by_key.liner if name.begins_with("liner") else (by_key.pirate if name.begins_with("pirate") else self)
		var circle := _make_circle(owner_node, "shelf:" + name, "Shelf " + name.replace("_", " "), Layout.v2(s.at), float(s.flat), float(s.out), Color(0.9, 0.9, 0.9))
		circle.set(&"depth", float(s.deep))
		var extra := {"slope": Layout.v2(s.slope)}
		if s.has("long"):
			extra["long"] = Layout.v2(s.long)
		if s.has("fill_only"):
			extra["fill_only"] = bool(s.fill_only)
		circle.set(&"extra", extra)
	var harbours := _add(self, Node3D.new(), "Harbours")
	n = 0
	for h: Dictionary in _layout.get("harbours", []):
		n += 1
		var at := Layout.v2(h.at)
		var parent: Node3D = harbours
		for key: String in ["docks_monterey", "docks_santa_cruz", "carmel_pier"]:
			if Layout.v2(p[key]).distance_to(at) < 25.0:
				parent = by_key[key]
		var circle := _make_circle(parent, "harbour", "Harbour %d" % n, at, float(h.radius), 0.0, Color(0.5, 0.7, 1.0))
		circle.set(&"depth", float(h.deep))
	# The biomes' outlines (the reef's goes with the liner).
	var biomes := _add(self, Node3D.new(), "Biomes")
	var shapes: Dictionary = _layout.biomes.shapes
	for biome: String in shapes:
		var group: Node3D = by_key.liner if biome == "reef" else _add(biomes, Node3D.new(), biome.capitalize())
		var k := 0
		for shape: Array in shapes[biome]:
			k += 1
			_make_outline(group, "biome:" + biome, "%s %d" % [biome.capitalize(), k], Layout.line(shape), true, BIOME_COLOURS.get(biome, Color.WHITE))
	var clear: Dictionary = _layout.biomes.ruins_clear
	_make_circle(by_key.atlantis, "ruins_clear", "Atlantis basin (no trench plants)", Layout.v2(clear.at), float(clear.radius), 0.0, Color(0.6, 0.6, 1.0))
	n = 0
	for box: Array in _layout.get("dune_fields", []):
		n += 1
		var x := float(box[0])
		var z := float(box[1])
		var w := float(box[2])
		var h := float(box[3])
		_make_outline(biomes, "dune_field", "Dune field %d (box)" % n, [Vector2(x, z), Vector2(x + w, z), Vector2(x + w, z + h), Vector2(x, z + h)], true, Color(0.8, 0.7, 0.2))
	var numbers := _add(biomes, DATA.new(), "Biome numbers")
	numbers.set(&"key", "biomes")
	numbers.set(&"values", {"edge": _layout.biomes.edge, "trench_deep": _layout.biomes.trench_deep, "beach_deep": _layout.biomes.beach_deep})
	# The river.
	var river: Dictionary = _layout.river
	var course := _make_outline(self, "river", "River", Layout.line(river.course), false, Color(0.65, 0.45, 0.2))
	course.set(&"extra", {"half": river.half, "deep": river.deep, "bank": river.bank, "banks": river.banks})
	var mouth := _make_circle(course, "estuary", "River mouth", Layout.v2(river.estuary), float(river.mouth), 0.0, Color(0.65, 0.45, 0.2))
	mouth.set(&"extra", {"mouth_deep": river.mouth_deep})
	# The trench.
	var trench := _add(self, Node3D.new(), "Trench")
	var t_data: Dictionary = _layout.get("trench", {})
	var loops: Array = []
	if not (t_data.get("shapes", []) as Array).is_empty():
		for s: Array in t_data.shapes:
			loops.append(Layout.line(s))
		_traced = ""
	else:
		loops = trace_trench()
		_traced = _text_of(loops)
	n = 0
	for loop: Array in loops:
		n += 1
		_make_outline(trench, "trench", "Trench %d" % n, loop, true, Color(0.35, 0.4, 1.0))
	var floor_numbers := _add(trench, DATA.new(), "Floor numbers")
	floor_numbers.set(&"key", "bake")
	floor_numbers.set(&"values", (_layout.get("bake", {}) as Dictionary).duplicate(true))
	# The spawn zones, with the kinds that live in each (those of a set piece go with it).
	var zones := _add(self, Node3D.new(), "Zones")
	var kinds: Dictionary = _layout.get("kinds", {})
	for zone: String in _layout.zones:
		var e: Dictionary = _layout.zones[zone]
		var parent: Node3D = zones
		match zone:
			"reef": parent = by_key.liner
			"pirate": parent = by_key.pirate
			"ruins": parent = by_key.atlantis
			"docks": parent = by_key.docks_monterey
		var living := PackedStringArray()
		for kind: String in kinds:
			if zone in (kinds[kind].zones as Array):
				living.append(kind)
		var circle := _make_circle(parent, "zone:" + zone, "Zone %s (%d kinds)" % [zone, living.size()], Layout.v2(e.at), float(e.radius), 0.0,
				Color(0.4, 1.0, 0.9) if not e.has("region") else Color(0.4, 0.7, 0.65))
		circle.set(&"kinds", living)
		var extra := {}
		for key: String in e:
			if key not in ["at", "radius", "also"]:
				extra[key] = e[key]
		circle.set(&"extra", extra)
		for also: Dictionary in e.get("also", []):
			var at := Layout.v2(also.at)
			var also_parent: Node3D = by_key.docks_santa_cruz if zone == "docks" and at.distance_to(Layout.v2(p.docks_santa_cruz)) < 25.0 else zones
			_make_circle(also_parent, "zone_also:" + zone, "Zone %s (more)" % zone, at, float(also.radius), 0.0, Color(0.4, 1.0, 0.9))
	var animals := _add(self, DATA.new(), "Animals")
	animals.set(&"key", "kinds_count")
	var counts := {}
	for kind: String in kinds:
		counts[kind] = int(kinds[kind].count)
	animals.set(&"values", counts)
	var schools := _add(self, DATA.new(), "Schools")
	schools.set(&"key", "schools")
	var school_zones := {}
	for school: String in _layout.get("schools", {}):
		school_zones[school] = PackedStringArray(_layout.schools[school])
	schools.set(&"values", school_zones)
	_seat_on_floor()
	status = "opened in %d ms" % (Time.get_ticks_msec() - t)
	if Engine.is_editor_hint() and _dump_stale():
		refresh_floor(false)


## Writes the layout (data/layout.json; the floor's edits; Atlantis's table if it moved). Returns true
## if what changed needs the floor baked again.
func save_layout() -> bool:
	var d := _layout.duplicate(true)
	var p: Dictionary = d.places
	var bake_before := _text_of([d.get("bake", {}), d.get("trench", {})])
	var markets := {}
	var anchors := []
	var eels := []
	for node in _all(self):
		if node.get_script() == PLACE:
			var key: String = node.get(&"key")
			var at := Vector2(node.global_position.x, node.global_position.z)
			if key in ["liner", "pirate", "atlantis"]:
				p[key].at = _arr3(node.global_position)
				if node.get(&"turns"):
					p[key].heading = snappedf(node.global_rotation.y, 0.0001)
			elif key == "start":
				p.start = _arr(at)
				var extra: Dictionary = node.get(&"extra")
				d["home"] = {"room": _arr(extra.room), "depth": _arr(extra.depth)}
			elif key.begins_with("market:"):
				markets[key.get_slice(":", 1)] = _arr(at)
			elif key == "dune_anchor":
				anchors.append({"at": _arr(at), "size": float(node.get(&"extra").get("size", 2.0)), "turn": snappedf(node.global_rotation.y, 0.0001)})
			elif p.has(key):
				p[key] = _arr(at)
	p.markets = markets
	d.dune_anchors = anchors
	var shapes := {}
	for biome: String in d.biomes.shapes:
		shapes[biome] = []
	var trench := []
	var harbours := []
	var fields := []
	var zones := {}
	for zone: String in d.zones:
		zones[zone] = null
	var also := {}
	var kinds_in := {}
	for node in _all(self):
		if node.get_script() == OUTLINE:
			var role: String = node.get(&"role")
			var pts: PackedVector2Array = node.call(&"points")
			var flat := []
			for q in pts:
				flat.append(_arr(q))
			if role.begins_with("biome:"):
				var biome := role.get_slice(":", 1)
				if not shapes.has(biome):
					shapes[biome] = []
				if flat.size() >= 3:
					shapes[biome].append(flat)
			elif role == "trench":
				if pts.size() >= 3:
					trench.append(pts)
			elif role == "river":
				var extra: Dictionary = node.get(&"extra")
				d.river.course = flat
				for key: String in extra:
					d.river[key] = extra[key]
			elif role == "eels" and pts.size() >= 2:
				eels.append({"from": flat[0], "to": flat[-1], "count": int(node.get(&"extra").get("count", 50))})
			elif role == "dune_field" and pts.size() >= 2:
				var box := Rect2(pts[0], Vector2.ZERO)
				for q in pts:
					box = box.expand(q)
				fields.append([box.position.x, box.position.y, box.size.x, box.size.y])
		elif node.get_script() == CIRCLE:
			var role: String = node.get(&"role")
			var at := _arr(Vector2(node.global_position.x, node.global_position.z))
			var r := float(node.get(&"radius"))
			if role.begins_with("zone:"):
				var zone := role.get_slice(":", 1)
				var e := {"at": at, "radius": r}
				var extra: Dictionary = node.get(&"extra")
				for key: String in extra:
					e[key] = extra[key]
				zones[zone] = e
				kinds_in[zone] = node.get(&"kinds")
			elif role.begins_with("zone_also:"):
				var zone := role.get_slice(":", 1)
				if not also.has(zone):
					also[zone] = []
				also[zone].append({"at": at, "radius": r})
			elif role == "harbour":
				harbours.append({"at": at, "radius": r, "deep": float(node.get(&"depth"))})
			elif role.begins_with("shelf:"):
				var s := {"at": at, "flat": r, "out": float(node.get(&"outer")), "deep": float(node.get(&"depth"))}
				var extra: Dictionary = node.get(&"extra")
				s["slope"] = _arr(extra.get("slope", Vector2.ZERO))
				if extra.has("long"):
					s["long"] = _arr(extra.long)
				if extra.has("fill_only"):
					s["fill_only"] = extra.fill_only
				d.shelves[role.get_slice(":", 1)] = s
			elif role == "ruins_clear":
				d.biomes.ruins_clear = {"at": at, "radius": r}
			elif role == "estuary":
				d.river.estuary = at
				d.river.mouth = r
				d.river.mouth_deep = node.get(&"extra").get("mouth_deep", d.river.mouth_deep)
			elif role == "reef_back":
				p.reef_back = {"at": at, "radius": r}
		elif node.get_script() == DATA:
			var key: String = node.get(&"key")
			var values: Dictionary = node.get(&"values")
			match key:
				"bake":
					d.bake = values.duplicate(true)
				"biomes":
					for k: String in values:
						d.biomes[k] = values[k]
				"schools":
					var out := {}
					for school: String in values:
						out[school] = Array(values[school])
					d.schools = out
				"kinds_count":
					for kind: String in values:
						if d.kinds.has(kind):
							d.kinds[kind].count = int(values[kind])
	d.biomes.shapes = shapes
	d.eel_colonies = eels
	d.harbours = harbours
	d.dune_fields = fields
	var zone_out := {}
	for zone: String in zones:
		# (a zone whose ring was deleted is kept as it was: the game asks for each by name)
		if zones[zone] == null:
			zone_out[zone] = d.zones[zone]
			continue
		var e: Dictionary = zones[zone]
		if also.has(zone):
			e["also"] = also[zone]
		# (the old key order: "at", "radius" first, then "also", then the rest)
		var ordered := {"at": e.at, "radius": e.radius}
		if e.has("also"):
			ordered["also"] = e.also
		for key: String in e:
			if not ordered.has(key):
				ordered[key] = e[key]
		zone_out[zone] = ordered
	d.zones = zone_out
	# Each kind's zones: those it was in that still list it (in their old order), then the new ones.
	for kind: String in d.kinds:
		var was: Array = d.kinds[kind].zones
		var now := []
		for zone: String in was:
			if kinds_in.has(zone) and kind in (kinds_in[zone] as PackedStringArray):
				now.append(zone)
			elif not kinds_in.has(zone):
				now.append(zone)
		for zone: String in kinds_in:
			if kind in (kinds_in[zone] as PackedStringArray) and zone not in now:
				now.append(zone)
		d.kinds[kind].zones = now
	# The trench: the traced mask is kept as it is unless an outline was changed.
	if _text_of(_loops_of(trench)) != _traced or _traced == "":
		var out := []
		for loop: PackedVector2Array in trench:
			var flat := []
			for q in loop:
				flat.append(_arr(q))
			out.append(flat)
		d.trench["shapes"] = out
		d.trench["note"] = "shapes, where there are any, replace the drawn mask and the outlines added to it (the bay editor traced them from the mask)"
	# Atlantis moved: its whole table moves with it (its buildings, stairs and the ledges under them).
	var atlantis := Vector2(float(p.atlantis.at[0]), float(p.atlantis.at[2]))
	if atlantis.distance_to(_atlantis_was) > 0.001:
		_move_ruins(atlantis - _atlantis_was)
		_atlantis_was = atlantis
	var text := Layout.to_text(d) + "\n"
	if text != FileAccess.get_file_as_string(Layout.PATH):
		var f := FileAccess.open(Layout.PATH, FileAccess.WRITE)
		f.store_string(text)
		f.close()
	_layout = d
	Layout.reload()
	var edited: bool = floor_node.call(&"save_adjust")
	return edited or floor_node.call(&"needs_bake") or _text_of([d.get("bake", {}), d.get("trench", {})]) != bake_before


## Makes the floor's picture again in a separate process (baking the floor first with `bake`); calls
## `then` when it is done. Non-blocking: `status` says how it went.
func refresh_floor(bake: bool, then := Callable()) -> void:
	if _pid > 0 and OS.is_process_running(_pid):
		return
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(DUMP.get_base_dir()))
	var args := ["--headless", "--path", ProjectSettings.globalize_path("res://"), "--audio-driver", "Dummy",
			"-s", "res://addons/bay_layout/floor_dump.gd", "--", "--out=" + ProjectSettings.globalize_path(DUMP)]
	if bake:
		args.append("--bake")
	_pid = OS.create_process(OS.get_executable_path(), args)
	_after_refresh = then
	status = "baking the floor..." if bake else "drawing the floor..."
	_refresh_started = Time.get_ticks_msec()
	set_process(true)


var _refresh_started := 0
var _unowned: Array[Node] = []


## The same, waiting for it (for Play here and tests). Returns how long it took (ms).
func refresh_floor_now(bake: bool) -> int:
	var t := Time.get_ticks_msec()
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(DUMP.get_base_dir()))
	var args := ["--headless", "--path", ProjectSettings.globalize_path("res://"), "--audio-driver", "Dummy",
			"-s", "res://addons/bay_layout/floor_dump.gd", "--", "--out=" + ProjectSettings.globalize_path(DUMP)]
	if bake:
		args.append("--bake")
	OS.execute(OS.get_executable_path(), args)
	_floor_refreshed()
	return Time.get_ticks_msec() - t


func _process(_delta: float) -> void:
	if _pid <= 0:
		set_process(false)
		return
	if OS.is_process_running(_pid):
		return
	_pid = -1
	set_process(false)
	_floor_refreshed()
	status = "floor ready in %.1f s" % ((Time.get_ticks_msec() - _refresh_started) / 1000.0)
	if _after_refresh.is_valid():
		_after_refresh.call()


func _floor_refreshed() -> void:
	floor_node.call(&"load_dump", _dump_path())
	_seat_on_floor()


func _notification(what: int) -> void:
	# Ctrl+S: the layout is saved, and the handles are kept out of the scene file (no owner while it
	# is written, given back after).
	if what == NOTIFICATION_EDITOR_PRE_SAVE:
		if save_layout():
			refresh_floor(true)
		else:
			refresh_floor(false)
		_unowned.clear()
		for node in _all(self):
			if node.owner == self:
				_unowned.append(node)
				node.owner = null
	elif what == NOTIFICATION_EDITOR_POST_SAVE:
		for node in _unowned:
			if is_instance_valid(node):
				node.owner = self
		_unowned.clear()


## Traces the trench's outline from the drawn mask and the outlines added to it: loops round the cells
## inside, as the bake reads them, simplified to within TRACE metres.
func trace_trench() -> Array:
	var size := BAKE.grid_size()
	var inside := BAKE.trench_inside(size.x, size.y)
	var cols := size.x
	var rows := size.y
	var is_in := func(c: int, r: int) -> bool: return c >= 0 and r >= 0 and c < cols and r < rows and inside[r * cols + c] > 0.0
	# Directed edges along the cells' sides, the inside on their right (as seen with z down).
	var next := {}
	for r in rows:
		for c in cols:
			if not is_in.call(c, r):
				continue
			if not is_in.call(c, r - 1):
				_edge(next, Vector2i(c, r), Vector2i(c + 1, r))
			if not is_in.call(c + 1, r):
				_edge(next, Vector2i(c + 1, r), Vector2i(c + 1, r + 1))
			if not is_in.call(c, r + 1):
				_edge(next, Vector2i(c + 1, r + 1), Vector2i(c, r + 1))
			if not is_in.call(c - 1, r):
				_edge(next, Vector2i(c, r + 1), Vector2i(c, r))
	var loops := []
	while not next.is_empty():
		var start: Vector2i = next.keys()[0]
		var loop := PackedVector2Array()
		var at := start
		while true:
			var outs: Array = next.get(at, [])
			if outs.is_empty():
				break
			var to: Vector2i = outs.pop_back()
			if outs.is_empty():
				next.erase(at)
			loop.append(Vector2(BAKE.WEST + at.x - 0.5, BAKE.NORTH + at.y - 0.5))
			at = to
			if at == start:
				break
		if loop.size() < 4:
			continue
		# (outer loops only: a hole would read as trench)
		var area := 0.0
		for i in loop.size():
			var a := loop[i]
			var b := loop[(i + 1) % loop.size()]
			area += a.x * b.y - b.x * a.y
		if area <= 0.0:
			continue
		var simple := _simplify(loop, TRACE)
		var as_list := []
		for q in simple:
			as_list.append(Vector2(snappedf(q.x, 0.5), snappedf(q.y, 0.5)))
		loops.append(as_list)
	return loops


static func _edge(next: Dictionary, a: Vector2i, b: Vector2i) -> void:
	if not next.has(a):
		next[a] = []
	next[a].append(b)


# Douglas-Peucker on a closed loop (split at its two farthest-apart points).
static func _simplify(loop: PackedVector2Array, tolerance: float) -> PackedVector2Array:
	var far := 0
	for i in loop.size():
		if loop[i].distance_to(loop[0]) > loop[far].distance_to(loop[0]):
			far = i
	var a := loop.slice(0, far + 1)
	var b := loop.slice(far)
	b.append(loop[0])
	var out := _dp(a, tolerance)
	var rest := _dp(b, tolerance)
	out.remove_at(out.size() - 1)
	rest.remove_at(rest.size() - 1)
	out.append_array(rest)
	return out


static func _dp(line: PackedVector2Array, tolerance: float) -> PackedVector2Array:
	if line.size() < 3:
		return line
	var worst := 0.0
	var at := 0
	for i in range(1, line.size() - 1):
		var d := line[i].distance_to(Geometry2D.get_closest_point_to_segment(line[i], line[0], line[-1]))
		if d > worst:
			worst = d
			at = i
	if worst <= tolerance:
		return PackedVector2Array([line[0], line[-1]])
	var left := _dp(line.slice(0, at + 1), tolerance)
	var right := _dp(line.slice(at), tolerance)
	left.remove_at(left.size() - 1)
	left.append_array(right)
	return left


func _move_ruins(by: Vector2) -> void:
	var data: Variant = JSON.parse_string(FileAccess.get_file_as_string(RUINS_LAYOUT))
	if not data is Dictionary:
		return
	data.origin = [float(data.origin[0]) + by.x, float(data.origin[1]) + by.y]
	for name: String in data.buildings:
		var b: Dictionary = data.buildings[name]
		b.at = [float(b.at[0]) + by.x, float(b.at[1]) + by.y]
	for name: String in data.stairs:
		var s: Dictionary = data.stairs[name]
		var moved := []
		for q: Array in s.points:
			moved.append([float(q[0]) + by.x, float(q[1]), float(q[2]) + by.y])
		s.points = moved
	var f := FileAccess.open(RUINS_LAYOUT, FileAccess.WRITE)
	f.store_string(JSON.stringify(data, "\t", false) + "\n")


func _make_place(parent: Node3D, spec: Array) -> Node3D:
	var node: Node3D = PLACE.new()
	node.set(&"key", spec[0])
	node.set(&"shape", spec[2])
	node.set(&"size", spec[3])
	node.set(&"colour", spec[4])
	node.set(&"keeps_height", spec[5])
	node.set(&"turns", spec[6])
	return _add(parent, node, spec[1])


func _make_circle(parent: Node3D, role: String, title: String, at: Vector2, r: float, outer: float, colour: Color) -> Node3D:
	var node: Node3D = CIRCLE.new()
	node.set(&"role", role)
	node.set(&"radius", r)
	node.set(&"outer", outer)
	node.set(&"colour", colour)
	_add(parent, node, title)
	node.global_position = Vector3(at.x, HIGH, at.y)
	node.global_rotation = Vector3.ZERO
	return node


func _make_outline(parent: Node3D, role: String, title: String, pts: Array, closed: bool, colour: Color) -> Node3D:
	var node: Path3D = OUTLINE.new()
	node.set(&"role", role)
	node.set(&"closed", closed)
	node.set(&"colour", colour)
	_add(parent, node, title)
	# (its points in its own frame: undo the parent's place and turn)
	var curve := Curve3D.new()
	var to_local := node.global_transform.affine_inverse()
	for q: Vector2 in pts:
		curve.add_point(to_local * Vector3(q.x, HIGH, q.y))
	if &"closed" in curve:
		curve.set(&"closed", closed)
	node.curve = curve
	return node


func _add(parent: Node, node: Node, title: String) -> Node:
	node.name = title.validate_node_name()
	parent.add_child(node)
	_made.append(node)
	if Engine.is_editor_hint() and is_inside_tree() and get_tree().edited_scene_root == self:
		node.owner = self
	return node



# Every node made by the editor or added by the user (duplicates of them), in tree order.
func _all(from: Node) -> Array[Node]:
	var out: Array[Node] = []
	for child in from.get_children():
		if child.get_script() in [PLACE, CIRCLE, OUTLINE, DATA, FLOOR] or child.get_script() == null and child is Node3D:
			out.append(child)
			out.append_array(_all(child))
	return out


# The places that sit on the floor are put on it (their height is not saved).
func _seat_on_floor() -> void:
	for node in _all(self):
		if node.get_script() == PLACE and not node.get(&"keeps_height"):
			var g: Vector3 = node.global_position
			node.global_position = Vector3(g.x, floor_node.call(&"height_at", g.x, g.z), g.z)


func _set_xz(node: Node3D, at: Vector2) -> void:
	node.global_position = Vector3(at.x, 0.0, at.y)


func _dump_path() -> String:
	return DUMP


# The floor's picture is older than the layout or the baked floor.
func _dump_stale() -> bool:
	if not FileAccess.file_exists(DUMP):
		return true
	var made := FileAccess.get_modified_time(DUMP)
	return made < FileAccess.get_modified_time(Layout.PATH) or made < FileAccess.get_modified_time(BAKE.OUT)


static func _arr(v: Vector2) -> Array:
	return [v.x, v.y]


static func _arr3(v: Vector3) -> Array:
	return [v.x, v.y, v.z]


static func _loops_of(list: Array) -> Array:
	var out := []
	for loop: PackedVector2Array in list:
		out.append(Array(loop))
	return out


static func _text_of(v: Variant) -> String:
	return var_to_str(v)
