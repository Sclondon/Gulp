class_name SeaLion
extends Node3D
## A California sea lion (Zalophus californianus), 2.2 m from its nose to the tips of its hind
## flippers: sleek and chocolate brown, with a dog-like pointed muzzle, small ear flaps, a long
## neck, very long fore flippers like wings and hind flippers that trail. `crest` gives it a
## bull's forehead bump.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down; its origin is on
## its middle line, half way along, so it reaches 1.1 m ahead and 1.1 m behind. `scale` it for
## a bigger or smaller one (a cow is about 0.8 of this, a big bull 1.1). No sound.
##
## It swims as sea lions do: it flies with its fore flippers, lifting them out and forward and
## sweeping them down and back to its belly; its hind flippers trail and steer. `fold` lays the
## fore flippers back along its sides, as in a glide. All of that is drawn by the shader (no
## bones).
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which it strokes
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat.
## Either call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or
## set `phase` yourself. The same names and meanings as GameCommon's fish (YellowfinTuna): the
## stroke is called a tail beat there, and keeps that name here.
##
## The model is creatures/sea_lion/models/sea_lion.glb (and _lo, _game), built by
## tools/build_sea_lion.py; sea_lion.gdshader draws its coat and moves it.

const MODEL := "res://creatures/sea_lion/models/sea_lion%s.glb"
const SHADER := preload("res://creatures/sea_lion/sea_lion.gdshader")
## As the model is built (tools/build_sea_lion.py): from the tip of its nose to the tips of its
## hind flippers, and how deep and how wide its body is at its chest (metres, at scale 1).
const LENGTH := 2.2
const DEPTH := 0.42
const WIDTH := 0.4

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 1.5
## How many times in a beat it strokes its fore flippers.
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How hard it strokes: 1 a sea lion cruising, 0 its flippers held still.
@export_range(0.0, 1.5) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Gliding: how far its fore flippers are folded back along its sides (0 out like wings, 1
## back; folded, they do not stroke).
@export_range(0.0, 1.0) var fold := 0.0:
	set(value):
		fold = value
		_send(&"fold", value)
## Its mouth: 0 shut, 1 wide open, as when it bites.
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = value
		_send(&"gape", value)
## Turning: how far its body is bent round to one side behind its head, radians from neck to
## hind flippers (more than 0 and its tail comes round to its left, +X).
@export_range(-2.0, 2.0) var curl := 0.0:
	set(value):
		curl = value
		_send(&"curl", value)
## The same, up or down (more than 0 and its tail comes up, as when it dives).
@export_range(-2.0, 2.0) var arch := 0.0:
	set(value):
		arch = value
		_send(&"arch", value)
## A bull's forehead bump: 0 none (a cow or a young one), 1 a full grown bull's, pale on top.
@export_range(0.0, 1.0) var crest := 0.0:
	set(value):
		crest = value
		_send(&"crest", value)
## The low model (about a fourteenth of the triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (models/sea_lion_game.glb, about a tenth of the full model's triangles,
## spent on its outline, face, eyes and flippers) in place of the full one. `low` still shows the
## low one. Each model is loaded only when it is first shown, so with `game` on the full .glb is
## never loaded (a game's web export can leave it out).
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 the eye as it is, 1 bigger and drawn as a cartoon (a bright, eager brown eye that shows its whites).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = value
		_send(&"cartoon_eyes", value)
## Where both eyes look, -1..1: x towards its nose, y up (the cartoon eye's iris slides that way).
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value
		_send(&"eye_look", value)
## Its lids: 0 open, 1 shut.
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
# (the models shown so far, by their ending: "" the full one, "_lo", "_game")
var _shown := {}
var _made := false


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`): for
## drawing a sea lion without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## The game model's mesh (one surface, to wear `new_material()`), without the thinned LOD meshes
## Godot's importer makes (bent in the shader, they would bend in straight pieces far off).
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game", true)


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase`
## (0..1 through one stroke), `sway`, `fold`, `gape`, `curl`, `arch`, `crest` and the rest (the
## top of the shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_made = true
	_show()
	_send_phase()
	_send(&"sway", sway)
	_send(&"fold", fold)
	_send(&"gape", gape)
	_send(&"curl", curl)
	_send(&"arch", arch)
	_send(&"cartoon_eyes", cartoon_eyes)
	_send(&"eye_look", eye_look)
	_send(&"blink", blink)
	_send(&"crest", crest)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the fish's are; its beat here does not change
## with its speed: set `sway`, `fold` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `wet` (1 just out of a dive, dark and shining; 0 dry fur)
## and its colours (`coat`, `coat_pale`, `muzzle`, `crest_pale`, `hide`, `nose`, `mouth_inside`,
## `tooth`, `whiskers`).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one stroke it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


func _show() -> void:
	if not _made:
		return
	var wanted := "_lo" if low else ("_game" if game else "")
	if not _shown.has(wanted):
		_shown[wanted] = _instance_of(wanted)
	for ending: String in _shown:
		(_shown[ending] as MeshInstance3D).visible = ending == wanted


func _instance_of(ending: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = game_mesh() if ending == "_game" else mesh_of(ending == "_lo")
	mesh.material_override = _material
	# (its flippers swing out past where the still model ends; `curl` and `arch` further)
	mesh.extra_cull_margin = 0.8
	mesh.name = "SeaLion" + {"": "", "_lo": "Lo", "_game": "Game"}[ending]
	add_child(mesh)
	return mesh


static func _mesh_at(path: String, plain := false) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh) if plain else found.mesh
		made.free()
	return _meshes[path]


## A copy of `mesh` without the LOD meshes Godot's importer made for it.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain
