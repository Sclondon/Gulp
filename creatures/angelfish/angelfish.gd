class_name Angelfish
extends Node3D
## A marine angelfish of a coral reef, of one of three types (`type`), each a model of its
## own, all built 0.35 m long (`SIZE` is how long each really is beside that). Every one is
## a deep, flat-sided oval with a blunt head, a small mouth set low, a spine at the lower
## corner of each cheek (the angelfishes' mark), one continuous dorsal fin and a fan tail:
##
## - EMPEROR (Pomacanthus imperator, the grown fish; the default): blue and yellow stripes
##   running back along the body, a pale face with a black mask over the eyes edged with
##   bright blue, a black patch behind the gill cover, an orange-yellow tail.
## - QUEEN (Holacanthus ciliaris): blue-green, every scale edged with gold; a yellow-green
##   face; the crown, a dark spot ringed and flecked with bright blue, on its nape; yellow
##   tail and pectoral fins; the dorsal and anal fins drawn out in long tips that trail
##   past the tail.
## - FRENCH (Pomacanthus paru): black, the scales of its sides each with a yellow rear
##   edge; a slate face with a white mouth, a yellow ring round the eye; a deeper body, the
##   dorsal and anal fins drawn out in long tips.
##
## All of the markings are drawn by the shader: no texture files. Its nose points along its
## own -Z, its belly down; its origin is on its middle line, half way along its length.
##
## It hovers and paddles about by rowing with its pectoral fins, and steers with its tail:
## its body hardly bends. Its lower jaw works (`gape`: 0 shut, 1 wide open, as it nips).
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`: in a beat its tail
## beats `tail_beats` times and its pectoral fins row `strokes` times (whole numbers), so
## its motion comes round again exactly every beat. Either call `step(velocity, delta)`
## each frame, which moves `phase` on by delta / beat (and swings its tail harder the faster
## it is going), or set `phase` yourself (for a picture that must loop: frame / frames in a
## beat; with `beat` 0, `step` leaves `phase` alone).
##
## A game that keeps its own MeshInstance3Ds needs no Angelfish node:
## `Angelfish.mesh_of(type, low)` is a type's mesh and `Angelfish.new_material(type)` a
## material for it, whose shader settings (phase, sway, row, gape, curl and the rest) the
## game sets itself.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way
## it goes. `scale` it for a bigger or smaller one. No sound.
##
## The models are creatures/angelfish/models/angelfish_<type>.glb (and _lo), built by
## tools/build_angelfish.py; its shader is angelfish.gdshader.

enum Type { EMPEROR, QUEEN, FRENCH }

const MODEL := "res://creatures/angelfish/models/angelfish_%s%s.glb"
const SHADER := preload("res://creatures/angelfish/angelfish.gdshader")
## As the models are built (tools/build_angelfish.py): snout to tail tip, every type; and
## the emperor's body at its deepest and widest, fins not counted (metres, at scale 1).
## `REACH` has how far each type's fins go.
const LENGTH := 0.35
const DEPTH := 0.172
const WIDTH := 0.055
## Each type's name in its model's file name.
const NAMES := { Type.EMPEROR: "emperor", Type.QUEEN: "queen", Type.FRENCH: "french" }
## How long each type really is beside `LENGTH` (a usual grown fish: emperor and French
## about 35 cm, queen 30 cm). Multiply `scale` by it for true sizes.
const SIZE := { Type.EMPEROR: 1.0, Type.QUEEN: 0.86, Type.FRENCH: 1.0 }
## How far each type's still model reaches above and below its middle line, fins and all
## (metres, at scale 1): x is down (negative), y is up. Every type reaches 0.175 ahead and
## about 0.057 to each side (its pectoral fins; its body 0.027); the emperor and the French
## reach 0.175 behind, the queen's fin tips 0.188.
const REACH := {
	Type.EMPEROR: Vector2(-0.116, 0.105), Type.QUEEN: Vector2(-0.119, 0.115),
	Type.FRENCH: Vector2(-0.129, 0.138),
}
## What each type sets in the shader: which markings, and the places on its model the shader
## needs (as its model is built: the build script prints them).
const TYPES := {
	Type.EMPEROR: {
		"kind": 0, "hinge_s": 0.036, "hinge_y": -0.033, "eye_at": Vector2(0.115, 0.058),
		"pec_root": Vector3(0.0705, -0.0675, 0.265),
	},
	Type.QUEEN: {
		"kind": 1, "hinge_s": 0.034, "hinge_y": -0.033, "eye_at": Vector2(0.115, 0.056),
		"pec_root": Vector3(0.0703, -0.0675, 0.265),
	},
	Type.FRENCH: {
		"kind": 2, "hinge_s": 0.036, "hinge_y": -0.033, "eye_at": Vector2(0.115, 0.064),
		"pec_root": Vector3(0.0713, -0.0675, 0.265),
	},
}

static var _meshes := {}

## Which type it is: its shape and its markings.
@export var type := Type.EMPEROR:
	set(value):
		type = value
		_dress()
		_fit()
## Seconds one beat takes: everything it does comes round again each beat. 0 for a caller
## that sets `phase` itself (`step` then leaves `phase` alone).
@export var beat := 2.6
## How many times in a beat its tail beats and its pectoral fins row.
@export var tail_beats := 2:
	set(value):
		tail_beats = maxi(value, 0)
		_send(&"tail_beats", float(tail_beats))
@export var strokes := 3:
	set(value):
		strokes = maxi(value, 0)
		_send(&"strokes", float(strokes))
## How widely its tail swings when it is going nowhere: 0 still, 1 a tenth of its length
## each way. `step` swings it wider the faster it goes.
@export_range(0.0, 1.5) var sway := 0.25:
	set(value):
		sway = value
		_effort = value
		_send(&"sway", _effort)
## How hard its pectoral fins row: 1 as it hovers and paddles about, 0 held still.
@export_range(0.0, 1.5) var row := 1.0:
	set(value):
		row = value
		_send(&"row", value)
## Its mouth: 0 shut, 1 wide open (its lower jaw swings down, its snout lifts a little).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## The speed (m/s, at scale 1) at which `step` has its tail swinging its widest.
@export var top_speed := 1.2
## The low model (far off, phones, many at once) in place of the full one.
@export var low := false:
	set(value):
		low = value
		_show()
## How far through a beat it is, 0 to 1. `step` moves it on; or set it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _effort := 0.25


## A type's mesh (the low one for fish far off, in numbers, on phones), for a game that
## keeps its own MeshInstance3Ds. Each is loaded once and kept.
static func mesh_of(type_wanted := Type.EMPEROR, low_wanted := false) -> Mesh:
	var path := MODEL % [NAMES[type_wanted], "_lo" if low_wanted else ""]
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]


## A new material for a type's mesh, with that type's markings. Its shader settings are the
## game's to set: phase (0..1), tail_beats, strokes, sway, row, gape (0..1), curl, arch,
## flash, rim, tint (the top of the shader lists them).
static func new_material(type_wanted := Type.EMPEROR) -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	_wear(made, type_wanted)
	return made


func _init() -> void:
	_material = ShaderMaterial.new()
	_material.shader = SHADER
	_effort = sway
	_dress()


func _ready() -> void:
	_full = _instance_of("Fish")
	_low = _instance_of("Fish_lo")
	_fit()
	_show()
	_send(&"tail_beats", float(tail_beats))
	_send(&"strokes", float(strokes))
	_send(&"sway", _effort)
	_send(&"row", row)
	_send(&"gape", gape)
	_send(&"phase", phase)


## Each frame, after putting it where it is: moves its beat on by `delta` seconds (unless
## `beat` is 0), and swings its tail wider the faster it is going (`velocity`, world, m/s;
## give Vector3.ZERO for one that hovers, and its tail swings as `sway` says).
func step(velocity: Vector3, delta: float) -> void:
	if beat > 0.0:
		phase += delta / beat
	var size := maxf(global_basis.get_scale().z, 0.001) if is_inside_tree() else 1.0
	var wanted := maxf(sway, clampf(velocity.length() / (top_speed * size), 0.0, 1.0))
	_effort = move_toward(_effort, wanted, delta * 1.5)
	_send(&"sway", _effort)


## Sets one of the shader's settings: how it moves (curl, arch, gape, sway, row), a game's
## effects (flash, rim, tint), or mouth (the colour inside it), sheen, ray_lines. `type`
## sets kind and the places on the model again.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_send(setting, value)


## The material it is drawn with.
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


static func _wear(on: ShaderMaterial, type_wanted: Type) -> void:
	var wears: Dictionary = TYPES[type_wanted]
	for setting: String in wears:
		on.set_shader_parameter(setting, wears[setting])


func _dress() -> void:
	if _material:
		_wear(_material, type)


func _fit() -> void:
	if _full:
		_full.mesh = mesh_of(type, false)
		_low.mesh = mesh_of(type, true)


func _show() -> void:
	if _full:
		_full.visible = not low
		_low.visible = low


func _instance_of(called: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.material_override = _material
	# (its fins row and its tail swings out past the still model's box)
	mesh.extra_cull_margin = LENGTH * 0.3
	mesh.name = called
	add_child(mesh)
	return mesh
