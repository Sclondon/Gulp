class_name GhostWhale
extends Node3D
## A ghost whale: the skeleton of a great whale (a baleen whale's, after a humpback's), 14 m long,
## still swimming, wreathed in a pale blue glowing mist in the shape of the body it lost. A long flat
## skull with wings of bone over the eye sockets and two long bowed jawbones; the spine from the neck
## to the flukes, a spine standing up from each vertebra; fourteen pairs of ribs; the flippers' long
## finger bones; the flukes only mist. It glows (light added over what is behind it: no lights, no
## shadows) and comes in and out with `fade`: a thing of the night and the deep.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it goes.
## Its nose points along its own -Z, its back up, its left side +X; its origin is on its middle line
## half way from the tip of its snout to the notch of its flukes (7 m each way). No sound.
##
## It swims as whales do (its bones bend with it): its flukes beat up and down, a wave growing down
## the tail, its flippers scull slowly; the mist wavers and trails behind. `curl` bends it round into
## a turn; `gape` drops its jawbones. All drawn by the shader, creatures/ghost_whale/ghost.gdshader,
## which the ghost fish shares (one shader program for both).
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its flukes beat
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat. Either call
## `step(velocity, delta)` each frame, or set `phase` yourself. The same names and meanings as
## GameCommon's whales (the humpback whale).
##
## The models are creatures/ghost_whale/models/ghost_whale.glb (the full model), _game.glb (the game
## model: about 4,200 triangles of bone and 1,400 of mist) and _lo.glb (far off), built by
## tools/build_ghost_whale.py. Each is loaded only when it is first shown: with `game` on, the full
## model is never loaded, so a game can leave models/ghost_whale.glb out of its export.

const MODEL := "res://creatures/ghost_whale/models/ghost_whale%s.glb"
const SHADER := preload("res://creatures/ghost_whale/ghost.gdshader")
## From the tip of its snout to the notch of its flukes, and how deep and how wide the mist of its body
## is at its deepest (metres, at scale 1). Its flukes' mist reaches 0.5 m behind the notch.
const LENGTH := 14.0
const DEPTH := 3.0
const WIDTH := 3.2
## How far its flippers' mist reaches out from its middle line, and its flukes' mist (metres).
const FLIPPER_REACH := 4.4
const SPAN := 4.7

## Seconds one beat takes.
@export var beat := 5.0
## How many times in a beat its flukes beat (a whole number).
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send(&"tail_beats", float(tail_beats))
## How hard it swims: 1 cruising (the notch of its flukes rises and falls about 1 m), 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Its jawbones: 0 shut, 1 dropped wide (31 degrees).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## Turning: radians from its chest to its flukes (more than 0 its flukes come round to +X).
@export_range(-3.0, 3.0) var curl := 0.0:
	set(value):
		curl = value
		_send(&"curl", value)
## How much it is there: 0 gone (it draws nothing to see), 1 all there. Bring it in at night and in the
## deep, and out again (it costs its draw even at 0: hide the node when it has gone).
@export_range(0.0, 1.0) var fade := 1.0:
	set(value):
		fade = clampf(value, 0.0, 1.0)
		_send(&"fade", fade)
## How brightly it glows (1 as made).
@export_range(0.0, 3.0) var glow := 1.0:
	set(value):
		glow = value
		_send(&"glow", glow)
## The game model in place of the full one (about 5,500 triangles against 19,300). Off by default.
@export var game := false:
	set(value):
		game = value
		_show()
## The low model (about 2,750 triangles), for far off. It wins over `game`.
@export var low := false:
	set(value):
		low = value
		_show()
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


## A new material for these meshes (the ghost shader with the whale's numbers). Its settings are the
## game's to set: `phase`, `tail_beats`, `sway`, `gape`, `curl`, `fade`, `glow`, `far`, `waver` and the
## colours.
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	made.set_shader_parameter(&"body_length", LENGTH)
	made.set_shader_parameter(&"lateral", false)
	made.set_shader_parameter(&"reach", 0.07)
	made.set_shader_parameter(&"wave", 1.3)
	made.set_shader_parameter(&"jaw_hinge", Vector2(3.55, -0.3))
	made.set_shader_parameter(&"flipper_root", Vector3(4.35, -0.75, 1.0))
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_started = true
	_show()
	for setting: StringName in [&"sway", &"gape", &"curl", &"fade", &"glow", &"phase"]:
		_send(setting, get(setting))
	_send(&"tail_beats", float(tail_beats))


## Each frame: moves it on through its beat (`velocity` is taken so that it is called as the fish are).
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `far` (metres off where it has faded to nothing, 70), `waver`
## (how far its mist billows, 1), `wave` (the length of the wave down its body, in body lengths) and
## the colours (`bone_colour`, `mist_colour`).
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
		_low = _instance_of(mesh_of(true), "GhostWhaleLo")
	elif not low and game and not _game:
		_game = _instance_of(game_mesh(), "GhostWhaleGame")
	elif not low and not game and not _full:
		_full = _instance_of(mesh_of(false), "GhostWhale")
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
	mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	# (its flukes swing, its mist billows and trails past where the still model ends)
	mesh.extra_cull_margin = 4.0
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
