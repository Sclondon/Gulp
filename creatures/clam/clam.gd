class_name Clam
extends Node3D
## A clam, of one of three kinds (`kind`):
## - a GIANT clam (Tridacna gigas, 1.0 m long): a thick deep shell sitting hinge down, folded into five great
##   folds so that its gape's edge zigzags; open, a fleshy blue-green patterned mantle bulges out of the gape;
## - a SCALLOP (a Pacific pink scallop, 0.078 m): a ribbed pink fan with ears either side of the hinge; inside
##   its gape a mantle edge with a fringe of tentacles and a row of tiny blue eyes that glint; it SWIMS by
##   clapping its shell shut (`swim`);
## - a RAZOR clam (a jackknife, 0.15 m): long, narrow and glossy, lying on its side, its pale foot out of its
##   front end; it DIGS (`dig`): it stands up on its front end and pumps its foot down.
##
## How it looks and moves only: whatever moves it puts it where it is. Its front points along its own -Z (the
## scallop's gape, the razor clam's foot; the giant clam's hinge runs along Z). **Its origin is on the ground
## under its middle.** It is life size: `scale` it for a game. No sound. No eyes worth drawing (no
## `cartoon_eyes`): the scallop's are a row of glints drawn on its mantle's edge.
##
## `open` 0..1 swings the shell open about its hinge: the scallop's and the razor clam's upper valve, both of the
## giant clam's (and its mantle comes up out of the gape as it opens). Everything that moves runs on `phase`, 0
## to 1 through one `beat` (`tail_beats` times a beat, a whole number: the scallop's claps, the razor clam's
## pumps of its foot), so it loops exactly. Either call `step(velocity, delta)` each frame, which moves `phase`
## on by delta / beat, or set `phase` yourself. It has no `gape` and no `curl`.
##
## The models are creatures/clam/models/<kind>.glb (and _game, _lo), built by tools/build_clam.py;
## clam.gdshader colours and moves them.

enum Kind { GIANT, SCALLOP, RAZOR }

const MODEL := "res://creatures/clam/models/%s%s.glb"
const SHADER := preload("res://creatures/clam/clam.gdshader")
## Each kind's name in its models' file names.
const NAMES := {Kind.GIANT: "giant_clam", Kind.SCALLOP: "scallop", Kind.RAZOR: "razor_clam"}
## As the models are built (tools/build_clam.py), life size, metres, shut: how long (the giant clam along its
## hinge, the scallop from hinge to gape, the razor clam end to end, its foot and siphons left out), how high, how
## wide.
const LENGTHS := {Kind.GIANT: 1.0, Kind.SCALLOP: 0.078, Kind.RAZOR: 0.15}
const DEPTHS := {Kind.GIANT: 0.62, Kind.SCALLOP: 0.025, Kind.RAZOR: 0.013}
const WIDTHS := {Kind.GIANT: 0.58, Kind.SCALLOP: 0.083, Kind.RAZOR: 0.028}
## The giant clam's (the default kind's) length, depth and width.
const LENGTH := 1.0
const DEPTH := 0.62
const WIDTH := 0.58
## What each kind sets in the shader: its hinge (kept in step with the build script's HINGE lines), how far
## each valve turns at `open` 1, its colours.
const KINDS := {
	Kind.GIANT: {
		"kind": 0, "body_length": 1.0, "hinge_at": Vector3(0.0, 0.0, 0.0), "hinge_axis": Vector3(0.0, 0.0, 1.0),
		"upper_turn": -0.2, "lower_turn": 0.2,
		"shell": Color(0.84, 0.82, 0.75), "shell_lower": Color(0.84, 0.82, 0.75), "shell_dark": Color(0.42, 0.44, 0.3),
		"inside": Color(0.96, 0.95, 0.92), "lip": Color(0.9, 0.86, 0.72), "mantle": Color(0.03, 0.26, 0.36),
		"mantle_mark": Color(0.22, 0.8, 0.78), "mantle_edge": Color(0.25, 0.5, 1.0), "flesh": Color(0.7, 0.6, 0.4),
		"flesh_dark": Color(0.33, 0.29, 0.17), "vivid": 0.07,
	},
	Kind.SCALLOP: {
		"kind": 1, "body_length": 0.08, "hinge_at": Vector3(0.0, 0.0138, 0.039), "hinge_axis": Vector3(1.0, 0.0, 0.0),
		"upper_turn": 0.38, "lower_turn": 0.0,
		"shell": Color(0.93, 0.42, 0.4), "shell_lower": Color(0.95, 0.8, 0.72), "shell_dark": Color(0.58, 0.22, 0.28),
		"inside": Color(0.97, 0.95, 0.93), "lip": Color(0.95, 0.6, 0.56), "mantle": Color(0.9, 0.6, 0.35),
		"mantle_mark": Color(0.9, 0.6, 0.35), "mantle_edge": Color(0.1, 0.45, 1.0), "flesh": Color(0.92, 0.64, 0.38),
		"flesh_dark": Color(0.5, 0.25, 0.12), "vivid": 0.05,
	},
	Kind.RAZOR: {
		"kind": 2, "body_length": 0.15, "hinge_at": Vector3(-0.0125, 0.0065, 0.0), "hinge_axis": Vector3(0.0, 0.0, 1.0),
		"upper_turn": 0.12, "lower_turn": 0.0,
		"shell": Color(0.62, 0.56, 0.3), "shell_lower": Color(0.62, 0.56, 0.3), "shell_dark": Color(0.3, 0.24, 0.1),
		"inside": Color(0.88, 0.84, 0.92), "lip": Color(0.28, 0.2, 0.09), "mantle": Color(0.9, 0.8, 0.7),
		"mantle_mark": Color(0.9, 0.8, 0.7), "mantle_edge": Color(0.9, 0.8, 0.7), "flesh": Color(0.93, 0.83, 0.72),
		"flesh_dark": Color(0.45, 0.3, 0.17), "vivid": 0.04,
	},
}
## Seconds a beat takes for each kind.
const BEATS := {Kind.GIANT: 6.0, Kind.SCALLOP: 0.7, Kind.RAZOR: 1.6}

static var _meshes := {}

## Which kind of clam it is: its shape and colours.
@export var kind := Kind.GIANT:
	set(value):
		kind = value
		_dress()
		_fit()
## Seconds one beat takes. 0 for a caller that sets `phase` itself (`step` then leaves `phase` alone).
## Changing `kind` sets it to that kind's beat.
@export var beat := 6.0
## How many times in a beat it claps (the scallop), pumps its foot (the razor clam) or heaves its mantle.
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How strongly it moves: 1 as it lives, 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far open its shell is: 0 shut, 1 as wide as it opens.
@export_range(0.0, 1.0) var open := 0.0:
	set(value):
		open = clampf(value, 0.0, 1.0)
		_send(&"open", open)
## The scallop: 0 lying still, 1 swimming, clapping its shell shut once a beat (`open` is then ignored; the game
## moves it, gape first, in jerks).
@export_range(0.0, 1.0) var swim := 0.0:
	set(value):
		swim = clampf(value, 0.0, 1.0)
		_send(&"swim", swim)
## The razor clam: 0 lying on its side, 1 digging: stood up on the front end of its shell, its foot pumping down
## into the sand (the game sinks it).
@export_range(0.0, 1.0) var dig := 0.0:
	set(value):
		dig = clampf(value, 0.0, 1.0)
		_send(&"dig", dig)
## The low model (a few hundred triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (Twilight Princess weight: about 1,900 triangles for the giant clam, 860 for the scallop,
## 1,450 for the razor clam; the same shader and settings) in place of the full one; `low` still shows the low
## model. Each model is loaded only when it is first shown, so with `game` on the full models are never loaded
## and a game's web export may leave them out.
@export var game := false:
	set(value):
		game = value
		_show()
## How far through a beat it is, 0 to 1 (only the fraction counts).
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D


## A kind's full model's mesh, or its low one's (each one surface, to wear `new_material(kind)`). Loaded once.
static func mesh_of(kind_wanted: Kind, low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % [NAMES[kind_wanted], "_lo" if low_wanted else ""])


## A kind's game model's mesh (see `game`). Loaded once and kept.
static func game_mesh(kind_wanted: Kind) -> Mesh:
	return _mesh_at(MODEL % [NAMES[kind_wanted], "_game"])


static func _mesh_at(path: String) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh)
		made.free()
	return _meshes[path]


## `mesh` again without the lower levels of detail Godot's importer makes for it (made from the shut model,
## they would open in pieces).
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


## A new material for a kind's meshes, dressed for that kind. Its other settings are the game's to set:
## `phase`, `open`, `swim`, `dig`, `sway`.
static func new_material(kind_wanted: Kind = Kind.GIANT) -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	_wear(made, kind_wanted)
	return made


static func _wear(on: ShaderMaterial, kind_wanted: Kind) -> void:
	var wears: Dictionary = KINDS[kind_wanted]
	for setting: String in wears:
		on.set_shader_parameter(setting, wears[setting])


func _init() -> void:
	_material = new_material(kind)


func _ready() -> void:
	_full = _instance_of("Clam")
	_low = _instance_of("Clam_lo")
	_game = _instance_of("Clam_game")
	_show()
	_send_phase()
	for setting: StringName in [&"sway", &"open", &"swim", &"dig"]:
		_send(setting, get(setting))


## Each frame: moves it on through its beat (`velocity` is not used).
func step(_velocity: Vector3, delta: float) -> void:
	if beat > 0.0:
		phase += delta / beat


## Sets one of the shader's settings: the colours (`shell`, `shell_lower`, `shell_dark`, `inside`, `lip`,
## `mantle`, `mantle_mark`, `mantle_edge`, `flesh`, `flesh_dark`), `vivid`, or how far the valves turn
## (`upper_turn`, `lower_turn`). `kind` sets them all again.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_send(setting, value)


## Its one material (all its models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


func _dress() -> void:
	if _material:
		_wear(_material, kind)
	beat = BEATS[kind]


func _fit() -> void:
	if _full == null:
		return
	# (only the model shown is loaded; the others are given theirs when they are first shown)
	_full.mesh = mesh_of(kind, false) if _full.visible else null
	_low.mesh = mesh_of(kind, true) if _low.visible else null
	_game.mesh = game_mesh(kind) if _game.visible else null


func _show() -> void:
	if _full:
		_full.visible = not low and not game
		_low.visible = low
		_game.visible = game and not low
		_fit()


func _instance_of(called: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.material_override = _material
	# (open, or digging, it reaches past the shut model's box)
	mesh.extra_cull_margin = 0.25
	mesh.name = called
	add_child(mesh)
	return mesh
