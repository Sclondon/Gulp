class_name Corydoras
extends Node3D
## A cory catfish, 0.06 m long from the tip of its snout to the tips of its tail, as either kind
## (`kind`: the same model, its own colours): BRONZE (Corydoras aeneus, the default: bronze plates with
## a green-gold sheen, a pale belly) or PANDA (C. panda: pale pinkish cream, a black mask down over
## each eye, a black patch on the dorsal fin and its root, a black spot on the root of the tail).
##
## A stubby armoured body, its back arched high and its belly flat, two rows of overlapping bony
## plates down each flank, a blunt snout with a down-turned mouth underneath and two pairs of short
## barbels at its corners, eyes high on the head, a tall triangular dorsal fin, a small adipose fin,
## a forked tail, big pectoral fins spread from the corners of the belly. Every marking is drawn by its
## shader: no texture files.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it goes
## (shuffling along the bottom, darting up for air: that is the game's to do). Its nose points along
## its own -Z (Godot's forward), its belly down; its origin is on its middle line, half way along, so
## it reaches 0.03 m ahead and 0.03 m behind, and its flat belly is BELLY (0.0081 m) below the origin:
## to rest it on the ground, put its origin that far above it. `scale` it for a bigger or smaller one.
## No sound.
##
## It swims by a wave down the back half of its body, drawn by the shader (no bones). Its mouth opens:
## `gape`.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat. Either
## call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or set `phase`
## yourself (for a picture that must loop: frame / frames in a beat). The same names and meanings as
## GameCommon's yellowfin tuna and sardine, so they are driven the same way.
##
## The models are creatures/corydoras/models/corydoras.glb (and _lo, and _game), built by
## tools/build_corydoras.py; corydoras.gdshader draws the markings and swims it. Each model is loaded
## only when it is first shown: with `game` on, the full model is never loaded, so a game's web
## export can leave it out.

enum Kind { BRONZE, PANDA }

const MODEL := "res://creatures/corydoras/models/corydoras%s.glb"
const SHADER := preload("res://creatures/corydoras/corydoras.gdshader")
## As the model is built (tools/build_corydoras.py): from the tip of its snout to the tips of its
## tail, how deep and how wide its body is at its deepest, without fins (metres, at scale 1), and how
## far below its origin its flat belly is.
const LENGTH := 0.06
const DEPTH := 0.0183
const WIDTH := 0.0136
const BELLY := 0.0081
## What each kind sets in the shader.
const KINDS := {
	Kind.BRONZE: {
		"body": Color(0.58, 0.43, 0.22), "back": Color(0.4, 0.31, 0.15), "belly": Color(0.9, 0.8, 0.66),
		"sheen": Color(0.2, 0.5, 0.36), "sheen_amount": 0.9, "mask_amount": 0.0, "saddle_amount": 0.0,
		"tail_spot_amount": 0.0, "plates_show": 0.6, "fin": Color(0.66, 0.62, 0.52),
		"fin_edge": Color(0.84, 0.82, 0.76), "barbel_colour": Color(0.78, 0.7, 0.55), "iris": Color(0.7, 0.55, 0.25),
	},
	Kind.PANDA: {
		"body": Color(0.94, 0.88, 0.82), "back": Color(0.86, 0.8, 0.74), "belly": Color(0.97, 0.94, 0.9),
		"sheen": Color(0.98, 0.9, 0.85), "sheen_amount": 0.4, "mask_amount": 1.0, "saddle_amount": 1.0,
		"tail_spot_amount": 1.0, "plates_show": 0.35, "fin": Color(0.88, 0.86, 0.82),
		"fin_edge": Color(0.95, 0.94, 0.92), "barbel_colour": Color(0.92, 0.86, 0.8), "iris": Color(0.55, 0.5, 0.42),
	},
}

## Which kind: its colours (the same shape).
@export var kind := Kind.BRONZE:
	set(value):
		kind = value
		_dress()
## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 0.8
## How many times in a beat its tail beats (there and back).
@export var tail_beats := 3:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it beats: 1 a cory swimming along, 0 still (resting on the bottom).
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far its mouth is open: 0 shut, 1 wide open (as when it grubs in the sand).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## The low model (about a fourteenth of the triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about 850 triangles, spent on the outline, the eye, the mouth and the fins'
## edges) in place of the full one; `low` still shows the low model. With it on the full model is
## never loaded.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 the eye as it was (the default), 1 the cartoon eye (bigger, a white,
## a big soft dark pupil in its bronze iris, the lid half down: a friendly, contented,
## slightly sleepy look). Gulp sets it to 1.
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = value
		_send(&"cartoon_eyes", value)
## Where the cartoon eye looks, -1..1 each way: x towards its nose (+) or tail, y up (+) or down.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value
		_send(&"eye_look", value)
## 0 open, 1 shut: the eye squashes flat (a fish has no lids) and a lid the colour of its head
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

static var _meshes := {}

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`): for drawing
## a cory without this node. Loaded once and kept, without the importer's automatic LODs (made from
## the still model, they would bend in straight pieces far off).
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## The game model's mesh (one surface, to wear `new_material()`), for a game that draws meshes
## itself. Loaded once and kept, without the importer's automatic LODs.
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game")


static func _mesh_at(path: String) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh)
		made.free()
	return _meshes[path]


## A new material for `mesh_of()`'s meshes, in a kind's colours. Its shader settings are the game's
## to set: `phase` (0..1 through one beat of the tail), `sway`, `gape`, `curl`, `wave` and the colours
## (the top of the shader lists them).
static func new_material(kind_wanted := Kind.BRONZE) -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	_wear(made, kind_wanted)
	return made


## The same mesh with no LODs: each surface's arrays alone.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


func _init() -> void:
	_material = new_material(kind)


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
## more than 0 the tail comes round to its left, +X), `wave`, or a colour or amount (`body`, `back`,
## `belly`, `sheen`, `sheen_amount`, `mark`, `mask_amount`, `saddle_amount`, `tail_spot_amount`,
## `plates_show`, `fin`, `fin_edge`, `barbel_colour`, `iris`, `mouth_inside`,
## the cartoon eye's `eye_grow`, `eye_white`, `iris_size`, `pupil_size`, `lid`, `lid_slant`, the gills'
## `gill_red`, `gill_raker`). `kind` sets most of
## them again.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_send(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one beat of the tail it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


static func _wear(on: ShaderMaterial, kind_wanted: Kind) -> void:
	var colours: Dictionary = KINDS[kind_wanted]
	for setting: String in colours:
		on.set_shader_parameter(setting, colours[setting])


func _dress() -> void:
	if _material:
		_wear(_material, kind)


func _show() -> void:
	if not is_inside_tree():
		return
	# (each model is made only when it is first shown)
	if low:
		if _low == null:
			_low = _instance_of("CorydorasLo", mesh_of(true))
	elif game:
		if _game == null:
			_game = _instance_of("CorydorasGame", game_mesh())
	elif _full == null:
		_full = _instance_of("Corydoras", mesh_of(false))
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
	# (its tail swings out past where the still model ends)
	mesh.extra_cull_margin = 0.015
	mesh.name = named
	add_child(mesh)
	return mesh
