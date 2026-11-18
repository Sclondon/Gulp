class_name Krill
extends Node3D
## A Pacific krill (Euphausia pacifica), 0.03 m from the front of its eyes to the tip of its tail
## fan (a big one: scale it up for a game): a slender, clear pink, shrimp-like body speckled with
## red, two big round black eyes, long antennae, a basket of six pairs of feathery legs under its
## carapace and five pairs of swimmerets under its abdomen.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it
## goes. Its head points along its own -Z (Godot's forward), its back up; its origin is on its
## middle line half way along, so it reaches 0.015 m ahead (its antennae a little more) and 0.015
## m behind. `scale` it for a bigger or smaller one. No sound.
##
## Everything moves in the shader (no bones), on `phase`, 0 to 1 through one `beat`, in which its
## swimmerets beat `strokes` times (a whole number) and its feeding basket opens and closes once,
## so it comes round again exactly every beat. `sway` is how widely the swimmerets beat; `curl`
## flicks its abdomen and tail fan down and under (its backwards escape: drive it from 0 to 1 and
## back in a tenth of a second while you move it backwards). Either call `step(velocity, delta)`
## each frame, which moves `phase` on by delta / beat, or set `phase` yourself.
##
## For a swarm of hundreds, do not make hundreds of these nodes: draw `Krill.school_mesh()` with
## one MultiMesh (GameCommon's Flock takes it as its `custom_mesh`).
##
## The models are creatures/krill/models/krill.glb (and _lo, _game and _school), built by
## tools/build_krill.py; krill.gdshader draws the markings and moves it.

const MODEL := "res://creatures/krill/models/krill%s.glb"
const SHADER := preload("res://creatures/krill/krill.gdshader")
## As the model is built (tools/build_krill.py), metres at scale 1: from the front of its eyes to
## the tip of its tail fan, and how deep and how wide its carapace is.
const LENGTH := 0.03
const DEPTH := 0.0042
const WIDTH := 0.0031
## How far its antennae reach out to each side and ahead of its origin; how far below its middle
## line its basket of legs reaches.
const ANTENNA_REACH := Vector2(0.0165, 0.0217)
const BASKET_DEPTH := 0.0064

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 0.6
## How many times its swimmerets beat in a beat.
@export var strokes := 3:
	set(value):
		strokes = maxi(value, 0)
		_send(&"strokes", float(strokes))
## How widely its swimmerets beat: 1 swimming, 0 still.
@export_range(0.0, 1.5) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Its tail flick: 0 straight, 1 the abdomen and tail fan curled right down and under.
@export_range(0.0, 1.0) var curl := 0.0:
	set(value):
		curl = clampf(value, 0.0, 1.0)
		_send(&"curl", curl)
## The low model (about a sixth of the triangles), for far off or for several of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (far fewer triangles than the full one, spent where the eye looks: the
## outline, its big eyes, its basket), shown in place of the full one; `low` still shows the low
## model. Each model is loaded only when it is first shown: with `game` on, the full model is never
## loaded.
@export var game := false:
	set(value):
		game = value
		_show()
## 0 its eyes as they are; 1 cartoon eyes (huge glossy black beads, a thin ring of deep blue round
## a great round pupil, wide awake and wondering: see the README).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where its cartoon eyes look, -1..1 each way: x across each eye towards its head (+), y up.
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
		_send(&"phase", phase)

static var _meshes := {}

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`).
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## The game model's mesh (one surface, to wear `new_material()`), without the importer's automatic
## LODs (a body bent in the shader would bend in straight pieces far off).
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game", true)


## A copy of `mesh` without its automatic LODs.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


## The school model's mesh: 51 triangles, the same size and the same way round as the others
## (0.03 m long, head at -Z, up +Y, origin half way along), its look in its vertex colours (a pink
## body, deeper on the back, a black eye each side, its antennae, basket, swimmerets and tail fan
## as single pale sheets). It has no UVs and does not wear this component's shader: it is for
## hundreds drawn by one MultiMesh whose shader reads COLOR (GameCommon's Flock: `custom_mesh`,
## body CUSTOM, its colour white). Its sheets are single, so draw it from both sides.
static func school_mesh() -> Mesh:
	return _mesh_at(MODEL % "_school")


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase`
## (0..1 through one beat), `strokes`, `sway`, `curl`, `pump`, `feel` and the colours (the top of
## the shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_show()
	_send(&"cartoon_eyes", cartoon_eyes)
	_send(&"eye_look", eye_look)
	_send(&"blink", blink)
	_send(&"phase", phase)
	_send(&"strokes", float(strokes))
	_send(&"sway", sway)
	_send(&"curl", curl)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the other animals' are; set `sway` and `beat`
## from its speed yourself.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `pump` (how far its basket opens and closes), `feel` (how far
## its antennae swing), its colours (`pink`, `deep`, `red`), `spots_show`, `glassy` (how bright the
## rim is where light glances off it), or `sway`, `curl`,
## `cartoon_eyes`, `eye_look`, `blink` for a game's own material.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# Shows the model wanted, making (and loading) it the first time it is wanted.
func _show() -> void:
	if not is_inside_tree():
		return
	if low and not _low:
		_low = _instance_of(mesh_of(true), "KrillLo")
	elif not low and game and not _game:
		_game = _instance_of(game_mesh(), "KrillGame")
	elif not low and not game and not _full:
		_full = _instance_of(mesh_of(false), "Krill")
	for shown: MeshInstance3D in [_full, _low, _game]:
		if shown:
			shown.visible = shown == (_low if low else (_game if game else _full))


func _instance_of(mesh_wanted: Mesh, named: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = mesh_wanted
	mesh.material_override = _material
	# (its tail curls under and its limbs swing past where the still model ends)
	mesh.extra_cull_margin = 0.012
	mesh.name = named
	add_child(mesh)
	return mesh


static func _mesh_at(path: String, plain := false) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh) if plain else found.mesh
		made.free()
	return _meshes[path]
