class_name NeonTetra
extends Node3D
## A neon tetra (Paracheirodon innesi) or a cardinal tetra (Paracheirodon axelrodi), `type`:
##
## - NEON (the default): 0.035 m long. A slender little fish with an olive back, a glowing
##   blue-green stripe from the snout through the top of the eye back to the adipose fin, a red
##   band under the rear half of the stripe down to the belly, and a silver-white belly in front.
## - CARDINAL: 0.042 m long, a little deeper in the body: the same stripe, the red running the
##   whole length of the lower body from the head to the tail.
##
## Both have a big eye, a small dorsal fin just behind the middle, the small adipose fin, a long
## anal fin, a forked tail, clear fins. The stripe catches the light: it turns from blue to green
## as it is seen more glancing, shines a little of itself (`glow`) and is glossy. All of the
## markings are drawn by its shader (no texture files).
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down; its origin is on its
## middle line, half way along. `scale` it for a bigger one (a game where it is the player may
## well want it bigger than life). No sound.
##
## It swims as small characins do: a wave down the back half of the body, drawn by the shader (no
## bones). Its mouth opens: `gape` (and through the open mouth its gills show).
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat. Either
## call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or set `phase`
## yourself (for a picture that must loop: frame / frames in a beat). The same names and meanings
## as GameCommon's yellowfin tuna and sardine, so they are driven the same way.
##
## For a school of hundreds, do not make hundreds of these nodes: draw
## `NeonTetra.school_mesh(type)` with one MultiMesh (GameCommon's Flock takes it as its
## `custom_mesh`).
##
## The models are creatures/neon_tetra/models/<type>_tetra.glb (and _lo, _game and _school),
## built by tools/build_neon_tetra.py; neon_tetra.gdshader draws the markings and swims it. Only
## the models shown are ever loaded: with `game` (or `low`) set, the full model is never loaded.

enum Type { NEON, CARDINAL }

const MODEL := "res://creatures/neon_tetra/models/%s_tetra%s.glb"
const SHADER := preload("res://creatures/neon_tetra/neon_tetra.gdshader")
## As the neon's model is built (tools/build_neon_tetra.py): from the tip of its jaw to the tips
## of its tail, and how deep and how wide its body is at its deepest (metres, at scale 1).
## `LENGTHS`, `DEPTHS` and `WIDTHS` give each type's.
const LENGTH := 0.035
const DEPTH := 0.0081
const WIDTH := 0.0041
const LENGTHS := {Type.NEON: 0.035, Type.CARDINAL: 0.042}
const DEPTHS := {Type.NEON: 0.0081, Type.CARDINAL: 0.0104}
const WIDTHS := {Type.NEON: 0.0041, Type.CARDINAL: 0.0049}
## Each type's name in its model's file name.
const NAMES := {Type.NEON: "neon", Type.CARDINAL: "cardinal"}
## What each type sets in the shader (`iris_low`: the colour of the lower half of its cartoon
## eye's iris).
const TYPES := {
	Type.NEON: {"length_m": 0.035, "red_from": 0.43, "iris_low": Color(0.72, 0.74, 0.74)},
	Type.CARDINAL: {"length_m": 0.042, "red_from": 0.04, "iris_low": Color(0.78, 0.1, 0.07)},
}

## Which of the two it is.
@export var type := Type.NEON:
	set(value):
		type = value
		_dress()
## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 0.5
## How many times in a beat its tail beats (there and back).
@export var tail_beats := 3:
	set(value):
		tail_beats = maxi(value, 0)
		_send(&"tail_beats", float(tail_beats))
## How widely it beats: 1 cruising (its tail tips swing about a tenth of its length either way),
## 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far its mouth is open: 0 shut, 1 wide open (as when it bites). From about half open its
## gills show inside.
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## The low model (about a tenth of the triangles), for far off or for several of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (Twilight Princess weight: a few hundred triangles, spent on the outline, the
## eye, the mouth and the fins' edges) in place of the full one. Only the model shown is ever
## loaded, so a game that always has this (or `low`) set can leave the full model's .glb out of its
## export. `low` still shows the low model.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 the eye as it is in life, 1 a bigger cartoon eye (a wide bright stare: a
## white, a huge pupil, the iris lit blue-green along its top, a highlight, an outline).
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


## A type's full model's mesh, or its low one's (each one surface, to wear
## `new_material(type)`): for drawing one without this node.
static func mesh_of(low_wanted := false, which := Type.NEON) -> Mesh:
	return _mesh_at(MODEL % [NAMES[which], "_lo" if low_wanted else ""])


## A type's game model's mesh (one surface, to wear `new_material(type)`; loaded without Godot's
## automatic LODs, which would bend in straight pieces far off): for drawing a game model without
## this node.
static func game_mesh(which := Type.NEON) -> Mesh:
	return _mesh_at(MODEL % [NAMES[which], "_game"])


## A type's school model's mesh: a few hundred triangles, the same size and the same way round as
## the others (nose at -Z, up +Y, origin half way along), its look in its vertex colours (olive
## back, blue-green stripe, red band, silver belly, an eye each side). It has no UVs and does not
## wear this component's shader: it is for hundreds drawn by one MultiMesh whose shader reads
## COLOR (GameCommon's Flock: `custom_mesh`, body CUSTOM, motion SWIM, its colour white). Its fins
## are single sheets, so draw it from both sides.
static func school_mesh(which := Type.NEON) -> Mesh:
	return _mesh_at(MODEL % [NAMES[which], "_school"])


## A new material for a type's `mesh_of()` and `game_mesh()` meshes. Its shader settings are the
## game's to set: `phase` (0..1 through one beat), `tail_beats`, `sway`, `gape`, `curl`, `wave`,
## `glow`, `cartoon_eyes`, `eye_look`, `blink` and the colours (the top of the shader lists them).
static func new_material(which := Type.NEON) -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	for setting: String in TYPES[which]:
		made.set_shader_parameter(setting, TYPES[which][setting])
	return made


func _init() -> void:
	_material = new_material(type)


func _ready() -> void:
	_dress()
	_send(&"phase", phase)
	_send(&"tail_beats", float(tail_beats))
	_send(&"sway", sway)
	_send(&"gape", gape)
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
## body, in body lengths), `glow` (how brightly the stripe shines of itself), `stripe_to`,
## `red_from`, and the colours (`back`, `back_dark`, `stripe_blue`, `stripe_green`, `red`,
## `silver`, `belly`, `fin`, `mouth_inside`, `gill_red`, `gill_raker`, `iris_low`).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (a new type: its settings in the shader, and its models made again as they are shown)
func _dress() -> void:
	for setting: String in TYPES[type]:
		_material.set_shader_parameter(setting, TYPES[type][setting])
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
	mesh.name = "Tetra" + {"": "", "_lo": "Lo", "_game": "Game"}[which]
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
