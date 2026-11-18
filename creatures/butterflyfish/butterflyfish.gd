class_name Butterflyfish
extends Node3D
## A butterflyfish of a coral reef, of one of five types (`type`), each a model of its own, all
## built 0.18 m long (`SIZE` is how long each really is beside that). Every one is a thin
## upright disc with a small beak of a mouth, one continuous spiny dorsal fin and a small
## square tail:
##
## - THREADFIN (Chaetodon auriga, the default): white in front with two sets of fine dark
##   lines that meet at right angles, yellow behind, a black bar through the eye, a black
##   spot on the soft dorsal fin and a thread trailing from it.
## - RACCOON (Chaetodon lunula): yellow-orange, dusky on the back, a black mask over the
##   eyes with a white band behind it, a black blotch on the wrist of the tail.
## - COPPERBAND (Chelmon rostratus): silver-white with upright copper-orange bands, a long
##   snout, a black false eye high on the last band.
## - LONGNOSE (Forcipiger flavissimus): bright yellow, the head black above and white below,
##   a very long thin snout, tall dorsal spines, a black spot at the rear of the anal fin.
## - BANNERFISH (Heniochus acuminatus, the pennant coralfish): white with two broad black
##   bands, yellow soft dorsal fin and tail, and a long white banner from its back.
##
## All of the markings are drawn by the shader: no texture files. Its nose points along its
## own -Z, its belly down; its origin is on its middle line, half way along its length.
##
## It hovers and paddles about by rowing with its pectoral fins, and steers with its tail:
## its body hardly bends. Its lower jaw works (`gape`: 0 shut, 1 wide open, as it pecks).
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`: in a beat its tail
## beats `tail_beats` times and its pectoral fins row `strokes` times (whole numbers), so
## its motion comes round again exactly every beat. Either call `step(velocity, delta)`
## each frame, which moves `phase` on by delta / beat (and swings its tail harder the faster
## it is going), or set `phase` yourself (for a picture that must loop: frame / frames in a
## beat; with `beat` 0, `step` leaves `phase` alone).
##
## A game that keeps its own MeshInstance3Ds needs no Butterflyfish node:
## `Butterflyfish.mesh_of(type, low)` is a type's mesh and `Butterflyfish.new_material(type)`
## a material for it, whose shader settings (phase, sway, row, gape, curl and the rest) the
## game sets itself.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way
## it goes. `scale` it for a bigger or smaller one. No sound.
##
## Three models of each type: the full one, the game one (`game`: a sixth of the triangles,
## the same outline) and the low one (`low`). `cartoon_eyes`, `eye_look` and `blink` give it a
## cartoon eye of its type's own character.
##
## The models are creatures/butterflyfish/models/butterflyfish_<type>.glb (and _game, _lo),
## built by tools/build_butterflyfish.py; its shader is butterflyfish.gdshader.

enum Type { THREADFIN, RACCOON, COPPERBAND, LONGNOSE, BANNERFISH }

const MODEL := "res://creatures/butterflyfish/models/butterflyfish_%s%s.glb"
const SHADER := preload("res://creatures/butterflyfish/butterflyfish.gdshader")
## As the models are built (tools/build_butterflyfish.py): snout to tail tip, every type; and
## the threadfin's body at its deepest and widest, fins not counted (metres, at scale 1).
## `REACH` has how far each type's fins go.
const LENGTH := 0.18
const DEPTH := 0.091
const WIDTH := 0.021
## Each type's name in its model's file name.
const NAMES := {
	Type.THREADFIN: "threadfin", Type.RACCOON: "raccoon", Type.COPPERBAND: "copperband",
	Type.LONGNOSE: "longnose", Type.BANNERFISH: "bannerfish",
}
## How long each type really is beside `LENGTH` (a usual grown fish: threadfin and raccoon
## 18 cm, copperband and longnose 16 cm, bannerfish 20 cm). Multiply `scale` by it for true
## sizes.
const SIZE := {
	Type.THREADFIN: 1.0, Type.RACCOON: 1.0, Type.COPPERBAND: 0.9, Type.LONGNOSE: 0.9, Type.BANNERFISH: 1.1,
}
## How far each type's still model reaches above and below its middle line, fins and all
## (metres, at scale 1): x is down (negative), y is up. Every type reaches 0.09 ahead and
## behind, and about 0.024 to each side (its pectoral fins; its body 0.011).
const REACH := {
	Type.THREADFIN: Vector2(-0.057, 0.062), Type.RACCOON: Vector2(-0.057, 0.058),
	Type.COPPERBAND: Vector2(-0.058, 0.06), Type.LONGNOSE: Vector2(-0.054, 0.059),
	Type.BANNERFISH: Vector2(-0.063, 0.131),
}
## What each type sets in the shader: which markings, and the places on its model the shader
## needs (as its model is built: the build script prints them).
## `eye_skin` is where the eye sits on the skin (x out, y up, how far along; the build script's
## SHAPE line); the rest is each type's cartoon eye (`cartoon_eyes`), its character: how much
## bigger than life (`eye_size`), the iris's colour and width (of the eye; the rest is white),
## the pupil's width (of the iris) and shape (0 round, 1 a bar across, 2 an upright slit, 3 a
## keyhole), where the upper lid rests (`lid`, in eye radii up from its middle: 1 or more none
## of it shows, 0 half shut) and how it slants (`lid_tilt`: more than 0 higher at the nose),
## and where the lower lid rests (-1 or less none of it shows). `throat`: the throat's ovals (how
## far along, the height of its middle, half height, half width; body lengths: the build script's
## THROAT_KNOTS line), for the shader to open the back of the mouth into it.
const TYPES := {
	Type.THREADFIN: {
		"throat": [
			Vector4(0.0300, -0.0324, 0.0110, 0.0071),
			Vector4(0.0529, -0.0385, 0.0130, 0.0107),
			Vector4(0.0993, -0.0456, 0.0130, 0.0131),
			Vector4(0.1625, -0.0532, 0.0130, 0.0131),
			Vector4(0.2400, -0.0624, 0.0130, 0.0131),
		],
		"kind": 0, "hinge_s": 0.045, "hinge_y": -0.033, "eye_at": Vector2(0.132, 0.04),
		"pec_root": Vector3(0.0495, -0.0725, 0.265), "eye_skin": Vector3(0.0393, 0.04, 0.132),
		# curious and wide awake: a big amber eye, round pupil, the lid just over its top
		"eye_size": 1.75, "iris": Color(0.95, 0.6, 0.12), "iris_size": 0.58, "pupil_size": 0.6,
		"pupil_shape": 0, "lid": 0.78, "lid_tilt": 0.0, "lower_lid": -1.2,
	},
	Type.RACCOON: {
		"throat": [
			Vector4(0.0250, -0.0291, 0.0120, 0.0067),
			Vector4(0.0479, -0.0359, 0.0134, 0.0114),
			Vector4(0.0943, -0.0437, 0.0134, 0.0138),
			Vector4(0.1575, -0.0513, 0.0134, 0.0138),
			Vector4(0.2350, -0.0606, 0.0134, 0.0138),
		],
		"kind": 1, "hinge_s": 0.04, "hinge_y": -0.031, "eye_at": Vector2(0.125, 0.05),
		"pec_root": Vector3(0.0512, -0.0725, 0.26), "eye_skin": Vector3(0.0397, 0.05, 0.125),
		# a sly bandit behind its mask: a red-orange eye half lidded over a narrowed lower lid,
		# a bar of a pupil
		"eye_size": 1.6, "iris": Color(0.92, 0.32, 0.06), "iris_size": 0.64, "pupil_size": 0.55,
		"pupil_shape": 1, "lid": 0.2, "lid_tilt": 0.18, "lower_lid": -0.7,
	},
	Type.COPPERBAND: {
		"throat": [
			Vector4(0.0190, -0.0266, 0.0047, 0.0036),
			Vector4(0.0479, -0.0295, 0.0062, 0.0052),
			Vector4(0.1067, -0.0385, 0.0062, 0.0065),
			Vector4(0.1869, -0.0481, 0.0062, 0.0065),
			Vector4(0.2850, -0.0599, 0.0062, 0.0065),
		],
		"kind": 2, "hinge_s": 0.034, "hinge_y": -0.0275, "eye_at": Vector2(0.185, 0.042),
		"pec_root": Vector3(0.05, -0.0725, 0.31), "eye_skin": Vector3(0.0372, 0.042, 0.185),
		# prim and unimpressed, looking down its long nose: a pale green-gold eye, a small pupil,
		# both lids lowered level
		"eye_size": 1.55, "iris": Color(0.7, 0.75, 0.35), "iris_size": 0.5, "pupil_size": 0.5,
		"pupil_shape": 0, "lid": 0.3, "lid_tilt": 0.0, "lower_lid": -0.85,
	},
	Type.LONGNOSE: {
		"throat": [
			Vector4(0.0170, -0.0241, 0.0019, 0.0014),
			Vector4(0.0505, -0.0242, 0.0038, 0.0035),
			Vector4(0.1186, -0.0277, 0.0041, 0.0049),
			Vector4(0.2114, -0.0476, 0.0041, 0.0049),
			Vector4(0.3250, -0.0612, 0.0041, 0.0049),
		],
		"kind": 3, "hinge_s": 0.032, "hinge_y": -0.025, "eye_at": Vector2(0.238, 0.034),
		"pec_root": Vector3(0.0474, -0.0675, 0.35), "eye_skin": Vector3(0.034, 0.034, 0.238),
		# startled: a big round stare, white all round a small yellow iris and a pinprick pupil,
		# no lid
		"eye_size": 1.85, "iris": Color(0.95, 0.82, 0.15), "iris_size": 0.42, "pupil_size": 0.48,
		"pupil_shape": 0, "lid": 1.3, "lid_tilt": 0.0, "lower_lid": -1.3,
	},
	Type.BANNERFISH: {
		"throat": [
			Vector4(0.0250, -0.0355, 0.0109, 0.0062),
			Vector4(0.0479, -0.0412, 0.0124, 0.0099),
			Vector4(0.0943, -0.0492, 0.0124, 0.0120),
			Vector4(0.1575, -0.0568, 0.0124, 0.0120),
			Vector4(0.2350, -0.0661, 0.0124, 0.0120),
		],
		"kind": 4, "hinge_s": 0.04, "hinge_y": -0.037, "eye_at": Vector2(0.128, 0.034),
		"pec_root": Vector3(0.0496, -0.0725, 0.26), "eye_skin": Vector3(0.0406, 0.034, 0.128),
		# gentle and a little wistful: a big soft dark-brown eye, a big pupil, the lid raised at
		# the nose
		"eye_size": 1.7, "iris": Color(0.4, 0.22, 0.1), "iris_size": 0.74, "pupil_size": 0.68,
		"pupil_shape": 0, "lid": 0.62, "lid_tilt": 0.22, "lower_lid": -1.2,
	},
}

static var _meshes := {}

## Which type it is: its shape and its markings.
@export var type := Type.THREADFIN:
	set(value):
		type = value
		_dress()
		_fit()
## Seconds one beat takes: everything it does comes round again each beat. 0 for a caller
## that sets `phase` itself (`step` then leaves `phase` alone).
@export var beat := 2.0
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
@export var top_speed := 0.9
## The low model (far off, phones, many at once) in place of the full one (or the game one).
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about 1,600 triangles, built to keep the full model's outline) in place of
## the full one (about 9,300). With `game` on, the full model is never loaded: each model is
## loaded only when it is first shown. `low` still shows the low model.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye (0 the eye as it is; 1 bigger, a white with a coloured iris, a big pupil, a
## highlight, a dark outline and a lid that gives each type its own character).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where the cartoon eyes look (-1..1 each way): x towards the nose (+) or the tail (-), y up
## (+) or down (-). Both eyes look the same way.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(Vector2(-1.0, -1.0), Vector2(1.0, 1.0))
		_send(&"eye_look", eye_look)
## The cartoon eyes' lids: 0 open, 1 shut (the lid comes down and the eye squashes).
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## How far through a beat it is, 0 to 1. `step` moves it on; or set it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D
var _effort := 0.25


## A type's mesh (the low one for fish far off, in numbers, on phones), for a game that
## keeps its own MeshInstance3Ds. Each is loaded once and kept.
static func mesh_of(type_wanted := Type.THREADFIN, low_wanted := false) -> Mesh:
	var path := MODEL % [NAMES[type_wanted], "_lo" if low_wanted else ""]
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]


## A type's game model (about 1,600 triangles, the full model's outline), for a game that
## keeps its own MeshInstance3Ds: loaded once and kept, without the importer's automatic LODs
## (thinned meshes bend in straight pieces in the shader). Loading it never loads the full one.
static func game_mesh(type_wanted := Type.THREADFIN) -> Mesh:
	var path := MODEL % [NAMES[type_wanted], "_game"]
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh)
		made.free()
	return _meshes[path]


## A mesh with the same surfaces and none of the importer's LODs.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


## A new material for a type's mesh, with that type's markings. Its shader settings are the
## game's to set: phase (0..1), tail_beats, strokes, sway, row, gape (0..1), curl, arch,
## flash, rim, tint (the top of the shader lists them).
static func new_material(type_wanted := Type.THREADFIN) -> ShaderMaterial:
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
	_game = _instance_of("Fish_game")
	_show()
	_send(&"cartoon_eyes", cartoon_eyes)
	_send(&"eye_look", eye_look)
	_send(&"blink", blink)
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
	_show()


# Only the model shown is given its mesh, so a model never shown is never loaded.
func _show() -> void:
	if not _full:
		return
	var shown := _low if low else (_game if game else _full)
	for each: MeshInstance3D in [_full, _low, _game]:
		each.visible = each == shown
	shown.mesh = mesh_of(type, true) if low else (game_mesh(type) if game else mesh_of(type, false))


func _instance_of(called: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.material_override = _material
	# (its fins row and its tail swings out past the still model's box)
	mesh.extra_cull_margin = LENGTH * 0.3
	mesh.name = called
	add_child(mesh)
	return mesh
