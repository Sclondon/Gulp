class_name Spinosaurus
extends Node3D
## A spinosaurus (Spinosaurus aegyptiacus), 14 m long, as the reconstructions since 2020 show it: a
## river monster that swam. A long low crocodile's snout with a rosette of fangs at its tip and its
## nostrils set far back; a slender neck; a tall sail along its back from the shoulders to the hips,
## scalloped over its spines; a tall thin paddle of a tail (more than half its length); short hind
## legs with broad webbed feet; strong arms with three big hooked claws. Grey-green, banded dark across
## the back and tail, a pale belly, an ochre sail striped dark up each spine.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it goes.
## Its nose points along its own -Z, its belly down, its right side +X; its origin is on its middle
## line half way from the tip of its snout to the tip of its tail (7 m each way). `scale` it for a
## bigger or smaller one. No sound.
##
## It swims SIDE TO SIDE as a crocodile does (all drawn by the shader, no bones), its limbs tucked;
## `wade` stands it in the shallows on its hind legs, its arms reaching down, its neck lifted. `curl`
## bends it round into a turn; `gape` opens its jaws.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat. Either call
## `step(velocity, delta)` each frame, or set `phase` yourself. The same names and meanings as
## GameCommon's fish (the yellowfin tuna) and the mosasaur.
##
## The models are creatures/spinosaurus/models/spinosaurus.glb (the full model), _game.glb (the game
## model: about 5,200 triangles, the same outline) and _lo.glb (far off), built by
## tools/build_spinosaurus.py. Each is loaded only when it is first shown: with `game` on, the full
## model is never loaded, so a game can leave models/spinosaurus.glb out of its export.

const MODEL := "res://creatures/spinosaurus/models/spinosaurus%s.glb"
const SHADER := preload("res://creatures/spinosaurus/spinosaurus.gdshader")
## As the model is built: from the tip of its snout to the tip of its tail, and how deep and how wide
## its body is at its deepest (metres, at scale 1).
const LENGTH := 14.0
const DEPTH := 1.74
const WIDTH := 1.08
## How high the top of its sail stands over its middle line, and how far its tucked limbs reach below.
const SAIL_TOP := 2.19
## Wading (`wade` 1): how far below its origin the soles of its hind feet are (put the origin this far
## over the bottom to stand it there).
const WADE_FEET := 1.78

## Seconds one beat takes.
@export var beat := 3.2
## How many times in a beat its tail beats (a whole number).
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send(&"tail_beats", float(tail_beats))
## How hard it swims: 1 cruising (the tip of its tail swings about 1 m each way), 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far its mouth is open: 0 shut, 1 wide (its lower jaw drops 54 degrees, its skull lifts a little).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## Turning: radians from the neck to the tip of the tail (more than 0 its tail comes round to +X).
@export_range(-3.0, 3.0) var curl := 0.0:
	set(value):
		curl = value
		_send(&"curl", value)
## 0 swimming, its limbs tucked; 1 standing in the shallows on its hind legs (their soles WADE_FEET
## below its origin), its arms reaching down, its neck lifted; its swimming eases off as it stands.
@export_range(0.0, 1.0) var wade := 0.0:
	set(value):
		wade = clampf(value, 0.0, 1.0)
		_send(&"wade", wade)
## The game model in place of the full one (about 5,200 triangles against 44,800). Off by default.
@export var game := false:
	set(value):
		game = value
		_show()
## The low model (about 3,900 triangles), for far off. It wins over `game`.
@export var low := false:
	set(value):
		low = value
		_show()
## The cartoon eye: 0 the eye as it is, 1 a big cartoon eye of its own (sly and patient: an amber
## iris with a tall crocodile's pupil under a heavy hooding brow).
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
## `sway`, `gape`, `curl`, `wade`, `wave`, `cartoon_eyes`, `eye_look`, `blink` and the colours.
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_started = true
	_show()
	for setting: StringName in [&"sway", &"gape", &"curl", &"wade", &"phase", &"cartoon_eyes", &"eye_look", &"blink"]:
		_send(setting, get(setting))
	_send(&"tail_beats", float(tail_beats))


## Each frame: moves it on through its beat (`velocity` is taken so that it is called as the fish are).
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `wave` (the wave's length in body lengths), `bands` (how strongly
## its dark bands show) and the colours (`back`, `flank`, `belly`, `band`, `sail_colour`, `sail_stripe`,
## `claw`, `mouth`, `tooth`).
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
		_low = _instance_of(mesh_of(true), "SpinosaurusLo")
	elif not low and game and not _game:
		_game = _instance_of(game_mesh(), "SpinosaurusGame")
	elif not low and not game and not _full:
		_full = _instance_of(mesh_of(false), "Spinosaurus")
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
	# (its tail swings, its jaw drops and its legs come down past where the still model ends)
	mesh.extra_cull_margin = 3.0
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
