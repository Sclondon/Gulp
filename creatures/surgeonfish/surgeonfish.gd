class_name Surgeonfish
extends Node3D
## A surgeonfish, 0.25 m long, of one of three kinds (`kind`), each a model of its own:
##
## - YELLOW_TANG (Zebrasoma flavescens, the default): all lemon yellow; a tall disc with a long
##   pointed snout and a small mouth at its end; very tall, sail-like dorsal and anal fins; the
##   white "scalpel" spine on each side of the tail's wrist.
## - POWDER_BLUE (Acanthurus leucosternon): an oval disc, powder blue, with a black face, a white
##   band from the chin to the belly, a yellow dorsal fin, white anal and pelvic fins, a white tail
##   with a black band across it, and yellow round the spine.
## - CONVICT (Acanthurus triostegus): the same oval, pale grey-green with a white belly and six
##   narrow black bars (the first through the eye, the last short, on the tail's wrist).
##
## All have small mouths that open (`gape`), eyes, the spine on each side of the tail's wrist, long
## dorsal and anal fins, a tail and a pair each of pectoral and pelvic fins. Every marking is drawn
## by its shader: no texture files. `set_shader_parameter` reaches every colour.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z, its belly down; its origin is on its middle line half
## way along its length. `scale` it for a bigger or smaller one. No sound.
##
## It swims as surgeonfish do: it rows with its pectoral fins (`strokes` a beat), its body and tail
## swaying a little (`sway`; more for a dash), its dorsal and anal fins rippling. Everything that
## moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats `tail_beats` times
## and its pectorals row `strokes` times (whole numbers), so its motion comes round again exactly
## every beat. Either call `step(velocity, delta)` each frame, which moves `phase` on by
## delta / beat, or set `phase` yourself (for a picture that must loop: frame / frames in a beat).
##
## A game that keeps its own MeshInstance3Ds needs no Surgeonfish node:
## `Surgeonfish.mesh_of(kind, low)` (or `game_mesh(kind)`) is a kind's mesh and
## `Surgeonfish.new_material(kind)` a material for it.
##
## Three models of each kind: the full one, the game one (`game`: about 1,740 triangles, the
## outline kept, for games) and the low one (`low`). Each is loaded only when first shown, so a
## game that sets `game` never loads the full model.
##
## The models are creatures/surgeonfish/models/surgeonfish_<kind>.glb (and _game, _lo), built by
## tools/build_surgeonfish.py; its shader is surgeonfish.gdshader.

enum Kind { YELLOW_TANG, POWDER_BLUE, CONVICT }

const MODEL := "res://creatures/surgeonfish/models/surgeonfish_%s%s.glb"
const SHADER := preload("res://creatures/surgeonfish/surgeonfish.gdshader")
## As the models are built (tools/build_surgeonfish.py): snout to tail tip, every kind; how deep
## and how wide the body is at its deepest, without fins (the yellow tang's; the others are a
## little less deep: see `KINDS`) (metres, at scale 1).
const LENGTH := 0.25
const DEPTH := 0.112
const WIDTH := 0.0215
## Each kind's name in its model's file name.
const NAMES := {Kind.YELLOW_TANG: "yellow_tang", Kind.POWDER_BLUE: "powder_blue", Kind.CONVICT: "convict"}
## What each kind sets in the shader: where its jaw hinges, its gill cover ends and its eye is (as
## its model is built: the build script prints them), which markings, and its colours. And its
## cartoon eye (`cartoon_eyes`), each with a character of its own: the yellow tang's big, round
## and wide open, all innocence; the powder blue's gold and half-lidded under its black face, cool
## and aloof; the convict's small and beady under a lid that slopes down to the snout, a shifty
## scowl from behind its bars.
const KINDS := {
	Kind.YELLOW_TANG: {
		"eye_centre": Vector3(0.00414, 0.01771, -0.08687), "eye_grow": 1.6, "eye_white": Color(0.98, 0.97, 0.9),
		"iris": Color(0.42, 0.24, 0.06), "iris_size": 0.56, "pupil_size": Vector2(0.32, 0.32),
		"lid": Color(0.98, 0.78, 0.04), "lid_low": 0.0, "lid_slant": 0.0,
		"depth": 0.112, "hinge_s": 0.05, "hinge_y": -0.007, "gill_s": 0.245, "eye_s": 0.15, "pattern": 0.0,
		"body_back": Color(0.98, 0.78, 0.04), "body_side": Color(1.0, 0.86, 0.1), "body_belly": Color(1.0, 0.9, 0.3),
		"face": Color(1.0, 0.86, 0.1), "throat": Color(1.0, 0.9, 0.3), "marks": Color(0.03, 0.03, 0.04),
		"fin_dorsal": Color(1.0, 0.82, 0.06), "fin_anal": Color(1.0, 0.82, 0.06), "fin_tail": Color(1.0, 0.84, 0.08),
		"fin_pectoral": Color(1.0, 0.9, 0.36), "fin_edge": Color(1.0, 0.74, 0.04), "spine_colour": Color(0.97, 0.97, 0.94),
		"eye_ring": Color(0.32, 0.26, 0.1),
	},
	Kind.POWDER_BLUE: {
		"eye_centre": Vector3(0.00474, 0.01762, -0.09068), "eye_grow": 1.45, "eye_white": Color(0.9, 0.94, 1.0),
		"iris": Color(0.95, 0.7, 0.12), "iris_size": 0.5, "pupil_size": Vector2(0.24, 0.3),
		"lid": Color(0.04, 0.04, 0.06), "lid_low": 0.3, "lid_slant": 0.0,
		"depth": 0.0955, "hinge_s": 0.04, "hinge_y": -0.007, "gill_s": 0.235, "eye_s": 0.135, "pattern": 1.0,
		"body_back": Color(0.3, 0.58, 0.88), "body_side": Color(0.42, 0.7, 0.95), "body_belly": Color(0.6, 0.8, 0.96),
		"face": Color(0.04, 0.04, 0.06), "throat": Color(0.96, 0.97, 0.98), "marks": Color(0.04, 0.04, 0.06),
		"fin_dorsal": Color(1.0, 0.86, 0.1), "fin_anal": Color(0.95, 0.96, 0.97), "fin_tail": Color(0.94, 0.95, 0.96),
		"fin_pectoral": Color(0.9, 0.9, 0.7), "fin_edge": Color(0.36, 0.62, 0.9), "spine_colour": Color(1.0, 0.86, 0.1),
		"eye_ring": Color(0.12, 0.12, 0.16),
	},
	Kind.CONVICT: {
		"eye_centre": Vector3(0.00458, 0.0176, -0.09066), "eye_grow": 1.4, "eye_white": Color(0.95, 0.95, 0.86),
		"iris": Color(0.5, 0.58, 0.3), "iris_size": 0.42, "pupil_size": Vector2(0.17, 0.17),
		"lid": Color(0.04, 0.04, 0.05), "lid_low": 0.22, "lid_slant": -0.45,
		"depth": 0.0955, "hinge_s": 0.04, "hinge_y": -0.007, "gill_s": 0.235, "eye_s": 0.135, "pattern": 2.0,
		"body_back": Color(0.7, 0.75, 0.62), "body_side": Color(0.84, 0.87, 0.78), "body_belly": Color(0.96, 0.96, 0.92),
		"face": Color(0.84, 0.87, 0.78), "throat": Color(0.96, 0.96, 0.92), "marks": Color(0.04, 0.04, 0.05),
		"fin_dorsal": Color(0.84, 0.84, 0.7), "fin_anal": Color(0.9, 0.9, 0.8), "fin_tail": Color(0.84, 0.86, 0.74),
		"fin_pectoral": Color(0.9, 0.9, 0.82), "fin_edge": Color(0.74, 0.74, 0.6), "spine_colour": Color(0.9, 0.9, 0.86),
		"eye_ring": Color(0.42, 0.38, 0.22),
	},
}

static var _meshes := {}

## Which kind of surgeonfish: its shape and its colours.
@export var kind := Kind.YELLOW_TANG:
	set(value):
		kind = value
		_dress()
		_fit()
## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 1.2
## How many times in a beat its tail beats, and its pectoral fins row (whole numbers).
@export var tail_beats := 2:
	set(value):
		tail_beats = maxi(value, 0)
		_send(&"tail_beats", float(tail_beats))
@export var strokes := 3:
	set(value):
		strokes = maxi(value, 0)
		_send(&"strokes", float(strokes))
## How widely its body and tail sway: 1 its tail's tip a tenth of its length each way (a dash),
## 0.35 cruising on its pectorals, 0 still.
@export_range(0.0, 2.0) var sway := 0.35:
	set(value):
		sway = value
		_send(&"sway", value)
## How hard its pectoral fins row: 1 cruising, 0 still.
@export_range(0.0, 2.0) var row := 1.0:
	set(value):
		row = value
		_send(&"row", value)
## How far its mouth is open: 0 shut, 1 wide open (as when it bites).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## The low model (about a sixteenth of the triangles), for far off, phones or many. It wins over
## `game`.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about 1,740 triangles, an eighth of the full one's, spent on the outline, the eye,
## the mouth and the fins' edges) in place of the full one: for games. With it set the full model
## is never loaded.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 the eye as it is in life, 1 big and cartoon-like, each kind's own (`KINDS`).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where its eyes look: x towards its snout (less than 0 back), y up, each -1..1 (the cartoon eye's
## iris and pupil slide that way).
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(Vector2(-1.0, -1.0), Vector2(1.0, 1.0))
		_send(&"eye_look", eye_look)
## A blink: 0 open, 1 shut (the eye squashes flat and the lid comes down over it).
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set it
## yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)

var _material: ShaderMaterial
var _body: MeshInstance3D


## A kind's full or low mesh (one surface, to wear `new_material(kind)`), for a game that draws
## its own. Each is loaded once and kept.
static func mesh_of(kind_wanted: Kind = Kind.YELLOW_TANG, low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % [NAMES[kind_wanted], "_lo" if low_wanted else ""], false)


## A kind's game mesh (one surface, to wear `new_material(kind)`), for a game that draws its own:
## loaded once and kept, without the importer's thinned LOD meshes (the shader bends it, and a
## thinned one would bend in straight pieces far off).
static func game_mesh(kind_wanted: Kind = Kind.YELLOW_TANG) -> Mesh:
	return _mesh_at(MODEL % [NAMES[kind_wanted], "_game"], true)


## The same mesh without the importer's LOD meshes.
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


## A new material for a kind's meshes, dressed in its colours. Its shader settings are the game's to
## set: phase (0..1), tail_beats, strokes, sway, row, gape, curl and the colours (the top of the
## shader lists them).
static func new_material(kind_wanted: Kind = Kind.YELLOW_TANG) -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	_wear(made, kind_wanted)
	return made


func _init() -> void:
	_material = new_material(kind)


func _ready() -> void:
	_body = _instance_of("Surgeonfish")
	_show()
	for setting: StringName in [&"tail_beats", &"strokes"]:
		_send(setting, float(get(setting)))
	for setting: StringName in [&"sway", &"row", &"gape", &"phase", &"cartoon_eyes", &"eye_look", &"blink"]:
		_send(setting, get(setting))


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the other fish's are; set `sway`, `row` and `beat`
## from its speed yourself.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `curl` (bent round into a turn: radians from gills to tail,
## more than 0 the tail comes round to +X), `gape_angle`, `lip_lift`, the colours (body_back,
## body_side, body_belly, face, throat, marks, fin_dorsal, fin_anal, fin_tail, fin_pectoral,
## fin_edge, spine_colour, eye_ring, mouth) and `sheen`. `kind` sets the colours again.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_send(setting, value)


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


static func _wear(on: ShaderMaterial, kind_wanted: Kind) -> void:
	var wears: Dictionary = KINDS[kind_wanted]
	for setting: String in wears:
		if setting != "depth":
			on.set_shader_parameter(setting, wears[setting])


func _dress() -> void:
	if _material:
		_wear(_material, kind)


func _fit() -> void:
	_show()


## (one mesh shown, loaded only now: a game that sets `game` never loads the full model)
func _show() -> void:
	if _body:
		if low:
			_body.mesh = mesh_of(kind, true)
		elif game:
			_body.mesh = game_mesh(kind)
		else:
			_body.mesh = mesh_of(kind, false)


func _instance_of(called: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.material_override = _material
	# (its tail and fins swing out past the still model's box)
	mesh.extra_cull_margin = LENGTH * 0.2
	mesh.name = called
	add_child(mesh)
	return mesh
