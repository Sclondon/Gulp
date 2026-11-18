class_name Shrimp
extends Node3D
## A shrimp, of one of three kinds (`kind`), each a model of its own:
##
## - CLEANER: a scarlet cleaner shrimp (Lysmata amboinensis), 0.058 m from its rostrum's tip to
##   its tail's: red down each side of its back with a white stripe down the middle, yellow-orange
##   below, ten long thin legs, and very long white antennae that it waves.
## - MANTIS: a peacock mantis shrimp (Odontodactylus scyllarus), 0.15 m: flattened and long,
##   vivid green with red spotted arms, orange antennal scales and blue and orange tail paddles;
##   big eyes on stalks that swivel each on its own (`swivel`); two club arms folded under its head
##   that punch out and back (`strike`); a row of broad paddle swimmerets and a fanned tail.
## - PISTOL: a pistol (snapping) shrimp (Alpheus), 0.045 m: small and drab olive-tan, its eyes
##   peeping out under the hood of its carapace, one huge claw on its right whose finger cocks open
##   and snaps shut (`snap`), a small claw on its left.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it
## faces. Its head points along its own -Z, its back up, its left side +X; its origin is ON THE
## GROUND under the middle of its body (half way along LENGTH), so put it where the sea floor is.
## `scale` it for a bigger or smaller one. No sound.
##
## Everything moves in the shader (no bones), on `phase`, 0 to 1 through one `beat`, in which
## each leg steps and each swimmeret beats `steps` times (a whole number), so it comes round again
## exactly every beat (the mantis shrimp's eyes swivel two and three times a beat; the cleaner's
## antennae wave once and twice). `walk` strides its legs (+ forwards), `paddle` beats its
## swimmerets (as it swims), `flick` curls its abdomen and tail fan down and under (its backwards
## dart: drive it from 0 to 1 and back in a fifth of a second while you move it backwards). Either
## call `step(velocity, delta)` each frame, which moves `phase` on by how far it has walked (so its
## feet do not slide) or, off the ground, by `beat`, or set `phase` yourself.
##
## Three models of each kind: the full one, the game one (`game`) and the low one (`low`). Each is
## loaded only when first shown: with `game` on, the full models are never loaded.
##
## The models are creatures/shrimps/models/shrimp_<kind>.glb (and _game, _lo), built by
## tools/build_shrimps.py; shrimp.gdshader draws the markings and moves them.

enum Kind { CLEANER, MANTIS, PISTOL }

const MODEL := "res://creatures/shrimps/models/shrimp_%s%s.glb"
const SHADER := preload("res://creatures/shrimps/shrimp.gdshader")
## Each kind's name in its models' file names.
const NAMES := {Kind.CLEANER: "cleaner", Kind.MANTIS: "mantis", Kind.PISTOL: "pistol"}
## As the models are built (metres, at scale 1): from the front of its head (the rostrum's tip,
## the mantis shrimp's rostral plate) to the tip of its tail fan; how deep and how wide its body
## is at its biggest; how high the top of its back stands above the ground.
const LENGTH := {Kind.CLEANER: 0.058, Kind.MANTIS: 0.1485, Kind.PISTOL: 0.045}
const DEPTH := {Kind.CLEANER: 0.0093, Kind.MANTIS: 0.0128, Kind.PISTOL: 0.009}
const WIDTH := {Kind.CLEANER: 0.0064, Kind.MANTIS: 0.0264, Kind.PISTOL: 0.008}
const HEIGHT := {Kind.CLEANER: 0.0147, Kind.MANTIS: 0.0235, Kind.PISTOL: 0.0134}
## How far everything reaches (antennae and claws included), metres from its origin at scale 1:
## x out to each side, y ahead (-Z), z behind (+Z). The pistol shrimp's big claw is what reaches
## furthest ahead of it; the mantis shrimp's antennules reach furthest ahead of it, and its punch
## brings its clubs to about 0.09 ahead at `strike` 1.
const REACH := {
	Kind.CLEANER: Vector3(0.0621, 0.0544, 0.09), Kind.MANTIS: Vector3(0.0351, 0.1282, 0.0745),
	Kind.PISTOL: Vector3(0.0281, 0.0355, 0.0225),
}
## How far a foot moves in one step at `walk` 1 (as each kind's shader settings have it), and how
## much of a step a foot is on the ground.
const STRIDE := {Kind.CLEANER: 0.0035, Kind.MANTIS: 0.005, Kind.PISTOL: 0.0026}
const ON_GROUND := 0.65
## What each kind sets in the shader: its build (as tools/build_shrimps.py has it), how it moves,
## its colours.
const KINDS := {
	Kind.CLEANER: {
		"kind": 0, "box_min": Vector3(-0.012, 0.0, -0.032), "box_max": Vector3(0.012, 0.024, 0.032),
		"legs_a_side": 5.0, "stride": 0.0035, "lift": 0.002,
		"curl_from": -0.0012, "curl_y": 0.0103, "curl_length": 0.0217, "curl_max": 2.7,
		"seg0": -0.0018, "seg_step": 0.0039, "feel": 0.3, "wave_up": 0.28, "swivel": 0.0,
		"shell": Color(0.82, 0.07, 0.06), "shell2": Color(0.98, 0.74, 0.3), "white": Color(0.97, 0.96, 0.93),
		"accent1": Color(0.92, 0.42, 0.36), "accent2": Color(0.98, 0.55, 0.12), "accent3": Color(0.12, 0.42, 0.9),
	},
	Kind.MANTIS: {
		"kind": 1, "box_min": Vector3(-0.03, 0.0, -0.09), "box_max": Vector3(0.03, 0.05, 0.09),
		"legs_a_side": 3.0, "stride": 0.005, "lift": 0.003,
		"curl_from": -0.012, "curl_y": 0.0148, "curl_length": 0.066, "curl_max": 2.4,
		"seg0": -0.0124, "seg_step": 0.0113, "feel": 0.12, "wave_up": 0.0, "swivel": 1.0,
		"shell": Color(0.16, 0.55, 0.2), "shell2": Color(0.62, 0.78, 0.3), "white": Color(0.97, 0.95, 0.9),
		"accent1": Color(0.93, 0.27, 0.2), "accent2": Color(1.0, 0.55, 0.1), "accent3": Color(0.1, 0.4, 0.95),
	},
	Kind.PISTOL: {
		"kind": 2, "box_min": Vector3(-0.014, 0.0, -0.045), "box_max": Vector3(0.014, 0.024, 0.025),
		"legs_a_side": 4.0, "stride": 0.0026, "lift": 0.0015,
		"curl_from": 0.0, "curl_y": 0.0089, "curl_length": 0.0155, "curl_max": 2.7,
		"seg0": -0.0004, "seg_step": 0.0031, "feel": 0.1, "wave_up": 0.0, "swivel": 0.0,
		"shell": Color(0.42, 0.4, 0.26), "shell2": Color(0.56, 0.48, 0.32), "white": Color(0.9, 0.88, 0.8),
		"accent1": Color(0.78, 0.4, 0.16), "accent2": Color(0.6, 0.5, 0.3), "accent3": Color(0.3, 0.35, 0.3),
	},
}
## Each kind's cartoon eye (`cartoon_eyes`): where its left eye is on its model and the way it
## looks (the build script's EYE lines), and its character:
## - the cleaner's: the eager helper: big and round, plenty of white, a warm red-orange iris and a
##   big soft pupil, the lid lifted high (wide awake, at your service);
## - the mantis shrimp's, the star: big and bright, no white at all, a turquoise-green eye all over
##   faceted in hexagons, a band of pink, yellow and violet across its middle, its dark
##   pseudopupil looking about over the facets: intense, alien, never blinking unless told to;
## - the pistol shrimp's: the little tough: small, half-lidded under its hood with a scowl that
##   slopes down to the front, an olive-gold iris round a small pupil.
const EYES := {
	Kind.CLEANER: {
		"eye_middle": Vector3(0.00286, 0.01251, -0.01908), "eye_gaze": Vector3(0.6027, 0.1507, -0.7836),
		"eye_grow": 1.6, "eye_white": Color(0.98, 0.97, 0.94), "eye_iris": Color(0.9, 0.32, 0.12),
		"iris_size": 0.55, "pupil_size": 0.33, "pupil_shape": Vector2(1.0, 1.0), "lid_rest": 1.08,
		"lid_slope": -0.12, "look_reach": 0.36, "eye_hex": 0.0,
	},
	Kind.MANTIS: {
		"eye_middle": Vector3(0.00632, 0.02627, -0.07325), "eye_gaze": Vector3(0.449, 0.2494, -0.858),
		"eye_grow": 1.45, "eye_white": Color(0.3, 0.85, 0.7), "eye_iris": Color(0.2, 0.85, 0.7),
		"iris_size": 1.0, "pupil_size": 0.25, "pupil_shape": Vector2(1.0, 1.0), "lid_rest": 1.1,
		"lid_slope": 0.0, "look_reach": 0.42, "eye_hex": 1.0,
	},
	Kind.PISTOL: {
		"eye_middle": Vector3(0.0024, 0.01003, -0.02003), "eye_gaze": Vector3(0.3505, 0.1001, -0.9312),
		"eye_grow": 1.8, "eye_white": Color(0.95, 0.93, 0.85), "eye_iris": Color(0.72, 0.62, 0.2),
		"iris_size": 0.5, "pupil_size": 0.2, "pupil_shape": Vector2(1.0, 1.0), "lid_rest": 0.32,
		"lid_slope": 0.35, "look_reach": 0.3, "eye_hex": 0.0,
	},
}

static var _meshes := {}

## Which shrimp it is: its model, its colours and how it moves.
@export var kind := Kind.CLEANER:
	set(value):
		kind = value
		_dress()
		_fit()
## Seconds one beat takes (used by `step` when it is not walking: swimming or standing).
@export var beat := 0.5
## How many times each leg steps and each swimmeret beats in a beat.
@export var steps := 1:
	set(value):
		steps = maxi(value, 0)
		_send_phase()
## Walking: 0 standing, 1 a walk forwards, -1 backwards; more is a longer stride.
@export_range(-2.0, 2.0) var walk := 0.0:
	set(value):
		walk = value
		_send(&"walk", value)
## How widely its swimmerets beat: 0 still, 1 swimming.
@export_range(0.0, 1.5) var paddle := 0.0:
	set(value):
		paddle = value
		_send(&"paddle", value)
## Its tail flick: 0 straight, 1 the abdomen and tail fan curled right down and under. (Curled,
## the tail reaches below its belly: lift it off the ground while it darts.)
@export_range(0.0, 1.0) var flick := 0.0:
	set(value):
		flick = clampf(value, 0.0, 1.0)
		_send(&"flick", flick)
## The mantis shrimp's punch: 0 its club arms folded under its head, 1 punched right out (the
## merus lifts, the forearm swings forward about its elbow, the club leading). A punch is 0 to 1
## and back in about a tenth of a second. Nothing on the others.
@export_range(0.0, 1.0) var strike := 0.0:
	set(value):
		strike = clampf(value, 0.0, 1.0)
		_send(&"strike", strike)
## The pistol shrimp's big claw: 0 shut, 1 its finger cocked wide open. Cock it slowly (0 to 1 in
## half a second), then snap: set 0 in one frame. Nothing on the others.
@export_range(0.0, 1.0) var snap := 0.0:
	set(value):
		snap = clampf(value, 0.0, 1.0)
		_send(&"snap", snap)
## How far its eyes swivel on their stalks, each on its own (the mantis shrimp's 1 to start with,
## the others' 0).
@export_range(0.0, 2.0) var swivel := 0.0:
	set(value):
		swivel = value
		_send(&"swivel", value)
## The low model (a few hundred triangles), for far off or for several of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about 900 triangles for the small two, 1,600 for the mantis shrimp, spent on
## the outline, the eyes, the claws) in place of the full one; `low` still shows the low model.
## Each model is loaded only when it is first shown: with `game` on, the full model is never loaded.
@export var game := false:
	set(value):
		game = value
		_show()
## 0 its eyes as they are; 1 cartoon eyes (bigger, a white, an iris, a pupil, a highlight and a
## lid, each kind its own: EYES).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where its cartoon eyes look, -1..1 each way: x towards its head (+) or its tail, y up or down.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(-Vector2.ONE, Vector2.ONE)
		_send(&"eye_look", eye_look)
## A blink: 0 open, 1 shut (a lid the colour of its shell comes down over each eye).
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## How far through a beat it is, 0 to 1 (only the fraction counts).
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D


## A kind's full model's mesh, or its low one's (each one surface, to wear `new_material(kind)`).
static func mesh_of(kind_wanted: Kind, low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % [NAMES[kind_wanted], "_lo" if low_wanted else ""], false)


## A kind's game model's mesh (one surface, to wear `new_material(kind)`), without the importer's
## automatic LODs (legs moved in the shader would move in straight pieces far off).
static func game_mesh(kind_wanted: Kind) -> Mesh:
	return _mesh_at(MODEL % [NAMES[kind_wanted], "_game"], true)


## A copy of `mesh` without its automatic LODs.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


static func _mesh_at(path: String, plain: bool) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh) if plain else found.mesh
		made.free()
	return _meshes[path]


## A new material for a kind's meshes, dressed as that kind. Its shader settings are the game's to
## set: `phase` (0..1 through one cycle of steps), `walk`, `paddle`, `flick`, `strike`, `snap`,
## `swivel`, `feel`, the eyes' and the colours (the top of the shader lists them).
static func new_material(kind_wanted: Kind) -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	_wear(made, kind_wanted)
	return made


static func _wear(on: ShaderMaterial, kind_wanted: Kind) -> void:
	var wears: Dictionary = KINDS[kind_wanted]
	for setting: String in wears:
		on.set_shader_parameter(setting, wears[setting])
	var eyes: Dictionary = EYES[kind_wanted]
	for setting: String in eyes:
		on.set_shader_parameter(setting, eyes[setting])
	on.set_shader_parameter(&"lid_colour", wears["shell"] if kind_wanted != Kind.PISTOL else wears["shell2"])


func _init() -> void:
	_material = new_material(kind)
	swivel = KINDS[kind]["swivel"]


func _ready() -> void:
	_show()
	_send_phase()
	for setting: StringName in [&"walk", &"paddle", &"flick", &"strike", &"snap", &"swivel", &"cartoon_eyes", &"eye_look", &"blink"]:
		_send(setting, get(setting))


## Each frame. Walking (`walk` not 0): moves `phase` on by how far it has gone forwards or
## backwards (`velocity` in the world's metres a second), so that its feet keep still on the
## ground, and points `walk` the way it is going (keeping its size). Not walking: moves `phase`
## on by delta / beat (its swimmerets beat, its antennae wave, its eyes swivel).
func step(velocity: Vector3, delta: float) -> void:
	if steps == 0:
		return
	if is_zero_approx(walk):
		phase += delta / maxf(beat, 0.01)
		return
	# (in its own metres: the basis's scale divides out)
	var speed := -(global_basis.inverse() * velocity).z
	if absf(speed) < 0.00005:
		return
	var amount := absf(walk)
	walk = amount * signf(speed)
	# (a foot moves STRIDE * amount while it is on the ground, which is ON_GROUND of a step)
	phase += absf(speed) * delta * ON_GROUND / (STRIDE[kind] * amount) / steps


## Sets one of the shader's settings: its colours (shell, shell2, white, accent1, accent2,
## accent3), `feel` (how far its antennae swing), `wave_up`, the cartoon eye's (eye_iris,
## iris_size, pupil_size, lid_rest...), or `walk`, `paddle`, `flick`, `strike`, `snap` for a
## game's own material. `kind` sets most of them again.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (all its models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one cycle of steps it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * steps, 1.0))


func _dress() -> void:
	if _material:
		_wear(_material, kind)
		swivel = KINDS[kind]["swivel"]


# Shows the model wanted, giving (and loading) each its mesh the first time it is wanted.
func _show() -> void:
	if not is_inside_tree():
		return
	if not _full:
		_full = _instance_of("Shrimp")
		_low = _instance_of("ShrimpLo")
		_game = _instance_of("ShrimpGame")
	_full.visible = not low and not game
	_low.visible = low
	_game.visible = game and not low
	_fit()


# (only the model shown is loaded; the others get theirs when they are first shown)
func _fit() -> void:
	if not _full:
		return
	_full.mesh = mesh_of(kind, false) if _full.visible else null
	_low.mesh = mesh_of(kind, true) if _low.visible else null
	_game.mesh = game_mesh(kind) if _game.visible else null


func _instance_of(named: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.material_override = _material
	# (its tail curls under, its arms punch out and its antennae swing past where the still model ends)
	mesh.extra_cull_margin = 0.06
	mesh.name = named
	add_child(mesh)
	return mesh
