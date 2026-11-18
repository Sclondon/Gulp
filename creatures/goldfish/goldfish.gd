class_name Goldfish
extends Node3D
## A goldfish (Carassius auratus), 0.15 m long from the tip of its snout to the tips of its tail, of
## either kind (`kind`), each a model of its own:
##
## - COMMON (the default): the wild shape kept: a torpedo a little flattened from side to side, a
##   rounded snout with a small end-on mouth, one long-based dorsal fin, a single forked tail.
## - FANTAIL: an egg-shaped body and a long double tail (two forked tails side by side, joined along
##   the top and spread apart below), paired anal fins; its fins billow as it swims.
##
## and in any of three colourings (`colouring`), on either kind: ORANGE (the default), RED_WHITE
## (white with red patches) and CALICO (pale blue-grey with patches of orange and black, peppered
## with black specks, matt scales). Every marking is drawn by its shader: no texture files.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it goes.
## Its nose points along its own -Z (Godot's forward), its belly down; its origin is on its middle
## line, half way along, so it reaches 0.075 m ahead and 0.075 m behind. `scale` it for a bigger or
## smaller one. No sound.
##
## It swims as carp do: a wave down the back half of the body, drawn by the shader (no bones). Its
## mouth opens: `gape`.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat. Either
## call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or set `phase`
## yourself (for a picture that must loop: frame / frames in a beat). The same names and meanings
## as GameCommon's yellowfin tuna and sardine, so they are driven the same way.
##
## The models are creatures/goldfish/models/goldfish_<kind>.glb (and _lo, and _game), built by
## tools/build_goldfish.py; goldfish.gdshader draws the markings and swims it. Each model is
## loaded only when it is first shown: with `game` on, the full models are never loaded, so a
## game's web export can leave them out.

enum Kind { COMMON, FANTAIL }
enum Colouring { ORANGE, RED_WHITE, CALICO }

const MODEL := "res://creatures/goldfish/models/goldfish_%s%s.glb"
const SHADER := preload("res://creatures/goldfish/goldfish.gdshader")
## As the models are built (tools/build_goldfish.py): from the tip of the snout to the tips of the
## tail, both kinds (metres, at scale 1).
const LENGTH := 0.15
## How deep and how wide the common goldfish's body is at its deepest, without fins (metres, at
## scale 1). Each kind's own are in KINDS ("depth", "width").
const DEPTH := 0.046
const WIDTH := 0.024
## Each kind's name in its model's file name.
const NAMES := {Kind.COMMON: "common", Kind.FANTAIL: "fantail"}
## What each kind sets in the shader (where its tail and jaw are hinged, where its body ends, its eye,
## its gill cover's edge: as its model is built, the build script prints them), how much its fins
## billow, and its body's depth and width (metres, not shader settings). The eye's middle on the
## skin and the way it faces, its radius, the gap between its gill arches and where its throat ends
## are the build script's EYE and GILLS lines; `eye_grow` is how much bigger its cartoon eye is.
const KINDS := {
	Kind.COMMON: {
		"joint": 0.108, "jaw_to": 0.0095, "hinge_y": -0.00154, "body_to": 0.116,
		"eye_at": Vector2(0.0175, 0.0042), "gill_at": 0.029, "billow": 0.3,
		"eye_middle": Vector3(0.00989, 0.0042, -0.0575), "eye_out": Vector3(0.9694, 0.1511, -0.1933),
		"eye_radius": 0.0043, "eye_grow": 1.55, "gill_gap": 0.00338, "throat_end": 0.0319,
		"depth": 0.046, "width": 0.024,
	},
	Kind.FANTAIL: {
		"joint": 0.083, "jaw_to": 0.0085, "hinge_y": -0.00179, "body_to": 0.0905,
		"eye_at": Vector2(0.0148, 0.0052), "gill_at": 0.026, "billow": 1.0,
		"eye_middle": Vector3(0.01299, 0.0052, -0.0602), "eye_out": Vector3(0.8719, 0.1916, -0.4507),
		"eye_radius": 0.0046, "eye_grow": 1.65, "gill_gap": 0.00303, "throat_end": 0.0286,
		"depth": 0.054, "width": 0.038,
	},
}
## What each colouring sets in the shader.
const COLOURINGS := {
	Colouring.ORANGE: {
		"base": Color(0.98, 0.45, 0.06), "back": Color(0.84, 0.3, 0.03), "belly": Color(1.0, 0.72, 0.36),
		"patch_amount": 0.0, "black_amount": 0.0, "speckle": 0.0, "shine": 0.8, "scales_show": 0.7,
		"fin_root": Color(0.98, 0.46, 0.08), "fin_edge": Color(1.0, 0.6, 0.26), "fin_clear": 0.2,
		"iris": Color(0.85, 0.55, 0.12),
	},
	Colouring.RED_WHITE: {
		"base": Color(0.96, 0.95, 0.92), "back": Color(0.92, 0.9, 0.88), "belly": Color(1.0, 0.98, 0.96),
		"patch": Color(0.86, 0.12, 0.04), "patch_amount": 0.55, "patch_on_back": 1.0,
		"black_amount": 0.0, "speckle": 0.0, "shine": 0.7, "scales_show": 0.55,
		"fin_root": Color(0.97, 0.94, 0.92), "fin_edge": Color(1.0, 0.98, 0.97), "fin_clear": 0.4,
		"iris": Color(0.82, 0.66, 0.4),
	},
	Colouring.CALICO: {
		"base": Color(0.74, 0.8, 0.88), "back": Color(0.55, 0.62, 0.74), "belly": Color(0.94, 0.94, 0.95),
		"patch": Color(0.96, 0.5, 0.1), "patch_amount": 0.4, "patch_on_back": 0.4,
		"black": Color(0.04, 0.04, 0.05), "black_amount": 0.4, "speckle": 0.7, "shine": 0.1, "scales_show": 0.25,
		"fin_root": Color(0.82, 0.8, 0.8), "fin_edge": Color(0.92, 0.93, 0.95), "fin_clear": 0.45,
		"iris": Color(0.6, 0.55, 0.45),
	},
}

static var _meshes := {}

## Which kind: its shape (each its own model).
@export var kind := Kind.COMMON:
	set(value):
		kind = value
		_dress()
		_fit()
## Its colours: on either kind.
@export var colouring := Colouring.ORANGE:
	set(value):
		colouring = value
		_dress()
## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 1.2
## How many times in a beat its tail beats (there and back).
@export var tail_beats := 3:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it beats: 1 a goldfish cruising, 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far its mouth is open: 0 shut, 1 wide open (as when it bites, or gulps at the surface).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## The low model (about a twelfth of the triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about 1,600 triangles on the common goldfish, 1,770 on the fantail, spent on the
## outline, the eye, the mouth and the fins' edges) in place of the full one; `low` still shows the
## low model. With it on the full model is never loaded.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 the eye as it was (the default), 1 the cartoon eye (bigger, a white, a gold
## iris, a big round pupil and a highlight: a goldfish's wide, goggling, empty-headed stare). Gulp
## sets it to 1.
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = value
		_send(&"cartoon_eyes", value)
## Where the cartoon eye looks, -1..1 each way: x towards its nose (+) or tail, y up (+) or down.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value
		_send(&"eye_look", value)
## 0 open, 1 shut: the eye squashes flat (a fish has no lids) and a lid the colour of its skin
## comes down over it.
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = value
		_send(&"blink", value)
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set it.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D


## A kind's full mesh or its low one (each one surface, to wear `new_material()`): for drawing a
## goldfish without this node. Loaded once and kept, without the importer's automatic LODs (which
## are made from the still model and would bend in straight pieces far off).
static func mesh_of(low_wanted := false, kind_wanted := Kind.COMMON) -> Mesh:
	return _mesh_at(MODEL % [NAMES[kind_wanted], "_lo" if low_wanted else ""])


## A kind's game mesh (one surface, to wear `new_material()`), for a game that draws meshes
## itself. Loaded once and kept, without the importer's automatic LODs.
static func game_mesh(kind_wanted := Kind.COMMON) -> Mesh:
	return _mesh_at(MODEL % [NAMES[kind_wanted], "_game"])


static func _mesh_at(path: String) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh)
		made.free()
	return _meshes[path]


## A new material for a kind's meshes, in a colouring. Its shader settings are the game's to set:
## `phase` (0..1 through one beat of the tail), `sway`, `gape`, `curl`, `billow`, `wave` and the
## colours (the top of the shader lists them).
static func new_material(kind_wanted := Kind.COMMON, colouring_wanted := Colouring.ORANGE) -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	_wear(made, kind_wanted, colouring_wanted)
	return made


## The same mesh with no LODs: each surface's arrays alone.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


func _init() -> void:
	_material = ShaderMaterial.new()
	_material.shader = SHADER
	_dress()


func _ready() -> void:
	_show()
	_send_phase()
	_send(&"sway", sway)
	_send(&"gape", gape)
	_send(&"cartoon_eyes", cartoon_eyes)
	_send(&"eye_look", eye_look)
	_send(&"blink", blink)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the other fish's are; its beat does not change with
## its speed: set `sway` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `curl` (bent round into a turn: radians from gills to tail,
## more than 0 the tail comes round to its left, +X), `billow`, `wave`, or a colour or amount (`base`,
## `back`, `belly`, `patch`, `patch_amount`, `patch_on_back`, `black`, `black_amount`, `speckle`,
## `shine`, `scales_show`, `fin_root`, `fin_edge`, `fin_clear`, `water`, `iris`, `mouth_inside`, the cartoon
## eye's `eye_grow`, `eye_white`, `iris_size`, `pupil_size`, `lid`, `lid_slant`, the gills' `gill_red`,
## `gill_raker`). `kind` and `colouring` set most of them again.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_send(setting, value)


## Its one material (both its models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one beat of the tail it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


static func _wear(on: ShaderMaterial, kind_wanted: Kind, colouring_wanted: Colouring) -> void:
	var shape: Dictionary = KINDS[kind_wanted]
	for setting: String in shape:
		if setting != "depth" and setting != "width":
			on.set_shader_parameter(setting, shape[setting])
	var colours: Dictionary = COLOURINGS[colouring_wanted]
	for setting: String in colours:
		on.set_shader_parameter(setting, colours[setting])
	# (what a colouring leaves out goes back to the shader's own)
	for setting: String in ["patch", "patch_on_back", "black"]:
		if not colours.has(setting):
			on.set_shader_parameter(setting, null)


func _dress() -> void:
	if _material:
		_wear(_material, kind, colouring)


func _fit() -> void:
	# (a model not yet shown is not loaded: its mesh is set when it is first shown)
	if _full:
		_full.mesh = mesh_of(false, kind)
	if _low:
		_low.mesh = mesh_of(true, kind)
	if _game:
		_game.mesh = game_mesh(kind)


func _show() -> void:
	if not is_inside_tree():
		return
	# (each model is made only when it is first shown)
	if low:
		if _low == null:
			_low = _instance_of("GoldfishLo", mesh_of(true, kind))
	elif game:
		if _game == null:
			_game = _instance_of("GoldfishGame", game_mesh(kind))
	elif _full == null:
		_full = _instance_of("Goldfish", mesh_of(false, kind))
	if _full:
		_full.visible = not low and not game
	if _low:
		_low.visible = low
	if _game:
		_game.visible = game and not low


func _instance_of(named: String, shown: Mesh) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = shown
	mesh.material_override = _material
	# (its tail swings and billows out past where the still model ends)
	mesh.extra_cull_margin = 0.05
	mesh.name = named
	add_child(mesh)
	return mesh
