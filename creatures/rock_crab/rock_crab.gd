class_name RockCrab
extends Node3D
## A red rock crab (Cancer productus), 0.16 m across its shell: a fan-shaped brick-red shell with a
## toothed front edge, two stout claws with black fingers folded in front of it, eight walking
## legs, eyes on short stalks. It walks sideways.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it
## faces. Its front points along its own -Z (Godot's forward), its back up; its origin is ON THE
## GROUND under the middle of its shell (its feet stand at y 0), so put it where the sea floor is.
## `scale` it for a bigger or smaller one. No sound.
##
## Its legs walk in the shader (no bones): each is two stiff lengths worked out so that a foot on
## the ground stays put. Everything that moves runs on `phase`, 0 to 1 through one `beat`, in
## which every leg steps `steps` times (a whole number), so it comes round again exactly every
## beat. `walk` says which way and how far it strides (+ to its left, +X; - to its right);
## `claws` raises and opens its claws. Either call `step(velocity, delta)` each frame, which
## moves `phase` on by how far it has gone sideways (so its feet do not slide) and turns `walk`
## the way it is going, or set `phase` and `walk` yourself.
##
## The models are creatures/rock_crab/models/rock_crab.glb (and _lo), built by
## tools/build_rock_crab.py; rock_crab.gdshader draws the markings and moves it.

const MODEL := "res://creatures/rock_crab/models/rock_crab%s.glb"
const SHADER := preload("res://creatures/rock_crab/rock_crab.gdshader")
## As the model is built (tools/build_rock_crab.py), metres at scale 1: the shell from front to
## back, how high it is from its underside to the top of its dome, and how wide it is across (a
## crab's size is usually given as this width).
const LENGTH := 0.104
const DEPTH := 0.044
const WIDTH := 0.16
## How high the top of its shell stands above the ground, and how far its feet reach out to each
## side of its middle (at rest).
const HEIGHT := 0.059
const REACH := 0.129
## How far a foot moves in one step at `walk` 1 (as the shader has it), and how much of a step a
## foot is on the ground.
const STRIDE := 0.026
const ON_GROUND := 0.6

## Seconds one beat takes, when it walks on the spot (`step` with no velocity does not walk it).
@export var beat := 1.0
## How many times each leg steps in a beat.
@export var steps := 2:
	set(value):
		steps = maxi(value, 0)
		_send_phase()
## Which way and how far it strides: 0 standing, 1 a walk to its left (+X), -1 to its right (-X).
@export_range(-2.0, 2.0) var walk := 0.0:
	set(value):
		walk = value
		_send(&"walk", value)
## Its claws: 0 folded in front of it, 1 raised high and spread with their fingers open.
@export_range(0.0, 1.0) var claws := 0.0:
	set(value):
		claws = clampf(value, 0.0, 1.0)
		_send(&"claws", claws)
## The low model (about a tenth of the triangles), for far off or for several of them.
@export var low := false:
	set(value):
		low = value
		_show()
## How far through a beat it is, 0 to 1 (only the fraction counts).
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()

static var _meshes := {}

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`).
static func mesh_of(low_wanted := false) -> Mesh:
	var path := MODEL % ("_lo" if low_wanted else "")
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase`
## (0..1 through one cycle of steps), `walk`, `claws` and the colours (the top of the shader lists
## them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_full = _instance_of(false)
	_low = _instance_of(true)
	_show()
	_send_phase()
	_send(&"walk", walk)
	_send(&"claws", claws)


## Each frame: moves `phase` on by how far it has gone sideways (`velocity` in the world's
## metres a second), so that its feet keep still on the ground, and points `walk` the way it is
## going (keeping its size). A crab going forwards or backwards still steps sideways here: it
## only knows how to walk sideways.
func step(velocity: Vector3, delta: float) -> void:
	var local := global_basis.inverse() * velocity
	var speed := local.x
	if absf(speed) < 0.0005 or steps == 0:
		return
	var size := maxf(absf(walk), 0.3)
	walk = size * signf(speed)
	# (a foot moves STRIDE * size while it is on the ground, which is ON_GROUND of a step)
	phase += absf(speed) * delta * ON_GROUND / (STRIDE * size) / steps


## Sets one of the shader's settings: its colours (`shell`, `shell_dark`, `shell_rim`, `under`,
## `tips`) and `mottle`, or `walk`, `claws` for a game's own material.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one cycle of steps it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * steps, 1.0))


func _show() -> void:
	if _full:
		_full.visible = not low
		_low.visible = low


func _instance_of(low_wanted: bool) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = mesh_of(low_wanted)
	mesh.material_override = _material
	# (its claws rise and its feet step out past where the still model ends)
	mesh.extra_cull_margin = 0.06
	mesh.name = "RockCrabLo" if low_wanted else "RockCrab"
	add_child(mesh)
	return mesh
