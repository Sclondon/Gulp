class_name Narwhal
extends Node3D
## A male narwhal (Monodon monoceros), 4.5 m from the front of its head to the back of its
## flukes, the tusk not counted: a stocky small whale with a rounded head and no beak, no dorsal
## fin but a low uneven ridge along the back, short rounded flippers whose tips turn up, and
## flukes whose tips curve forward (the tail looks put on backwards); pale grey thickly mottled
## with dark spots that run together into near-black on its back. Its long, straight, spiralled
## tusk runs straight ahead out of the left of its upper lip, 2.5 m ahead of its head
## (`TUSK_REACH`; `tusk` sets its length). Its mouth opens (`gape`); it has no other teeth.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down; its origin is on its
## middle line, half way along its body, so its head reaches 2.25 m ahead and its flukes 2.25 m
## behind, and its tusk's tip 4.75 m ahead. `scale` it for a bigger or smaller one. No sound.
##
## It swims as whales do: its flukes beat UP AND DOWN, a wave growing down the tail stock and
## the flukes pitching as one stiff plate, by a bend drawn by the shader (no bones). `curl` bends
## it sideways for a turn, `arch` up or down for a dive (the tusk stays straight).
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its flukes beat
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat.
## Either call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or
## set `phase` yourself. The same names and meanings as GameCommon's fish and its dolphin.
##
## The model is creatures/narwhal/models/narwhal.glb (and _lo, _game), built by
## tools/build_narwhal.py; narwhal.gdshader draws its markings, swims it and works its jaw.

const MODEL := "res://creatures/narwhal/models/narwhal%s.glb"
const SHADER := preload("res://creatures/narwhal/narwhal.gdshader")
## As the model is built (tools/build_narwhal.py): from the front of its head to the back of its
## flukes (the tusk not counted), and how deep and how wide its body is at its fattest (metres,
## at scale 1).
const LENGTH := 4.5
const DEPTH := 0.97
const WIDTH := 0.88
## How far ahead of the front of its head the tip of its tusk reaches at `tusk` 1 (so 4.75 m
## ahead of its origin). It comes out of the left of the upper lip (its left is -X), 0.06 m left
## of the middle line and 0.045 m below it.
const TUSK_REACH := 2.5

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 3.0
## How many times in a beat its flukes beat (up and down again).
@export var tail_beats := 2:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it beats: 1 a narwhal cruising (its fluke tips rise and fall about 0.3 m), 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Its mouth: 0 shut, 1 wide open (the lower jaw swings down about the corner of its mouth).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## Its tusk's length: 1 a grown male's (`TUSK_REACH` ahead of its head), less a young male's
## (shorter and a little thinner), 0 none (a female or a calf).
@export_range(0.0, 1.2) var tusk := 1.0:
	set(value):
		tusk = maxf(value, 0.0)
		_send(&"tusk", tusk)
## How far its body is bent round to one side behind the head, as when it turns tightly:
## radians from the flippers to the flukes (more than 0, the flukes come round to +X).
@export_range(-1.5, 1.5) var curl := 0.0:
	set(value):
		curl = value
		_send(&"curl", value)
## How far its whole body is bent up or down about its middle: radians from head to flukes.
## More than 0 its head and flukes both come up; less than 0 both go down, its back arched. The
## tusk goes on straight from its head.
@export_range(-1.5, 1.5) var arch := 0.0:
	set(value):
		arch = value
		_send(&"arch", value)
## The low model (about a twentieth of the triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model: about 4,800 triangles, Twilight Princess weight, spent on its outline, eyes,
## mouth, tusk's spiral and fin edges, shown in place of the full one (`low` still shows the low
## one). Each model is loaded only when it is first shown, so with `game` on the full model is
## never loaded and a game's web export can leave it out.
@export var game := false:
	set(value):
		game = value
		_show()
## Its eyes: 0 as in life, 1 cartoon eyes (small, mild and curious). On all three models.
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where its cartoon eyes look, each in its own plane: x +1 towards its nose, -1 towards its tail;
## y +1 up, -1 down (both eyes the same way).
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(Vector2(-1.0, -1.0), Vector2(1.0, 1.0))
		_send(&"eye_look", eye_look)
## Its cartoon eyes' lids: 0 open, 1 shut.
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set
## it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()

static var _meshes := {}

var _material: ShaderMaterial
# (the models shown so far, by their file's ending: "", "_lo", "_game")
var _shown := {}
var _started := false


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`): for
## drawing one without this node (many of them in a MultiMesh, say).
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at("_lo" if low_wanted else "")


## The game model's mesh (one surface, to wear `new_material()`), without the thinned copies
## Godot's importer makes for far off (they would bend in straight pieces).
static func game_mesh() -> Mesh:
	return _mesh_at("_game")


## A mesh rebuilt from its surfaces alone, without the importer's automatic LODs.
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
		_meshes[path] = without_lods(found.mesh) if ending == "_game" else found.mesh
		made.free()
	return _meshes[path]


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase`
## (0..1 through one beat of the flukes), `sway`, `curl`, `arch`, `gape`, `tusk`, `wave` and the
## colours (the top of the shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_started = true
	_show()
	_send_phase()
	_send(&"cartoon_eyes", cartoon_eyes)
	_send(&"eye_look", eye_look)
	_send(&"blink", blink)
	_send(&"sway", sway)
	_send(&"gape", gape)
	_send(&"tusk", tusk)
	_send(&"curl", curl)
	_send(&"arch", arch)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the fish are; its beat here does not change
## with its speed: set `sway` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: its colours (`pale`, `spot`, `back`, `fin`, `mouth`,
## `ivory`), `spots` (0 an old, nearly white narwhal, 1 the usual, more a young dark one) and
## `wave` (the length of the wave along its body, in body lengths).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one beat of the flukes it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


# (shows the model wanted, loading it the first time)
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
	# (its flukes rise and fall past where the still model ends, and it bends; its tusk swings
	# with the arch)
	mesh.extra_cull_margin = 0.35 * LENGTH
	mesh.name = "Narwhal" + ending
	add_child(mesh)
	return mesh
