class_name HorseshoeCrab
extends Node3D
## An Atlantic horseshoe crab (Limulus polyphemus), 0.5 m from the front of its shell to the tip
## of its tail spike: a smooth olive-brown domed front shell, horseshoe-shaped, with a ridge down
## its middle and one each side, a kidney-shaped eye on the outside of each side ridge; a hinged
## rear shell with six spines along each side; a long rigid tail spike; five pairs of legs and five
## book gills underneath, paler.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it
## faces. Its head points along its own -Z (Godot's forward), its back up; ITS ORIGIN IS ON THE
## GROUND under its middle (half way from the front of its shell to the tip of its tail spike,
## which is near the back of the rear shell), so put it where the sea floor is. `scale` it for a
## bigger or smaller one. No sound.
##
## Everything moves in the shader (no bones), on `phase`, 0 to 1 through one cycle of `steps`
## steps: `walk` strides its legs (+ forwards), `gills` flaps its book gills, `swing` swings its tail
## spike. Either call `step(velocity, delta)` each frame, which moves `phase` on by how far it has
## walked (so its feet do not slide) or, standing, by `beat`, or set `phase` yourself.
##
## The models are creatures/horseshoe_crab/models/horseshoe_crab.glb (and _lo, and _game), built by
## tools/build_horseshoe_crab.py; horseshoe_crab.gdshader draws the markings and moves it.

const MODEL := "res://creatures/horseshoe_crab/models/horseshoe_crab%s.glb"
const SHADER := preload("res://creatures/horseshoe_crab/horseshoe_crab.gdshader")
## As the model is built (tools/build_horseshoe_crab.py), metres at scale 1: from the front of its
## shell to the tip of its tail spike; how deep its front shell is (from its rim to the top of its
## dome) and how wide.
const LENGTH := 0.5
const DEPTH := 0.066
const WIDTH := 0.251
## How high the top of its shell stands above the ground; how high its rim is; how long its tail
## spike is.
const HEIGHT := 0.082
const RIM := 0.012
const TAIL := 0.244
## How far a foot moves in one step at `walk` 1 (as the shader has it), and how much of a step a
## foot is on the ground.
const STRIDE := 0.016
const ON_GROUND := 0.65

## Seconds one cycle takes when it is not walking (its gills and tail spike keep moving).
@export var beat := 2.0
## How many steps each leg takes in a cycle.
@export var steps := 1:
	set(value):
		steps = maxi(value, 0)
		_send_phase()
## Walking: 0 standing, 1 a walk forwards, -1 backwards; more is a longer stride.
@export_range(-2.0, 2.0) var walk := 0.0:
	set(value):
		walk = value
		_send(&"walk", value)
## How widely its book gills flap: 0 still, 1 breathing hard.
@export_range(0.0, 1.5) var gills := 0.4:
	set(value):
		gills = value
		_send(&"gills", value)
## How far its tail spike swings from side to side and lifts: 0 still, 1 a lot.
@export_range(0.0, 2.0) var swing := 0.5:
	set(value):
		swing = value
		_send(&"swing", value)
## The low model (about a ninth of the triangles), for far off or for several of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (far fewer triangles than the full one, spent where the eye looks: the shells'
## outline and the flare of the rim, the eyes, the tail spike), shown in place of the full one;
## `low` still shows the low model. Each model is loaded only when it is first shown: with `game`
## on, the full model is never loaded.
@export var game := false:
	set(value):
		game = value
		_show()
## 0 its eyes as they are; 1 cartoon eyes (bigger glossy eyes half asleep under heavy lids, an
## olive-amber iris, a slit pupil: see the README).
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
## How far through a cycle it is, 0 to 1 (only the fraction counts).
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()

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


static func _mesh_at(path: String, plain := false) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh) if plain else found.mesh
		made.free()
	return _meshes[path]


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase`
## (0..1 through one cycle of steps), `walk`, `gills`, `swing`, `hinge` and the colours (the top of
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
	_send_phase()
	_send(&"walk", walk)
	_send(&"gills", gills)
	_send(&"swing", swing)


## Each frame. Walking (`walk` not 0): moves `phase` on by how far it has gone forwards or
## backwards (`velocity` in the world's metres a second), so that its feet keep still on the
## ground, and points `walk` the way it is going (keeping its size). Not walking: moves `phase`
## on by delta / beat (its gills flap, its tail spike swings).
func step(velocity: Vector3, delta: float) -> void:
	if steps == 0:
		return
	if is_zero_approx(walk):
		phase += delta / maxf(beat, 0.01)
		return
	var speed := -(global_basis.inverse() * velocity).z
	if absf(speed) < 0.0002:
		return
	var size := absf(walk)
	walk = size * signf(speed)
	# (a foot moves STRIDE * size * scale while it is on the ground, which is ON_GROUND of a step)
	var grown := global_basis.get_scale().z
	phase += absf(speed) * delta * ON_GROUND / (STRIDE * size * grown) / steps


## Sets one of the shader's settings: `hinge` (the rear shell bent on its hinge, radians: more than
## 0 down), its colours (`olive`, `mottle`, `underside`, `legs`, `eye`), or `walk`, `gills`, `swing`,
## `cartoon_eyes`, `eye_look`, `blink` for a game's own material.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one cycle of steps it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * steps, 1.0))


# Shows the model wanted, making (and loading) it the first time it is wanted.
func _show() -> void:
	if not is_inside_tree():
		return
	if low and not _low:
		_low = _instance_of(mesh_of(true), "HorseshoeCrabLo")
	elif not low and game and not _game:
		_game = _instance_of(game_mesh(), "HorseshoeCrabGame")
	elif not low and not game and not _full:
		_full = _instance_of(mesh_of(false), "HorseshoeCrab")
	for shown: MeshInstance3D in [_full, _low, _game]:
		if shown:
			shown.visible = shown == (_low if low else (_game if game else _full))


func _instance_of(mesh_wanted: Mesh, named: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = mesh_wanted
	mesh.material_override = _material
	# (its tail spike swings and its rear shell bends past where the still model ends)
	mesh.extra_cull_margin = 0.06
	mesh.name = named
	add_child(mesh)
	return mesh
