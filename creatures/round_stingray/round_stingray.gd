class_name RoundStingray
extends Node3D
## A round stingray (Urobatis halleri), 0.5 m long (a big one): a nearly round disc, its eyes on
## top, a short stout tail with a sting half way along it and a small tail fin round its end,
## tan-brown covered with pale spots above and pale beneath. Its mouth is underneath.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its back is up. Its origin is on
## its middle line, half way from its nose to the end of its tail and half way up its height:
## so the nose is 0.25 m ahead of the origin and the middle of the disc `DISC_MIDDLE` (0.105 m)
## ahead of it. Its underside is `UNDER` (0.0293 m) below the origin: put the origin that far
## above the sand to rest it there (with `sway` 0 it lies flat). `scale` it for a bigger or
## smaller one. No sound.
##
## It swims by a ripple that runs round the edge of its disc, drawn by the shader (no bones).
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which the ripple goes
## by `tail_beats` times (a whole number), so its motion comes round again exactly every beat.
## Either call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or
## set `phase` yourself (for a picture that must loop: frame / frames in a beat). The same
## names and meanings as GameCommon's yellowfin tuna.
##
## The model is creatures/round_stingray/models/round_stingray.glb (and _lo, _game), built by
## tools/build_round_stingray.py; round_stingray.gdshader draws its markings and moves it.

const MODEL := "res://creatures/round_stingray/models/round_stingray%s.glb"
const SHADER := preload("res://creatures/round_stingray/round_stingray.gdshader")
## As the model is built (tools/build_round_stingray.py), metres at scale 1: from its nose to
## the end of its tail; how tall it is (belly to the top of its back); how wide its disc is.
const LENGTH := 0.5
const DEPTH := 0.058
const WIDTH := 0.28
## How long the disc is, and how far ahead of the origin its middle is.
const DISC_LENGTH := 0.29
const DISC_MIDDLE := 0.105
## How far its underside is below its origin.
const UNDER := 0.0293

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 1.4
## How many times in a beat the ripple goes by.
@export var tail_beats := 2:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How high the ripple is: 1 a round stingray swimming (the disc's edge rises and falls about
## 0.02 m), 0 lying still and flat.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Its mouth (underneath): 0 shut, 1 wide open.
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = value
		_send(&"gape", value)
## The low model (about a twelfth of the triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (1,656 triangles; the full one has 24,056, the low one 2,112): built for games, its
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


## The mesh of the full model, or of the low one: for drawing round stingrays yourself (a
## MultiMesh, a MeshInstance3D of your own) with `new_material()`.
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
## (0..1 through one beat of the ripple), `sway`, `gape`, `curl`, `waves`, `spots` and the
## colours (the top of the shader lists them).
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


## Sets one of the shader's settings: `curl` (bends its tail round to one side, radians from
## the rear of the disc to the tail's end; more than 0 and the tail comes round to +X; the disc
## is not bent), `waves` (how many waves there are along each side of the disc at once),
## `spots` (how strongly its spots show) and its colours (`back`, `net`, `spot`, `belly`,
## `mouth`, `iris`, `spine`).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one beat of the ripple it is)
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
	# (the ripple and the tail's swing reach a little past where the still model ends)
	mesh.extra_cull_margin = 0.1
	mesh.name = "RoundStingray" + ("_lo" if low_wanted else "_game" if game_wanted else "")
	add_child(mesh)
	return mesh
