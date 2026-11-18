class_name NorthernPike
extends Node3D
## A northern pike (Esox lucius), 1.0 m long: a long torpedo of a body, a flat duck-bill snout
## full of teeth (they show when its mouth opens), its dorsal and anal fins far back near the
## forked tail, olive green with rows of pale bean-shaped spots, a cream-white belly.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down; its origin is on
## its middle line, half way along, so it reaches 0.5 m ahead and 0.5 m behind. `scale` it for a
## bigger or smaller one. No sound.
##
## It swims as pike do, body and tail, drawn by the shader (no bones). A pike hangs still and
## strikes: `sway` 0 (or near it) hangs it, its fins still; a strike is the game's to move, with a
## few fast tail beats (`sway` up, `beat` short) and the mouth opening (`gape`) as it arrives;
## `curl` bends it into the S it strikes from.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat.
## Either call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or
## set `phase` yourself (for a picture that must loop: frame / frames in a beat). The same
## names and meanings as GameCommon's yellowfin tuna and sardine, so they are driven the same way.
##
## The models are creatures/northern_pike/models/northern_pike.glb (and _lo), built by
## tools/build_northern_pike.py; northern_pike.gdshader draws the markings and swims it.

const MODEL := "res://creatures/northern_pike/models/northern_pike%s.glb"
const SHADER := preload("res://creatures/northern_pike/northern_pike.gdshader")
## As the model is built (tools/build_northern_pike.py): from the tip of its lower jaw to the
## tips of its tail, and how deep and how wide its body is at its deepest (metres, at scale 1).
const LENGTH := 1.0
const DEPTH := 0.144
const WIDTH := 0.094

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 1.5
## How many times in a beat its tail beats (there and back).
@export var tail_beats := 2:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it beats: 1 a pike cruising (its tail tips swing about 0.08 m either way), 0 hanging still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far its mouth is open: 0 shut, 1 wide open (as it strikes: the lower jaw drops, the snout
## tips up a little and the teeth show).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## The low model (about a fourteenth of the triangles), for far off or for several of them.
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
## drawing a pike without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase`
## (0..1 through one beat of the tail), `sway`, `gape`, `curl`, `wave` and the colours (the top of
## the shader lists them).
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
## (`velocity` is taken so that it is called as the other fish's are; its beat here does not
## change with its speed: set `sway` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `curl` (bent round into a turn: radians from gills to tail,
## more than 0 the tail comes round to its left, +X), `wave` (the length of the wave along its
## body, in body lengths), its colours (`back`, `olive`, `belly`, `spot`, `fin`, `fin_dark`,
## `fin_low`, `tooth`, `mouth_inside`) and `spots_show` (how strongly the spots and the fins'
## blotches show).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one beat of the tail it is)
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
	# (its tail swings out past where the still model ends, and its jaw drops below it)
	mesh.extra_cull_margin = 0.15
	mesh.name = "NorthernPikeLo" if low_wanted else "NorthernPike"
	add_child(mesh)
	return mesh


static func _mesh_at(path: String) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]
