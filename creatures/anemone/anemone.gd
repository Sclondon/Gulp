class_name Anemone
extends Node3D
## A sea anemone of the Californian coast, of one of three kinds (`kind`), each a model of its own:
##
## - GIANT_GREEN (Anthopleura xanthogrammica): squat, a stout olive column studded with rows of pale
##   bumps, a broad flat green disc with a slit mouth, and rows of short thick blunt green tentacles
##   round its outer part. 0.24 m across its tentacles, 0.085 m high.
## - TUBE (Pachycerianthus fimbriatus): a long slender felt tube standing out of the sand, an inner
##   ring of short dark tentacles over the mouth at its top and a crown of very long thin tentacles
##   that arch out and trail down. 0.3 m high, its crown about 0.31 m across.
## - PLUMOSE (Metridium farcimen): a tall smooth column, white or orange (`colour`, see WHITE and
##   ORANGE), with a collar under a lobed, frilled crown covered in very many fine short tentacles:
##   the feathery head. 0.47 m high, its crown about 0.4 m across.
##
## Its base is at y = 0 and its middle on its own Y axis: put it on the ground where it stands (the
## tube goes 0.012 m into the sand). Its tentacles sway in the vertex shader, from where each one's
## root is in the world and the global shader uniform `water_clock` (seconds), which the project must
## declare (Project Settings > Shader Globals: a float named water_clock) and move on itself, as Gulp
## does; the plumose's tall column leans to and fro with them. No clock of its own, no physics, no
## sound. `retract` (0..1) pulls its tentacles in and squats its column down into a closed blob (the
## tube anemone instead pulls down into its tube): drive it up when something touches it, and back
## down slowly. How far its sting reaches is `STING_REACH` (what stinging means is the game's).
##
## Three models of each kind: the full one, the game one (`game`) and the low one (`low`). Each is
## loaded only when first shown, so a game that sets `game` never loads the full models.
##
## The models are creatures/anemone/models/anemone_<kind>.glb (and _game, _lo), built by
## tools/build_anemone.py; anemone.gdshader sways them, draws them in and colours them.

enum Kind { GIANT_GREEN, TUBE, PLUMOSE }

const MODEL := "res://creatures/anemone/models/anemone_%s%s.glb"
const SHADER := preload("res://creatures/anemone/anemone.gdshader")
## Each kind's name in its models' file names.
const NAMES := {Kind.GIANT_GREEN: "giant_green", Kind.TUBE: "tube", Kind.PLUMOSE: "plumose"}
## As the models are built (metres, at scale 1): how far out from its middle line its tentacles
## reach, and how high its highest point stands.
const RADIUS := {Kind.GIANT_GREEN: 0.121, Kind.TUBE: 0.156, Kind.PLUMOSE: 0.201}
const HEIGHT := {Kind.GIANT_GREEN: 0.085, Kind.TUBE: 0.302, Kind.PLUMOSE: 0.471}
## How far its sting reaches, metres from its middle line at scale 1 (its tentacles' reach and a
## little more): the giant green's and the plumose's from their discs, the tube anemone's from its
## crown at the top of its tube. Something nearer than this to the tentacles may be stung; at
## `retract` 1 nothing is (its tentacles are in).
const STING_REACH := {Kind.GIANT_GREEN: 0.135, Kind.TUBE: 0.17, Kind.PLUMOSE: 0.21}
## The plumose's two usual colours (it is one or the other in the wild).
const WHITE := Color(0.93, 0.91, 0.86)
const ORANGE := Color(0.95, 0.52, 0.22)
## What each kind sets in the shader: how it sways, the blob it closes into, its colours.
const KINDS := {
	Kind.GIANT_GREEN: {
		"kind": 0, "sway_reach": 0.004, "wave": 0.0, "column_sway": 0.0, "body_height": 0.085,
		"blob": Vector2(0.08, 0.042), "sink": 0.0,
		"colour": Color(0.24, 0.6, 0.36), "tip_colour": Color(0.55, 0.86, 0.72),
		"disc_colour": Color(0.3, 0.54, 0.3), "column_colour": Color(0.36, 0.4, 0.2),
		"spot_colour": Color(0.62, 0.6, 0.48), "inner_colour": Color(0.3, 0.4, 0.2),
		"tube_colour": Color(0.3, 0.3, 0.2),
	},
	Kind.TUBE: {
		"kind": 1, "sway_reach": 0.028, "wave": 2.2, "column_sway": 0.0, "body_height": 0.3,
		"blob": Vector2(0.02, 0.02), "sink": 0.055,
		"colour": Color(0.86, 0.56, 0.28), "tip_colour": Color(0.96, 0.86, 0.7),
		"disc_colour": Color(0.42, 0.26, 0.18), "column_colour": Color(0.4, 0.3, 0.24),
		"spot_colour": Color(0.5, 0.4, 0.3), "inner_colour": Color(0.34, 0.16, 0.28),
		"tube_colour": Color(0.33, 0.28, 0.23),
	},
	Kind.PLUMOSE: {
		"kind": 2, "sway_reach": 0.003, "wave": 0.0, "column_sway": 0.012, "body_height": 0.45,
		"blob": Vector2(0.085, 0.085), "sink": 0.0,
		"colour": WHITE, "tip_colour": Color(1.0, 0.98, 0.95),
		"disc_colour": WHITE, "column_colour": WHITE,
		"spot_colour": WHITE, "inner_colour": WHITE, "tube_colour": WHITE,
	},
}

static var _meshes := {}

## Which anemone it is: its model and its colours (setting it puts `colour` back to the kind's own).
@export var kind := Kind.GIANT_GREEN:
	set(value):
		kind = value
		colour = KINDS[kind]["colour"]
		_dress()
		_show()
## Its own colour: the giant green's and the tube anemone's tentacles, all of the plumose (WHITE or
## ORANGE in the wild). Each kind starts with its own.
@export var colour := Color(0.24, 0.6, 0.36):
	set(value):
		colour = value
		_send(&"colour", value)
## 0 open; 1 its tentacles pulled right in and its column squatted into a closed blob (the tube
## anemone: down into its tube). Its tentacles go in first, then its body.
@export_range(0.0, 1.0) var retract := 0.0:
	set(value):
		retract = clampf(value, 0.0, 1.0)
		_send(&"retract", retract)
## How far its tentacles sway (1 as each kind is set: the giant green's stout ones a few mm at their
## tips, the tube anemone's long ones about 3 cm), 0 still.
@export_range(0.0, 3.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How fast they sway: 1 about once every six seconds of `water_clock`.
@export_range(0.0, 4.0) var sway_speed := 1.0:
	set(value):
		sway_speed = value
		_send(&"sway_speed", value)
## The low model (a few hundred triangles), for far off, phones or many.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about 1,500 to 1,800 triangles, spent on the outline: the tentacles, the
## plumose's frilled crown) in place of the full one. With it set the full model is never loaded.
## `low` wins over it.
@export var game := false:
	set(value):
		game = value
		_show()

var _material: ShaderMaterial
var _body: MeshInstance3D


## A kind's full model's mesh, or its low one's (each one surface, to wear `new_material(kind)`):
## for drawing anemones without this node. Loaded once and kept.
static func mesh_of(kind_wanted: Kind, low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % [NAMES[kind_wanted], "_lo" if low_wanted else ""], false)


## A kind's game model's mesh (one surface, to wear `new_material(kind)`): loaded once and kept,
## without the importer's thinned LOD meshes (the shader sways it, and a thinned one would sway in
## straight pieces far off).
static func game_mesh(kind_wanted: Kind) -> Mesh:
	return _mesh_at(MODEL % [NAMES[kind_wanted], "_game"], true)


## The same mesh without the importer's LOD meshes.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


static func _mesh_at(path: String, plain: bool) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh) if plain else found.mesh
		made.free()
	return _meshes[path]


## A new material for a kind's meshes, dressed as that kind. Its shader settings are the game's to
## set: `retract`, `sway`, `sway_speed`, `current`, `colour` and the others (the top of the shader
## lists them).
static func new_material(kind_wanted: Kind) -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	var wears: Dictionary = KINDS[kind_wanted]
	for setting: String in wears:
		made.set_shader_parameter(setting, wears[setting])
	return made


func _init() -> void:
	_material = new_material(kind)


func _ready() -> void:
	_body = MeshInstance3D.new()
	_body.material_override = _material
	# (its tentacles sway out past the still model's box)
	_body.extra_cull_margin = 0.05
	_body.name = "Anemone"
	add_child(_body)
	_show()
	_send(&"colour", colour)
	_send(&"retract", retract)
	_send(&"sway", sway)
	_send(&"sway_speed", sway_speed)


## How far its sting reaches from its middle line now (STING_REACH for its kind, times its scale;
## nothing once it is drawn in).
func sting_reach() -> float:
	var size := global_basis.get_scale().x if is_inside_tree() else scale.x
	return STING_REACH[kind] * size if retract < 0.5 else 0.0


## Sets one of the shader's settings: `current` (a Vector2: a steady lean of the tips with the
## water, metres in its own x and z), the colours (colour, tip_colour, disc_colour, column_colour,
## spot_colour, inner_colour, tube_colour), or how it sways (sway_reach, wave, column_sway).
## `kind` sets most of them again.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_send(setting, value)


## Its one material (all its models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


func _dress() -> void:
	if _material:
		var wears: Dictionary = KINDS[kind]
		for setting: String in wears:
			_material.set_shader_parameter(setting, wears[setting])
		_material.set_shader_parameter(&"colour", colour)


## (one mesh shown, loaded only now: a game that sets `game` never loads the full model)
func _show() -> void:
	if _body:
		if low:
			_body.mesh = mesh_of(kind, true)
		elif game:
			_body.mesh = game_mesh(kind)
		else:
			_body.mesh = mesh_of(kind, false)
