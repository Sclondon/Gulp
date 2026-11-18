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
## The game model (about 3,900 triangles, spent where they show: the outline, the eye, the mouth, the
## fins' edges), shown in place of the full one; `low` still shows the low model. With it true the full model
## is never loaded (each model is loaded when it is first shown), so a game's export can leave the full .glb out.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 the eye as it is (the default), 1 bigger, white, a coloured iris and big pupil, a
## highlight, a dark outline, and this animal's own lid (see the shader's top for its character).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = value
		_send(&"cartoon_eyes", value)
## Where its eyes look, -1..1 each way: x forward (towards its snout), y up.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value
		_send(&"eye_look", value)
## 0 open, 1 shut: its eyes squash flat and, with `cartoon_eyes`, a lid comes down over them.
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = value
		_send(&"blink", value)
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set
## it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()

var _material: ShaderMaterial
# (the models shown so far, by suffix: each is loaded when it is first shown)
var _shown := {}
var _ready_done := false


func _init() -> void:
	_material = ShaderMaterial.new()
	_material.shader = SHADER


func _ready() -> void:
	_ready_done = true
	_show()
	_send_phase()
	_send(&"cartoon_eyes", cartoon_eyes)
	_send(&"eye_look", eye_look)
	_send(&"blink", blink)
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


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


## The game model's mesh by itself (without the importer's thinned LODs, which would bend in straight
## pieces far off), for a game that draws meshes itself: give it the node's material or `new_material()`.
static func game_mesh() -> Mesh:
	var made := (load(MODEL % "_game") as PackedScene).instantiate()
	var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
	var mesh := without_lods(found.mesh)
	made.free()
	return mesh


## A copy of `mesh` without its LODs.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one beat of the tail it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


func _show() -> void:
	if not _ready_done:
		return
	var want := "_lo" if low else ("_game" if game else "")
	if not _shown.has(want):
		_shown[want] = _mesh_of(want)
	for suffix: String in _shown:
		(_shown[suffix] as MeshInstance3D).visible = suffix == want


func _mesh_of(suffix: String) -> MeshInstance3D:
	var scene := load(MODEL % suffix) as PackedScene
	var made := scene.instantiate()
	var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
	var mesh := MeshInstance3D.new()
	mesh.mesh = without_lods(found.mesh) if suffix == "_game" else found.mesh
	mesh.material_override = _material
	# (its tail swings out past where the still model ends)
	mesh.extra_cull_margin = 0.4
	mesh.name = "Sailfish" + suffix
	made.free()
	add_child(mesh)
	return mesh
