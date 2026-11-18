class_name BlueTang
extends Node3D
## A regal blue tang (Paracanthurus hepatus), 0.25 m long: an oval disc flattened from side to
## side, royal blue, with the black "palette" marking (a band from the eye along the back to the
## tail's wrist, and a loop from it down round the flank and back, holding an oval of blue), a
## yellow triangle from the tail's wrist over the tail between thick black edges, yellow tips to
## its pectoral fins, dorsal and anal fins edged with black, and the pale "scalpel" spine on each
## side of the tail's wrist. Its small mouth opens (`gape`).
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z, its belly down; its origin is on its middle line half
## way along its length, so it reaches 0.125 m ahead and 0.125 m behind. `scale` it for a bigger
## or smaller one. No sound.
##
## It swims as surgeonfish do: it rows with its pectoral fins (`strokes` a beat), its body and tail
## swaying a little (`sway`; more for a dash), its dorsal and anal fins rippling. Everything that
## moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats `tail_beats` times
## and its pectorals row `strokes` times (whole numbers), so its motion comes round again exactly
## every beat. Either call `step(velocity, delta)` each frame, which moves `phase` on by
## delta / beat, or set `phase` yourself (for a picture that must loop: frame / frames in a beat).
##
## For a school of hundreds, do not make hundreds of these nodes: draw `BlueTang.school_mesh()`
## with one MultiMesh (GameCommon's Flock takes it as its `custom_mesh`).
##
## Three models besides the school one: the full one, the game one (`game`: about 1,720
## triangles, the outline kept, for games) and the low one (`low`). Each is loaded only when first
## shown, so a game that sets `game` never loads the full model.
##
## The models are creatures/blue_tang/models/blue_tang.glb (and _game, _lo, and _school), built by
## tools/build_blue_tang.py; blue_tang.gdshader draws the markings and swims it.

const MODEL := "res://creatures/blue_tang/models/blue_tang%s.glb"
const SHADER := preload("res://creatures/blue_tang/blue_tang.gdshader")
## As the model is built (tools/build_blue_tang.py): snout to tail tip, and how deep and how wide
## its body is at its deepest, without fins (metres, at scale 1).
const LENGTH := 0.25
const DEPTH := 0.0865
const WIDTH := 0.023

static var _meshes := {}

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
## The low model (about a sixteenth of the triangles), for far off, phones or many.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about 1,720 triangles, spent on the outline, the eye, the mouth and the fins'
## edges) in place of the full one: for games. With it set the full model is never loaded. `low`
## wins over it.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 the eye as it is in life, 1 big and cartoon-like: a friendly, eager
## eye, a little anxious, its brow raised towards its snout.
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


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`): for drawing
## a blue tang without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## The game model's mesh (one surface, to wear `new_material()`), for drawing a blue tang without this
## node: loaded once and kept, without the importer's thinned LOD meshes (the shader bends it, and
## a thinned one would bend in straight pieces far off).
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game", true)


## The same mesh without the importer's LOD meshes.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


## The school model's mesh: about 420 triangles, the same size and the same way round as the others
## (0.25 m long, nose at -Z, up +Y, origin half way along), its look in its vertex colours (the
## blue, the black palette, the yellow tail, the eyes; its mouth shut). It has no UVs and does not
## wear this component's shader: it is for hundreds drawn by one MultiMesh whose shader reads
## COLOR (GameCommon's Flock: `custom_mesh`, body CUSTOM, motion SWIM, its colour white). Its fins
## and eyes are single sheets, so draw it from both sides.
static func school_mesh() -> Mesh:
	return _mesh_at(MODEL % "_school")


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase`
## (0..1 through one beat), `tail_beats`, `strokes`, `sway`, `row`, `gape`, `curl` and the colours
## (the top of the shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_body = _instance_of()
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
## more than 0 the tail comes round to +X), `gape_angle`, `lip_lift`, the colours (blue, belly,
## black, yellow, fin_blue, fin_edge, spine_colour, eye_ring, mouth) and `sheen`.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_send(setting, value)


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


## (one mesh shown, loaded only now: a game that sets `game` never loads the full model)
func _show() -> void:
	if _body:
		if low:
			_body.mesh = mesh_of(true)
		elif game:
			_body.mesh = game_mesh()
		else:
			_body.mesh = mesh_of(false)


func _instance_of() -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.material_override = _material
	# (its tail and fins swing out past the still model's box)
	mesh.extra_cull_margin = LENGTH * 0.2
	mesh.name = "BlueTang"
	add_child(mesh)
	return mesh


static func _mesh_at(path: String, plain := false) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh) if plain else found.mesh
		made.free()
	return _meshes[path]
