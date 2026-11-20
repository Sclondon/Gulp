class_name Warmer
extends Node
## Everything is loaded and compiled on the loading screen, before the title shows; nothing after
## (the user, 2026-11-19: "there should be no freezing", "whats the point of loading if you have to
## load after pressing start anyways??", "All loading should just happen at the start you shouldnt
## have to wait for buttons or anything"). CLAUDE.md, "Decision: everything compiled on the loading
## screen".
##
## A browser compiles each shader program the first time it is drawn and stops the game for it
## (tools/PERF.md, "Shader programs"). So every animal kind (dressed as the game dresses it, its far
## model too, from its baked look) and every other material of the sea (each by its shader and the
## way it is drawn: alone, or in a MultiMesh of a format) is shown once to a tiny view far under the
## sea, a few a frame (see `now`), in the sea's own world (its light, fog and sky). Things made only later in play
## are made here too and shown (the eelgrass fields' squares, splashes and the rest: Main's
## `_warm_extras`). Each is shown under the water's light, then again beside a lamp (an omni light),
## as the jellies' lamps make the engine compile another version of a lit program for what they
## light; and what is lit per pixel (the water, the sand) a third time under the air's light (the
## sky): a program lit per pixel has a version for each (tools/PERF.md, "Shader programs").
##
## `done()` says when all of it is done; `progress()` how far (0..1, by the time each step is
## expected to take). Nothing is done once it is ready: there is no warming in play.

var viewport: SubViewport
var life: Life
## Every kind and material, each {name, kind or thing}; those not yet shown.
var left: Array = []
## How many there were.
var total := 0
## Whether what is shown now is to be lit as above the water (Main sets the sea's light from it).
var above := false
## What is being shown now (freed after two frames): a few things at a time while frames come back
## quickly (a program already compiled costs nothing, and the animals share a handful of motion family
## shaders), one at a time when the last were slow (a compile).
var now: Node3D
## How many are shown together: doubled (to BATCH_MOST) while the two frames took under BATCH_FAST ms,
## back to one when they took over BATCH_SLOW ms.
const BATCH_MOST := 16
const BATCH_FAST := 60
const BATCH_SLOW := 300
var _batch := 1
var _shown_ms := 0

var _view: SubViewport
var _lamp: OmniLight3D
var _wait := 0
var _weight_total := 0.0
var _weight_done := 0.0
var _began_ms := -1
var _done_ms := -1
## When everything was ready (s from the engine's start; -1 until then).
var ready_s := -1.0


## Makes the list (call when the sea is built).
func begin(extra: Array = []) -> void:
	# (the plain materials lit per vertex first, so they are shown as they will be drawn)
	light_per_vertex(viewport)
	for kind: String in Species.ALL:
		# (the sea monsters are not in the sea until something calls them up: Species `monster`)
		if not Species.has(kind) or Species.of(kind).get("monster", false) or Species.of(kind).script == "":
			continue
		left.append({"name": kind, "kind": kind, "weight": 1.0})
	for thing: Dictionary in materials_to_warm(viewport) + extra:
		thing["weight"] = 0.6
		left.append(thing)
	# (twice each: alone, then lit by a lamp; what is lit per pixel a third time, in the air's light)
	var lit: Array = []
	var aired: Array = []
	for item: Dictionary in left:
		var again := item.duplicate()
		again["lamp"] = true
		again["weight"] = 0.15
		lit.append(again)
		if item.has("thing") and lit_per_pixel(item.thing[1]):
			var air := item.duplicate()
			air["above"] = true
			air["weight"] = 0.3
			aired.append(air)
	left.append_array(lit)
	left.append_array(aired)
	total = left.size()
	for item: Dictionary in left:
		_weight_total += float(item.weight)
	_view = SubViewport.new()
	_view.size = Vector2i(32, 32)
	_view.world_3d = viewport.find_world_3d()
	_view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(_view)
	var eye := Camera3D.new()
	eye.position = Vector3(0.0, -800.0, 3.0)
	eye.far = 12.0
	_view.add_child(eye)
	_lamp = OmniLight3D.new()
	_lamp.position = Vector3(0.0, -799.0, 1.5)
	_lamp.omni_range = 4.0
	_lamp.visible = false
	viewport.add_child(_lamp)
	print("GULP WARM %d things to show once (%d kinds), each also lit by a lamp" % [total, _count_kinds()])


## Whether everything has been shown.
func done() -> bool:
	return left.is_empty() and now == null


## How far along it is (0..1).
func progress() -> float:
	if done():
		return 1.0
	return clampf(_weight_done / maxf(_weight_total, 0.001), 0.0, 0.999)


## A frame of the loading screen: shows the next thing.
func step() -> void:
	if _began_ms < 0:
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
			_lamp.queue_free()
			_done_ms = Time.get_ticks_msec()
			ready_s = _done_ms / 1000.0
			print("GULP WARM everything is ready at %.1f s (%.1f s of warming)" % [_done_ms / 1000.0, (_done_ms - _began_ms) / 1000.0])
		return
	var took := Time.get_ticks_msec() - _shown_ms
	if _shown_ms > 0:
		_batch = 1 if took > BATCH_SLOW else (mini(_batch * 2, BATCH_MOST) if took < BATCH_FAST else _batch)
	now = Node3D.new()
	viewport.add_child(now)
	# (a batch shares the lamp, and the light above or under the water)
	var first: Dictionary = left[0]
	_lamp.visible = first.get("lamp", false)
	above = first.get("above", false)
	var names: PackedStringArray = []
	while not left.is_empty() and names.size() < _batch and left[0].get("lamp", false) == first.get("lamp", false) \
			and left[0].get("above", false) == first.get("above", false):
		var item: Dictionary = left.pop_front()
		_weight_done += float(item.weight)
		names.append(String(item.name))
		if item.has("kind"):
			_show_kind(item.kind)
		else:
			_show_thing(item.thing)
	Hitches.note("warm " + ", ".join(names))
	_wait = 2
	_shown_ms = Time.get_ticks_msec()


func _count_kinds() -> int:
	var n := 0
	for item: Dictionary in left:
		if item.has("kind") and not item.get("lamp", false):
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
	var one := Node3D.new()
	one.add_child(look)
	one.scale = Vector3.ONE / maxf(Species.long_of(kind, look), 0.05)
	now.add_child(one)
	one.global_position = Vector3(0.0, -800.0, 0.0)
	# (and its far model, which a component loads only when first asked for it)
	if &"low" in look:
		look.set(&"low", true)
		# (shown too: both models are drawn the frame after)
		var near: Node3D = Species.make(kind)
		if &"game" in near:
			near.set(&"game", true)
		if &"cartoon_eyes" in near:
			near.set(&"cartoon_eyes", 1.0)
		one.add_child(near)
	if life:
		life.mark_dressed(kind)


# [mesh, material, MultiMesh to copy the format of, or null]
func _show_thing(thing: Array) -> void:
	var mesh: Mesh = thing[0]
	var material: Material = thing[1]
	var like: MultiMesh = thing[2]
	var one := Node3D.new()
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
		var single := MeshInstance3D.new()
		single.mesh = mesh
		drawn = single
	drawn.material_override = material
	drawn.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	one.add_child(drawn)
	var box := mesh.get_aabb()
	one.scale = Vector3.ONE / maxf(box.size.length(), 0.05)
	now.add_child(one)
	one.global_position = Vector3(0.0, -800.0, 0.0) - box.get_center() * one.scale.x


## Every material drawn in the sea but the animals' (shown by kind), once each by its shader and
## the way it is drawn (alone, or many in a MultiMesh of a format), with a mesh it is drawn on:
## {name, thing: [mesh, material, MultiMesh or null]}.
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
			# (particles are drawn as a MultiMesh with colours and custom data: that version, not the
			# plain one, is what they need)
			many = MultiMesh.new()
			many.transform_format = MultiMesh.TRANSFORM_3D
			many.use_colors = true
			many.use_custom_data = true
		if mesh == null:
			continue
		var geometry := node as GeometryInstance3D
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
				continue
			seen[key] = true
			out.append({"name": "%s %s" % [node.name, (what as Resource).resource_path.get_file() if what is Resource else ""], "thing": [mesh, material, many]})
	return out


## Whether a material is lit per pixel (not per vertex, not unshaded).
static func lit_per_pixel(material: Material) -> bool:
	if material is BaseMaterial3D:
		return (material as BaseMaterial3D).shading_mode == BaseMaterial3D.SHADING_MODE_PER_PIXEL
	if material is ShaderMaterial and (material as ShaderMaterial).shader:
		var m := RegEx.create_from_string("render_mode([^;]*);").search((material as ShaderMaterial).shader.code)
		var modes := m.get_string(1) if m else ""
		return not modes.contains("vertex_lighting") and not modes.contains("unshaded")
	return false


## Every StandardMaterial3D under `under` lit per vertex instead of per pixel: a browser compiles a
## program lit per pixel about five times slower (1.4 s against 0.3 s each under ANGLE; tools/PERF.md,
## "Shader programs"). Their models are low-poly, so the light looks the same but for the shine.
static func light_per_vertex(under: Node) -> int:
	var changed := 0
	var all: Array = under.find_children("*", "GeometryInstance3D", true, false)
	if under is GeometryInstance3D:
		all.append(under)
	for node: Node in all:
		var materials: Array = [(node as GeometryInstance3D).material_override]
		var mesh: Mesh = null
		if node is MeshInstance3D:
			mesh = (node as MeshInstance3D).mesh
			for s in (node as MeshInstance3D).get_surface_override_material_count():
				materials.append((node as MeshInstance3D).get_surface_override_material(s))
		elif node is MultiMeshInstance3D and (node as MultiMeshInstance3D).multimesh:
			mesh = (node as MultiMeshInstance3D).multimesh.mesh
		elif node is CPUParticles3D:
			mesh = (node as CPUParticles3D).mesh
		if mesh:
			for s in mesh.get_surface_count():
				materials.append(mesh.surface_get_material(s))
		for m: Variant in materials:
			if m is BaseMaterial3D and (m as BaseMaterial3D).shading_mode == BaseMaterial3D.SHADING_MODE_PER_PIXEL:
				(m as BaseMaterial3D).shading_mode = BaseMaterial3D.SHADING_MODE_PER_VERTEX
				changed += 1
	return changed
