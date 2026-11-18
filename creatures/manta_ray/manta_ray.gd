class_name MantaRay
extends Node3D
## A giant oceanic manta ray (Mobula birostris), 5 m across its wings: a broad black diamond
## with pale marks across its shoulders, white beneath with dark spots on its belly and five gill
## slits a side, a wide mouth across the front of its head between two cephalic fins (rolled up
## into horns, or unrolled into scoops when it feeds), and a short whip of a tail.
##
## How it looks and flies only: whatever moves it puts it where it is and turns it the way it
## goes. Its mouth points along its own -Z (Godot's forward), its belly down; its origin is on
## its middle line, half way along its body disc (the disc reaches 1.1 m ahead and behind; the
## horns 0.5 m further ahead, the tail 1.5 m further behind). `scale` it for a bigger or smaller
## one. No sound.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its wings beat
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat.
## Either call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or
## set `phase` yourself (for a picture that must loop: frame / frames in a beat). The same
## names as GameCommon's fish (`YellowfinTuna` and the rest), so that it is driven as they are:
## what is a tail beat there is a wing beat here.
##
## The model is creatures/manta_ray/models/manta_ray.glb (and _lo, _game), built by
## tools/build_manta_ray.py; manta_ray.gdshader draws its markings and moves it.

const MODEL := "res://creatures/manta_ray/models/manta_ray%s.glb"
const SHADER := preload("res://creatures/manta_ray/manta_ray.gdshader")
## As the model is built (tools/build_manta_ray.py), in metres at scale 1: from the tips of its
## unrolled cephalic fins to the tip of its tail; across its wing tips; how deep its body is.
## (WIDTH is SPAN: the name the fish have.)
const LENGTH := 4.13
const SPAN := 5.0
const DEPTH := 0.56
const WIDTH := SPAN
## How long its body disc is, from its mouth to the root of its tail (the origin is half way).
const DISC := 2.2
## How far ahead of its origin it reaches (its cephalic fins) and how far behind (its tail's tip).
const AHEAD := 1.53
const BEHIND := 2.6

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 3.2
## How many times in a beat its wings beat (up and down). The fish's name for it is kept.
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it beats: 1 cruising (its wing tips rise about 0.7 m and fall about 0.5 m), 0
## gliding with its wings held out.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far its mouth is open: 0 shut, 1 wide open, as it holds it when it feeds.
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## Its cephalic fins: 0 rolled up into horns (as when it cruises), 1 unrolled into scoops beside
## its mouth (as when it feeds).
@export_range(0.0, 1.0) var scoops := 0.0:
	set(value):
		scoops = clampf(value, 0.0, 1.0)
		_send(&"scoops", scoops)
## Banked into a turn: more than 0 it turns towards +X, less than 0 towards -X; about 1 is a tight
## turn. At `curl` c the whole animal is rolled 0.6 c radians about its long axis with its +X
## side down, the +X wing (inside the turn) droops a further 0.35 c radians by its tip and the
## other lifts as much, and the tail trails round to +X, c radians by its tip.
@export_range(-1.5, 1.5) var curl := 0.0:
	set(value):
		curl = value
		_send(&"curl", value)
## The low model (about a tenth of the triangles), for far off or for several of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (4,964 triangles; the full one has 46,644, the low one 4,874): built for games, its
## triangles spent on the outline, the eyes and the mouth. Shown in place of the full model;
## `low` still shows the low model. Each model is loaded only when it is first shown, so while
## `game` is set the full model is never loaded (a game's web export can leave its .glb out).
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 the eye as it is, 1 the cartoon one (bigger, a white, an iris, a pupil of
## its own, a highlight and a dark outline). On all three models.
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = value
		_send(&"cartoon_eyes", value)
## Where its eyes look, each axis -1 to 1: x towards its nose (+) or its tail (-), y up (+) or
## down (-), in each eye's own plane (the cartoon eye's pupil and iris slide that way).
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value
		_send(&"eye_look", value)
## 0 its eyes open, 1 shut: a lid of its skin's colour closes over each.
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = value
		_send(&"blink", value)
## How far its gill slits open for breathing, 0 shut (the default) to 1 wide: a flap of skin behind each
## of the five slits a side under its head lifts and the red of the gills shows. They open with `gape`
## too (as far as the wider of the two).
@export_range(0.0, 1.0) var gills := 0.0:
	set(value):
		gills = value
		_send(&"gills", value)
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set
## it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()

static var _meshes := {}

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D
var _ready_done := false


## The full model's mesh, or the low one's (to wear `new_material()`): for
## drawing a manta without this node.
## (The full model has two surfaces, the body and then its gills; give both the material, as
## `material_override` does. The low and game models have one.)
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## The game model's mesh (one surface, to wear `new_material()`), without the thinned LOD meshes
## Godot's importer adds (far off, a body bent in the shader would bend in straight pieces): for
## drawing them yourself. Loading it does not load the full model.
static func game_mesh() -> Mesh:
	var path := MODEL % "_game"
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh)
		made.free()
	return _meshes[path]


## `mesh` again, without its LOD meshes.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase`
## (0..1 through one beat of the wings), `sway`, `gape`, `scoops`, `curl` and the colours (the
## top of the shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_ready_done = true
	_show()
	_send(&"cartoon_eyes", cartoon_eyes)
	_send(&"eye_look", eye_look)
	_send(&"blink", blink)
	_send(&"gills", gills)
	_send_phase()
	_send(&"sway", sway)
	_send(&"gape", gape)
	_send(&"scoops", scoops)
	_send(&"curl", curl)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the fish's are; its beat here does not change
## with its speed: set `sway` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: its colours (`back`, `back_sheen`, `shoulder`, `belly`,
## `belly_dark`, `mouth_inside`), `shoulder_show` and `spots_show` (how strongly the pale
## shoulder marks and the belly's dark spots show).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one beat of the wings it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


func _show() -> void:
	if not _ready_done:
		return
	# (each model is loaded the first time it is shown)
	if low:
		if not _low:
			_low = _instance_of(mesh_of(true), true)
	elif game:
		if not _game:
			_game = _instance_of(game_mesh(), false, true)
	elif not _full:
		_full = _instance_of(mesh_of(false), false)
	var shown: MeshInstance3D = _low if low else _game if game else _full
	for each: MeshInstance3D in [_full, _low, _game]:
		if each:
			each.visible = each == shown


func _instance_of(model: Mesh, low_wanted: bool, game_wanted := false) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = model
	mesh.material_override = _material
	# (its wing tips rise and its tail swings well past where the still model ends)
	mesh.extra_cull_margin = SPAN * 0.5
	mesh.name = "MantaRayLo" if low_wanted else "MantaRayGame" if game_wanted else "MantaRay"
	add_child(mesh)
	return mesh


static func _mesh_at(path: String) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]
