class_name KelpBass
extends Node3D
## A kelp bass, or calico bass (Paralabrax clathratus), of the Californian kelp forests, 0.5 m
## long: the classic bass shape, a pointed head with the lower jaw a little forward, a notched
## dorsal whose third and fourth spines are the longest, a square tail; olive brown on the back
## with rows of pale squarish blotches, a yellowish belly, yellowish fins.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z, its belly down; its origin is on its middle line, half
## way along its length. `scale` it for a bigger or smaller one. No sound.
##
## It swims by a wave down its body and tail, drawn by the shader (no bones): the head nearly
## still, the tail swinging widest. It hovers and turns by sculling its pectoral fins, which never
## stop; it breathes with its mouth and gill covers. `gape` opens its mouth: 0 shut, 1 wide open
## into a round tube, the lower jaw dropped and the upper jaw pushed forward, as when it sucks in
## its prey.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`: in a beat the tail beats
## `tail_beats` times, it breathes `breaths` times and its fins scull `sculls` times (whole
## numbers), so its motion comes round again exactly every beat. Either call
## `step(velocity, delta)` each frame, which moves `phase` on by delta / beat (and swims harder
## the faster it is going), or set `phase` yourself (for a picture that must loop).
##
## A game that keeps its own MeshInstance3Ds needs no KelpBass node: `KelpBass.mesh_of(low)` is the
## mesh and `KelpBass.new_material()` a material for it, whose shader settings (phase, sway,
## tail_beats, breaths, sculls, gape, curl, scull, flash, rim, the colours) the game sets itself.
##
## The models are creatures/kelp_bass/models/kelp_bass.glb (and _lo), built by
## tools/build_kelp_bass.py; kelp_bass.gdshader draws its markings and moves it.

const MODEL := "res://creatures/kelp_bass/models/kelp_bass%s.glb"
const SHADER := preload("res://creatures/kelp_bass/kelp_bass.gdshader")
## As the model is built (tools/build_kelp_bass.py): from the tip of its lower jaw to the tip of its
## tail, and how deep and how wide its body is at its deepest, fins left out (metres, at scale 1).
const LENGTH := 0.5
const DEPTH := 0.135
const WIDTH := 0.068

static var _meshes := {}

## Seconds one beat takes: everything it does comes round again each beat. 0 for a caller that
## sets `phase` itself (`step` then leaves `phase` alone).
@export var beat := 1.8
## How many times in a beat its tail beats, it breathes, and its pectoral fins scull.
@export var tail_beats := 2:
	set(value):
		tail_beats = maxi(value, 0)
		_send(&"tail_beats", float(tail_beats))
@export var breaths := 2:
	set(value):
		breaths = maxi(value, 0)
		_send(&"breaths", float(breaths))
@export var sculls := 2:
	set(value):
		sculls = maxi(value, 0)
		_send(&"sculls", float(sculls))
## How hard it swims when it is not going anywhere (hovering): 0 still, 1 its tail tip swinging
## about a tenth of its length each way. `step` raises it with speed.
@export_range(0.0, 1.5) var sway := 0.3:
	set(value):
		sway = value
		_effort = value
		_send(&"sway", _effort)
## The speed (m/s, at scale 1) at which `step` has it swimming as hard as it can.
@export var top_speed := 1.2
## How wide its mouth is open: 0 shut, 1 wide open (it still breathes a little either way).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = value
		_send(&"gape", value)
## The low model (about a tenth of the triangles), for far off, phones, many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set it
## yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _effort := 0.3


## The mesh (`low` for the low one), for a game that keeps its own MeshInstance3Ds. Each is
## loaded once and kept.
static func mesh_of(low_wanted := false) -> Mesh:
	var path := MODEL % ("_lo" if low_wanted else "")
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]


## A new material for its mesh. Its shader settings are the game's to set (the top of the shader
## lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()
	_effort = sway


func _ready() -> void:
	_full = _instance_of("KelpBass", false)
	_low = _instance_of("KelpBass_lo", true)
	_show()
	for setting: StringName in [&"tail_beats", &"breaths", &"sculls"]:
		_send(setting, float(get(setting)))
	_send(&"sway", _effort)
	_send(&"gape", gape)
	_send(&"phase", phase)


## Each frame, after putting it where it is: moves its beat on by `delta` seconds (unless `beat`
## is 0), and has it swim harder the faster it is going (`velocity`, world, m/s; Vector3.ZERO for
## one that hovers, and it swims as `sway` says).
func step(velocity: Vector3, delta: float) -> void:
	if beat > 0.0:
		phase += delta / beat
	var size := maxf(global_basis.get_scale().z, 0.001) if is_inside_tree() else 1.0
	var wanted := maxf(sway, clampf(velocity.length() / (top_speed * size), 0.0, 1.0))
	_effort = move_toward(_effort, wanted, delta * 1.5)
	_send(&"sway", _effort)


## Sets one of the shader's settings: a colour (back, side, belly, pale, fin_dark, fin_tail, fin_paired, mouth, eye_ring), an amount
## (blotch_amount, mottle, scales, sheen), how it moves (curl, gape_breath, gill_flare, scull), or
## a game's effects (flash, rim).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_send(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


func _show() -> void:
	if _full:
		_full.visible = not low
		_low.visible = low


func _instance_of(called: String, low_wanted: bool) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = mesh_of(low_wanted)
	mesh.material_override = _material
	# (its tail swings, and its mouth opens, out past the still model's box)
	mesh.extra_cull_margin = LENGTH * 0.25
	mesh.name = called
	add_child(mesh)
	return mesh
