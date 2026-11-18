class_name SpinyLobster
extends Node3D
## A California spiny lobster (Panulirus interruptus), 0.6 m from the horns over its eyes to the
## end of its tail fan: no claws, a spiny reddish-brown carapace with two big horns, two very long,
## thick, spiny antennae swept forward and out in a V (longer than its body), a broad tail fan and
## ten walking legs.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it
## faces. Its head points along its own -Z (Godot's forward), its back up; its origin is ON THE
## GROUND under the middle of its body (half way from its horns to the end of its tail fan), so
## put it where the sea floor is; its body is held 0.055 to 0.165 m up on its legs. `scale` it for
## a bigger or smaller one (0.6 m is a big one: 0.3 to 0.4 is usual). No sound.
##
## Everything moves in the shader (no bones), on `phase`, 0 to 1 through one `beat`, in which each
## leg steps `steps` times (a whole number), so it comes round again exactly every beat. `walk`
## strides its legs (+ forwards); its antennae swing slowly as `phase` goes round. Either call
## `step(velocity, delta)` each frame, which moves `phase` on by how far it has walked (so its feet
## do not slide) or, standing, by `beat` (its antennae still swing), or set `phase` yourself.
##
## The models are creatures/spiny_lobster/models/spiny_lobster.glb (and _lo), built by
## tools/build_spiny_lobster.py; spiny_lobster.gdshader draws the markings and moves it.

const MODEL := "res://creatures/spiny_lobster/models/spiny_lobster%s.glb"
const SHADER := preload("res://creatures/spiny_lobster/spiny_lobster.gdshader")
## As the model is built (tools/build_spiny_lobster.py), metres at scale 1: from the front of its
## carapace (its horns) to the end of its tail fan, and how deep and how wide its carapace is.
const LENGTH := 0.6
const DEPTH := 0.109
const WIDTH := 0.126
## How high the top of its back stands above the ground; how far its legs' feet reach out to each
## side; how far its antennae reach out to each side and ahead of its origin.
const HEIGHT := 0.165
const REACH := 0.17
const ANTENNA_REACH := Vector2(0.261, 0.961)
## How far a foot moves in one step at `walk` 1 (as the shader has it), and how much of a step a
## foot is on the ground.
const STRIDE := 0.05
const ON_GROUND := 0.65

## Seconds one beat takes (used by `step` when it is standing: its antennae swing once a beat).
@export var beat := 3.0
## How many times each leg steps in a beat.
@export var steps := 1:
	set(value):
		steps = maxi(value, 0)
		_send_phase()
## Walking: 0 standing, 1 a walk forwards, -1 backwards; more is a longer stride.
@export_range(-2.0, 2.0) var walk := 0.0:
	set(value):
		walk = value
		_send(&"walk", value)
## The low model (about a seventh of the triangles), for far off or for several of them.
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
## (0..1 through one cycle of steps), `walk`, `feel` and the colours (the top of the shader lists
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


## Each frame. Walking (`walk` not 0): moves `phase` on by how far it has gone forwards or
## backwards (`velocity` in the world's metres a second), so that its feet keep still on the
## ground, and points `walk` the way it is going (keeping its size). Standing (`walk` 0): moves
## `phase` on by delta / beat (its antennae swing).
func step(velocity: Vector3, delta: float) -> void:
	if steps == 0:
		return
	if is_zero_approx(walk):
		phase += delta / maxf(beat, 0.01)
		return
	var speed := -(global_basis.inverse() * velocity).z
	if absf(speed) < 0.0005:
		return
	var size := absf(walk)
	walk = size * signf(speed)
	# (a foot moves STRIDE * size while it is on the ground, which is ON_GROUND of a step)
	phase += absf(speed) * delta * ON_GROUND / (STRIDE * size) / steps


## Sets one of the shader's settings: its colours (`shell`, `shell_dark`, `pale`, `spine_tip`),
## `speckle`, `feel` (how far its antennae swing), or `walk` for a game's own material.
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
	# (its antennae swing and its feet step out past where the still model ends)
	mesh.extra_cull_margin = 0.15
	mesh.name = "SpinyLobsterLo" if low_wanted else "SpinyLobster"
	add_child(mesh)
	return mesh
