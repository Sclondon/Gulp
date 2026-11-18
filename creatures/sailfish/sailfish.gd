class_name Sailfish
extends Node3D
## A sailfish (Istiophorus platypterus), 2.6 m long from the tip of its bill to the tips of its
## tail: a long, thin, round bill, a slim flat-sided body, a huge spotted blue sail along its back
## that it raises and folds, two very long thin pelvic fins trailing like rods, a narrow keeled
## tail wrist and a wide, deeply forked crescent tail. A dark cobalt back, brownish-blue flanks
## crossed by upright rows of pale blue dots, a silver-white belly, blue-black fins.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its bill points along its own -Z (Godot's forward), its belly down; its origin is on
## its middle line, half way along, so it reaches 1.3 m ahead and 1.3 m behind. `scale` it for
## a bigger or smaller one. No sound.
##
## It swims stiffly, as tunas and billfish do: the bill and head are one stiff piece, the body
## barely bends and the tail does the work, by a bend drawn by the shader (no bones).
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat.
## Either call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or
## set `phase` yourself (for a picture that must loop: frame / frames in a beat). The same
## names and meanings as GameCommon's yellowfin tuna and cutthroat trout, so they are all driven
## the same way.
##
## The model is creatures/sailfish/models/sailfish.glb (and _lo), built by
## tools/build_sailfish.py; sailfish.gdshader draws its markings, folds its sail and swims it.

const MODEL := "res://creatures/sailfish/models/sailfish%s.glb"
const SHADER := preload("res://creatures/sailfish/sailfish.gdshader")
## As the model is built (tools/build_sailfish.py), in metres at scale 1: from the tip of its
## bill to the tips of its tail; how deep and how wide its body is at its deepest (without fins).
const LENGTH := 2.6
const DEPTH := 0.3
const WIDTH := 0.172
## How much of LENGTH is bill ahead of the tip of the lower jaw (metres): the bare spike.
const BILL := 0.3

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 1.8
## How many times in a beat its tail beats (there and back).
@export var tail_beats := 3:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it beats: 1 a sailfish cruising (its tail tips swing about 0.2 m either way), 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far its sail is raised: 1 fully up (as when it herds prey or turns), 0 folded down into
## its groove along the back (as when it swims fast).
@export_range(0.0, 1.0) var sail := 1.0:
	set(value):
		sail = value
		_send(&"sail", value)
## How far its mouth is open: 0 shut, 1 wide open, as when it bites (the lower jaw swings down
## about its hinge; the inside of the mouth is dark).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = value
		_send(&"gape", value)
## The low model (about a twelfth of the triangles), for far off or for many of them.
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

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D


func _init() -> void:
	_material = ShaderMaterial.new()
	_material.shader = SHADER


func _ready() -> void:
	_full = _mesh_of("")
	_low = _mesh_of("_lo")
	_show()
	_send_phase()
	_send(&"sway", sway)
	_send(&"sail", sail)
	_send(&"gape", gape)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the tuna's and the trout's are; the beat here
## does not change with its speed: set `sway`, `beat` and `sail` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `curl` (bends the body into a turn behind the head, in
## radians from gills to tail; more than 0 the tail comes round to +X), `ripple` (how far the top
## of the raised sail waves to each side, metres), `wave` (the length of the wave along its
## body), `bars_show` (how strongly the flank's rows of dots show) and its colours (`back`,
## `back_blue`, `flank`, `silver`, `belly`, `bars`, `sail_blue`, `sail_dark`, `sail_spots`,
## `fin_dark`, `bill`, `mouth`).
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


func _mesh_of(suffix: String) -> MeshInstance3D:
	var scene := load(MODEL % suffix) as PackedScene
	var made := scene.instantiate()
	var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
	var mesh := MeshInstance3D.new()
	mesh.mesh = found.mesh
	mesh.material_override = _material
	# (its tail swings out past where the still model ends)
	mesh.extra_cull_margin = 0.4
	mesh.name = "Sailfish" + suffix
	made.free()
	add_child(mesh)
	return mesh
