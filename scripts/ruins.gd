class_name Ruins
extends Node3D
## The drowned precinct of Atlantis (the user, 2026-11-18: "another location should be atlanits
## ruins"; laid out after the concept art tools/art_src/concept_atlantis.jpg; tools/RUINS.md): a
## processional way to a carved gate, a round temple with its dome broken open, a colossal hollow
## head and a hand fallen before it, a colonnade behind, a stepped pyramid with a chamber, a pillar
## with a glowing crystal, carved frieze blocks and drums strewn about. One model
## (models/atlantis_ruins.glb, built by tools/build_ruins.py) in six parts, drawn with one shader
## (shaders/ruins.gdshader) as three materials: the stone, the statue (its own picture) and what
## glows.
##
## Its origin is the middle of the precinct, y = 0 on the sea bed (everything reaches a metre or two
## below that, so it sits on uneven ground); the processional way runs along +Z, so a visitor comes
## in from +Z swimming towards -Z (the gate is at x -18, the temple in the middle, the pyramid at
## x 26, the pillar at x 38). About 64 m by 66 m, 21 m high at the crystal.
##
## Place it BEFORE adding it: `Ruins.new()`, position, rotation.y, then add_child. On `_ready` its
## collision spheres go to `Sea.add_rock` (where it stands then), sea life is grown at its reef
## spots (GameCommon's sea floor props, as Scenery grows the reef), and each part hides itself
## beyond the sea's sight. `fish_spots()` and `lanterns()` give places in the world for the game to
## use. `routes()` are the swim routes that must stay open (tests/ruins_view.gd -- --check).

const MODEL := "res://models/atlantis_ruins.glb"
const ATLAS := "res://textures/ruins_atlas.png"
const STATUE_ATLAS := "res://textures/ruins_atlas_statue.png"
const SHADER := "res://shaders/ruins.gdshader"
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
	for rock in _rocks:
		var middle := global_transform * Vector3(rock.x, rock.y, rock.z)
		Sea.add_rock(Vector4(middle.x, middle.y, middle.z, rock.w * global_basis.get_scale().x))
	if ResourceLoader.exists(PROPS):
		_grow(reef)


## Places where fish could gather (in the world): the way, the court, round the temple, over the
## dome, in the colonnade, round the pillar, over the pyramid and in its chamber, in the field.
func fish_spots() -> PackedVector3Array:
	var out := PackedVector3Array()
	for at in _fish:
		out.append(global_transform * at)
	return out


## Where a light could hang (in the world): in the pyramid's chamber, under the dome, in the gate,
## at the crystal, in the colonnade, inside her hollow head.
func lanterns() -> PackedVector3Array:
	var out := PackedVector3Array()
	for at in _lanterns:
		out.append(global_transform * at)
	return out


## The collision spheres in its own space (x, y, z, radius).
func rocks() -> Array[Vector4]:
	return _rocks


## The swim routes that must stay open, in its own space: name -> [points, room]. `room` is the
## clearance a swimmer keeps (Player: 0.3 of its length), so a route open at room 0.9 takes a fish
## about 3 m long. The test walks each, every 0.4 m, through `Sea.clear_of_rocks`.
static func routes() -> Dictionary:
	# (the same places as tools/build_ruins.py: GATE_X/Z, TX/TZ, HEAD_AT, STOA_*, PX/PZ, CH, SH, DOOR_X)
	var temple := Transform3D(Basis.IDENTITY, Vector3(-2.0, 0.0, -6.0)) * Transform3D(Basis(Vector3(0, 0, 1), 0.015), Vector3.ZERO) \
			* Transform3D(Basis(Vector3(1, 0, 0), -0.01), Vector3.ZERO)
	var head := Transform3D(Basis.IDENTITY, Vector3(5.2, 0.0, 9.8)) * Transform3D(Basis(Vector3(0, 1, 0), 0.25), Vector3.ZERO) \
			* Transform3D(Basis(Vector3(1, 0, 0), 1.0 - PI * 0.5), Vector3.ZERO)
	var ring := PackedVector3Array()
	for k in 49:
		ring.append(temple * Vector3(sin(TAU * k / 48.0) * 9.2, 3.0, cos(TAU * k / 48.0) * 9.2))
	var out := {
		"way and gate": [PackedVector3Array([Vector3(-18.0, 2.2, 36.0), Vector3(-18.0, 2.2, 20.0), Vector3(-18.0, 2.5, 10.0), Vector3(-6.0, 3.0, 6.0)]), 0.9],
		"round the temple": [ring, 0.9],
		"between its columns and out of the dome": [PackedVector3Array([temple * Vector3(0.0, 3.5, 11.0), temple * Vector3(0.0, 3.5, 7.4),
				temple * Vector3(0.0, 4.0, 0.0), temple * Vector3(0.0, 9.5, 0.5), temple * Vector3(2.4, 13.6, 4.4), temple * Vector3(4.0, 18.0, 7.0)]), 0.9],
		"through her head, temple to temple": [PackedVector3Array([head * Vector3(-5.5, 3.6, -0.4), head * Vector3(5.5, 3.6, -0.4)]), 0.9],
		"into her mouth": [PackedVector3Array([head * Vector3(0.0, 2.12, 5.0), head * Vector3(0.0, 2.12, 1.2), head * Vector3(0.0, 3.0, -0.6)]), 0.1],
		"colonnade aisle": [PackedVector3Array([Vector3(-3.0, 2.8, -24.0), Vector3(22.0, 2.8, -24.0)]), 0.9],
		"pyramid door, chamber, shaft, high door": [PackedVector3Array([Vector3(29.8, 1.6, 8.0), Vector3(29.8, 1.6, -6.0), Vector3(28.2, 2.2, -6.0),
				Vector3(26.0, 2.2, -6.0), Vector3(26.0, 10.15, -6.0), Vector3(26.0, 10.15, 1.0), Vector3(26.0, 10.6, 5.0)]), 0.9],
	}
	var weave := {}
	for k in 5:
		var x := 0.6 + 3.6 * k + 1.8
		weave["colonnade gap %d" % k] = [PackedVector3Array([Vector3(x, 2.6, -17.0), Vector3(x, 2.6, -24.0)]), 0.9]
	out.merge(weave)
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
	part.visibility_range_end = SEEN + mesh.get_aabb().size.length() * 0.5


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
