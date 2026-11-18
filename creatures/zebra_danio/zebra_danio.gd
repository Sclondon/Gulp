class_name ZebraDanio
extends Node3D
## A zebra danio (Danio rerio), 0.045 m long: a slim torpedo, gold-silver, with five steel-blue stripes
## running from behind its gill cover to the tip of its tail, an olive back, a silver-white belly, a
## big eye, two tiny barbels at the corners of its small upturned mouth, a small dorsal fin set well
## back over a long low striped anal fin, and a forked tail whose middle rays carry the stripes on.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it goes.
## Its nose points along its own -Z (Godot's forward), its belly down; its origin is on its middle
## line, half way along, so it reaches 0.0225 m ahead and 0.0225 m behind. `scale` it for a bigger or
## smaller one. No sound.
##
## It swims as small minnows do: a quick wave down the back half of the body, drawn by the shader (no
## bones). Its mouth opens: `gape`.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat. Either
## call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or set `phase`
## yourself (for a picture that must loop: frame / frames in a beat). The same names and meanings as
## GameCommon's yellowfin tuna and sardine, so they are driven the same way.
##
## For a school of hundreds, do not make hundreds of these nodes: draw `ZebraDanio.school_mesh()`
## with one MultiMesh (GameCommon's Flock takes it as its `custom_mesh`).
##
## The models are creatures/zebra_danio/models/zebra_danio.glb (and _lo, _game and _school), built
## by tools/build_zebra_danio.py; zebra_danio.gdshader draws the markings and swims it. Each model is
## loaded only when it is first shown: with `game` on, the full model is never loaded, so a game's
## web export can leave it out.

const MODEL := "res://creatures/zebra_danio/models/zebra_danio%s.glb"
const SHADER := preload("res://creatures/zebra_danio/zebra_danio.gdshader")
## As the model is built (tools/build_zebra_danio.py): from the tip of its snout to the tips of its
## tail, and how deep and how wide its body is at its deepest, without fins (metres, at scale 1).
const LENGTH := 0.045
const DEPTH := 0.0094
const WIDTH := 0.0052

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 0.6
## How many times in a beat its tail beats (there and back).
@export var tail_beats := 4:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it beats: 1 a danio cruising, 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far its mouth is open: 0 shut, 1 wide open (as when it snaps up food).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## The low model (about a tenth of the triangles), for far off or for several of them.
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
## The cartoon eye: 0 the eye as it was (the default), 1 the cartoon eye (bigger, a white, a pale
## gold iris ringed in steel blue, a round pupil, a highlight, the lid sloping down to the back: a
## keen, quick, slightly jumpy look). Gulp sets it to 1.
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
## a danio without this node. Loaded once and kept, without the importer's automatic LODs (made from
## the still model, they would bend in straight pieces far off).
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## The game model's mesh (one surface, to wear `new_material()`), for a game that draws meshes
## itself. Loaded once and kept, without the importer's automatic LODs.
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game")


## The school model's mesh: about 350 triangles, the same size and the same way round as the others
## (0.045 m long, nose at -Z, up +Y, origin half way along), its look in its vertex colours (olive
## back, five blue stripes over gold from behind the head, silver belly, an eye each side). It has no
## UVs and does not wear this component's shader: it is for hundreds drawn by one MultiMesh whose
## shader reads COLOR (GameCommon's Flock: `custom_mesh`, body CUSTOM, motion SWIM, its colour
## white). Its fins are single sheets, so draw it from both sides.
static func school_mesh() -> Mesh:
	return _mesh_at(MODEL % "_school")


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase` (0..1
## through one beat of the tail), `sway`, `gape`, `curl`, `wave` and the colours (the top of the
## shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


## The same mesh with no LODs: each surface's arrays alone.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


func _init() -> void:
	_material = new_material()


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
## more than 0 the tail comes round to its left, +X), `wave`, or a colour (`back`, `gold`, `stripe`,
## `stripe_glint`, `belly`, `fin`, `fin_white`, `mouth_inside`, the cartoon eye's `eye_grow`, `eye_white`,
## `eye_iris`, `eye_iris_ring`, `iris_size`, `pupil_size`, `lid`, `lid_slant`, the gills' `gill_red`,
## `gill_raker`).
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


func _show() -> void:
	if not is_inside_tree():
		return
	# (each model is made only when it is first shown)
	if low:
		if _low == null:
			_low = _instance_of("ZebraDanioLo", mesh_of(true))
	elif game:
		if _game == null:
			_game = _instance_of("ZebraDanioGame", game_mesh())
	elif _full == null:
		_full = _instance_of("ZebraDanio", mesh_of(false))
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


static func _mesh_at(path: String) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh)
		made.free()
	return _meshes[path]
