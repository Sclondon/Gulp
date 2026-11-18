class_name Guppy
extends Node3D
## A guppy (Poecilia reticulata), `type`:
##
## - FEMALE: 0.045 m long, the bigger fish: a full olive-tan body with a rounded belly and a dark
##   gravid spot, a net of darker-edged scales, a small rounded dorsal fin set well back, a small
##   rounded tail, clear fins.
## - The males, each 0.04 m long: a small slender body carrying a big fan tail (a delta with a
##   rounded back edge) as long as the body, a long flag of a dorsal fin trailing back over it, the
##   anal fin made into a gonopodium (a thin rod under the belly):
##   - WILD (the default): grey-olive with big orange, black and shining blue-green spots, the tail
##     pale orange with spots of the same.
##   - RED: a red delta: the tail and dorsal solid deep red, the back half of the body red.
##   - BLUE_GRASS: a sky-blue tail and dorsal covered in fine black dots, the back half of the body
##     metallic blue with dots.
##   - COBRA: a yellow-green snakeskin net over the whole body, a yellow tail and dorsal netted in
##     black.
##   `pattern_seed` makes each one's spots and marks its own (it is a random number when the node is
##   made: set it for one that must stay the same).
##
## All of the markings are drawn by its shader (no texture files). How it looks and swims only:
## whatever moves it puts it where it is and turns it the way it goes. Its nose points along its
## own -Z (Godot's forward), its belly down; its origin is on its middle line, half way along its
## length (tail included). `scale` it for a bigger one. No sound.
##
## It swims by a wave down its body, drawn by the shader (no bones); the male's big tail is carried
## partly as a plate and partly lags behind, and a ripple runs across the tail and the dorsal fin
## like cloth. Its mouth opens: `gape`.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats
## `tail_beats` times and `ripples` ripples run across its fins (whole numbers), so its motion comes
## round again exactly every beat. Either call `step(velocity, delta)` each frame, which moves
## `phase` on by delta / beat, or set `phase` yourself (for a picture that must loop: frame /
## frames in a beat). The same names and meanings as GameCommon's yellowfin tuna and sardine.
##
## The models are creatures/guppy/models/guppy_female.glb and guppy_male.glb (and _lo and _game),
## built by
## tools/build_guppy.py; guppy.gdshader draws the markings and swims it. Only the models shown are
## ever loaded: with `game` (or `low`) set, the full models are never loaded.

enum Type { FEMALE, WILD, RED, BLUE_GRASS, COBRA }

const MODEL := "res://creatures/guppy/models/guppy_%s%s.glb"
const SHADER := preload("res://creatures/guppy/guppy.gdshader")
## As the male's model is built (tools/build_guppy.py): from the tip of its jaw to the end of its
## tail, and how deep and how wide its body is at its deepest (metres, at scale 1). `LENGTHS`,
## `DEPTHS` and `WIDTHS` give each type's.
const LENGTH := 0.04
const DEPTH := 0.0056
const WIDTH := 0.0034
const LENGTHS := {Type.FEMALE: 0.045, Type.WILD: 0.04, Type.RED: 0.04, Type.BLUE_GRASS: 0.04, Type.COBRA: 0.04}
const DEPTHS := {Type.FEMALE: 0.0100, Type.WILD: 0.0056, Type.RED: 0.0056, Type.BLUE_GRASS: 0.0056, Type.COBRA: 0.0056}
const WIDTHS := {Type.FEMALE: 0.0063, Type.WILD: 0.0034, Type.RED: 0.0034, Type.BLUE_GRASS: 0.0034, Type.COBRA: 0.0034}
## Each model's shape, as the shader needs it (tools/build_guppy.py prints these: its SHADER lines).
const SHAPES := {
	"female": {
		"length_m": 0.045, "jaw_to": 0.042, "hinge_y": -0.01312, "eye_at": Vector2(0.09, 0.018), "eye_radius": 0.037,
		"joint": 0.775, "body_to": 0.8, "mouth": Vector2(0.002, -0.36), "gill": Vector2(0.2, 7.0), "male": 0.0,
		"gill_from": 0.0996, "gill_to": 0.186, "wall_up": 0.0156, "eye_big": 1.35,
	},
	"male": {
		"length_m": 0.04, "jaw_to": 0.037, "hinge_y": -0.01132, "eye_at": Vector2(0.074, 0.013), "eye_radius": 0.031,
		"joint": 0.525, "body_to": 0.548, "mouth": Vector2(0.002, -0.36), "gill": Vector2(0.16, 8.0), "male": 1.0,
		"gill_from": 0.0806, "gill_to": 0.146, "wall_up": 0.0129, "eye_big": 1.45,
	},
}
## Each type: which model it wears, and its pattern and colours in the shader.
const TYPES := {
	Type.FEMALE: {
		"model": "female", "pattern": 0,
		"body_back": Color(0.34, 0.33, 0.2), "body_side": Color(0.64, 0.61, 0.46), "belly": Color(0.9, 0.88, 0.8),
		"body_rear": Color(0.64, 0.61, 0.46), "sheen": Color(0.45, 0.55, 0.55),
		"fin_main": Color(0.74, 0.71, 0.58), "fin_root": Color(0.62, 0.59, 0.45), "fin_edge": Color(0.8, 0.77, 0.66),
		"fin_mark": Color(0.1, 0.1, 0.08),
		"eye_iris": Color(0.78, 0.52, 0.2), "iris_r": 0.6, "pupil_r": 0.36, "lid_rest": 0.38, "lid_slant": -0.12,
	},
	Type.WILD: {
		"model": "male", "pattern": 1,
		"body_back": Color(0.35, 0.36, 0.25), "body_side": Color(0.68, 0.68, 0.6), "belly": Color(0.9, 0.9, 0.86),
		"body_rear": Color(0.6, 0.62, 0.55), "sheen": Color(0.3, 0.75, 0.8),
		"fin_main": Color(0.88, 0.66, 0.32), "fin_root": Color(0.7, 0.6, 0.42), "fin_edge": Color(0.92, 0.6, 0.25),
		"fin_mark": Color(0.04, 0.04, 0.04),
		"spot_a": Color(0.98, 0.45, 0.08), "spot_b": Color(0.03, 0.03, 0.03), "spot_c": Color(0.15, 0.75, 0.8),
		"eye_iris": Color(0.98, 0.52, 0.1), "iris_r": 0.64, "pupil_r": 0.42, "lid_rest": 1.3, "lid_slant": 0.0,
	},
	Type.RED: {
		"model": "male", "pattern": 2,
		"body_back": Color(0.45, 0.3, 0.25), "body_side": Color(0.85, 0.72, 0.66), "belly": Color(0.92, 0.88, 0.85),
		"body_rear": Color(0.75, 0.1, 0.08), "sheen": Color(0.9, 0.5, 0.5),
		"fin_main": Color(0.8, 0.06, 0.05), "fin_root": Color(0.55, 0.04, 0.04), "fin_edge": Color(0.92, 0.25, 0.2),
		"fin_mark": Color(0.2, 0.02, 0.02),
		"eye_iris": Color(0.9, 0.12, 0.08), "iris_r": 0.64, "pupil_r": 0.42, "lid_rest": 1.3, "lid_slant": 0.0,
	},
	Type.BLUE_GRASS: {
		"model": "male", "pattern": 3,
		"body_back": Color(0.3, 0.35, 0.4), "body_side": Color(0.75, 0.78, 0.8), "belly": Color(0.9, 0.9, 0.9),
		"body_rear": Color(0.15, 0.35, 0.78), "sheen": Color(0.3, 0.6, 1.0),
		"fin_main": Color(0.35, 0.6, 0.95), "fin_root": Color(0.2, 0.35, 0.72), "fin_edge": Color(0.55, 0.75, 1.0),
		"fin_mark": Color(0.03, 0.04, 0.06),
		"eye_iris": Color(0.3, 0.6, 1.0), "iris_r": 0.64, "pupil_r": 0.42, "lid_rest": 1.3, "lid_slant": 0.0,
	},
	Type.COBRA: {
		"model": "male", "pattern": 4,
		"body_back": Color(0.3, 0.35, 0.15), "body_side": Color(0.75, 0.78, 0.35), "belly": Color(0.9, 0.9, 0.75),
		"body_rear": Color(0.62, 0.72, 0.3), "sheen": Color(0.5, 0.8, 0.4),
		"fin_main": Color(0.95, 0.8, 0.2), "fin_root": Color(0.72, 0.6, 0.15), "fin_edge": Color(0.98, 0.86, 0.35),
		"fin_mark": Color(0.05, 0.05, 0.03),
		"eye_iris": Color(0.92, 0.8, 0.2), "iris_r": 0.64, "pupil_r": 0.42, "lid_rest": 1.3, "lid_slant": 0.0,
	},
}

## Which guppy it is.
@export var type := Type.WILD:
	set(value):
		type = value
		_dress()
## A number that makes this one's spots and marks its own.
@export var pattern_seed := 0.0:
	set(value):
		pattern_seed = value
		_send(&"pattern_seed", value)
## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 0.75
## How many times in a beat its tail beats (there and back), and how many ripples run across its
## tail and dorsal fin.
@export var tail_beats := 3:
	set(value):
		tail_beats = maxi(value, 0)
		_send(&"tail_beats", float(tail_beats))
@export var ripples := 2:
	set(value):
		ripples = maxi(value, 0)
		_send(&"ripples", float(ripples))
## How widely it beats: 1 cruising, 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How strongly its tail and dorsal fin ripple: 1 cruising, 0 still.
@export_range(0.0, 2.0) var ripple := 1.0:
	set(value):
		ripple = value
		_send(&"ripple", value)
## How far its mouth is open: 0 shut, 1 wide open (as when it bites).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## The low model (about a tenth of the triangles), for far off or for several of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (Twilight Princess weight: several hundred triangles, spent on the outline, the
## eye, the mouth and the fins' edges) in place of the full one. Only the model shown is ever
## loaded, so a game that always has this (or `low`) set can leave the full models' .glb files out
## of its export. `low` still shows the low model.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 the eye as it is in life, 1 a bigger cartoon eye of the type's own character
## (the males a bright eager stare, the iris their tail's colour; the female a calm half lid).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where the cartoon eyes look: x towards the snout (+1) or back (-1), y up (+1) or down (-1), in
## each eye's own plane, so both look the same way.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(Vector2(-1.0, -1.0), Vector2.ONE)
		_send(&"eye_look", eye_look)
## A blink: 0 open, 1 shut (a lid the colour of the skin over each eye, on the cartoon eye and the
## eye in life alike).
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set
## it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)

static var _meshes := {}

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D


## A type's full model's mesh, or its low one's (each one surface, to wear `new_material(type)`):
## for drawing one without this node. (The four males share one model.)
static func mesh_of(low_wanted := false, which := Type.WILD) -> Mesh:
	return _mesh_at(MODEL % [TYPES[which]["model"], "_lo" if low_wanted else ""])


## A type's game model's mesh (one surface, to wear `new_material(type)`; loaded without Godot's
## automatic LODs, which would bend in straight pieces far off): for drawing a game model without
## this node. (The four males share one.)
static func game_mesh(which := Type.WILD) -> Mesh:
	return _mesh_at(MODEL % [TYPES[which]["model"], "_game"])


## A new material for a type's `mesh_of()` meshes, with its shape and colours set. Its other shader
## settings are the game's to set: `phase` (0..1 through one beat), `tail_beats`, `ripples`,
## `sway`, `ripple`, `gape`, `curl`, `wave`, `pattern_seed` (the top of the shader lists them).
static func new_material(which := Type.WILD) -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	_set_type(made, which)
	return made


static func _set_type(material_to: ShaderMaterial, which: int) -> void:
	var shape: Dictionary = SHAPES[TYPES[which]["model"]]
	for setting: String in shape:
		material_to.set_shader_parameter(setting, shape[setting])
	for setting: String in TYPES[which]:
		if setting != "model":
			material_to.set_shader_parameter(setting, TYPES[which][setting])


func _init() -> void:
	_material = new_material(type)
	pattern_seed = randf() * 100.0


func _ready() -> void:
	_dress()
	_send(&"phase", phase)
	_send(&"tail_beats", float(tail_beats))
	_send(&"ripples", float(ripples))
	_send(&"sway", sway)
	_send(&"ripple", ripple)
	_send(&"gape", gape)
	_send(&"pattern_seed", pattern_seed)
	_send(&"cartoon_eyes", cartoon_eyes)
	_send(&"eye_look", eye_look)
	_send(&"blink", blink)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the other fish's are; its beat does not change
## with its speed: set `sway` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `curl` (bent round into a turn: radians from gills to tail,
## more than 0 the tail comes round to its left, +X), `wave` (the length of the wave along its
## body, in body lengths), and the colours (`body_back`, `body_side`, `belly`, `body_rear`,
## `sheen`, `fin_main`, `fin_root`, `fin_edge`, `fin_mark`, `spot_a`, `spot_b`, `spot_c`,
## `fin_clear`, `mouth_inside`, `gill_red`, `gill_raker`, and the cartoon eye's `eye_iris`). A new
## `type` sets its colours again.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (a new type: its settings in the shader, and its models made again as they are shown)
func _dress() -> void:
	_set_type(_material, type)
	if not is_inside_tree():
		return
	for shown: MeshInstance3D in [_full, _low, _game]:
		if shown:
			shown.queue_free()
	_full = null
	_low = null
	_game = null
	_show()


# (each model is made, and loaded, only when it is first shown)
func _show() -> void:
	if not is_inside_tree():
		return
	if low and not _low:
		_low = _instance_of("_lo")
	elif not low and game and not _game:
		_game = _instance_of("_game")
	elif not low and not game and not _full:
		_full = _instance_of("")
	if _full:
		_full.visible = not low and not game
	if _low:
		_low.visible = low
	if _game:
		_game.visible = game and not low


func _instance_of(which: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = game_mesh(type) if which == "_game" else mesh_of(which == "_lo", type)
	mesh.material_override = _material
	# (its tail swings out past where the still model ends)
	mesh.extra_cull_margin = LENGTHS[type] * 0.3
	mesh.name = "Guppy" + {"": "", "_lo": "Lo", "_game": "Game"}[which]
	add_child(mesh)
	return mesh


static func _mesh_at(path: String) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		# (the game model without the automatic LODs; the others as they always were)
		_meshes[path] = without_lods(found.mesh) if path.ends_with("_game.glb") else found.mesh
		made.free()
	return _meshes[path]


## The mesh with only its own triangles: none of the thinned LOD meshes Godot's importer makes,
## which a body bent in the vertex shader would show in straight pieces far off.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain
