class_name Wreck
extends Node3D
## The reef wreck: a sunken four-funnel liner of about 1910, broken in two on the sea bed, with the
## reef growing on it (the user, 2026-11-18: "the reef should be built into a ship wreck like an onld
## timy passenger titanic style"). The model, its paint, its collision spheres and its swim routes
## are made by tools/build_wreck.py; tools/WRECK.md has the design and the checks.
##
## The map places it: `Wreck.new()`, its position on the sea bed and rotation.y, then add_child.
## Its own axes: the bow points to -Z, starboard is +X; the origin is the middle of the keel's
## resting line, y = 0 at the sea bed (the keel lies about half a metre under it). About 66 m from the
## stern's rudder to the bow, 9 m across the two halves, 17.5 m from the bed to the funnel's rim.
##
## On `_ready` (placed by then) it gives every solid part to `Sea.add_rock` as spheres, grows reef
## life from GameCommon's sea floor kit at the ReefSpots, and from then on hides each half (and the
## reef) when it is beyond sight. `fish_spots()` and `lanterns()` are places in the world for fish to
## hang about and for a faint glow inside.

const MODEL := "res://models/wreck_liner.glb"
const DATA := "res://models/wreck_liner.json"
const SHADER := preload("res://shaders/wreck.gdshader")
const ATLAS := {"WreckBow": "res://textures/wreck_atlas_bow.png", "WreckStern": "res://textures/wreck_atlas_stern.png"}
const PROPS := "res://scenery/sea_floor_props/sea_floor_props.gd"
## Beyond this the water hides it (m, to the nearest point of a half), as Scenery's plants.
const SEEN := 60.0
## How many reef pieces at a ReefSpot, and how far round it they spread (m).
const CLUMP := Vector2i(9, 15)
const SPREAD := 1.5
## Reef spilling on to the sand along the hull (the concept art's): clumps along each half.
const SPILL := 70
## Big coral heads on the sand beside her (they stop a swimmer).
const HEADS := 12
const WEED := "res://plants/seaweed/seaweed_bed.gd"
## Tints for pieces the kit paints pale to be tinted.
const WARM: Array[Color] = [Color(1.0, 0.55, 0.65), Color(1.0, 0.62, 0.38), Color(0.78, 0.55, 1.0), Color(0.8, 1.0, 0.5), Color(1.0, 0.85, 0.45), Color(1.0, 1.0, 1.0)]
## Each half's keel on the bed, end to end, in the wreck's own space (as build_wreck.py lays them).
const KEELS := [[Vector2(-0.4, -29.0), Vector2(-0.2, 9.0)], [Vector2(-2.25, 16.6), Vector2(4.4, 34.9)]]

## Tints and dims the paint (white: as painted). For day and night.
var tint := Color.WHITE:
	set(to):
		tint = to
		for drawn: ShaderMaterial in _paints:
			drawn.set_shader_parameter(&"tint", to)

var _halves: Array[MeshInstance3D] = []
var _paints: Array[ShaderMaterial] = []
var _reef: Node3D
var _spots: Array[Node3D] = []
var _fish := PackedVector3Array()
var _lamps := PackedVector3Array()
var _spheres: Array[Vector4] = []
var _routes: Array = []
var _rng := RandomNumberGenerator.new()
var _clock := 0.0


func _ready() -> void:
	_rng.seed = 1912
	var made: Node3D = (load(MODEL) as PackedScene).instantiate()
	made.name = "Liner"
	add_child(made)
	for drawn: MeshInstance3D in made.find_children("*", "MeshInstance3D", true, false):
		var paint := ShaderMaterial.new()
		paint.shader = SHADER
		paint.set_shader_parameter(&"atlas", load(ATLAS.get(String(drawn.name), ATLAS.WreckBow)))
		paint.set_shader_parameter(&"tint", tint)
		drawn.material_override = paint
		drawn.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_paints.append(paint)
		_halves.append(drawn)
	for marker: Node3D in made.find_children("*", "Node3D", true, false):
		var named := String(marker.name)
		if named.begins_with("ReefSpot"):
			_spots.append(marker)
		elif named.begins_with("FishSpot"):
			_fish.append(marker.global_position)
		elif named.begins_with("Lantern"):
			_lamps.append(marker.global_position)
	_load_data()
	for sphere: Vector4 in _spheres:
		Sea.add_rock(sphere)
	if ResourceLoader.exists(PROPS):
		_grow_reef()


func _process(delta: float) -> void:
	_clock -= delta
	if _clock > 0.0:
		return
	_clock = 0.25
	var eye := get_viewport().get_camera_3d()
	if eye == null:
		return
	var at := eye.global_position
	var any := false
	for half in _halves:
		var box := half.global_transform * half.get_aabb()
		var seen := _distance(box, at) < SEEN
		half.visible = seen
		any = any or seen
	if _reef:
		_reef.visible = any


## Places in the world where fish might hang about: the saloon, the hold, the boiler room, the
## promenade, under the bridge's roof, the engine room, under the stern, the lounge, the gap.
func fish_spots() -> PackedVector3Array:
	return _fish


## Places in the world where a faint glow could sit: the saloon, the boiler room, the hold, the
## engine room.
func lanterns() -> PackedVector3Array:
	return _lamps


## The collision spheres as given to Sea (world: x, y, z, radius).
func spheres() -> Array[Vector4]:
	return _spheres


## The swim routes the build checks, in the world: [{name, room, points}].
func routes() -> Array:
	return _routes


func _load_data() -> void:
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(DATA))
	var to_world := global_transform
	var grow := to_world.basis.get_scale().x
	for s: Array in data.spheres:
		var middle := to_world * Vector3(s[0], s[1], s[2])
		_spheres.append(Vector4(middle.x, middle.y, middle.z, float(s[3]) * grow))
	for route: Dictionary in data.routes:
		var points := PackedVector3Array()
		for p: Array in route.points:
			points.append(to_world * Vector3(p[0], p[1], p[2]))
		_routes.append({"name": route.name, "room": float(route.room) * grow, "points": points})


# Whether a point is in the way of a swim route (reef is kept out of the openings).
func _on_route(p: Vector3, margin := 1.0) -> bool:
	for route: Dictionary in _routes:
		var points: PackedVector3Array = route.points
		for i in points.size() - 1:
			var near := Geometry3D.get_closest_point_to_segment(p, points[i], points[i + 1])
			if near.distance_to(p) < float(route.room) + margin:
				return true
	return false


static func _distance(box: AABB, p: Vector3) -> float:
	var nearest := p.clamp(box.position, box.end)
	return nearest.distance_to(p)


# Reef life on the wreck (the concept art, tools/art_src/concept_liner_wreck.jpg: decks, rails and
# the sand at her foot thick with coral, fans, sponges and weed in warm colours). From GameCommon's
# sea floor kit (the tropical and cold-water pieces Scenery plants) and its seaweed:
# - a clump at every ReefSpot and ReefPatch (+Y out of the surface), denser where she is seen first;
# - clumps and big coral heads on the sand along both sides, as if the reef had spilled off her;
# - weed standing on the decks and tall on the sand.
# None within a metre of a swim route. Only the coral heads stop a swimmer (their own spheres).
func _grow_reef() -> void:
	var props: GDScript = load(PROPS)
	var kinds: PackedStringArray = props.call(&"names", "tropical")
	kinds.append_array(props.call(&"names", "cold"))
	# (the barrel sponge, scaled up on a deck, reads as a barrel: it grows on the sand only)
	var on_decks := kinds.duplicate()
	on_decks.remove_at(on_decks.find("barrel_sponge"))
	var placed := {}
	var to_local := global_transform.affine_inverse()
	var weed_at := PackedVector3Array()
	var weed_size := PackedFloat32Array()
	var weed_kind := PackedInt32Array()
	for spot in _spots:
		var base := to_local * spot.global_transform.orthonormalized()
		for k in _rng.randi_range(CLUMP.x, CLUMP.y):
			var off := Vector2.from_angle(_rng.randf() * TAU) * SPREAD * sqrt(_rng.randf())
			var local := Transform3D(Basis(Vector3.UP, _rng.randf() * TAU).scaled(Vector3.ONE * _rng.randf_range(0.8, 1.8)), Vector3(off.x, -0.03, off.y))
			_put(props, placed, on_decks[_rng.randi() % on_decks.size()], base * local)
		# (weed on what faces up)
		if base.basis.y.normalized().y > 0.7:
			for k in _rng.randi_range(1, 4):
				var off := Vector2.from_angle(_rng.randf() * TAU) * SPREAD * sqrt(_rng.randf())
				var foot := global_transform * (base * Vector3(off.x, -0.02, off.y))
				if not _on_route(foot):
					weed_at.append(foot)
					var kind: int = [1, 2, 3, 4][_rng.randi() % 4]
					weed_kind.append(kind)
					weed_size.append(_rng.randf_range(0.6, 1.4) if kind != 3 else _rng.randf_range(1.0, 2.2))
	# (on the sand along each side)
	for k in SPILL:
		var middle := _beside(_rng.randf_range(4.0, 7.0))
		for j in _rng.randi_range(6, 12):
			var at := middle + Vector2.from_angle(_rng.randf() * TAU) * 2.0 * sqrt(_rng.randf())
			_put(props, placed, kinds[_rng.randi() % kinds.size()], Transform3D(Basis(Vector3.UP, _rng.randf() * TAU).scaled(Vector3.ONE * _rng.randf_range(1.2, 2.6)), Vector3(at.x, -0.05, at.y)))
		for j in _rng.randi_range(2, 5):
			var at := middle + Vector2.from_angle(_rng.randf() * TAU) * 2.5 * sqrt(_rng.randf())
			var foot := global_transform * Vector3(at.x, -0.05, at.y)
			if not _on_route(foot):
				weed_at.append(foot)
				var kind := 3 if _rng.randf() < 0.6 else 4
				weed_kind.append(kind)
				weed_size.append(_rng.randf_range(1.5, 3.8) if kind == 3 else _rng.randf_range(0.8, 1.6))
	# (big coral heads among them: they stop a swimmer)
	var heads: PackedStringArray = props.call(&"names", "bommie")
	var made := 0
	for attempt in HEADS * 4:
		if made >= HEADS:
			break
		var at := _beside(_rng.randf_range(6.5, 9.5))
		var piece := heads[_rng.randi() % heads.size()]
		var where := Transform3D(Basis(Vector3.UP, _rng.randf() * TAU).scaled(Vector3.ONE * _rng.randf_range(0.6, 1.0)), Vector3(at.x, -0.3, at.y))
		var world := global_transform * where
		var clear := true
		for sphere: Vector4 in props.call(&"spheres_of", piece):
			if _on_route(world * Vector3(sphere.x, sphere.y, sphere.z), sphere.w * where.basis.get_scale().x + 1.0):
				clear = false
		if not clear:
			continue
		made += 1
		_put(props, placed, piece, where, false)
		for sphere: Vector4 in props.call(&"spheres_of", piece):
			var middle := world * Vector3(sphere.x, sphere.y, sphere.z)
			var rock := Vector4(middle.x, middle.y, middle.z, sphere.w * world.basis.get_scale().x)
			_spheres.append(rock)
			Sea.add_rock(rock)
		# (a table coral or two on its shoulder)
		for j in 2:
			_put(props, placed, "table_coral", Transform3D(Basis(Vector3.UP, _rng.randf() * TAU).scaled(Vector3.ONE * _rng.randf_range(1.0, 1.8)), where * Vector3(_rng.randf_range(-0.8, 0.8), (props.call(&"size_of", piece) as Vector3).y * 0.8, _rng.randf_range(-0.8, 0.8))))
	_reef = Node3D.new()
	_reef.name = "Reef"
	add_child(_reef)
	for piece: String in placed:
		var wheres: Array = placed[piece][0]
		var colours: Array = placed[piece][1]
		var many := MultiMesh.new()
		many.transform_format = MultiMesh.TRANSFORM_3D
		many.use_colors = true
		many.mesh = props.call(&"mesh_of", piece, false)
		many.instance_count = wheres.size()
		for i in wheres.size():
			many.set_instance_transform(i, wheres[i])
			many.set_instance_color(i, colours[i])
		var drawn := MultiMeshInstance3D.new()
		drawn.name = piece
		drawn.multimesh = many
		drawn.material_override = props.call(&"material_of", piece)
		drawn.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_reef.add_child(drawn)
	if ResourceLoader.exists(WEED) and not weed_at.is_empty():
		var bed: Node3D = (load(WEED) as GDScript).new()
		bed.name = "Weed"
		bed.top_level = true
		bed.set(&"far", SEEN)
		bed.set(&"cell", 8.0)
		bed.set(&"current", Vector2(0.3, 0.1))
		_reef.add_child(bed)
		bed.global_transform = Transform3D.IDENTITY
		bed.call(&"plant", weed_at, weed_size, weed_kind, Sea.SURFACE)


# One reef piece placed (in the wreck's space), unless it is in a route's way; tinted from the
# piece's own tints, or else warm (the concept's pinks, oranges, purples, yellow-greens).
func _put(props: GDScript, placed: Dictionary, piece: String, where: Transform3D, check := true) -> void:
	if check and _on_route(global_transform * where.origin):
		return
	var tints: PackedColorArray = props.call(&"tints_of", piece)
	var tint := tints[_rng.randi() % tints.size()] if tints.size() > 1 else WARM[_rng.randi() % WARM.size()]
	if not placed.has(piece):
		placed[piece] = [[], []]
	placed[piece][0].append(where)
	placed[piece][1].append(tint)


# A place on the sand (the wreck's space, x and z) `out` metres off one side of either half's keel.
func _beside(out: float) -> Vector2:
	var keel: Array = KEELS[_rng.randi() % 2]
	var along: Vector2 = (keel[0] as Vector2).lerp(keel[1], _rng.randf())
	var across: Vector2 = ((keel[1] as Vector2) - keel[0]).normalized().orthogonal() * (1.0 if _rng.randf() < 0.5 else -1.0)
	return along + across * out
