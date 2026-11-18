class_name Parrotfish
extends Node3D
## A stoplight parrotfish (Sparisoma viride), a full-grown male in his terminal colours, 0.5 m
## long: a heavy, deep oval body with big scales, a blunt rounded head and, at the front of it,
## the BEAK: his teeth fused into two pale plates, upper and lower, that always show. Emerald
## and blue-green, every scale edged with rose; two salmon stripes across the head; a yellow
## spot high on the gill cover and a yellow bar at the root of the tail; rose fins edged with
## blue; a square-cut tail with drawn-out corners and a rose crescent; a yellow eye.
##
## It swims as parrotfish do: it rows with its broad pectoral fins, both together like oars,
## its body bobbing a little with each stroke and its tail trailing; with `sway` up its tail
## beats too, as when it hurries.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down; its origin is on
## its middle line, half way along its length. `scale` it for a bigger or smaller one. No sound.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its pectoral fins
## row `tail_beats` times (a whole number) and its tail swings as often, so its motion comes
## round again exactly every beat. Either call `step(velocity, delta)` each frame, which moves
## `phase` on by delta / beat, or set `phase` yourself (for a picture that must loop). The same
## names and meanings as GameCommon's yellowfin tuna and snapper.
##
## Its mouth opens: `gape` 0 shut to 1 wide, as when it bites at the coral (the lower jaw with
## its beak plate swings down about its hinge, the upper beak lifts a little, the dark inside of
## the mouth shows).
##
## The model is creatures/parrotfish/models/parrotfish.glb (and _lo), built by
## tools/build_parrotfish.py; parrotfish.gdshader draws its markings and moves it (no bones).

const MODEL := "res://creatures/parrotfish/models/parrotfish%s.glb"
const SHADER := preload("res://creatures/parrotfish/parrotfish.gdshader")
## As the model is built (tools/build_parrotfish.py): from the tip of its beak to the tips of
## its tail, and how deep and how wide its body is at its deepest (metres, at scale 1).
const LENGTH := 0.5
const DEPTH := 0.159
const WIDTH := 0.075

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 1.4
## How many strokes of its pectoral fins (and swings of its tail) in a beat.
@export var tail_beats := 2:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely its body and tail beat: 1 cruising (the tail trailing), 2 hurrying, 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How hard its pectoral fins row: 1 as it cruises, 0 folded back and still (it bobs less too).
@export_range(0.0, 1.5) var scull := 1.0:
	set(value):
		scull = value
		_send(&"scull", value)
## Its mouth: 0 shut, 1 wide open, as when it bites.
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = value
		_send(&"gape", value)
## How far its dorsal fin is raised: 1 up, 0 folded down.
@export_range(0.0, 1.0) var dorsal := 1.0:
	set(value):
		dorsal = value
		_send(&"dorsal", value)
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

static var _meshes := {}

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`): for
## drawing one without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	var path := MODEL % ("_lo" if low_wanted else "")
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase`
## (0..1 through one stroke), `sway`, `scull`, `gape`, `dorsal`, `curl`, `wave` and the colours
## (the top of the shader lists them).
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
	for setting: StringName in [&"sway", &"scull", &"gape", &"dorsal"]:
		_send(setting, get(setting))


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the other fish's are; its beat here does not
## change with its speed: set `sway`, `scull` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `curl` (bends the body round to one side behind the head,
## radians from gills to tail; more than 0 and the tail comes round to +X), `wave` (the length
## of the wave along its body), `mouth` (the colour inside its mouth) and its colours (`back`,
## `flank`, `belly`, `scale_edge`, `stripe`, `yellow`, `beak`, `fin`, `fin_edge`, `iris`,
## `iris_ring`).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one stroke it is)
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
	# (its tail and fins swing out past where the still model ends)
	mesh.extra_cull_margin = LENGTH * 0.25
	mesh.name = "ParrotfishLo" if low_wanted else "Parrotfish"
	add_child(mesh)
	return mesh
