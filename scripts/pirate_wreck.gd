class_name PirateWreck
extends Node3D
## A pirate ship of about 1700 wrecked on the sand: a three-master heeled 20 degrees to starboard, her stern sunk in
## the sand and her bow up on a rock, her mainmast fallen over the side, her treasure in the hold (the user,
## 2026-11-18: "and another location should be pirate ship wreck"; tools/PIRATE_WRECK.md is the design sheet).
##
##     var wreck := PirateWreck.new()
##     wreck.position = Vector3(x, Sea.ground(x, z), z)
##     wreck.rotation.y = turn
##     add_child(wreck)
##
## The model (models/pirate_wreck.glb, built by tools/build_pirate_wreck.py) has its origin at the middle of the
## keel's resting line, y = 0 at the sand; her bow points to -Z, her starboard (low) side is +X. Her highest point
## (the foremast's stump) is 14.3 m above the sand, so she wants water at least 15.5 m deep over the sand to stay under.
##
## On `_ready` it draws her with one shader (shaders/pirate_wreck.gdshader) and her baked paint, registers her solid
## parts as rocks of the sea (`Sea.add_rock`, from models/pirate_wreck.json, fitted in Blender so that every swim
## route through her stays clear: this is checked here too), grows a little sea life on her (GameCommon's sea floor
## pieces, at her ReefSpot markers) and hides beyond the sea's sight. Turn and place it before adding it: the rocks
## are laid where it stands then, and do not move with it.

const MODEL := "res://models/pirate_wreck.glb"
const ATLAS := "res://textures/pirate_atlas.png"
const DATA := "res://models/pirate_wreck.json"
const SHADER := preload("res://shaders/pirate_wreck.gdshader")
const PROPS := "res://scenery/sea_floor_props/sea_floor_props.gd"
const SEAWEED := "res://plants/seaweed/seaweed_bed.gd"
## Beyond this from the camera it is not drawn (the sea's sight, 60 m, plus her own reach from her middle).
const SEEN := 60.0
const REACH := 24.0
## The sea life that grows on her: tropical pieces of the sea floor kit (this is shallow, sunlit water).
const LIFE: PackedStringArray = ["sea_fan_purple", "sea_rods", "sea_fan_purple", "vase_sponge", "pillar_coral", "table_coral",
		"soft_coral", "puffball_sponges", "ochre_star", "urchin_purple", "giant_clam", "brain_coral"]

## The water's colour over her; dim it for night.
@export var tint := Color(0.9, 0.96, 1.0):
	set(to):
		tint = to
		for paint: ShaderMaterial in [_paint, _gold]:
			if paint:
				paint.set_shader_parameter(&"tint", to)

var _paint: ShaderMaterial
var _gold: ShaderMaterial
var _fish := PackedVector3Array()
var _lanterns := PackedVector3Array()
var _treasure := Vector3.ZERO
var _den := Vector3.ZERO
var _weed := PackedVector3Array()
var _reef: Array[Transform3D] = []
var _rocks: Array[Vector4] = []
var _checks: Array = []


func _ready() -> void:
	var model: Node3D = (load(MODEL) as PackedScene).instantiate()
	model.name = "Model"
	add_child(model)
	_paint = ShaderMaterial.new()
	_paint.shader = SHADER
	_paint.set_shader_parameter(&"atlas", load(ATLAS))
	_paint.set_shader_parameter(&"tint", tint)
	_gold = _paint.duplicate()
	_gold.set_shader_parameter(&"glow", 1.0)
	for drawn: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
		drawn.material_override = _gold if String(drawn.name).begins_with("PirateTreasure") else _paint
		drawn.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		drawn.visibility_range_end = SEEN + REACH
		drawn.visibility_range_end_margin = 4.0
	for marker: Node in model.find_children("*", "Node3D", true, false):
		var named := String(marker.name)
		var at: Transform3D = (marker as Node3D).global_transform
		if named.begins_with("ReefSpot"):
			_reef.append(at)
		elif named.begins_with("FishSpot"):
			_fish.append(at.origin)
		elif named.begins_with("Lantern"):
			_lanterns.append(at.origin)
		elif named == "TreasureSpot":
			_treasure = at.origin
		elif named == "OctopusDen":
			_den = at.origin
		elif named.begins_with("WeedSpot"):
			_weed.append(at.origin)
	_add_rocks()
	var bad := routes_blocked()
	assert(bad == 0, "PirateWreck: %d points of its swim routes are blocked" % bad)
	_grow_life()
	_grow_weed()


## Places a fish might hang about in and round her (world): the great cabin, the gun deck aft and forward, the hold,
## under the bow, under the fallen mast, over the waist, in the lee of the stern.
func fish_spots() -> PackedVector3Array:
	return _fish


## Her lanterns (world): the two on the stern, the cabin's and the hold's.
func lanterns() -> PackedVector3Array:
	return _lanterns


## The middle of the treasure's hoard in her hold (world).
func treasure() -> Vector3:
	return _treasure


## The octopus's den (world): on the sand at the foot of the big hole in her starboard side, as on the concept art.
func octopus_den() -> Vector3:
	return _den


## How many of her swim routes' check points one of her own rocks blocks (0 when all is well). Each check is a point
## and the room a swimmer there needs: the routes' middles with a 0.9 m room, their sides with almost none.
func routes_blocked() -> int:
	var bad := 0
	for check: Vector4 in _checks:
		var p := Vector3(check.x, check.y, check.z)
		for rock: Vector4 in _rocks:
			if p.distance_to(Vector3(rock.x, rock.y, rock.z)) < rock.w + check.w:
				bad += 1
				break
	return bad


## The check points of her swim routes (world), each with its room in w.
func route_checks() -> Array:
	return _checks


func _add_rocks() -> void:
	var data: Dictionary = (load(DATA) as JSON).data
	var place := global_transform
	for s: Array in data.spheres:
		var at := place * Vector3(s[0], s[1], s[2])
		var rock := Vector4(at.x, at.y, at.z, s[3])
		_rocks.append(rock)
		Sea.add_rock(rock)
	for c: Array in data.checks:
		var at := place * Vector3(c[0], c[1], c[2])
		_checks.append(Vector4(at.x, at.y, at.z, c[3]))


# A little sea life on her: at each reef spot one piece of the kit, standing on the surface there (its +Y), turned
# and sized at random (the same every time). One MultiMesh a piece, drawn with the kit's own materials.
func _grow_life() -> void:
	if _reef.is_empty() or not ResourceLoader.exists(PROPS):
		return
	var props: GDScript = load(PROPS)
	var rng := RandomNumberGenerator.new()
	rng.seed = 1717
	var placed := {}
	for at: Transform3D in _reef:
		var piece := LIFE[rng.randi() % LIFE.size()]
		var size := rng.randf_range(0.55, 1.0) if piece in ["barrel_sponge", "table_coral", "brain_coral"] else rng.randf_range(0.8, 1.5)
		var where := Transform3D(at.basis.orthonormalized() * Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3.ONE * size), at.origin - at.basis.y.normalized() * 0.03)
		var tints: PackedColorArray = props.call(&"tints_of", piece)
		if not placed.has(piece):
			placed[piece] = [[], []]
		placed[piece][0].append(where)
		placed[piece][1].append(tints[rng.randi() % tints.size()] if tints.size() > 0 else Color.WHITE)
	for piece: String in placed:
		var many := MultiMesh.new()
		many.transform_format = MultiMesh.TRANSFORM_3D
		many.use_colors = true
		# (the full model for light pieces, the low one for heavy ones)
		many.mesh = props.call(&"mesh_of", piece, int(props.call(&"triangles_of", piece)) > 1100)
		var wheres: Array = placed[piece][0]
		many.instance_count = wheres.size()
		for i in wheres.size():
			many.set_instance_transform(i, global_transform.affine_inverse() * (wheres[i] as Transform3D))
			many.set_instance_color(i, placed[piece][1][i])
		var drawn := MultiMeshInstance3D.new()
		drawn.name = "Life_" + piece
		drawn.multimesh = many
		drawn.material_override = props.call(&"material_of", piece)
		drawn.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		drawn.visibility_range_end = SEEN + REACH
		add_child(drawn)


# Weed in the sand along her sides and round her stern (as on the concept art): tall strands of feather boa kelp
# with sea palms among them, from GameCommon's seaweed (the game's scenery already draws it, so it costs no new
# shader). The bed lies in world space, unturned, as the seaweed component asks.
func _grow_weed() -> void:
	if _weed.is_empty() or not ResourceLoader.exists(SEAWEED):
		return
	var rng := RandomNumberGenerator.new()
	rng.seed = 1718
	var places := PackedVector3Array()
	var sizes := PackedFloat32Array()
	var kinds := PackedInt32Array()
	for at in _weed:
		for k in rng.randi_range(2, 4):
			places.append(at + Vector3(rng.randf_range(-0.6, 0.6), -0.02, rng.randf_range(-0.6, 0.6)))
			var palm := rng.randf() < 0.3
			kinds.append(4 if palm else 3)
			sizes.append(rng.randf_range(0.5, 0.9) if palm else rng.randf_range(1.4, 3.2))
	var bed: Node3D = (load(SEAWEED) as GDScript).new()
	bed.name = "Weed"
	bed.top_level = true
	bed.set(&"far", SEEN + REACH)
	bed.set(&"current", Vector2(0.3, 0.1))
	add_child(bed)
	bed.global_transform = Transform3D.IDENTITY
	bed.call(&"plant", places, sizes, kinds, Sea.SURFACE)
