class_name CaliforniaHalibut
extends Node3D
## A California halibut (Paralichthys californicus), 1 m long: a flatfish that lies on its side,
## both eyes on its upper side, a big toothed mouth, mottled sandy brown above (to match the
## sand) and white beneath, low fins fringing the whole body, a high arch in its lateral line.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. It is modelled as it lies: its flat upper (eyed) side is +Y, its nose points along its
## own -Z (Godot's forward), the edge of its back is +X and the edge of its belly (and its lower
## jaw) -X. Its origin is on its middle line, half way along and half way up its thickness, so
## it reaches 0.5 m ahead and 0.5 m behind, and its underside is `UNDER` (0.0355 m) below the
## origin: put the origin that far above the sand to rest it there. `scale` it for a bigger or
## smaller one. No sound.
##
## It swims as flatfish do: a wave up and down along its flat body, and a quicker ripple along
## its fins, drawn by the shader (no bones). `settle` lays it down on the sand; `gape` opens its
## mouth.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its body beats
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat.
## Either call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or
## set `phase` yourself (for a picture that must loop: frame / frames in a beat). The same
## names and meanings as GameCommon's yellowfin tuna.
##
## The model is creatures/california_halibut/models/california_halibut.glb (and _lo, _game), built by
## tools/build_california_halibut.py; california_halibut.gdshader draws its markings and moves it.

const MODEL := "res://creatures/california_halibut/models/california_halibut%s.glb"
const SHADER := preload("res://creatures/california_halibut/california_halibut.gdshader")
## As the model is built (tools/build_california_halibut.py), metres at scale 1: from the tip of
## its snout to the end of its tail; how thick its body is, as it lies (top to underside); how
## wide its body is across, as it lies, without its fins (they reach 0.21 to each side).
const LENGTH := 1.0
const DEPTH := 0.071
const WIDTH := 0.32
## How far its underside is below its origin (its fins and tail too, when `settle` is 1).
const UNDER := 0.0355

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 1.6
## How many times in a beat the wave runs down its body.
@export var tail_beats := 2:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it beats: 1 a halibut cruising (its tail rises and falls about 0.05 m), 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Its mouth: 0 shut, 1 wide open, as when it bites.
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = value
		_send(&"gape", value)
## Lying on the sand: 0 swimming, 1 flat on the ground (no wave; its fins and tail laid down to
## the level of its underside).
@export_range(0.0, 1.0) var settle := 0.0:
	set(value):
		settle = value
		_send(&"settle", value)
## The low model (about a twelfth of the triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (2,920 triangles; the full one has 44,088, the low one 3,680): built for games, its
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


## The mesh of the full model, or of the low one: for drawing halibut yourself (a MultiMesh, a
## MeshInstance3D of your own) with `new_material()`.
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
## (0..1 through one beat of the body), `sway`, `gape`, `settle`, `curl`, `wave`, `mottle` and
## the colours (the top of the shader lists them).
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
	_send_phase()
	_send(&"sway", sway)
	_send(&"gape", gape)
	_send(&"settle", settle)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the other fish are; its beat here does not
## change with its speed: set `sway` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `curl` (bends the body round to one side behind the head,
## radians from gills to tail, as it lies; more than 0 and the tail comes round to +X), `wave`
## (the length of the wave along its body), `mottle` (how strongly its blotches and spots show)
## and its colours (`sand`, `blotch`, `pale`, `belly`, `mouth`, `teeth`, `iris`).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one beat of the body it is)
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
	# (its tail rises and falls past where the still model ends)
	mesh.extra_cull_margin = 0.3
	mesh.name = "Halibut" + ("_lo" if low_wanted else "_game" if game_wanted else "")
	add_child(mesh)
	return mesh
