class_name BatRay
extends Node3D
## A bat ray (Myliobatis californica), 1.2 m across its wings and 1.4 m from its nose to the tip
## of its tail: a raised blunt head with an eye on each of its sides, two long pointed wings
## that it flaps like a bird, a whip of a tail with a small dorsal fin and a sting at its root,
## dark brown-olive above and white beneath. Its mouth is underneath.
##
## How it looks and flies only: whatever moves it puts it where it is and turns it the way it
## goes (bank it into its turns yourself). Its nose points along its own -Z (Godot's forward),
## its back is up. Its origin is on its middle line, half way from its nose to its tail's tip
## and half way up its height: so the origin is where the disc ends and the tail begins, the
## nose 0.7 m ahead of it and the middle of the disc `DISC_MIDDLE` (0.35 m) ahead of it. Its
## underside is `UNDER` (0.0713 m) below the origin. `scale` it for a bigger or smaller one. No
## sound.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its wings beat
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat.
## Either call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or
## set `phase` yourself (for a picture that must loop: frame / frames in a beat). The same
## names and meanings as GameCommon's yellowfin tuna.
##
## The model is creatures/bat_ray/models/bat_ray.glb (and _lo, _game), built by tools/build_bat_ray.py
## with its wings held out flat; bat_ray.gdshader draws its markings and flaps it.

const MODEL := "res://creatures/bat_ray/models/bat_ray%s.glb"
const SHADER := preload("res://creatures/bat_ray/bat_ray.gdshader")
## As the model is built (tools/build_bat_ray.py), metres at scale 1: from its nose to the tip of
## its tail; from wing tip to wing tip; how tall it is at its head (belly to the top of its
## back); and `WIDTH`, the same as `SPAN` (so that it can be asked what every fish is asked).
const LENGTH := 1.4
const SPAN := 1.2
const DEPTH := 0.143
const WIDTH := SPAN
## How long the disc is (nose to the root of the tail), and how far ahead of the origin its
## middle is.
const DISC_LENGTH := 0.7
const DISC_MIDDLE := 0.35
## How far its underside is below its origin.
const UNDER := 0.0713

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 1.8
## How many times in a beat its wings beat (down and up).
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely its wings beat: 1 a bat ray cruising (its wing tips rise about 0.3 m and fall
## about 0.23 m), 0 gliding with them held flat.
@export_range(0.0, 1.6) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Its mouth (underneath): 0 shut, 1 wide open.
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = value
		_send(&"gape", value)
## The low model (about a fifteenth of the triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (2,980 triangles; the full one has 46,604, the low one 3,360): built for games, its
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


## The mesh of the full model, or of the low one: for drawing bat rays yourself (a MultiMesh, a
## MeshInstance3D of your own) with `new_material()`. Give what draws it room for the wings'
## beat (`extra_cull_margin` 0.4).
## (The full model has two surfaces, the body and then its gills; give both the material, as
## `material_override` does. The low and game models have one.)
static func mesh_of(low_wanted := false) -> Mesh:
	var path := MODEL % ("_lo" if low_wanted else "")
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]


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
## (0..1 through one beat of the wings), `sway`, `gape`, `curl`, `lag` and the colours (the top
## of the shader lists them).
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


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the other fish are; its beat here does not
## change with its speed: set `sway` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `curl` (bends its rear and tail round to one side, radians
## from the middle of the disc to the tail's tip; more than 0 and the tail comes round to +X;
## the wings are not bent), `lag` (how late the wing tips follow the roots, as a part of a beat)
## and its colours (`back`, `back_dark`, `belly`, `belly_dusk`, `mouth`, `iris`, `spine`).
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
	# (its wing tips rise and fall well past where the still model ends)
	mesh.extra_cull_margin = 0.4
	mesh.name = "BatRay" + ("_lo" if low_wanted else "_game" if game_wanted else "")
	add_child(mesh)
	return mesh
