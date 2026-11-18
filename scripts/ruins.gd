class_name Ruins
extends Node3D
## The drowned precinct of Atlantis, built into the walls of the Monterey Canyon (tools/RUINS.md). The
## user (2026-11-18): "another location should be atlanits ruins"; then "atlantis shouldn't just be a
## giant crater"; then "The Atlantis ruines area shouldnt just be a big open flat area, it should be built
## into the trench sides". Laid out after the concept art tools/art_src/concept_atlantis_canyon.png (the
## buildings' look from concept_atlantis.jpg): a round temple with its broken dome on the north rim,
## jutting over the drop on its own crag; a colonnade on a terrace built out from the north wall, a
## rock-cut temple front behind it; a stone arch bridge across the canyon to a landing on the south wall
## with the pillar of the glowing crystal; a stepped pyramid half into the south wall on its own
## terrace; rock-cut fronts low in both walls; stairs down the walls; the colossal fallen head and hand
## of the sea queen on the canyon floor; carved blocks, drums and jars spilled about.
##
## Where each building stands is ONE table, data/ruins_layout.json (Bay.RUINS_LAYOUT): the model's build
## (tools/build_atlantis_canyon.py) places the buildings from it, Bay cuts the ledges under them from it,
## and this reads it for the routes and the places kept clear of plants. One model
## (models/atlantis_canyon.glb), a part a building, drawn with one shader (shaders/ruins.gdshader) as
## three materials: the stone, the statue (its own picture) and what glows.
##
## Its origin is the table's `origin` at `origin_depth` (Sea.RUINS_AT must be the same place), with no
## turn: its own x, z are the world's less the origin's, its own y the world's less the origin's.
##
## Place it BEFORE adding it: `Ruins.new()`, position, then add_child. On `_ready` its collision spheres
## go to `Sea.add_rock`, sea life is grown at its reef spots, and each part hides itself beyond the sea's
## sight. `fish_spots()` and `lanterns()` give places in the world; `routes()` the swim routes that must
## stay open (tests/ruins_view.gd -- --check); `covers(at)` whether a place is kept clear for it.

const MODEL := "res://models/atlantis_canyon.glb"
const ATLAS := "res://textures/ruins_canyon_atlas.png"
const STATUE_ATLAS := "res://textures/ruins_canyon_statue.png"
const SHADER := "res://shaders/ruins.gdshader"
## Collision spheres added over what the build's own fitting left open (its own space: x, y, z, radius).
const EXTRA := "res://models/ruins_canyon_extra.json"
const PROPS := "res://scenery/sea_floor_props/sea_floor_props.gd"
## Beyond this (from a part's middle, plus its own size) the water hides it, as Scenery's plants.
const SEEN := 60.0
## The sea life that grows on the stones (cheap pieces of GameCommon's kit, cold water and warm).
const LIFE: PackedStringArray = ["vase_sponge", "puffball_sponges", "sea_fan_red", "sea_fan_gold", "green_anemone", "strawberry_anemones",
		"urchin_purple", "ochre_star", "bat_star", "mussel_clump", "feather_dusters", "sea_rods", "pillar_coral",
		"table_coral", "soft_coral", "sea_fan_purple"]
## A piece of life with more triangles than this is drawn with its light model.
const LIFE_FULL := 1300
## The materials of the model that are the statue's (its own picture) and what glows.
const STATUE_PAINTS: PackedStringArray = ["statue", "relief", "face"]
const GLOW_PART := "RuinsGlow"
## How far her head lies sunk below her ledge (tools/build_atlantis_canyon.py QUEEN_SINK).
const QUEEN_SINK := -0.8

## How bright the crystal and the inlays glow.
@export var glow := 1.0:
	set(to):
		glow = to
		if _glowing:
			_glowing.set_shader_parameter(&"glow", to)
## Day and night can dim it (multiplies its paint).
@export var tint := Color.WHITE:
	set(to):
		tint = to
		for paint: ShaderMaterial in [_stone, _statue, _glowing]:
			if paint:
				paint.set_shader_parameter(&"tint", to)

var _stone: ShaderMaterial
var _statue: ShaderMaterial
var _glowing: ShaderMaterial
# Places kept in its own space (they follow it if it is moved after).
var _fish := PackedVector3Array()
var _lanterns := PackedVector3Array()
var _rocks: Array[Vector4] = []
var _rng := RandomNumberGenerator.new()

static var _layout := {}
# (what `covers` tries: [middle (world x, z), heading, half size or (radius, -1)])
static var _covered: Array = []


func _ready() -> void:
	_rng.seed = 23
	_paints()
	var model: Node3D = (load(MODEL) as PackedScene).instantiate()
	model.name = "Model"
	add_child(model)
	var reef: Array[Transform3D] = []
	var gone: Array[Node] = []
	for node: Node in model.find_children("*", "", true, false):
		var named := String(node.name)
		if node is MeshInstance3D:
			_dress(node as MeshInstance3D)
			continue
		if not node is Node3D:
			continue
		var at := transform.affine_inverse() * (node as Node3D).global_transform
		if named.begins_with("Rock"):
			_rocks.append(Vector4(at.origin.x, at.origin.y, at.origin.z, at.basis.get_scale().x))
		elif named.begins_with("ReefSpot"):
			reef.append(at)
		elif named.begins_with("FishSpot"):
			_fish.append(at.origin)
		elif named.begins_with("Lantern"):
			_lanterns.append(at.origin)
		else:
			continue
		gone.append(node)
	for node in gone:
		node.free()
	# (and the extra ones over what the build's fitting left open, thin slabs above all:
	# tests/setpiece_hits.gd --fit-ruins makes them, which leaves them out itself with --no-ruins-extra)
	if FileAccess.file_exists(EXTRA) and not OS.get_cmdline_user_args().has("--no-ruins-extra"):
		var data: Variant = JSON.parse_string(FileAccess.get_file_as_string(EXTRA))
		if data is Dictionary:
			for s: Array in data.spheres:
				_rocks.append(Vector4(s[0], s[1], s[2], s[3]))
	for rock in _rocks:
		var middle := global_transform * Vector3(rock.x, rock.y, rock.z)
		Sea.add_rock(Vector4(middle.x, middle.y, middle.z, rock.w * global_basis.get_scale().x))
	if ResourceLoader.exists(PROPS):
		_grow(reef)


## Places where fish could gather (in the world).
func fish_spots() -> PackedVector3Array:
	var out := PackedVector3Array()
	for at in _fish:
		out.append(global_transform * at)
	return out


## Where a light could hang (in the world): in the pyramid's chamber, under the dome, in the gate, at
## the crystal, in the colonnade, inside her hollow head, in the rock-cut fronts' chambers.
func lanterns() -> PackedVector3Array:
	var out := PackedVector3Array()
	for at in _lanterns:
		out.append(global_transform * at)
	return out


## The collision spheres in its own space (x, y, z, radius).
func rocks() -> Array[Vector4]:
	return _rocks


## The table (data/ruins_layout.json), read once.
static func layout() -> Dictionary:
	if _layout.is_empty():
		var data: Variant = JSON.parse_string(FileAccess.get_file_as_string(Bay.RUINS_LAYOUT))
		if data is Dictionary:
			_layout = data
	return _layout


## Where the ruins' own origin is in the world (Sea.RUINS_AT must agree: the check says).
static func origin() -> Vector3:
	var data := layout()
	return Vector3(float(data.origin[0]), Sea.SURFACE - float(data.origin_depth), float(data.origin[1]))


## A building's own frame in the ruins' own space: its front +Z, y = 0 at its depth.
static func frame(building: String) -> Transform3D:
	var b: Dictionary = layout().buildings[building]
	var o := origin()
	var at := Vector3(float(b.at[0]) - o.x, Sea.SURFACE - float(b.depth) - o.y, float(b.at[1]) - o.z)
	return Transform3D(Basis(Vector3.UP, float(b.heading)), at)


## A stair's points in the ruins' own space.
static func stair(name: String) -> PackedVector3Array:
	var o := origin()
	var out := PackedVector3Array()
	for p: Array in layout().stairs[name].points:
		out.append(Vector3(float(p[0]) - o.x, Sea.SURFACE - float(p[1]) - o.y, float(p[2]) - o.z))
	return out


## Whether a place (world x, z) is kept clear for the ruins (no plants or floor pieces): on any
## building's ledge or terrace, before a rock-cut front, under the bridge, on a stair, `margin` more.
static func covers(at: Vector2, margin := 2.0) -> bool:
	if _covered.is_empty():
		var data := layout()
		for name: String in data.buildings:
			var b: Dictionary = data.buildings[name]
			var h := float(b.heading)
			var middle := Vector2(float(b.at[0]), float(b.at[1]))
			var areas := []
			for l: Dictionary in b.get("ledges", []):
				areas.append([Vector2(float(l.at[0]), float(l.at[1])), Vector2(float(l.radius), -1.0) if l.has("radius") else Vector2(float(l.size[0]), float(l.size[1])) * 0.5])
			if b.has("terrace"):
				areas.append([Vector2(float(b.terrace.at[0]), float(b.terrace.at[1])), Vector2(float(b.terrace.size[0]), float(b.terrace.size[1])) * 0.5])
			if b.has("facade"):
				areas.append([Vector2(0.0, 1.0), Vector2(float(b.facade[0]) * 0.5 + 1.0, 2.0)])
			if b.has("span"):
				areas.append([Vector2.ZERO, Vector2(2.6, float(b.span[0]))])
			for area: Array in areas:
				var off: Vector2 = area[0]
				_covered.append([middle + Vector2(off.x * cos(h) + off.y * sin(h), -off.x * sin(h) + off.y * cos(h)), h, area[1]])
		for ledge: Array in Bay.ruins_ledges():
			if float(ledge[5]) != 0.0 or (ledge[2] as Vector2).y > 0.0:
				_covered.append([ledge[0], ledge[1], ledge[2]])
	for area: Array in _covered:
		var d: Vector2 = at - area[0]
		var h: float = area[1]
		var local := Vector2(d.x * cos(h) - d.y * sin(h), d.x * sin(h) + d.y * cos(h))
		var half: Vector2 = area[2]
		if half.y < 0.0:
			if local.length() < half.x + margin:
				return true
		elif absf(local.x) < half.x + margin and absf(local.y) < half.y + margin:
			return true
	return false


## The swim routes that must stay open, in its own space: name -> [points, room]. `room` is the
## clearance a swimmer keeps (Player: 0.3 of its length), so a route open at room 0.9 takes a fish
## about 3 m long. The test walks each, every 0.4 m, through `Sea.clear_of_rocks`, and checks it
## stays above the floor.
static func routes() -> Dictionary:
	# (the same places as tools/build_atlantis_canyon.py builds them in each building's own frame)
	var temple := frame("Temple") * Transform3D(Basis(Vector3(0, 0, 1), 0.015), Vector3.ZERO) * Transform3D(Basis(Vector3(1, 0, 0), -0.01), Vector3.ZERO)
	var head := frame("Queen") * Transform3D(Basis.IDENTITY, Vector3(0.0, QUEEN_SINK, 0.0)) * Transform3D(Basis(Vector3(0, 1, 0), 0.25), Vector3.ZERO) * Transform3D(Basis(Vector3(1, 0, 0), 1.0 - PI * 0.5), Vector3.ZERO)
	var gate := frame("Gate")
	var stoa := frame("Colonnade")
	var pyramid := frame("Pyramid")
	var bridge := frame("Bridge")
	var span: Array = layout().buildings.Bridge.span
	# (round the temple outside its columns, on its open side, over the drop)
	var ring := PackedVector3Array()
	for k in 25:
		var a := PI * 0.5 + PI * k / 24.0
		ring.append(temple * Vector3(sin(a) * 9.2, 3.0, cos(a) * 9.2))
	var out := {
		"way and gate": [PackedVector3Array([gate * Vector3(0.0, 2.2, 18.0), gate * Vector3(0.0, 2.2, 6.0), gate * Vector3(0.0, 2.5, 0.0), gate * Vector3(0.0, 3.0, -3.0)]), 0.9],
		"round the temple": [ring, 0.9],
		"between its columns and out of the dome": [PackedVector3Array([temple * Vector3(0.0, 3.5, 11.0), temple * Vector3(0.0, 3.5, 7.4),
				temple * Vector3(0.0, 4.0, 0.0), temple * Vector3(0.0, 9.5, 0.5), temple * Vector3(2.4, 13.6, 4.4), temple * Vector3(4.0, 18.0, 7.0)]), 0.9],
		"through her head, temple to temple": [PackedVector3Array([head * Vector3(-4.8, 3.6, -0.4), head * Vector3(4.8, 3.6, -0.4)]), 0.9],
		"into her mouth": [PackedVector3Array([head * Vector3(0.0, 2.12, 5.0), head * Vector3(0.0, 2.12, 1.2), head * Vector3(0.0, 3.0, -0.6)]), 0.1],
		"colonnade aisle": [PackedVector3Array([stoa * Vector3(-7.0, 2.8, -0.2), stoa * Vector3(6.5, 2.8, -0.2)]), 0.9],
		"pyramid door, chamber, shaft, high door": [PackedVector3Array([pyramid * Vector3(3.8, 1.6, 12.5), pyramid * Vector3(3.8, 1.6, 0.0), pyramid * Vector3(2.2, 2.2, 0.0),
				pyramid * Vector3(0.0, 2.2, 0.0), pyramid * Vector3(0.0, 10.15, 0.0), pyramid * Vector3(0.0, 10.15, 7.0), pyramid * Vector3(0.0, 10.6, 11.0)]), 0.9],
		"over the bridge": [PackedVector3Array([bridge * Vector3(0.0, 2.0, -float(span[0]) + 3.0), bridge * Vector3(0.0, 2.0, float(span[0]) - 1.0)]), 0.9],
		"under the bridge, along the trench": [PackedVector3Array([bridge * Vector3(-5.0, -float(span[2]) + 4.0, 0.0), bridge * Vector3(5.0, -float(span[2]) + 4.0, 0.0)]), 0.9],
	}
	for name: String in ["FacadeNorth", "FacadeSouth", "FacadeTomb"]:
		var f := frame(name)
		out["into the doorway of " + name] = [PackedVector3Array([f * Vector3(0.0, 2.4, 4.0), f * Vector3(0.0, 2.4, -4.5)]), 0.6]
	for name: String in layout().stairs:
		var points := stair(name)
		var over := PackedVector3Array()
		var width := float(layout().stairs[name].width)
		for i in points.size():
			# (a flight going down off a landing at a turn starts at the landing's edge, as the build
			# makes it: the swimmer stays over the landing till there)
			if i > 1 and absf(points[i].y - points[i - 1].y) >= 0.05 and absf(points[i - 1].y - points[i - 2].y) < 0.05:
				var before := Vector3(points[i - 1].x - points[i - 2].x, 0.0, points[i - 1].z - points[i - 2].z).normalized()
				var along := Vector3(points[i].x - points[i - 1].x, 0.0, points[i].z - points[i - 1].z).normalized()
				if absf(before.dot(along)) < 0.7:
					over.append(points[i - 1] + along * (width * 0.5 + 0.9) + Vector3(0.0, 2.8, 0.0))
			over.append(points[i] + Vector3(0.0, 2.8, 0.0))
		out["down " + name] = [over, 0.9]
	for k in 4:
		var x := -6.4 + 3.2 * k + 1.6
		out["colonnade gap %d" % k] = [PackedVector3Array([stoa * Vector3(x, 2.6, 6.5), stoa * Vector3(x, 2.6, 0.0)]), 0.9]
	return out


# The three materials of the one shader.
func _paints() -> void:
	var shader: Shader = load(SHADER)
	_stone = ShaderMaterial.new()
	_stone.shader = shader
	_stone.set_shader_parameter(&"atlas", load(ATLAS))
	_statue = ShaderMaterial.new()
	_statue.shader = shader
	_statue.set_shader_parameter(&"atlas", load(STATUE_ATLAS))
	_statue.set_shader_parameter(&"grain", 0.05)
	_glowing = ShaderMaterial.new()
	_glowing.shader = shader
	_glowing.set_shader_parameter(&"atlas", load(ATLAS))
	_glowing.set_shader_parameter(&"grain", 0.0)
	_glowing.set_shader_parameter(&"glow", glow)


# A part of the model: each of its surfaces given the material it takes, hidden beyond sight.
func _dress(part: MeshInstance3D) -> void:
	var mesh := part.mesh
	for i in mesh.get_surface_count():
		var named := mesh.surface_get_material(i).resource_name if mesh.surface_get_material(i) else ""
		var paint := _stone
		if String(part.name) == GLOW_PART:
			paint = _glowing
		elif named in STATUE_PAINTS:
			paint = _statue
		part.set_surface_override_material(i, paint)
	part.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var box := mesh.get_aabb()
	# (measured from the part's own origin: its box may lie well off it)
	part.visibility_range_end = SEEN + box.get_center().length() + box.size.length() * 0.5


# Sea life on the stones: at each reef spot one to three pieces of the kit, standing on the stone
# (+Y of the spot is the stone's normal), drawn as one MultiMesh a kind, as Scenery draws the reef.
func _grow(spots: Array[Transform3D]) -> void:
	var props: GDScript = load(PROPS)
	var known := props.call(&"names") as PackedStringArray
	var kinds := PackedStringArray()
	for kind in LIFE:
		if kind in known:
			kinds.append(kind)
	if kinds.is_empty():
		return
	var placed := {}
	for spot in spots:
		for k in _rng.randi_range(1, 3):
			var kind := kinds[_rng.randi() % kinds.size()]
			var aside := Vector3.ZERO if k == 0 else (spot.basis.x * _rng.randf_range(-0.4, 0.4) + spot.basis.z * _rng.randf_range(-0.4, 0.4))
			var turn := Basis(spot.basis.y.normalized(), _rng.randf() * TAU) * Basis(spot.basis.get_rotation_quaternion())
			var where := Transform3D(turn.scaled(Vector3.ONE * _rng.randf_range(1.0, 1.7)), spot.origin + aside - spot.basis.y * 0.02)
			var tints: PackedColorArray = props.call(&"tints_of", kind)
			if not placed.has(kind):
				placed[kind] = [[], []]
			placed[kind][0].append(where)
			placed[kind][1].append(tints[_rng.randi() % tints.size()] if tints.size() > 0 else Color.WHITE)
	for kind: String in placed:
		var wheres: Array = placed[kind][0]
		var many := MultiMesh.new()
		many.transform_format = MultiMesh.TRANSFORM_3D
		many.use_colors = true
		many.mesh = props.call(&"mesh_of", kind, int(props.call(&"triangles_of", kind)) > LIFE_FULL)
		many.instance_count = wheres.size()
		for i in wheres.size():
			many.set_instance_transform(i, wheres[i])
			many.set_instance_color(i, placed[kind][1][i])
		var drawn := MultiMeshInstance3D.new()
		drawn.name = "Life_" + kind
		drawn.multimesh = many
		drawn.material_override = props.call(&"material_of", kind)
		drawn.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		drawn.visibility_range_end = SEEN + 40.0
		add_child(drawn)
