class_name SeaMyth
extends Node3D
## What the sea's mythical creatures share (Mermaid, Hippocampus, DeepSpawn): one shader for all of
## them (sea_myth.gdshader, so a game compiles one program for the three), the driving names of
## GameCommon's fish, and their three models (full, low, game), each loaded when first shown.
##
## Each creature is a script that extends this one and says its model's path, its sizes and the
## shader numbers that make it itself (its `SETTINGS`). Its nose points along its own -Z, its belly
## down, its origin on its middle line half way along. How it looks and swims only; no sound.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, so its motion comes round again
## exactly every beat. Call `step(velocity, delta)` each frame, or set `phase` yourself.

## The shader every one of them wears.
const SHADER := preload("res://creatures/sea_myth/sea_myth.gdshader")

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 2.4
## How many times its tail beats in a beat (a whole number).
@export var tail_beats := 2:
	set(value):
		tail_beats = maxi(value, 0)
		_send(&"tail_beats", float(tail_beats))
## How widely it swims: 0 still, 1 cruising, 2 hard.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Its mouth (or jaw, or the ring of tentacles round its mouth): 0 shut, 1 wide open.
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## How far its body is bent round to one side behind its head, as when it turns: radians at its
## tail (more than 0 the tail comes round to +X, its right).
@export_range(-1.5, 1.5) var curl := 0.0:
	set(value):
		curl = value
		_send(&"curl", value)
## How far it is bent up or down about its middle: radians at each end (more than 0 both ends up,
## less than 0 its back arched: the top of a leap, the start of a dive).
@export_range(-1.5, 1.5) var arch := 0.0:
	set(value):
		arch = value
		_send(&"arch", value)
## The low model, for far off or many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (Twilight Princess weight), shown in place of the full one (`low` still shows the
## low one). With it on, the full model is never loaded.
@export var game := false:
	set(value):
		game = value
		_show()
## How far through a beat it is, 0 to 1 (only the fraction counts).
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)

static var _meshes := {}

var _material: ShaderMaterial
var _shown := {}
var _started := false


## A model's mesh by its path (one surface), loaded once; the game model's without the importer's
## automatic LODs (they would bend in straight pieces far off).
static func load_mesh(path: String, plain := false) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh) if plain else found.mesh
		made.free()
	return _meshes[path]


## A mesh rebuilt from its surfaces alone, without the importer's automatic LODs.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var bare := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		bare.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return bare


## A material of the shared shader with a creature's settings.
static func material_with(settings: Dictionary) -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	for key: StringName in settings:
		made.set_shader_parameter(key, settings[key])
	return made


## (each creature: its model's path with %s for "", "_lo" or "_game")
func _model() -> String:
	return ""


## (each creature: its shader settings)
func _settings() -> Dictionary:
	return {}


## (each creature: how far past its still box it reaches as it swims, metres)
func _margin() -> float:
	return 0.5


func _init() -> void:
	_material = material_with(_settings())


func _ready() -> void:
	_started = true
	_show()
	_send(&"phase", phase)
	_send(&"tail_beats", float(tail_beats))
	_send(&"sway", sway)
	_send(&"gape", gape)
	_send(&"curl", curl)
	_send(&"arch", arch)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as GameCommon's fish are.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings (the top of sea_myth.gdshader lists them).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


func _show() -> void:
	if not _started:
		return
	var wanted := "_lo" if low else ("_game" if game else "")
	if not _shown.has(wanted):
		var mesh := MeshInstance3D.new()
		mesh.mesh = load_mesh(_model() % wanted, wanted == "_game")
		mesh.material_override = _material
		mesh.extra_cull_margin = _margin()
		mesh.name = name + wanted
		add_child(mesh)
		_shown[wanted] = mesh
	for ending: String in _shown:
		(_shown[ending] as MeshInstance3D).visible = ending == wanted
