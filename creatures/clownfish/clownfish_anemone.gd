class_name ClownfishAnemone
extends Node3D
## The ocellaris clownfish's home: a magnificent sea anemone (Heteractis magnifica), about 0.5 m
## across its tentacles and 0.16 m high. A short magenta column standing on its foot, a broad olive
## oral disc on top whose margin rises and falls in folds, a mouth with pale lips in its middle, and
## a few hundred finger-like tentacles with blunt pale tips crowded over the disc, upright in the
## middle and leaning out and down at the margin.
##
## Its base is at y = 0 and its middle on its own Y axis: put it on the ground where it stands. It
## sways only its tentacles, in the vertex shader, from where each tentacle's root is in the world
## and the global shader uniform `water_clock` (seconds), which the project must declare (Project
## Settings > Shader Globals: a float named water_clock) and move on itself, as Gulp does. No clock
## of its own, no physics, no sound; nothing stings.
##
## Three models: the full one (250 tentacles), the game one (`game`: 100 four-sided tentacles,
## about 2,540 triangles, for games) and the low one (`low`). Each is loaded only when first shown,
## so a game that sets `game` never loads the full model.
##
## The models are creatures/clownfish/models/clownfish_anemone.glb (and _game, _lo), built by
## tools/build_clownfish_anemone.py; clownfish_anemone.gdshader sways it and draws its colours.

const MODEL := "res://creatures/clownfish/models/clownfish_anemone%s.glb"
const SHADER := preload("res://creatures/clownfish/clownfish_anemone.gdshader")
## As the model is built: how far its tentacles reach out from its middle, and how high it stands
## (metres, at scale 1).
const RADIUS := 0.255
const HEIGHT := 0.16

static var _meshes := {}

## How far the tentacles sway: 1 their tips about 15 mm either way, 0 still.
@export_range(0.0, 3.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How fast they sway: 1 about once every six seconds of `water_clock`.
@export_range(0.0, 4.0) var sway_speed := 1.0:
	set(value):
		sway_speed = value
		_send(&"sway_speed", value)
## The low model (50 thicker tentacles, about 780 triangles), for far off, phones or many.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (100 four-sided tentacles a little thicker, about 2,540 triangles against the
## full one's 13,824) in place of the full one: for games. With it set the full model is never
## loaded. `low` wins over it.
@export var game := false:
	set(value):
		game = value
		_show()

var _material: ShaderMaterial
var _body: MeshInstance3D


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`): for drawing
## anemones without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""), false)


## The game model's mesh (one surface, to wear `new_material()`): loaded once and kept, without
## the importer's thinned LOD meshes (the shader sways it, and a thinned one would sway in
## straight pieces far off).
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game", true)


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


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `sway`,
## `sway_speed`, `current` and the colours (the top of the shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_body = _instance_of()
	_show()
	_send(&"sway", sway)
	_send(&"sway_speed", sway_speed)


## Sets one of the shader's settings: `current` (a Vector2: a steady lean of the tips with the
## water, metres in its own x and z), the colours (column, column_dark, disc, disc_lines, lips,
## tentacle_root, tentacle, tentacle_tip) and `mouth_out`.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_send(setting, value)


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


## (one mesh shown, loaded only now: a game that sets `game` never loads the full model)
func _show() -> void:
	if _body:
		if low:
			_body.mesh = mesh_of(true)
		elif game:
			_body.mesh = game_mesh()
		else:
			_body.mesh = mesh_of(false)


func _instance_of() -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.material_override = _material
	# (its tentacles sway out past the still model's box)
	mesh.extra_cull_margin = 0.03
	mesh.name = "Anemone"
	add_child(mesh)
	return mesh
