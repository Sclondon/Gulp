class_name BatRay
extends Node3D
## A bat ray (Myliobatis californica), 1.2 m across its wings and 1.4 m from its nose to the tip
## of its tail: a raised blunt head with an eye on each of its sides, two long pointed wings
## that it flaps like a bird, a whip of a tail with a small dorsal fin and a sting at its root,
## dark brown-olive above and white beneath. Its mouth is underneath.
##
## How it looks and flies only: whatever moves it puts it where it is and turns it the way it
## goes (bank it into its turns yourself). Its nose points along its own -Z (Godot's forward),
## its back is up. Its origin is on its middle line, half way from its nose to its tail's tip
## and half way up its height: so the origin is where the disc ends and the tail begins, the
## nose 0.7 m ahead of it and the middle of the disc `DISC_MIDDLE` (0.35 m) ahead of it. Its
## underside is `UNDER` (0.0713 m) below the origin. `scale` it for a bigger or smaller one. No
## sound.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its wings beat
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat.
## Either call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or
## set `phase` yourself (for a picture that must loop: frame / frames in a beat). The same
## names and meanings as GameCommon's yellowfin tuna.
##
## The model is creatures/bat_ray/models/bat_ray.glb (and _lo), built by tools/build_bat_ray.py
## with its wings held out flat; bat_ray.gdshader draws its markings and flaps it.

const MODEL := "res://creatures/bat_ray/models/bat_ray%s.glb"
const SHADER := preload("res://creatures/bat_ray/bat_ray.gdshader")
## As the model is built (tools/build_bat_ray.py), metres at scale 1: from its nose to the tip of
## its tail; from wing tip to wing tip; how tall it is at its head (belly to the top of its
## back); and `WIDTH`, the same as `SPAN` (so that it can be asked what every fish is asked).
const LENGTH := 1.4
const SPAN := 1.2
const DEPTH := 0.143
const WIDTH := SPAN
## How long the disc is (nose to the root of the tail), and how far ahead of the origin its
## middle is.
const DISC_LENGTH := 0.7
const DISC_MIDDLE := 0.35
## How far its underside is below its origin.
const UNDER := 0.0713

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 1.8
## How many times in a beat its wings beat (down and up).
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely its wings beat: 1 a bat ray cruising (its wing tips rise about 0.3 m and fall
## about 0.23 m), 0 gliding with them held flat.
@export_range(0.0, 1.6) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Its mouth (underneath): 0 shut, 1 wide open.
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = value
		_send(&"gape", value)
## The low model (about a fifteenth of the triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set
## it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()

static var _meshes := {}

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D


## The mesh of the full model, or of the low one: for drawing bat rays yourself (a MultiMesh, a
## MeshInstance3D of your own) with `new_material()`. Give what draws it room for the wings'
## beat (`extra_cull_margin` 0.4).
static func mesh_of(low_wanted := false) -> Mesh:
	var path := MODEL % ("_lo" if low_wanted else "")
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase`
## (0..1 through one beat of the wings), `sway`, `gape`, `curl`, `lag` and the colours (the top
## of the shader lists them).
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
	_send(&"sway", sway)
	_send(&"gape", gape)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the other fish are; its beat here does not
## change with its speed: set `sway` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `curl` (bends its rear and tail round to one side, radians
## from the middle of the disc to the tail's tip; more than 0 and the tail comes round to +X;
## the wings are not bent), `lag` (how late the wing tips follow the roots, as a part of a beat)
## and its colours (`back`, `back_dark`, `belly`, `belly_dusk`, `mouth`, `iris`, `spine`).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one beat of the wings it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


func _show() -> void:
	if _full:
		_full.visible = not low
		_low.visible = low


func _instance_of(low_wanted: bool) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = mesh_of(low_wanted)
	mesh.material_override = _material
	# (its wing tips rise and fall well past where the still model ends)
	mesh.extra_cull_margin = 0.4
	mesh.name = "BatRay" + ("_lo" if low_wanted else "")
	add_child(mesh)
	return mesh
