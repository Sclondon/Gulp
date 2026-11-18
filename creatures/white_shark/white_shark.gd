class_name WhiteShark
extends Node3D
## A great white shark (Carcharodon carcharias), 4.8 m long: a heavy spindle with a conical snout,
## a black eye, five gill slits each side, a tall triangular first dorsal fin, long pectoral fins,
## a keeled tail wrist and a crescent tail; slate grey above, with a sharp ragged line to the white
## belly, the pectoral fins tipped black underneath.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down; its origin is on the
## line through the tip of its snout, half way along, so it reaches 2.4 m ahead and 2.4 m behind.
## `scale` it for a bigger or smaller one. No sound.
##
## It swims as sharks do: a wave down the whole rear of the body, the tail sweeping wide, drawn by
## the shader (no bones). Its mouth opens (`gape`): the lower jaw drops, the upper jaw pushes out
## and the rows of teeth show.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat. Either
## call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or set `phase`
## yourself (for a picture that must loop: frame / frames in a beat). The same names and meanings
## as GameCommon's yellowfin tuna and sardine, so they are driven the same way.
##
## The models are creatures/white_shark/models/white_shark.glb (and _lo, _game), built by
## tools/build_white_shark.py; white_shark.gdshader draws the markings, swims it and works its jaws.

const MODEL := "res://creatures/white_shark/models/white_shark%s.glb"
const SHADER := preload("res://creatures/white_shark/white_shark.gdshader")
## As the model is built (tools/build_white_shark.py): from the tip of its snout to the tip of its
## tail, and how deep and how wide its body is at its deepest, without fins (metres, at scale 1).
const LENGTH := 4.8
const DEPTH := 0.92
const WIDTH := 0.73
## How far the fins reach from its middle line: the dorsal's tip above, the tail's lower lobe below,
## the pectorals' tips to each side (metres, at scale 1, still).
const REACH_UP := 0.99
const REACH_DOWN := 0.83
const REACH_SIDE := 0.92

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 2.4
## How many times in a beat its tail beats (there and back).
@export var tail_beats := 2:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it beats: 1 a white shark cruising (its tail tip swings about 0.5 m either way), 0
## still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far its mouth is open: 0 shut, 1 wide open as when it bites (the lower jaw drops and the
## upper jaw pushes out and down, showing the teeth).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## The low model (about a sixteenth of the triangles), for far off or for several of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about a seventh of the full model's triangles, spent where they show: the
## outline, the eye, the mouth, the fins' edges) in place of the full one; `low` still shows the
## low model. Each model is loaded only when first shown: with `game` on from the start, the full
## model is never loaded (so a game's export can leave its .glb out).
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 the eye as it is, 1 a bigger cartoon eye (a white, an iris, a pupil, a
## highlight and a lid of its own character). On every model.
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where the cartoon eye looks, -1..1 each way: x towards its nose (+) or its tail (-), y up (+) or
## down (-), in the eye's own plane. Both eyes alike.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(Vector2(-1.0, -1.0), Vector2(1.0, 1.0))
		_send(&"eye_look", eye_look)
## The eyelids: 0 open, 1 shut (a lid the colour of its skin closes down over the eye).
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set it
## yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()

static var _meshes := {}

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`): for
## drawing a white shark without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## The game model's mesh (one surface, to wear `new_material()`), without the importer's
## automatic LODs (which the shader would bend in straight pieces far off).
static func game_mesh() -> Mesh:
	var path := MODEL % "_game"
	if not _meshes.has(path):
		var plain := ArrayMesh.new()
		var mesh := _mesh_at(path)
		for surface in mesh.get_surface_count():
			plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
		_meshes[path] = plain
	return _meshes[path]


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase`
## (0..1 through one beat of the tail), `sway`, `gape`, `curl`, `wave` and the colours (the top of
## the shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


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
## (`velocity` is taken so that it is called as the other fish's are; its beat here does not
## change with its speed: set `sway` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `curl` (bent round into a turn: radians from gills to tail,
## more than 0 the tail comes round to its left, +X), `wave` (the length of the wave along its
## body, in body lengths) and its colours (`back`, `belly`, `tip`, `mouth`, `tooth`).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one beat of the tail it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


# (each model is made, and its mesh loaded, only when it is first shown)
func _show() -> void:
	if not is_inside_tree():
		return
	if low and not _low:
		_low = _instance_of(mesh_of(true), "WhiteSharkLo")
	elif not low and game and not _game:
		_game = _instance_of(game_mesh(), "WhiteSharkGame")
	elif not low and not game and not _full:
		_full = _instance_of(mesh_of(false), "WhiteShark")
	if _full:
		_full.visible = not low and not game
	if _game:
		_game.visible = not low and game
	if _low:
		_low.visible = low


func _instance_of(mesh_wanted: Mesh, named: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = mesh_wanted
	mesh.material_override = _material
	# (its tail swings out past where the still model ends, and its jaw drops below it)
	mesh.extra_cull_margin = 0.8
	mesh.name = named
	add_child(mesh)
	return mesh


static func _mesh_at(path: String) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]
