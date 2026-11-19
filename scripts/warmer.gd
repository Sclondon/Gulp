class_name Warmer
extends Node
## Shows each animal kind and every other material of the sea once to a tiny view far under the sea,
## so that its shader program is compiled before it is first seen in play: a browser compiles each
## program the first time it is drawn, and stops the game for it (about a second each on a Windows
## desktop, more on a slow phone; tools/PERF.md, "Hitches"). CLAUDE.md, "Decision: shaders warmed
## by nearness".
##
## Everything is warmed in order of how near it is to the player (each kind by its nearest animal,
## each material by its nearest piece). Behind the title as fast as it can go (one thing every
## other frame); the start waits until everything within START_REACH of the start is done (or
## START_MOST seconds have gone by). In play
## it carries on, one thing every PLAY_GAP frames, but only what lies within PLAY_REACH of the
## player (past the 55 m where animals wake and the 60 m where plants and pieces show), so a
## program is ready before its thing comes into sight; on the sale, shop, run-over and paused
## screens, and while the fish chooses what to become, as fast as behind the title.

## The start waits for what is this near the start (m), and for what is everywhere (the water,
## the sand, effects).
const START_REACH := 75.0
## ...but for no longer than this (s, from the first frame shown): a browser on a Windows desktop
## took one to three seconds a program on a first visit (tools/PERF.md, "Hitches"), so the rest are
## then warmed in play, nearest first.
const START_MOST := 60.0
## In play, only what is this near the player is warmed (m)...
const PLAY_REACH := 110.0
## ...and at most one thing every this many frames.
const PLAY_GAP := 30
## How often what is left is put in order again (frames).
const SORT_EVERY := 30

var viewport: SubViewport
var life: Life
## Every kind and material, each {name, kind or thing, box (where it is: AABB, or null for
## everywhere), far (its distance from the player when last sorted)}; those not yet shown.
var left: Array = []
## How many there were, and how many lay within START_REACH of the start.
var total := 0
var first := 0
## The thing being shown now (freed after two frames).
var now: Node3D

var _view: SubViewport
var _wait := 0
var _gap := 0
var _sorted_at := -1000
var _frames := 0
var _start := Vector3.ZERO
var _first_left := 0
var _began_ms := -1


## Makes the list (call when the sea is built, the run placed at `start`).
func begin(start: Vector3, extra: Array = []) -> void:
	_start = start
	for kind: String in Species.ALL:
		# (the sea monsters are not in the sea until something calls them up: Species `monster`)
		if not Species.has(kind) or Species.of(kind).get("monster", false):
			continue
		left.append({"name": kind, "kind": kind, "box": null, "far": INF})
	for thing: Dictionary in materials_to_warm(viewport) + extra:
		left.append(thing)
	total = left.size()
	_sort(start)
	for item: Dictionary in left:
		if item.far <= START_REACH:
			first += 1
	_first_left = first
	_view = SubViewport.new()
	_view.size = Vector2i(32, 32)
	_view.world_3d = viewport.find_world_3d()
	_view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(_view)
	var eye := Camera3D.new()
	eye.position = Vector3(0.0, -800.0, 3.0)
	eye.far = 12.0
	_view.add_child(eye)
	print("GULP WARM %d things to show once (%d kinds), %d of them near the start" % [total, _count_kinds(), first])


## Whether everything near the start has been shown.
func ready_to_start() -> bool:
	return (_first_left <= 0 and now == null) or (_began_ms >= 0 and Time.get_ticks_msec() - _began_ms > START_MOST * 1000.0)


## How far along the start's share is (0..1).
func progress() -> float:
	if ready_to_start():
		return 1.0
	return 1.0 if first == 0 else clampf(float(first - _first_left) / first, 0.0, 1.0)


## Puts these kinds first (what the fish may become, offered now).
func hurry(kinds: Array) -> void:
	for item: Dictionary in left:
		if item.has("kind") and item.kind in kinds:
			item.far = -1.0
			item.hurried = true
	left.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return float(a.far) < float(b.far))


## A frame: `fast` behind the title and on screens where nothing swims; else the pace of play.
## `at` is where the player is.
func step(at: Vector3, fast: bool) -> void:
	_frames += 1
	if _began_ms < 0 and Engine.get_frames_drawn() > 1:
		_began_ms = Time.get_ticks_msec()
	_wait -= 1
	if _wait > 0:
		return
	if now:
		now.queue_free()
		now = null
	if left.is_empty():
		if _view:
			_view.queue_free()
			_view = null
			print("GULP WARM everything is ready")
		return
	if _frames - _sorted_at >= SORT_EVERY:
		_sort(at)
	if not fast:
		_gap -= 1
		if _gap > 0:
			return
		if float(left[0].far) > PLAY_REACH:
			return
	_gap = PLAY_GAP
	var item: Dictionary = left.pop_front()
	if item.get("near_start", false):
		_first_left -= 1
		if _first_left == 0:
			print("GULP WARM the starting waters are ready at %.1f s" % (Time.get_ticks_msec() / 1000.0))
	Hitches.note("warm " + String(item.name))
	if item.has("kind"):
		_show_kind(item.kind)
	else:
		_show_thing(item.thing)


func _sort(at: Vector3) -> void:
	_sorted_at = _frames
	# (each kind's nearest animal)
	var nearest := {}
	if life:
		for each: Creature in life.creatures:
			var d := each.global_position.distance_to(at)
			if d < float(nearest.get(each.kind, INF)):
				nearest[each.kind] = d
	for item: Dictionary in left:
		if item.get("hurried", false):
			item.far = -1.0
		elif item.has("kind"):
			# (a kind not stocked in the sea is warmed last)
			item.far = float(nearest.get(item.kind, 1.0e6))
		elif item.box == null:
			item.far = 0.0
		else:
			var far := INF
			for box: AABB in item.box:
				far = minf(far, at.distance_to(at.clamp(box.position, box.end)))
			item.far = far
		if _frames <= 1 and item.far <= START_REACH:
			item.near_start = true
	left.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return float(a.far) < float(b.far))


func _count_kinds() -> int:
	var n := 0
	for item: Dictionary in left:
		if item.has("kind"):
			n += 1
	return n


func _show_kind(kind: String) -> void:
	var look := Species.make(kind)
	if look == null:
		return
	if &"game" in look:
		look.set(&"game", true)
	if &"cartoon_eyes" in look:
		look.set(&"cartoon_eyes", 1.0)
	now = Node3D.new()
	now.add_child(look)
	now.scale = Vector3.ONE / maxf(Species.long_of(kind, look), 0.05)
	viewport.add_child(now)
	now.global_position = Vector3(0.0, -800.0, 0.0)
	# (and its far model loaded too, which a component loads only when first asked for it: a
	# load in play otherwise, the first time one of the kind is far off)
	if &"low" in look:
		look.set(&"low", true)
	_wait = 2
	if life:
		life.mark_dressed(kind)


# [mesh, material, MultiMesh to copy the format of, or null]
func _show_thing(thing: Array) -> void:
	var mesh: Mesh = thing[0]
	var material: Material = thing[1]
	var like: MultiMesh = thing[2]
	now = Node3D.new()
	var drawn: GeometryInstance3D
	if like:
		var many := MultiMesh.new()
		many.transform_format = like.transform_format
		many.use_colors = like.use_colors
		many.use_custom_data = like.use_custom_data
		many.mesh = mesh
		many.instance_count = 1
		many.set_instance_transform(0, Transform3D.IDENTITY)
		if like.use_colors:
			many.set_instance_color(0, Color.WHITE)
		var holder := MultiMeshInstance3D.new()
		holder.multimesh = many
		drawn = holder
	else:
		var one := MeshInstance3D.new()
		one.mesh = mesh
		drawn = one
	drawn.material_override = material
	drawn.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	now.add_child(drawn)
	var box := mesh.get_aabb()
	now.scale = Vector3.ONE / maxf(box.size.length(), 0.05)
	viewport.add_child(now)
	now.global_position = Vector3(0.0, -800.0, 0.0) - box.get_center() * now.scale.x
	_wait = 2


## Every material drawn in the sea but the animals' (warmed by kind), once each by its shader and
## the way it is drawn (alone, or many in a MultiMesh of a format), with a mesh it is drawn on and
## where its nearest piece is: {name, thing: [mesh, material, MultiMesh or null], box}.
static func materials_to_warm(under: Node) -> Array:
	var seen := {}
	var out := []
	for node in under.find_children("*", "GeometryInstance3D", true, false):
		var up := node.get_parent()
		var animal := false
		while up and up != under:
			if up is Creature:
				animal = true
				break
			up = up.get_parent()
		if animal:
			continue
		var mesh: Mesh = null
		var many: MultiMesh = null
		if node is MeshInstance3D:
			mesh = (node as MeshInstance3D).mesh
		elif node is MultiMeshInstance3D and (node as MultiMeshInstance3D).multimesh:
			many = (node as MultiMeshInstance3D).multimesh
			mesh = many.mesh
		elif node is CPUParticles3D:
			mesh = (node as CPUParticles3D).mesh
		if mesh == null:
			continue
		var geometry := node as GeometryInstance3D
		# (where it is: particles and things that follow the eye are everywhere)
		var box: Variant = null
		if not (node is CPUParticles3D) and geometry.is_inside_tree():
			var b := geometry.global_transform * geometry.get_aabb()
			if b.size.length() < 2000.0:
				box = b
		for s in mesh.get_surface_count():
			var material: Material = geometry.material_override
			if material == null and node is MeshInstance3D:
				material = (node as MeshInstance3D).get_active_material(s)
			if material == null:
				material = mesh.surface_get_material(s)
			if material == null:
				continue
			var what: Object = (material as ShaderMaterial).shader if material is ShaderMaterial and (material as ShaderMaterial).shader else material
			var key := "%d %s" % [what.get_instance_id(), "" if many == null else "%d%d%d" % [many.transform_format, int(many.use_colors), int(many.use_custom_data)]]
			if seen.has(key):
				# (the nearest of its pieces counts)
				var had: Dictionary = seen[key]
				if had.box != null and box != null:
					var boxes: Array = had.box
					if boxes.size() < 48:
						boxes.append(box)
					else:
						boxes[boxes.size() - 1] = (boxes[boxes.size() - 1] as AABB).merge(box)
				elif box == null:
					had.box = null
				continue
			var item := {"name": "%s %s" % [node.name, (what as Resource).resource_path.get_file() if what is Resource else ""], "thing": [mesh, material, many], "box": null if box == null else [box], "far": INF}
			seen[key] = item
			out.append(item)
	return out
