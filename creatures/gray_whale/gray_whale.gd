class_name GrayWhale
extends Node3D
## A gray whale (Eschrichtius robustus), 13 m long: robust, mottled slate grey dappled with pale
## scars and crusted with pale patches of barnacles (orange whale lice crowding round them); a
## narrow arched head with two or three short throat grooves and short cream baleen; no dorsal
## fin but a low hump and a row of knuckles down the tail stock; short pointed paddle flippers;
## broad flukes with a deep notch.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down, its left side +X;
## its origin is on its middle line half way from the tip of its snout to the notch of its
## flukes, so it reaches 6.5 m ahead and 6.5 m behind (the tips of its flukes a little
## further). `scale` it for a bigger or smaller one. No sound.
##
## It swims as whales do: its flukes beat up and down, a wave growing down the tail stock, the
## flukes pitching as one stiff plate; its flippers scull slowly. All drawn by the shader (no
## bones). `curl` bends it round into a turn, `arch` up or down; `gape` drops its lower jaw.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its flukes beat
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat.
## Either call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or
## set `phase` yourself (for a picture that must loop: frame / frames in a beat). The same
## names and meanings as GameCommon's fish (the yellowfin tuna, the sardine).
##
## The models are creatures/gray_whale/models/gray_whale.glb (the full model), _game.glb (the game
## model: about 5,400 triangles, the same outline, for games) and _lo.glb (far off), built by
## tools/build_gray_whale.py; gray_whale.gdshader draws the markings, swims it and opens its mouth.
## Each model is loaded only when it is first shown: with `game` on, the full model is never
## loaded, so a game can leave models/gray_whale.glb out of its export.

const MODEL := "res://creatures/gray_whale/models/gray_whale%s.glb"
const SHADER := preload("res://creatures/gray_whale/gray_whale.gdshader")
## As the model is built (tools/build_gray_whale.py): from the tip of its snout to the notch of its
## flukes, and how deep and how wide its body is at its deepest (metres, at scale 1).
const LENGTH := 13.0
const DEPTH := 2.7
const WIDTH := 2.5
## How far its flukes reach from tip to tip, and how far out from its middle line the tip of a
## flipper reaches (metres, at scale 1).
const SPAN := 3.4
const FLIPPER_REACH := 2.0

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 4.0
## How many times in a beat its flukes beat (up and down again).
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send(&"tail_beats", float(tail_beats))
## How hard it swims: 1 cruising (the notch of its flukes rises and falls about 0.85 m either
## way), 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far its mouth is open: 0 shut, 1 its lower jaw dropped wide (a gray whale's mouth opens only so far: it sucks up mud and sieves it).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## Turning: how far its body is bent round to one side behind the head, in radians from the head
## to the flukes (0 straight; more than 0 its flukes come round to +X, its left, as it turns left).
@export_range(-3.0, 3.0) var curl := 0.0:
	set(value):
		curl = value
		_send(&"curl", value)
## The same up and down, about its middle (radians from snout to flukes): more than 0 its head
## and flukes both come up, less than 0 both go down (its back arched, as it dives).
@export_range(-2.0, 2.0) var arch := 0.0:
	set(value):
		arch = value
		_send(&"arch", value)
## The game model in place of the full one: about 5,400 triangles (the full model has about
## 53,900), the same outline, the same markings and movement. Off by default.
@export var game := false:
	set(value):
		game = value
		_show()
## The low model (about a twelfth of the full model's triangles), for far off or for several of
## them. It wins over `game`.
@export var low := false:
	set(value):
		low = value
		_show()
## The cartoon eye: 0 the eye as it is, 1 a big cartoon eye of its own (curious and friendly, as gray whales that come up to boats are: wide open, plenty of white round a small hazel iris, a round pupil, its brow raised towards the front).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where the cartoon eyes look, -1..1 each way: right and up as seen by someone looking at that
## eye (so both turn the same way: x more than 0 turns its gaze towards its -X side).
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(Vector2(-1.0, -1.0), Vector2(1.0, 1.0))
		_send(&"eye_look", eye_look)
## A blink: 0 open, 1 shut (its lids close over its eyes, the cartoon eye or the eye as it is).
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set
## it yourself.
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


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`): for
## drawing one without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## The game model's mesh (one surface, to wear `new_material()`), without the thinned LOD meshes
## Godot's importer adds (the shader bends it, and a thinned mesh would bend in straight pieces far
## off): for a game that draws its meshes itself. Loads only the game model.
static func game_mesh() -> Mesh:
	var path := MODEL % "_game"
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh)
		made.free()
	return _meshes[path]


## A copy of a mesh with its surfaces only (no LODs).
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


## A new material for `mesh_of()`'s and `game_mesh()`'s meshes. Its shader settings are the game's
## to set: `phase` (0..1 through one beat), `tail_beats`, `sculls`, `sway`, `scull`, `gape`, `curl`,
## `arch`, `wave`, `cartoon_eyes`, `eye_look`, `blink` and the colours (the top of the shader lists
## them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_started = true
	_show()
	for setting: StringName in [&"sway", &"gape", &"curl", &"arch", &"phase", &"cartoon_eyes", &"eye_look", &"blink"]:
		_send(setting, get(setting))
	_send(&"tail_beats", float(tail_beats))


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the fish are; its beat here does not change with
## its speed: set `sway` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `sculls` (how many times its flippers scull in a beat, a
## whole number), `scull` (how far), `wave` (the length of the wave down its body, in body
## lengths), and its colours (`slate`, `slate_dark`, `scar`, `barnacle`, `lice`, `mouth_roof`, `tongue`,
## `mouth_wall`, `baleen`, `fringe`, `eye_dark`, `eye_iris`), `barnacles_show` (how many barnacles and
## scars: 0 for a calf) and `lice_show`.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# Shows the model wanted, making it the first time (each model is loaded only when first shown).
func _show() -> void:
	if not _started:
		return
	if low and not _low:
		_low = _instance_of(mesh_of(true), "GrayWhaleLo")
	elif not low and game and not _game:
		_game = _instance_of(game_mesh(), "GrayWhaleGame")
	elif not low and not game and not _full:
		_full = _instance_of(mesh_of(false), "GrayWhale")
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
	# (its flukes swing, its jaw drops and its throat balloons out past where the still model ends)
	mesh.extra_cull_margin = 3.5
	mesh.name = named
	add_child(mesh)
	return mesh


static func _mesh_at(path: String) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]
