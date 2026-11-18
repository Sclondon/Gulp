class_name Platy
extends Node3D
## A southern platy (Xiphophorus maculatus), 0.05 m long from the tip of its snout to the edge of its
## tail, in any of three colourings (`colouring`, the same model): SUNSET (the default: yellow-orange
## at the head running to red-orange at the tail, orange fins), RED_WAGTAIL (red-orange, its fins and
## lips black, its pectoral fins clear) or BLUE_MICKEY (silvery blue, clear fins, the "mickey mouse"
## mark on the root of its tail: a black spot and two small ones behind it). A short deep body
## flattened from side to side, a small upturned mouth, a big eye, a rounded dorsal fin and a broad
## rounded fan of a tail. Every marking is drawn by its shader: no texture files.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it goes.
## Its nose points along its own -Z (Godot's forward), its belly down; its origin is on its middle
## line, half way along, so it reaches 0.025 m ahead and 0.025 m behind. `scale` it for a bigger or
## smaller one. No sound.
##
## It swims by a wave down the back half of its body, drawn by the shader (no bones), the fan of its
## tail rippling a little. Its mouth opens: `gape`.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat. Either
## call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or set `phase`
## yourself (for a picture that must loop: frame / frames in a beat). The same names and meanings as
## GameCommon's yellowfin tuna and sardine, so they are driven the same way.
##
## The models are creatures/platy/models/platy.glb (and _lo, and _game), built by
## tools/build_platy.py; platy.gdshader draws the markings and swims it. Each model is loaded
## only when it is first shown: with `game` on, the full model is never loaded, so a game's web
## export can leave it out.

enum Colouring { SUNSET, RED_WAGTAIL, BLUE_MICKEY }

const MODEL := "res://creatures/platy/models/platy%s.glb"
const SHADER := preload("res://creatures/platy/platy.gdshader")
## As the model is built (tools/build_platy.py): from the tip of its snout to the edge of its tail,
## and how deep and how wide its body is at its deepest, without fins (metres, at scale 1).
const LENGTH := 0.05
const DEPTH := 0.0178
const WIDTH := 0.0076
## What each colouring sets in the shader.
const COLOURINGS := {
	Colouring.SUNSET: {
		"front": Color(0.98, 0.72, 0.16), "rear": Color(0.95, 0.36, 0.08), "back": Color(0.86, 0.32, 0.07),
		"belly": Color(0.99, 0.88, 0.55), "sheen": Color(1.0, 0.85, 0.5), "sheen_amount": 0.4,
		"fin": Color(0.98, 0.5, 0.14), "fin_black": 0.0, "lips_black": 0.0, "mickey": 0.0,
		"iris": Color(0.8, 0.62, 0.3),
	},
	Colouring.RED_WAGTAIL: {
		"front": Color(0.92, 0.26, 0.07), "rear": Color(0.88, 0.18, 0.05), "back": Color(0.72, 0.13, 0.04),
		"belly": Color(0.98, 0.62, 0.4), "sheen": Color(1.0, 0.6, 0.45), "sheen_amount": 0.35,
		"fin": Color(0.9, 0.3, 0.1), "fin_black": 1.0, "lips_black": 1.0, "mickey": 0.0,
		"iris": Color(0.75, 0.45, 0.25),
	},
	Colouring.BLUE_MICKEY: {
		"front": Color(0.66, 0.74, 0.84), "rear": Color(0.6, 0.7, 0.84), "back": Color(0.36, 0.46, 0.62),
		"belly": Color(0.94, 0.95, 0.96), "sheen": Color(0.55, 0.75, 1.0), "sheen_amount": 0.7,
		"fin": Color(0.78, 0.82, 0.86), "fin_black": 0.0, "lips_black": 0.0, "mickey": 1.0,
		"iris": Color(0.72, 0.68, 0.55),
	},
}

## Its colours (the same shape).
@export var colouring := Colouring.SUNSET:
	set(value):
		colouring = value
		_dress()
## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 0.8
## How many times in a beat its tail beats (there and back).
@export var tail_beats := 3:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it beats: 1 a platy swimming along, 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far its mouth is open: 0 shut, 1 wide open (as when it picks at food).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## The low model (about a twelfth of the triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about 860 triangles, spent on the outline, the eye, the mouth and the fins'
## edges) in place of the full one; `low` still shows the low model. With it on the full model is
## never loaded.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 the eye as it was (the default), 1 the cartoon eye (bigger, a white,
## a big iris filling most of the eye, a big pupil, two big soft highlights: sweet, gentle
## and doe-eyed). Gulp sets it to 1.
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
## a platy without this node. Loaded once and kept, without the importer's automatic LODs (made from
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


## A new material for `mesh_of()`'s meshes, in a colouring. Its shader settings are the game's to
## set: `phase` (0..1 through one beat of the tail), `sway`, `gape`, `curl`, `billow`, `wave` and the
## colours (the top of the shader lists them).
static func new_material(colouring_wanted := Colouring.SUNSET) -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	_wear(made, colouring_wanted)
	return made


## The same mesh with no LODs: each surface's arrays alone.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


func _init() -> void:
	_material = new_material(colouring)


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
## more than 0 the tail comes round to its left, +X), `billow`, `wave`, or a colour or amount
## (`front`, `rear`, `back`, `belly`, `sheen`, `sheen_amount`, `scales_show`, `fin`, `fin_black`,
## `lips_black`, `mickey`, `black`, `iris`, `mouth_inside`,
## the cartoon eye's `eye_grow`, `eye_white`, `iris_size`, `pupil_size`, `lid`, `lid_slant`, the gills'
## `gill_red`, `gill_raker`). `colouring` sets most of them again.
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


static func _wear(on: ShaderMaterial, colouring_wanted: Colouring) -> void:
	var colours: Dictionary = COLOURINGS[colouring_wanted]
	for setting: String in colours:
		on.set_shader_parameter(setting, colours[setting])


func _dress() -> void:
	if _material:
		_wear(_material, colouring)


func _show() -> void:
	if not is_inside_tree():
		return
	# (each model is made only when it is first shown)
	if low:
		if _low == null:
			_low = _instance_of("PlatyLo", mesh_of(true))
	elif game:
		if _game == null:
			_game = _instance_of("PlatyGame", game_mesh())
	elif _full == null:
		_full = _instance_of("Platy", mesh_of(false))
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
	mesh.extra_cull_margin = 0.012
	mesh.name = named
	add_child(mesh)
	return mesh
