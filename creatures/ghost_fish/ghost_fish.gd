class_name GhostFish
extends Node3D
## A ghost fish: a little glowing fish skeleton, 0.4 m long, with a faint halo; one of a school of
## them. A skull with a round eye socket right through it, a spine, five pairs of ribs, a forked tail.
## It glows (light added over what is behind it) and comes in and out with `fade`: a thing of the
## night and the deep, swimming with the ghost whale.
##
## Drawn by creatures/ghost_whale/ghost.gdshader, the ghost whale's own shader (this component needs
## godot/ghost-whale installed): one shader program for both. It sweeps its tail side to side.
##
## For a school, do not make hundreds of these nodes: draw `GhostFish.school_mesh()` with one
## MultiMesh. Drawn by GameCommon's Flock (its `custom_mesh`), the bare mesh works with the Flock's own
## shader (pale lit bones, no glow); for the glow, put `GhostFish.school_material()` on the Flock's
## MultiMeshInstance3D as its `material_override` and use `school_mesh(true)` for the halo: each fish
## then swims by its own beat (the Flock's instance data) and the whole school fades together with
## `school_material().set_shader_parameter("fade", ...)`.
##
## Its nose points along -Z, its back up; its origin is on its middle line half way along. Everything
## that moves runs on `phase` (0..1 through a `beat`), so its motion loops exactly. No sound.
##
## The models are creatures/ghost_fish/models/ghost_fish.glb (about 94 triangles, with the halo) and
## ghost_fish_bare.glb (about 90, without), built by tools/build_ghost_fish.py.

const MODEL := "res://creatures/ghost_fish/models/ghost_fish%s.glb"
const SHADER := preload("res://creatures/ghost_whale/ghost.gdshader")
## From the tip of its snout to the tips of its tail, how deep (the tail's tips) and how wide (the ribs)
## it is (metres, at scale 1). Its halo reaches 0.11 m round it.
const LENGTH := 0.4
const DEPTH := 0.096
const WIDTH := 0.04

## Seconds one beat takes.
@export var beat := 0.6
## How many times in a beat its tail sweeps (a whole number).
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send(&"tail_beats", float(tail_beats))
## How hard it swims: 1 cruising.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Turning: radians from its gills to its tail (more than 0 the tail comes round to +X).
@export_range(-3.0, 3.0) var curl := 0.0:
	set(value):
		curl = value
		_send(&"curl", value)
## How much it is there: 0 gone, 1 all there.
@export_range(0.0, 1.0) var fade := 1.0:
	set(value):
		fade = clampf(value, 0.0, 1.0)
		_send(&"fade", fade)
## How brightly it glows (1 as made).
@export_range(0.0, 3.0) var glow := 1.0:
	set(value):
		glow = value
		_send(&"glow", glow)
## How far through a beat it is, 0 to 1. `step` moves it on; or set it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)

static var _meshes := {}
static var _school_material: ShaderMaterial

var _material: ShaderMaterial


## Its mesh, with the halo (one surface, to wear `new_material()`). There is no lower model: it is
## already about 94 triangles.
static func mesh_of(_low := false) -> Mesh:
	return _mesh_at(MODEL % "")


## The mesh for a school drawn by one MultiMesh: the bones only (about 90 triangles, vertex-coloured
## pale, for a Flock's own shader), or with `halo` its halo cards too (for `school_material()` only).
static func school_mesh(halo := false) -> Mesh:
	return _mesh_at(MODEL % ("" if halo else "_bare"))


## A new material for one fish (the ghost shader with the fish's numbers).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	made.set_shader_parameter(&"body_length", LENGTH)
	made.set_shader_parameter(&"lateral", true)
	made.set_shader_parameter(&"reach", 0.09)
	made.set_shader_parameter(&"wave", 1.0)
	made.set_shader_parameter(&"jaw_hinge", Vector2(-1.0, 0.0))
	made.set_shader_parameter(&"flipper_root", Vector3(-1.0, 0.0, 0.0))
	made.set_shader_parameter(&"far", 45.0)
	made.set_shader_parameter(&"waver", 0.0)
	return made


## The one material for a whole school drawn by a MultiMesh: each fish swims by its own beat (the
## instance's custom data x, radians, as GameCommon's Flock keeps it; y its effort). Shared: set `fade`
## and `glow` on it for the whole school.
static func school_material() -> ShaderMaterial:
	if _school_material == null:
		_school_material = new_material()
		_school_material.set_shader_parameter(&"school", true)
	return _school_material


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	var mesh := MeshInstance3D.new()
	mesh.mesh = mesh_of()
	mesh.material_override = _material
	mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mesh.extra_cull_margin = 0.15
	mesh.name = "GhostFish"
	add_child(mesh)
	for setting: StringName in [&"sway", &"curl", &"fade", &"glow", &"phase"]:
		_send(setting, get(setting))
	_send(&"tail_beats", float(tail_beats))


## Each frame: moves it on through its beat.
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings (`far`, `bone_colour`, `mist_colour`, ...).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its material.
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


static func _mesh_at(path: String) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		# (without the thinned LOD meshes Godot's importer adds: the shader bends it)
		var bare := ArrayMesh.new()
		for surface in found.mesh.get_surface_count():
			bare.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, found.mesh.surface_get_arrays(surface))
		_meshes[path] = bare
		made.free()
	return _meshes[path]
