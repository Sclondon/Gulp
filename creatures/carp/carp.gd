class_name Carp
extends Node3D
## A carp (Cyprinus carpio), as the wild common carp or as one of its koi (`type`): one
## model, the same deep heavy body for all of them, with the colours and the pattern of
## each type drawn by its shader (no texture files):
##
## - COMMON (the default): the common carp: bronze-gold, darker olive along the back, pale
##   yellowish below, each big scale edged dark; dusky upper fins, reddish lower ones.
## - KOHAKU: white with red patches.
## - SANKE: white, red patches and small black marks on the back, black stripes in the fins.
## - SHOWA: black with red and white patches, the pectoral fins black at their roots.
## - YAMABUKI_OGON and PLATINUM_OGON: one metallic colour, gold or platinum.
##
## Where a koi's patches fall is set by `pattern_seed`: each whole number another fish.
##
## It has a small mouth with thick lips; two barbels each side (a short one on the upper
## lip, a longer one at the corner of the mouth); a long dorsal fin with its spine in front,
## a forked tail, a short anal fin, and a pair each of pelvic and pectoral fins. `gape` opens
## its mouth: the lower jaw swings down and the lips push forward and down into a round tube,
## as a carp's do when it feeds. Its nose points along its own -Z, its belly down; its origin
## is the middle of its length.
##
## It swims by a wave down its body, drawn by the shader (no bones). Everything that moves
## runs on `phase`, 0 to 1 through one `beat`: in a beat the tail beats `tail_beats` times and
## its paired fins scull `sculls` times (whole numbers), so its motion comes round again
## exactly every beat. Either call `step(velocity, delta)` each frame, or set `phase` yourself
## (with `beat` 0, `step` leaves `phase` alone).
##
## A game that keeps its own MeshInstance3Ds needs no Carp node: `Carp.mesh_of(low)` is the
## mesh and `Carp.new_material(type, pattern_seed)` a material for it.
##
## The models are creatures/carp/models/carp.glb (and carp_lo.glb), built by
## tools/build_carp.py; its shader is carp.gdshader.

enum Type { COMMON, KOHAKU, SANKE, SHOWA, YAMABUKI_OGON, PLATINUM_OGON }

const MODEL := "res://creatures/carp/models/carp%s.glb"
const SHADER := preload("res://creatures/carp/carp.gdshader")
## Snout to tail tip (metres, at scale 1), as built.
const LENGTH := 0.69
## The body's greatest depth and width (metres, at scale 1), fins left out. With its fins it
## is 0.28 m from the top of the dorsal fin to the tips of the pelvic fins, and 0.14 m across
## the pectoral fins.
const DEPTH := 0.183
const WIDTH := 0.095
## What each type sets in the shader: its pattern (`kind`), its colours, how its scales and
## fins are marked.
const TYPES := {
	Type.COMMON: {
		"kind": 0.0, "back": Color(0.22, 0.2, 0.1), "side": Color(0.62, 0.48, 0.2), "belly": Color(0.86, 0.78, 0.52),
		"head": Color(0.56, 0.44, 0.2), "head_top": Color(0.24, 0.21, 0.1), "lip_colour": Color(0.7, 0.56, 0.4),
		"scale_edge": Color(0.12, 0.09, 0.04), "scale_dark": 0.55,
		"fin_upper": Color(0.34, 0.3, 0.2), "fin_lower": Color(0.62, 0.36, 0.2), "fin_pectoral": Color(0.52, 0.4, 0.22),
		"fin_dark": Color(0.12, 0.1, 0.06), "eye_gold": Color(0.86, 0.66, 0.22), "sheen_colour": Color(1.0, 0.9, 0.62),
		"sheen": 0.35, "metal": 0.0, "hi_amount": 0.0, "sumi_amount": 0.0, "white_amount": 0.0,
		"fin_stripes": 0.0, "motoguro": 0.0,
	},
	Type.KOHAKU: {
		"kind": 1.0, "white": Color(0.95, 0.94, 0.9), "hi": Color(0.86, 0.13, 0.05), "lip_colour": Color(0.93, 0.8, 0.76),
		"scale_edge": Color(0.55, 0.5, 0.46), "scale_dark": 0.18,
		"fin_upper": Color(0.93, 0.92, 0.88), "fin_lower": Color(0.93, 0.92, 0.88), "fin_pectoral": Color(0.94, 0.93, 0.9),
		"fin_dark": Color(0.6, 0.58, 0.55), "eye_gold": Color(0.7, 0.66, 0.56), "sheen_colour": Color(1.0, 0.97, 0.92),
		"sheen": 0.3, "metal": 0.0, "hi_amount": 0.55, "sumi_amount": 0.0, "white_amount": 0.0,
		"fin_stripes": 0.0, "motoguro": 0.0,
	},
	Type.SANKE: {
		"kind": 2.0, "white": Color(0.95, 0.94, 0.9), "hi": Color(0.86, 0.13, 0.05), "sumi": Color(0.04, 0.04, 0.045),
		"lip_colour": Color(0.93, 0.8, 0.76), "scale_edge": Color(0.55, 0.5, 0.46), "scale_dark": 0.18,
		"fin_upper": Color(0.93, 0.92, 0.88), "fin_lower": Color(0.93, 0.92, 0.88), "fin_pectoral": Color(0.94, 0.93, 0.9),
		"fin_dark": Color(0.6, 0.58, 0.55), "eye_gold": Color(0.7, 0.66, 0.56), "sheen_colour": Color(1.0, 0.97, 0.92),
		"sheen": 0.3, "metal": 0.0, "hi_amount": 0.45, "sumi_amount": 0.5, "white_amount": 0.0,
		"fin_stripes": 0.8, "motoguro": 0.0,
	},
	Type.SHOWA: {
		"kind": 3.0, "white": Color(0.95, 0.94, 0.9), "hi": Color(0.86, 0.13, 0.05), "sumi": Color(0.04, 0.04, 0.045),
		"lip_colour": Color(0.86, 0.74, 0.7), "scale_edge": Color(0.5, 0.46, 0.42), "scale_dark": 0.15,
		"fin_upper": Color(0.9, 0.89, 0.86), "fin_lower": Color(0.93, 0.92, 0.88), "fin_pectoral": Color(0.94, 0.93, 0.9),
		"fin_dark": Color(0.4, 0.38, 0.36), "eye_gold": Color(0.6, 0.56, 0.46), "sheen_colour": Color(1.0, 0.97, 0.92),
		"sheen": 0.3, "metal": 0.0, "hi_amount": 0.5, "sumi_amount": 0.0, "white_amount": 0.45,
		"fin_stripes": 0.45, "motoguro": 1.0,
	},
	Type.YAMABUKI_OGON: {
		"kind": 4.0, "side": Color(0.95, 0.72, 0.2), "back": Color(0.76, 0.52, 0.12), "lip_colour": Color(0.96, 0.8, 0.46),
		"scale_edge": Color(1.0, 0.9, 0.6), "scale_dark": -0.35,
		"fin_upper": Color(0.92, 0.72, 0.3), "fin_lower": Color(0.94, 0.76, 0.34), "fin_pectoral": Color(0.95, 0.78, 0.36),
		"fin_dark": Color(0.6, 0.42, 0.12), "eye_gold": Color(0.8, 0.6, 0.2), "sheen_colour": Color(1.0, 0.9, 0.55),
		"sheen": 0.8, "metal": 1.0, "hi_amount": 0.0, "sumi_amount": 0.0, "white_amount": 0.0,
		"fin_stripes": 0.0, "motoguro": 0.0,
	},
	Type.PLATINUM_OGON: {
		"kind": 4.0, "side": Color(0.9, 0.91, 0.9), "back": Color(0.7, 0.72, 0.73), "lip_colour": Color(0.92, 0.88, 0.86),
		"scale_edge": Color(1.0, 1.0, 1.0), "scale_dark": -0.3,
		"fin_upper": Color(0.86, 0.87, 0.86), "fin_lower": Color(0.9, 0.9, 0.88), "fin_pectoral": Color(0.9, 0.9, 0.89),
		"fin_dark": Color(0.5, 0.52, 0.54), "eye_gold": Color(0.7, 0.7, 0.66), "sheen_colour": Color(0.95, 0.98, 1.0),
		"sheen": 0.8, "metal": 1.0, "hi_amount": 0.0, "sumi_amount": 0.0, "white_amount": 0.0,
		"fin_stripes": 0.0, "motoguro": 0.0,
	},
}

static var _meshes := {}

## Which carp: the wild common carp or a koi (above).
@export var type := Type.COMMON:
	set(value):
		type = value
		if _material:
			_wear(_material, type)
## Where a koi's patches fall: each whole number another fish (no change to a common carp
## or an ogon).
@export var pattern_seed := 0:
	set(value):
		pattern_seed = value
		_send(&"pattern_seed", float(value))
## Seconds one beat takes: everything it does comes round again each beat. 0 for a caller
## that sets `phase` itself (`step` then leaves `phase` alone).
@export var beat := 2.4
## How many times in a beat its tail beats and its paired fins scull.
@export var tail_beats := 2:
	set(value):
		tail_beats = maxi(value, 0)
		_send(&"tail_beats", float(tail_beats))
@export var sculls := 2:
	set(value):
		sculls = maxi(value, 0)
		_send(&"sculls", float(sculls))
## How hard it swims when it is not going anywhere: 0 hangs still, 1 swings its tail about a
## tenth of its length each way. `step` swims it harder when it goes faster.
@export_range(0.0, 2.0) var sway := 0.6:
	set(value):
		sway = value
		_effort = value
		_send(&"sway", value)
## The speed (m/s, at scale 1) at which `step` has it swimming as hard as `sway` 1.
@export var top_speed := 1.2
## Its mouth: 0 shut, 1 wide open, the lips pushed out into a tube (as it feeds or bites).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## The low model (far off, phones) in place of the full one.
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
var _effort := 0.6


## The mesh (the low one for fish far off, in packs, on phones), for a game that keeps its
## own MeshInstance3Ds. Each is loaded once and kept. Every type uses the same mesh.
static func mesh_of(low_wanted := false) -> Mesh:
	var path := MODEL % ("_lo" if low_wanted else "")
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]


## A new material for the mesh, in a type's colours and pattern (`seed`: where a koi's
## patches fall). Its shader settings are the game's to set: phase (0..1), sway, tail_beats,
## sculls, gape, curl and the rest (the top of the shader lists them).
static func new_material(type_wanted := Type.COMMON, seed := 0) -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	_wear(made, type_wanted)
	made.set_shader_parameter(&"pattern_seed", float(seed))
	return made


func _init() -> void:
	_material = ShaderMaterial.new()
	_material.shader = SHADER
	_wear(_material, type)


func _ready() -> void:
	_full = _instance_of("Carp", mesh_of(false))
	_low = _instance_of("Carp_lo", mesh_of(true))
	_show()
	for setting: StringName in [&"tail_beats", &"sculls"]:
		_send(setting, float(get(setting)))
	_send(&"sway", _effort)
	_send(&"gape", gape)
	_send(&"pattern_seed", float(pattern_seed))
	_send(&"phase", phase)


## Each frame, after putting it where it is: moves its beat on by `delta` seconds (unless
## `beat` is 0), and has it swim harder the faster it is going (`velocity`, world, m/s; give
## Vector3.ZERO for one that holds its place, and it swims as `sway` says).
func step(velocity: Vector3, delta: float) -> void:
	if beat > 0.0:
		phase += delta / beat
	var size := maxf(global_basis.get_scale().z, 0.001) if is_inside_tree() else 1.0
	var wanted := maxf(sway, clampf(velocity.length() / (top_speed * size), 0.0, 1.0))
	_effort = move_toward(_effort, wanted, delta * 1.5)
	_send(&"sway", _effort)


## Sets one of the shader's settings: how it moves (curl, gape, scull, sway, phase), a colour
## (back, side, belly, head, head_top, lip_colour, mouth, scale_edge, white, hi, sumi,
## fin_upper, fin_lower, fin_pectoral, fin_dark, eye_gold, sheen_colour) or an amount
## (scale_dark, scale_size, hi_amount, sumi_amount, white_amount, fin_stripes, motoguro,
## sheen, metal). `type` sets the colours and amounts again.
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


func _show() -> void:
	if _full:
		_full.visible = not low
		_low.visible = low


func _instance_of(called: String, mesh: Mesh) -> MeshInstance3D:
	var made := MeshInstance3D.new()
	made.mesh = mesh
	made.material_override = _material
	# (its tail swings out past the still model's box, and its lips push out)
	made.extra_cull_margin = LENGTH * 0.25
	made.name = called
	add_child(made)
	return made
