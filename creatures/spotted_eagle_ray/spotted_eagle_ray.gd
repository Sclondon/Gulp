class_name SpottedEagleRay
extends Node3D
## A spotted eagle ray (Aetobatus narinari; A. laticeps is its Pacific twin), 2 m across its
## wings: a head that stands out ahead of the wings and ends in a flat, rounded bill like a
## duck's; pointed wings; a whip of a tail more than twice as long as its body, with a small
## dorsal fin at its root and two barbed spines behind that. Blue-black above, covered in white
## spots and rings; white beneath.
##
## How it looks and flies only: whatever moves it puts it where it is and turns it the way it
## goes. Its bill points along its own -Z (Godot's forward), its belly down; its origin is on
## its middle line, half way along its body disc (the disc reaches 0.575 m ahead and behind; the
## tail 2.7 m further behind). `scale` it for a bigger or smaller one. No sound.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its wings beat
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat.
## Either call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or
## set `phase` yourself (for a picture that must loop: frame / frames in a beat). The same
## names as GameCommon's fish (`YellowfinTuna` and the rest), so that it is driven as they are:
## what is a tail beat there is a wing beat here.
##
## The model is creatures/spotted_eagle_ray/models/spotted_eagle_ray.glb (and _lo), built by
## tools/build_spotted_eagle_ray.py; spotted_eagle_ray.gdshader draws its markings and moves it.

const MODEL := "res://creatures/spotted_eagle_ray/models/spotted_eagle_ray%s.glb"
const SHADER := preload("res://creatures/spotted_eagle_ray/spotted_eagle_ray.gdshader")
## As the model is built (tools/build_spotted_eagle_ray.py), in metres at scale 1: from the tip
## of its bill to the tip of its tail; across its wing tips; how deep its body is.
## (WIDTH is SPAN: the name the fish have.)
const LENGTH := 3.85
const SPAN := 2.0
const DEPTH := 0.23
const WIDTH := SPAN
## How long its body disc is, from its bill to the root of its tail (the origin is half way).
const DISC := 1.15
## How far ahead of its origin it reaches (its bill) and how far behind (its tail's tip).
const AHEAD := 0.575
const BEHIND := 3.275

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 1.9
## How many times in a beat its wings beat (up and down). The fish's name for it is kept.
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it beats: 1 cruising (its wing tips rise about 0.32 m and fall about 0.24 m), 0
## gliding with its wings held out.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far its mouth (a slit under its head) is open: 0 shut, 1 wide open.
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## Banked into a turn: more than 0 it turns towards +X, less than 0 towards -X; about 1 is a tight
## turn. At `curl` c the whole animal is rolled 0.6 c radians about its long axis with its +X
## side down, the +X wing (inside the turn) droops a further 0.35 c radians by its tip and the
## other lifts as much, and the tail trails round to +X, c radians by its tip.
@export_range(-1.5, 1.5) var curl := 0.0:
	set(value):
		curl = value
		_send(&"curl", value)
## The low model (about a tenth of the triangles), for far off or for several of them.
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


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`): for
## drawing an eagle ray without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase`
## (0..1 through one beat of the wings), `sway`, `gape`, `curl` and the colours (the
## top of the shader lists them).
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
	_send(&"curl", curl)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the fish's are; its beat here does not change
## with its speed: set `sway` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: its colours (`back`, `back_blue`, `spot`, `belly`,
## `belly_dusk`, `slit_dark`, `tail_dark`, `spine`, `mouth_inside`), `spots_show` (how strongly
## the white spots show) and `spots_apart` (how far apart they are, metres).
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
	# (its wing tips rise and its tail swings well past where the still model ends)
	mesh.extra_cull_margin = SPAN * 0.8
	mesh.name = "SpottedEagleRayLo" if low_wanted else "SpottedEagleRay"
	add_child(mesh)
	return mesh


static func _mesh_at(path: String) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]
