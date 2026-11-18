class_name BlueMarlin
extends Node3D
## A blue marlin (Makaira nigricans), 3.6 m long from the tip of its bill to the tips of its
## tail: a stout round bill, a heavy deep-shouldered body, a first dorsal with a high pointed
## lobe at its front that then runs low along the back (no sail), long pectoral fins, thin
## pelvic fins, two keels each side of a narrow tail wrist and a wide crescent tail. A cobalt
## blue back, a silver-white belly, about fifteen upright pale blue bars down each flank.
## Its lower jaw works: `gape` opens its mouth.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its bill points along its own -Z (Godot's forward), its belly down; its origin is on
## the middle line of its body, half way along, so it reaches 1.8 m ahead and 1.8 m behind.
## `scale` it for a bigger or smaller one. No sound.
##
## It swims stiffly, as tunas and billfish do: the bill and head are one stiff piece, the body
## barely bends and the tail does the work, by a bend drawn by the shader (no bones).
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat.
## Either call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or
## set `phase` yourself (for a picture that must loop: frame / frames in a beat). The same
## names and meanings as GameCommon's yellowfin tuna, sailfish and swordfish, so they are all
## driven the same way.
##
## The model is creatures/blue_marlin/models/blue_marlin.glb (and _lo), built by
## tools/build_blue_marlin.py; blue_marlin.gdshader draws its markings, opens its mouth and
## swims it.

const MODEL := "res://creatures/blue_marlin/models/blue_marlin%s.glb"
const SHADER := preload("res://creatures/blue_marlin/blue_marlin.gdshader")
## As the model is built (tools/build_blue_marlin.py), in metres at scale 1: from the tip of its
## bill to the tips of its tail; how deep and how wide its body is at its deepest (without fins).
const LENGTH := 3.6
const DEPTH := 0.6
const WIDTH := 0.36
## How much of LENGTH is bill ahead of the tip of the lower jaw (metres): the bare spike.
const BILL := 0.42

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 2.4
## How many times in a beat its tail beats (there and back).
@export var tail_beats := 3:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it beats: 1 a marlin cruising (its tail tips swing about 0.3 m either way), 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Its mouth: 0 shut, 1 wide open, as when it bites (the tip of its lower jaw drops 0.16 m).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## The low model (about a twelfth of the triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about 3,800 triangles, spent where they show: the outline, the eye, the mouth, the
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
	_material = new_material()


func _ready() -> void:
	_ready_done = true
	_show()
	_send_phase()
	_send(&"cartoon_eyes", cartoon_eyes)
	_send(&"eye_look", eye_look)
	_send(&"blink", blink)
	_send(&"sway", sway)
	_send(&"gape", gape)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the tuna's is; the beat here does not change
## with its speed: set `sway` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `curl` (bends the body into a turn behind the head, in
## radians from gills to tail; more than 0 the tail comes round to +X), `gape` (as the property),
## `wave` (the length of the wave along its body), `bars_show` (how strongly the flank's bars
## show) and its colours (`back`, `back_blue`, `silver`, `belly`, `bars`, `fin_dark`, `bill`,
## `mouth`).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


## The model's mesh by itself (the full one, or the low one), for a MultiMesh or a MeshInstance3D
## of your own: give it `new_material()` and set that material's `phase`, `gape` and the rest.
static func mesh_of(low_one := false) -> Mesh:
	var scene := load(MODEL % ("_lo" if low_one else "")) as PackedScene
	var made := scene.instantiate()
	var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
	var mesh := found.mesh
	made.free()
	return mesh


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


## A new material of its shader, for `mesh_of`.
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


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
		_shown[want] = _mesh_instance(want)
	for suffix: String in _shown:
		(_shown[suffix] as MeshInstance3D).visible = suffix == want


func _mesh_instance(suffix: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = game_mesh() if suffix == "_game" else mesh_of(suffix == "_lo")
	mesh.material_override = _material
	# (its tail swings out past where the still model ends)
	mesh.extra_cull_margin = 0.5
	mesh.name = "BlueMarlin" + suffix
	add_child(mesh)
	return mesh
