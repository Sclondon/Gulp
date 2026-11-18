class_name SeaTurtle
extends Node3D
## A sea turtle, of one of four kinds (`type`): a GREEN (a smooth teardrop shell, a starburst on each plate, a
## small blunt head), a HAWKSBILL (a narrow hooked beak, thick overlapping plates with a serrated rear rim, amber
## and brown tortoiseshell), a LOGGERHEAD (a very big blocky head, a reddish-brown heart-shaped shell) or a
## LEATHERBACK (no plates: a long leathery back with seven ridges, blue-black speckled with white, very long fore
## flippers; the biggest). Each is a model of its own; one shader draws them all.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it goes. Its beak points
## along its own -Z (Godot's forward), its back up; its origin is on its middle line half way along its shell.
## `scale` it for a bigger or smaller one. No sound.
##
## It swims as sea turtles do: it flies with its fore flippers, sweeping them down and back in a strong stroke and
## bringing them up and forward again turned edge on (feathered); its hind flippers trail and steer. All of that is
## drawn by the shader (no bones).
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which it strokes `tail_beats` times (a whole
## number), so its motion comes round again exactly every beat. Either call `step(velocity, delta)` each frame,
## which moves `phase` on by delta / beat, or set `phase` yourself. The names are GameCommon's fish's
## (YellowfinTuna): a "tail beat" here is one stroke of the fore flippers.
##
## The models are creatures/sea_turtle/models/sea_turtle_<type>.glb (and _lo, _game), built by
## tools/build_sea_turtle.py; sea_turtle.gdshader draws them and moves them.

enum Type { GREEN, HAWKSBILL, LOGGERHEAD, LEATHERBACK }

const MODEL := "res://creatures/sea_turtle/models/sea_turtle_%s%s.glb"
const SHADER := preload("res://creatures/sea_turtle/sea_turtle.gdshader")
## Each type's name in its model's file name.
const NAMES := {
	Type.GREEN: "green", Type.HAWKSBILL: "hawksbill", Type.LOGGERHEAD: "loggerhead", Type.LEATHERBACK: "leatherback",
}
## As the models are built (metres, at scale 1, life size), for each type: the shell's length (straight, front to
## back; the origin is half way along it), how far the tip of its beak is ahead of the origin (head and neck out),
## how far its hind flippers reach behind it, the shell's width and the depth of its body (shell and plastron), and
## the fore flippers' span from tip to tip as they are held (out like wings, half way through a stroke).
const LENGTHS := {Type.GREEN: 1.1, Type.HAWKSBILL: 0.9, Type.LOGGERHEAD: 1.0, Type.LEATHERBACK: 1.8}
const FRONT := {Type.GREEN: 0.712, Type.HAWKSBILL: 0.611, Type.LOGGERHEAD: 0.738, Type.LEATHERBACK: 1.161}
const BACK := {Type.GREEN: 0.557, Type.HAWKSBILL: 0.456, Type.LOGGERHEAD: 0.506, Type.LEATHERBACK: 0.9}
const WIDTHS := {Type.GREEN: 0.935, Type.HAWKSBILL: 0.648, Type.LOGGERHEAD: 0.86, Type.LEATHERBACK: 1.098}
const DEPTHS := {Type.GREEN: 0.312, Type.HAWKSBILL: 0.241, Type.LOGGERHEAD: 0.306, Type.LEATHERBACK: 0.538}
const SPANS := {Type.GREEN: 1.776, Type.HAWKSBILL: 1.352, Type.LOGGERHEAD: 1.668, Type.LEATHERBACK: 3.002}
## The green's (the default type's) shell length, depth and width, for code that reads one number as GameCommon's
## fish have it; LENGTHS and the rest have every type's.
const LENGTH := 1.1
const DEPTH := 0.312
const WIDTH := 0.935
## What each type sets in the shader: where things are on its model (the build script prints them: its SHADER
## line), its plate layout (as the build script lays them out), its colours.
const TYPES := {
	Type.GREEN: {
		"shell_length": 1.1, "nose_z": -0.7117, "head_length": 0.165, "neck_front": -0.5467, "neck_back": -0.462,
		"neck_pivot": Vector3(0.0, -0.044, -0.55), "tuck_back": 0.0693, "mouth_corner": -0.6424, "jaw_open": 0.55,
		"fore_span": Vector3(0.9516, -0.1142, 0.2855), "rim_len": 1.4641,
		"hard_shell": 1.0, "plate_vw": 0.3, "plate_mw": 0.062, "plate_nm": 12.5,
		"vert_seams": Vector4(0.25, 0.43, 0.6, 0.77), "side_seams": Vector4(0.31, 0.52, 0.73, 2.0), "plate_slant": 0.9,
		"plastron_seams": Vector4(0.17, 0.33, 0.58, 0.8), "pattern": 0,
		"shell_base": Color(0.3, 0.25, 0.11), "shell_dark": Color(0.1, 0.07, 0.035), "shell_light": Color(0.62, 0.52, 0.22),
		"seam": Color(0.66, 0.58, 0.34), "plastron": Color(0.88, 0.82, 0.58),
		"scale_dark": Color(0.24, 0.17, 0.09), "scale_edge": Color(0.8, 0.72, 0.46), "skin_under": Color(0.82, 0.76, 0.56),
		"beak": Color(0.55, 0.5, 0.36), "mouth_inside": Color(0.62, 0.4, 0.36), "claw_colour": Color(0.5, 0.46, 0.34),
		"scale_size": 0.022, "scales": 1.0, "speckles": 0.0, "pink_spot": 0.0,
	},
	Type.HAWKSBILL: {
		"shell_length": 0.9, "nose_z": -0.6107, "head_length": 0.153, "neck_front": -0.4577, "neck_back": -0.378,
		"neck_pivot": Vector3(0.0, -0.036, -0.45), "tuck_back": 0.0643, "mouth_corner": -0.5403, "jaw_open": 0.5,
		"fore_span": Vector3(0.9516, -0.1142, 0.2855), "rim_len": 1.3604,
		"hard_shell": 1.0, "plate_vw": 0.27, "plate_mw": 0.07, "plate_nm": 12.5,
		"vert_seams": Vector4(0.25, 0.43, 0.6, 0.77), "side_seams": Vector4(0.31, 0.52, 0.73, 2.0), "plate_slant": 0.9,
		"plastron_seams": Vector4(0.17, 0.33, 0.58, 0.8), "pattern": 1,
		"shell_base": Color(0.4, 0.19, 0.06), "shell_dark": Color(0.09, 0.045, 0.02), "shell_light": Color(0.8, 0.54, 0.18),
		"seam": Color(0.14, 0.07, 0.03), "plastron": Color(0.9, 0.8, 0.5),
		"scale_dark": Color(0.17, 0.09, 0.05), "scale_edge": Color(0.82, 0.66, 0.35), "skin_under": Color(0.86, 0.76, 0.5),
		"beak": Color(0.55, 0.42, 0.22), "mouth_inside": Color(0.62, 0.4, 0.36), "claw_colour": Color(0.45, 0.38, 0.25),
		"scale_size": 0.02, "scales": 1.0, "speckles": 0.0, "pink_spot": 0.0,
	},
	Type.LOGGERHEAD: {
		"shell_length": 1.0, "nose_z": -0.7375, "head_length": 0.25, "neck_front": -0.4875, "neck_back": -0.42,
		"neck_pivot": Vector3(0.0, -0.035, -0.5), "tuck_back": 0.105, "mouth_corner": -0.625, "jaw_open": 0.6,
		"fore_span": Vector3(0.9516, -0.1142, 0.2855), "rim_len": 1.4746,
		"hard_shell": 1.0, "plate_vw": 0.3, "plate_mw": 0.064, "plate_nm": 12.5,
		"vert_seams": Vector4(0.24, 0.42, 0.6, 0.77), "side_seams": Vector4(0.24, 0.4, 0.56, 0.73), "plate_slant": 0.9,
		"plastron_seams": Vector4(0.17, 0.33, 0.58, 0.8), "pattern": 2,
		"shell_base": Color(0.42, 0.17, 0.065), "shell_dark": Color(0.2, 0.075, 0.03), "shell_light": Color(0.64, 0.38, 0.17),
		"seam": Color(0.56, 0.33, 0.15), "plastron": Color(0.9, 0.78, 0.5),
		"scale_dark": Color(0.4, 0.17, 0.07), "scale_edge": Color(0.8, 0.62, 0.32), "skin_under": Color(0.86, 0.7, 0.4),
		"beak": Color(0.62, 0.48, 0.25), "mouth_inside": Color(0.62, 0.4, 0.36), "claw_colour": Color(0.5, 0.42, 0.26),
		"scale_size": 0.03, "scales": 1.0, "speckles": 0.0, "pink_spot": 0.0,
	},
	Type.LEATHERBACK: {
		"shell_length": 1.8, "nose_z": -1.161, "head_length": 0.261, "neck_front": -0.9, "neck_back": -0.756,
		"neck_pivot": Vector3(0.0, -0.081, -0.9), "tuck_back": 0.1096, "mouth_corner": -1.0435, "jaw_open": 0.55,
		"fore_span": Vector3(0.9535, -0.0953, 0.286), "rim_len": 1.272,
		"hard_shell": 0.0, "plate_vw": 0.3, "plate_mw": 0.06, "plate_nm": 12.5,
		"vert_seams": Vector4(0.25, 0.43, 0.6, 0.77), "side_seams": Vector4(0.31, 0.52, 0.73, 2.0), "plate_slant": 0.9,
		"plastron_seams": Vector4(2.0, 2.0, 2.0, 2.0), "pattern": 3,
		"shell_base": Color(0.045, 0.055, 0.07), "shell_dark": Color(0.02, 0.025, 0.035), "shell_light": Color(0.74, 0.77, 0.8),
		"seam": Color(0.1, 0.1, 0.12), "plastron": Color(0.84, 0.8, 0.8),
		"scale_dark": Color(0.05, 0.06, 0.08), "scale_edge": Color(0.05, 0.06, 0.08), "skin_under": Color(0.78, 0.74, 0.76),
		"beak": Color(0.07, 0.08, 0.09), "mouth_inside": Color(0.6, 0.38, 0.4), "claw_colour": Color(0.1, 0.1, 0.1),
		"scale_size": 0.03, "scales": 0.0, "speckles": 1.0, "pink_spot": 1.0,
	},
}
## Each type's cartoon eye (`cartoon_eyes`): where its eye is on its model (the build script prints its EYE line),
## how much bigger the cartoon eye grows, and its character, old and kind and heavy-lidded in each, a little
## different: the green's gentle sleepy brown eye under a half-closed lid; the hawksbill's brighter amber eye, its
## lid higher and level (wise, a little sharp); the loggerhead's heaviest lid, drooping to the back, over a
## reddish-brown eye (a sleepy old grandfather); the leatherback's big dark soulful eye, its lid drooping a long
## way to the back (sad and wise).
const EYES := {
	Type.GREEN: {"eye_mid": Vector3(0.048, -0.019, -0.6539), "eye_out": Vector3(0.8614, 0.448, -0.2393),
		"eye_ahead": Vector3(-0.2123, -0.1104, -0.9709), "eye_up": Vector3(-0.4614, 0.8872, 0.0), "eye_r": 0.014,
		"eye_sag": 0.00176, "eye_grow": 1.7, "iris": Color(0.36, 0.22, 0.1), "iris_size": 0.62, "pupil_size": 0.5,
		"lid_top": 0.35, "lid_droop": 0.15, "lid_low": -0.78},
	Type.HAWKSBILL: {"eye_mid": Vector3(0.0307, -0.0175, -0.5464), "eye_out": Vector3(0.8784, 0.392, -0.2732),
		"eye_ahead": Vector3(-0.2495, -0.1114, -0.9619), "eye_up": Vector3(-0.4075, 0.9132, 0.0), "eye_r": 0.0115,
		"eye_sag": 0.00167, "eye_grow": 1.65, "iris": Color(0.66, 0.42, 0.12), "iris_size": 0.6, "pupil_size": 0.46,
		"lid_top": 0.5, "lid_droop": 0.05, "lid_low": -0.74},
	Type.LOGGERHEAD: {"eye_mid": Vector3(0.0787, 0.0042, -0.655), "eye_out": Vector3(0.8392, 0.4336, -0.3283),
		"eye_ahead": Vector3(-0.2917, -0.1507, -0.9446), "eye_up": Vector3(-0.459, 0.8884, 0.0), "eye_r": 0.0163,
		"eye_sag": 0.00144, "eye_grow": 1.55, "iris": Color(0.44, 0.17, 0.07), "iris_size": 0.64, "pupil_size": 0.52,
		"lid_top": 0.15, "lid_droop": 0.25, "lid_low": -0.68},
	Type.LEATHERBACK: {"eye_mid": Vector3(0.0806, -0.0428, -1.0723), "eye_out": Vector3(0.8655, 0.394, -0.3092),
		"eye_ahead": Vector3(-0.2814, -0.1281, -0.951), "eye_up": Vector3(-0.4143, 0.9101, 0.0), "eye_r": 0.0183,
		"eye_sag": 0.0018, "eye_grow": 1.7, "iris": Color(0.1, 0.11, 0.15), "iris_size": 0.72, "pupil_size": 0.62,
		"lid_top": 0.3, "lid_droop": 0.35, "lid_low": -0.82},
}

static var _meshes := {}

## Which sea turtle it is: its model, shell and colours.
@export var type := Type.GREEN:
	set(value):
		type = value
		_wear(_material, type)
		_show()
## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 2.0
## How many times in a beat it strokes its fore flippers.
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How hard it strokes: 1 a turtle cruising, 0 its flippers held still (gliding).
@export_range(0.0, 1.5) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Turning: more than 0 turns it to its left (+X). It banks (its left side rolls down by half of `curl`, in
## radians), turns its head into the turn (by 0.45 of `curl` at the head, less down the neck) and swings its hind
## flippers' tips round to its left (0.6 of `curl`), as a rudder. Less than 0, the same to its right.
@export_range(-2.0, 2.0) var curl := 0.0:
	set(value):
		curl = value
		_send(&"curl", value)
## Diving and rising: more than 0 its tail comes up and its beak goes down. It pitches by 0.4 of `arch` (radians,
## about its origin), its head bends down by 0.3 of it more and its hind flippers lift by 0.5 of it.
@export_range(-2.0, 2.0) var arch := 0.0:
	set(value):
		arch = value
		_send(&"arch", value)
## Its beak: 0 shut, 1 wide open, as when it bites.
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = value
		_send(&"gape", value)
## Drawn in, 0 to 1: its head and neck drawn back a little (sea turtles cannot pull right in) and dipped, its fore
## flippers swept back along its sides, its hind flippers drawn in, and it strokes half as hard.
@export_range(0.0, 1.0) var tuck := 0.0:
	set(value):
		tuck = value
		_send(&"tuck", value)
## The low model (about 1,700 to 2,100 triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about 2,750 to 3,150 triangles, spent on its outline, head, eyes and flippers) in place of the
## full one; `low` still shows the low one. Each model is loaded only when it is first shown, so with `game` on the
## full .glb files are never loaded (a game's web export can leave them out).
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 the eye as it is, 1 bigger and drawn as a cartoon, old and kind and heavy-lidded (each type a
## little different: EYES).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = value
		_send(&"cartoon_eyes", value)
## Where both eyes look, -1..1: x towards its beak, y up (the cartoon eye's iris slides that way).
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value
		_send(&"eye_look", value)
## Its lids: 0 open, 1 shut.
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = value
		_send(&"blink", value)
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()

var _material: ShaderMaterial
# (the models shown so far, by type and ending: "" the full one, "_lo", "_game")
var _shown := {}
var _made := false


## A type's full model's mesh, or its low one's (each one surface, to wear `new_material(type)`): for drawing sea
## turtles without this node.
static func mesh_of(type_wanted := Type.GREEN, low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % [NAMES[type_wanted], "_lo" if low_wanted else ""])


## A type's game model's mesh (one surface, to wear `new_material(type)`), without the thinned LOD meshes Godot's
## importer makes (bent in the shader, they would move in straight pieces far off).
static func game_mesh(type_wanted := Type.GREEN) -> Mesh:
	return _mesh_at(MODEL % [NAMES[type_wanted], "_game"], true)


## A new material for a type's meshes, dressed as that type. Its shader settings are the game's to set: `phase`
## (0..1 through one stroke), `sway`, `curl`, `arch`, `gape`, `tuck`, `cartoon_eyes`, `eye_look`, `blink` (the top
## of the shader lists them all).
static func new_material(type_wanted := Type.GREEN) -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	_wear(made, type_wanted)
	return made


## A type's shell length, as LENGTHS has it (metres at scale 1).
static func length_of(type_wanted := Type.GREEN) -> float:
	return LENGTHS[type_wanted]


func _init() -> void:
	_material = new_material(type)


func _ready() -> void:
	_made = true
	_show()
	_send_phase()
	for setting: StringName in [&"sway", &"curl", &"arch", &"gape", &"tuck", &"cartoon_eyes", &"eye_look", &"blink"]:
		_send(setting, get(setting))


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat. (`velocity` is taken
## so that it is called as the fish's are; its beat does not change with its speed: set `sway` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: its colours (`shell_base`, `shell_dark`, `shell_light`, `seam`, `plastron`,
## `scale_dark`, `scale_edge`, `skin_under`, `beak`, `mouth_inside`, `claw_colour`, `iris`), `speckles`,
## `pink_spot`, `scales`. Setting `type` puts that type's own back.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


## The shell length of the type it is (metres at scale 1).
func length() -> float:
	return LENGTHS[type]


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one stroke it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


static func _wear(on: ShaderMaterial, type_wanted: Type) -> void:
	if on == null:
		return
	var wears: Dictionary = TYPES[type_wanted]
	for setting: String in wears:
		on.set_shader_parameter(setting, wears[setting])
	var eyes: Dictionary = EYES[type_wanted]
	for setting: String in eyes:
		on.set_shader_parameter(setting, eyes[setting])


func _show() -> void:
	if not _made:
		return
	var wanted := "%s%s" % [NAMES[type], "_lo" if low else ("_game" if game else "")]
	if not _shown.has(wanted):
		_shown[wanted] = _instance_of(wanted)
	for ending: String in _shown:
		(_shown[ending] as MeshInstance3D).visible = ending == wanted


func _instance_of(named: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	if named.ends_with("_game"):
		mesh.mesh = game_mesh(type)
	else:
		mesh.mesh = mesh_of(type, named.ends_with("_lo"))
	mesh.material_override = _material
	# (its flippers swing out past where the still model ends; banking and pitching further)
	mesh.extra_cull_margin = 0.6 * LENGTHS[type]
	mesh.name = "SeaTurtle_" + named
	add_child(mesh)
	return mesh


static func _mesh_at(path: String, plain := false) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh) if plain else found.mesh
		made.free()
	return _meshes[path]


## A copy of `mesh` without the LOD meshes Godot's importer made for it.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain
