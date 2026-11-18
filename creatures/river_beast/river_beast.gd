class_name RiverBeast
extends Node3D
## The river beast: a creature of our own, as big as a big bear, 3.93 m from the tip of its snout to
## the tip of its tail, 2.6 m tall standing. A caiman's head (broad flat snout, raised nostrils, eyes
## raised on top under bony brows, teeth showing along the lips) on a heavy bear's body in wet matted
## brown fur, shaggy in clumps (a ruff round the neck and shoulders); scaly hands and feet with big
## dark claws; a broad flat scaly tail like a long beaver's.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it goes.
## Its nose points along its own -Z, its belly down, its right side +X; its origin is on its middle line
## half way from the tip of its snout to the tip of its tail as it lies swimming (1.965 m each way).
## `scale` it for a bigger or smaller one. No sound.
##
## It swims at the surface as a beaver or an otter does: its broad tail sculls side to side and its
## hind feet kick by turns, its forelimbs tucked under its chest. `stand` (0..1) stands it up on its
## hind legs on a bank or in the shallows: the body turns up about the hips, the head comes back to
## level, the arms hang bent in front of the chest, the tail lies along the ground behind. Standing,
## its soles are STAND_FEET below its origin and the top of its head STAND_TOP above it. All drawn by
## the shader (hinges on per-point pivots, no bones). `curl` bends it round into a turn as it swims;
## `gape` opens its jaws.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail sculls and its
## feet kick `tail_beats` times (a whole number), so its motion comes round again exactly every beat.
## Either call `step(velocity, delta)` each frame, or set `phase` yourself. The same names and meanings
## as GameCommon's fish (the yellowfin tuna) and the sea otter.
##
## The models are creatures/river_beast/models/river_beast.glb (the full model), _game.glb (the game
## model: about 3,300 triangles, the same outline) and _lo.glb (far off), built by
## tools/build_river_beast.py. Each is loaded only when it is first shown: with `game` on, the full
## model is never loaded, so a game can leave models/river_beast.glb out of its export.

const MODEL := "res://creatures/river_beast/models/river_beast%s.glb"
const SHADER := preload("res://creatures/river_beast/river_beast.gdshader")
## As the model is built (swimming): from the tip of its snout to the tip of its tail, and how deep
## and how wide its body is at its deepest, without its fur (metres, at scale 1).
const LENGTH := 3.93
const DEPTH := 0.98
const WIDTH := 0.88
## Standing (`stand` 1): how far below its origin the soles of its feet are (put the origin this far
## over the ground to stand it there), and how far above its origin the top of its head is.
const STAND_FEET := 1.0
const STAND_TOP := 1.6

## Seconds one beat takes.
@export var beat := 1.8
## How many times in a beat its tail sculls and its feet kick (a whole number).
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send(&"tail_beats", float(tail_beats))
## How hard it swims: 1 cruising (the tip of its tail swings about 0.22 m each way, its feet kick), 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far its mouth is open: 0 shut, 1 wide (its lower jaw drops 49 degrees, its skull lifts a little).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## Turning as it swims: radians from the neck to the tip of the tail (more than 0 its tail comes round
## to +X). It fades out as it stands.
@export_range(-3.0, 3.0) var curl := 0.0:
	set(value):
		curl = value
		_send(&"curl", value)
## 0 swimming along the surface, 1 standing on its hind legs (between, it rears up).
@export_range(0.0, 1.0) var stand := 0.0:
	set(value):
		stand = clampf(value, 0.0, 1.0)
		_send(&"stand", stand)
## The game model in place of the full one (about 3,300 triangles against 55,000). Off by default.
@export var game := false:
	set(value):
		game = value
		_show()
## The low model (about 2,700 triangles), for far off. It wins over `game`.
@export var low := false:
	set(value):
		low = value
		_show()
## The cartoon eye: 0 the eye as it is, 1 a big cartoon eye of its own (a wary old grouch: a
## green-gold iris and a fat slit under heavy, low lids).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where the cartoon eyes look, -1..1 each way (x towards the snout, y up).
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(Vector2(-1.0, -1.0), Vector2(1.0, 1.0))
		_send(&"eye_look", eye_look)
## A blink: 0 open, 1 shut.
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## How far through a beat it is, 0 to 1. `step` moves it on; or set it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)

static var _meshes := {}

var _material: ShaderMaterial
var _full: MeshInstance3D
var _game: MeshInstance3D
var _low: MeshInstance3D
var _started := false


## The full model's mesh, or the low one's (one surface each, to wear `new_material()`).
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""), false)


## The game model's mesh (one surface), without the thinned LOD meshes Godot's importer adds (the
## shader bends it, and a thinned mesh would bend in straight pieces). Loads only the game model.
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game", true)


## A new material for these meshes. Its shader settings are the game's to set: `phase`, `tail_beats`,
## `sway`, `gape`, `curl`, `stand`, `wave`, `wet`, `cartoon_eyes`, `eye_look`, `blink` and the colours.
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_started = true
	_show()
	for setting: StringName in [&"sway", &"gape", &"curl", &"stand", &"phase", &"cartoon_eyes", &"eye_look", &"blink"]:
		_send(setting, get(setting))
	_send(&"tail_beats", float(tail_beats))


## Each frame: moves it on through its beat (`velocity` is taken so that it is called as the fish are).
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `wave` (the length of the wave down its tail, in body lengths),
## `wet` (0 a dry dull coat, 1 slick with water) and the colours (`fur_root`, `fur`, `fur_tip`,
## `scale_top`, `scale_under`, `claw`, `mouth`, `tooth`).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


func _show() -> void:
	if not _started:
		return
	if low and not _low:
		_low = _instance_of(mesh_of(true), "RiverBeastLo")
	elif not low and game and not _game:
		_game = _instance_of(game_mesh(), "RiverBeastGame")
	elif not low and not game and not _full:
		_full = _instance_of(mesh_of(false), "RiverBeast")
	if _full:
		_full.visible = not low and not game
	if _game:
		_game.visible = not low and game
	if _low:
		_low.visible = low


func _instance_of(made: Mesh, named: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = made
	mesh.material_override = _material
	# (standing, it rears 1.6 m over its origin and its feet go 1 m below; its jaw drops)
	mesh.extra_cull_margin = 1.8
	mesh.name = named
	add_child(mesh)
	return mesh


static func _mesh_at(path: String, plain: bool) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		var mesh: Mesh = found.mesh
		if plain:
			var bare := ArrayMesh.new()
			for surface in mesh.get_surface_count():
				bare.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
			mesh = bare
		_meshes[path] = mesh
		made.free()
	return _meshes[path]
