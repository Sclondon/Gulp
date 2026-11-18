class_name WhaleShark
extends Node3D
## A whale shark (Rhincodon typus), 10 m long: a broad flat head with a very wide mouth right at
## the front, small eyes just behind its corners, five very long gill slits each side, three ridges
## along each flank, a tall first dorsal and a tall crescent tail; grey-blue above, covered in a
## checkerboard of pale spots and thin pale bars, white beneath.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down; its origin is on the
## line through the front of its head, half way along, so it reaches 5 m ahead and 5 m behind.
## `scale` it for a bigger or smaller one. No sound.
##
## It swims as sharks do, slowly: a wide lazy sweep down the whole rear of the body, drawn by the
## shader (no bones). Its mouth opens (`gape`) into a great oval for filter feeding: the lower jaw
## drops and bows, the upper lip lifts.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat. Either
## call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or set `phase`
## yourself (for a picture that must loop: frame / frames in a beat). The same names and meanings
## as GameCommon's yellowfin tuna and sardine, so they are driven the same way.
##
## The models are creatures/whale_shark/models/whale_shark.glb (and _lo), built by
## tools/build_whale_shark.py; whale_shark.gdshader draws the markings, swims it and works its jaws.

const MODEL := "res://creatures/whale_shark/models/whale_shark%s.glb"
const SHADER := preload("res://creatures/whale_shark/whale_shark.gdshader")
## As the model is built (tools/build_whale_shark.py): from the tip of its snout to the tip of its
## tail, and how deep and how wide its body is at its deepest (with its ridges), without fins (metres, at scale 1).
const LENGTH := 10.0
const DEPTH := 1.77
const WIDTH := 1.6
## How far the fins reach from its middle line: the dorsal's tip above, the tail's lower lobe below,
## the pectorals' tips to each side (metres, at scale 1, still).
const REACH_UP := 1.93
const REACH_DOWN := 1.53
const REACH_SIDE := 1.99

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 6.0
## How many times in a beat its tail beats (there and back).
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it beats: 1 a whale shark cruising (its tail tip swings about 0.9 m either way), 0
## still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far its mouth is open: 0 shut, 1 wide open as when it feeds, straining the water (the lower
## jaw drops and bows down, the upper lip lifts: a great oval, the filter pads dark at its back).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## The low model (about a sixteenth of the triangles), for far off or for several of them.
@export var low := false:
	set(value):
		low = value
		_show()
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set it
## yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()

static var _meshes := {}

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`): for
## drawing a whale shark without this node.
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
## body, in body lengths) and its colours (`back`, `spots`, `belly`, `mouth`) and `spots_show` (how strongly the spots and bars show).
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
	mesh.extra_cull_margin = 1.5
	mesh.name = "WhaleSharkLo" if low_wanted else "WhaleShark"
	add_child(mesh)
	return mesh


static func _mesh_at(path: String) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]
