class_name OldOne
extends Node3D
## The old one: a vast original sea monster in the spirit of the cosmic-horror "old one" (not any published
## depiction), asleep on the floor of a deep basin, about 45 m across as it lies (50 m from wing tip to wing tip).
## A great bulbous head tilted back over its body, a ring of ten small pale glowing eyes round the top of its face,
## fourteen thick tentacles spilling forward from its face across the floor and curling at their ends, two huge
## folded membranous wings like collapsed sails rising to a clawed wrist high over its head and hanging to the
## floor, a low half-buried body behind, weed growing on its crown, body and wings, and glowing freckles.
##
## How it looks and moves only (no thinking, no sound). Its face points along its own -Z (Godot's forward), up is
## +Y. Its origin is ON THE FLOOR under the middle of where it lies (it reaches 18.4 m ahead of it and 21.8 m behind,
## 25.2 m to each side, 30 m up to the claws on its wrists): stand it on the floor (it sinks into it a metre or so, as if half buried, so a
## floor up to a metre lower or higher under its edges hides nothing). `scale` it for a bigger or smaller one.
##
## It sleeps: its head swells and settles with each slow breath, its wings rise and fall a little, its tentacles
## drift like ropes in the water, the weed on it sways, its eyes are glowing slits. `wake` stirs it, 0 asleep to 1:
## its eyes open one by one and brighten, its tentacles lift off the floor and writhe wider, its wings part and lift
## and its hands spread, its head rises, its freckles glow brighter. All of it is drawn by the shader (no bones).
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat` (one breath), so its motion comes round again
## exactly every beat. Either call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or
## set `phase` yourself.
##
## The models are creatures/old_one/models/old_one.glb (full), _game and _lo, built by tools/build_old_one.py;
## old_one.gdshader draws its markings and moves it.

const MODEL := "res://creatures/old_one/models/old_one%s.glb"
const SHADER := preload("res://creatures/old_one/old_one.gdshader")
## As the model is built (metres, at scale 1): from the tips of its tentacles ahead to the back of its body
## (the curls of its tentacles reach 18.4 m ahead of its origin), from wing tip to wing tip, and how high its
## wrists' claws stand.
const LENGTH := 40.2
const WIDTH := 50.5
const HEIGHT := 30.0

## Seconds one breath takes: everything it does comes round again each beat.
@export var beat := 14.0
## Asleep (0) to stirring (1).
@export_range(0.0, 1.0) var wake := 0.0:
	set(value):
		wake = clampf(value, 0.0, 1.0)
		_send(&"wake", wake)
## How deeply it breathes (1 as built, 0 still).
@export_range(0.0, 2.0) var breathe := 1.0:
	set(value):
		breathe = value
		_send(&"breathe", value)
## How far its tentacles drift (1 as built, 0 still).
@export_range(0.0, 2.0) var drift := 1.0:
	set(value):
		drift = value
		_send(&"drift", value)
## The low model (about 2,200 triangles), for far off.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model: about 6,800 triangles, Twilight Princess boss weight, shown in place of the full one (`low`
## still shows the low one). Each model is loaded only when it is first shown, so with `game` on (set before it
## enters the tree) the full model is never loaded and a web export can leave it out.
@export var game := false:
	set(value):
		game = value
		_show()
## Its eyes: 0 plain glowing eyes, 1 cartoon eyes with a character (an ancient sleeper: a thin dark slit of a
## pupil in each pale glowing eye, a dark rim, a glint, heavy lids).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where its cartoon eyes look, each in its own plane: x across (+ to its right), y up (-1..1).
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(Vector2(-1.0, -1.0), Vector2(1.0, 1.0))
		_send(&"eye_look", eye_look)
## Its lids: 0 as `wake` has them (slits asleep, open awake), 1 shut.
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## How far through a breath it is, 0 to 1 (only the fraction counts). `step` moves it on; or set it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)

static var _meshes := {}

var _material: ShaderMaterial
var _shown := {}
var _started := false


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`).
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at("_lo" if low_wanted else "")


## The game model's mesh (one surface, to wear `new_material()`), without the importer's automatic LODs.
static func game_mesh() -> Mesh:
	return _mesh_at("_game")


## A mesh rebuilt from its surfaces alone, without the importer's automatic LODs (a body moved in its shader
## would move in straight pieces far off).
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


static func _mesh_at(ending: String) -> Mesh:
	var path := MODEL % ending
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh)
		made.free()
	return _meshes[path]


## A new material for these meshes. Its shader settings are the game's to set: `phase`, `wake`, `breathe`,
## `drift`, `cartoon_eyes`, `eye_look`, `blink`, `glow` and the colours (the top of the shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_started = true
	_show()
	for setting: StringName in [&"phase", &"wake", &"breathe", &"drift", &"cartoon_eyes", &"eye_look", &"blink"]:
		_send(setting, get(setting))


## Each frame, for one that is not having its `phase` set for it: moves it on through its breath. (`velocity` is
## taken so that it is called as the fish are; it does not go anywhere.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: its colours (`dark`, `skin`, `pale`, `silt`, `wing_skin`, `vein`, `bone`,
## `weed`, `glow_colour`, `eye_colour`) and `glow` (how strongly its freckles glow).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (all its models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


func _show() -> void:
	if not _started:
		return
	var wanted := "_lo" if low else ("_game" if game else "")
	if not _shown.has(wanted):
		_shown[wanted] = _instance_of(wanted)
	for ending: String in _shown:
		(_shown[ending] as MeshInstance3D).visible = ending == wanted


func _instance_of(ending: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = _mesh_at(ending)
	mesh.material_override = _material
	# (stirring, its tentacles lift and its wings part past where the still model ends)
	mesh.extra_cull_margin = 8.0
	mesh.name = "OldOne" + ending
	add_child(mesh)
	return mesh
