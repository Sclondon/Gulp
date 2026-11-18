class_name Rockfish
extends Node3D
## A vermilion rockfish (Sebastes miniatus), 0.5 m long: a stocky, heavy-headed fish with big
## eyes set high and a big mouth, bright orange-red mottled with grey along its sides and
## lateral line, three paler stripes fanning back from each eye, a dorsal fin of thirteen
## strong spines (the skin cut deep between them) and a taller soft lobe, big round pectoral
## fins, a broad tail; its fins red edged with black.
##
## Mostly it hangs still, fanning its pectoral fins in turn (`sway` 0); when it goes, a slow
## wave runs down its rear half and tail.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down; its origin is on
## its middle line, half way along its length. `scale` it for a bigger or smaller one. No sound.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats
## `tail_beats` times (a whole number) and its pectoral fins scull as often, so its motion comes
## round again exactly every beat. Either call `step(velocity, delta)` each frame, which moves
## `phase` on by delta / beat, or set `phase` yourself (for a picture that must loop). The same
## names and meanings as GameCommon's yellowfin tuna and sardine.
##
## Its mouth opens: `gape` 0 shut to 1 wide, as when it bites (the lower jaw swings down about
## its hinge, the snout lifts a little, the dark inside of the mouth shows).
##
## The model is creatures/rockfish/models/rockfish.glb (and _lo), built by
## tools/build_rockfish.py; rockfish.gdshader draws its markings and moves it (no bones).

const MODEL := "res://creatures/rockfish/models/rockfish%s.glb"
const SHADER := preload("res://creatures/rockfish/rockfish.gdshader")
## As the model is built (tools/build_rockfish.py): from the tip of its snout to the tips of its
## tail, and how deep and how wide its body is at its deepest (metres, at scale 1).
const LENGTH := 0.5
const DEPTH := 0.15
const WIDTH := 0.085

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 2.4
## How many times in a beat its tail beats and its pectoral fins scull (there and back).
@export var tail_beats := 2:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely its body and tail beat: 1 cruising, 0 still (hovering on its pectoral fins alone).
@export_range(0.0, 2.0) var sway := 0.6:
	set(value):
		sway = value
		_send(&"sway", value)
## How hard its pectoral fins scull: 1 as it hovers or cruises, 0 folded in and still.
@export_range(0.0, 2.0) var scull := 1.0:
	set(value):
		scull = value
		_send(&"scull", value)
## Its mouth: 0 shut, 1 wide open, as when it bites.
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = value
		_send(&"gape", value)
## How far the spines of its dorsal fin are raised: 1 up, 0 folded back.
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
## (0..1 through one beat of the tail), `sway`, `scull`, `gape`, `dorsal`, `curl`, `wave` and
## the colours (the top of the shader lists them).
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
## of the wave along its body), `mouth` (the colour inside its mouth) and its colours
## (`vermilion`, `back`, `belly`, `grey` and how much of it, `mottle`, `fin`, `fin_edge`, `iris`, `iris_ring`).
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
	# (its tail and fins swing out past where the still model ends)
	mesh.extra_cull_margin = LENGTH * 0.25
	mesh.name = "RockfishLo" if low_wanted else "Rockfish"
	add_child(mesh)
	return mesh
