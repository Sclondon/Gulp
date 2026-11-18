class_name SeaOtter
extends Node3D
## A sea otter (Enhydra lutris), 1.3 m from its nose to the tip of its tail: dense brown fur, a
## paler blond head and throat, a blunt whiskered face with small ears and a big dark nose,
## small fore paws, big webbed hind feet like flippers and a thick flattened tail.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down; its origin is on
## its middle line, half way along, so it reaches 0.65 m ahead and 0.65 m behind. `scale` it
## for a bigger or smaller one. No sound.
##
## Under water it swims as otters do: its body, hind feet and tail wave UP AND DOWN, its fore
## legs tucked to its chest. `afloat` turns it over on to its back at the surface, head and feet
## lifted, paws together on its chest (put its origin about 0.03 m under the water then; its
## nose still points to -Z). All of that is drawn by the shader (no bones).
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which it beats its feet
## and tail `tail_beats` times (a whole number), so its motion comes round again exactly every
## beat. Either call `step(velocity, delta)` each frame, which moves `phase` on by delta /
## beat, or set `phase` yourself. The same names and meanings as GameCommon's fish
## (YellowfinTuna).
##
## The model is creatures/sea_otter/models/sea_otter.glb (and _lo, _game), built by
## tools/build_sea_otter.py; sea_otter.gdshader draws its fur and moves it.

const MODEL := "res://creatures/sea_otter/models/sea_otter%s.glb"
const SHADER := preload("res://creatures/sea_otter/sea_otter.gdshader")
## As the model is built (tools/build_sea_otter.py): from the tip of its nose to the tip of its
## tail, and how deep and how wide its body is at its fattest (metres, at scale 1).
const LENGTH := 1.3
const DEPTH := 0.24
const WIDTH := 0.26

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 1.6
## How many times in a beat it beats its hind feet and tail (down and up).
@export var tail_beats := 2:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How hard it swims: 1 an otter cruising under water (its tail tip beats about 0.09 m either
## way), 0 gliding still. Afloat, it only sets how much its feet bob.
@export_range(0.0, 1.5) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Floating: 0 swimming belly down, 1 on its back at the surface with its paws on its chest;
## between, it rolls over. (The pose the task called `float`: that word is taken in GDScript
## and in shaders.)
@export_range(0.0, 1.0) var afloat := 0.0:
	set(value):
		afloat = value
		_send(&"afloat", value)
## Its mouth: 0 shut, 1 wide open, as when it bites.
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = value
		_send(&"gape", value)
## Turning: how far its body is bent round to one side behind its head, radians from neck to
## tail (more than 0 and its tail comes round to its left, +X).
@export_range(-2.0, 2.0) var curl := 0.0:
	set(value):
		curl = value
		_send(&"curl", value)
## The same, up or down (more than 0 and its tail comes up, as when it dives).
@export_range(-2.0, 2.0) var arch := 0.0:
	set(value):
		arch = value
		_send(&"arch", value)
## The low model (about a fourteenth of the triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (models/sea_otter_game.glb, about a tenth of the full model's triangles,
## spent on its outline, face, eyes and flippers) in place of the full one. `low` still shows the
## low one. Each model is loaded only when it is first shown, so with `game` on the full .glb is
## never loaded (a game's web export can leave it out).
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 the eye as it is, 1 bigger and drawn as a cartoon (a big round black eye, its cheeks pushed up under it in a grin).
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
## drawing a sea otter without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## The game model's mesh (one surface, to wear `new_material()`), without the thinned LOD meshes
## Godot's importer makes (bent in the shader, they would bend in straight pieces far off).
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game", true)


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase`
## (0..1 through one beat of its feet), `sway`, `afloat`, `gape`, `curl`, `arch` and the rest
## (the top of the shader lists them).
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
	_send(&"afloat", afloat)
	_send(&"gape", gape)
	_send(&"curl", curl)
	_send(&"arch", arch)
	_send(&"cartoon_eyes", cartoon_eyes)
	_send(&"eye_look", eye_look)
	_send(&"blink", blink)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the fish's are; its beat here does not change
## with its speed: set `sway` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `wave` (the length of the wave along its body, in body
## lengths), `wet` (1 soaked and sleek, 0 dry and fluffy) and its colours (`coat`, `coat_tip`,
## `blond`, `hide`, `nose`, `mouth_inside`, `tooth`, `whiskers`).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one beat of its feet it is)
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
	# (its tail and feet swing out past where the still model ends; `curl` and `arch` further)
	mesh.extra_cull_margin = 0.5
	mesh.name = "SeaOtter" + {"": "", "_lo": "Lo", "_game": "Game"}[ending]
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
