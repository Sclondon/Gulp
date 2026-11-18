class_name FinWhale
extends Node3D
## A fin whale (Balaenoptera physalus), 20 m long: long and sleek, a narrow V-shaped head with
## a single ridge down its middle, long throat pleats from the chin to the navel, small pointed
## flippers, a tall swept-back dorsal fin two thirds of the way back and a sharp ridge on the tail
## stock behind it; dark grey-brown above and white beneath, and lopsided at the head: its lower
## jaw white on its right side and dark on its left (the front of its right baleen pale too), a
## pale chevron on its back behind the head and a pale blaze up its right side.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down, its left side +X;
## its origin is on its middle line half way from the tip of its snout to the notch of its
## flukes, so it reaches 10.0 m ahead and 10.0 m behind (the tips of its flukes a little
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
## The models are creatures/fin_whale/models/fin_whale.glb (and _lo), built by
## tools/build_fin_whale.py; fin_whale.gdshader draws the markings, swims it and opens its mouth.

const MODEL := "res://creatures/fin_whale/models/fin_whale%s.glb"
const SHADER := preload("res://creatures/fin_whale/fin_whale.gdshader")
## As the model is built (tools/build_fin_whale.py): from the tip of its snout to the notch of its
## flukes, and how deep and how wide its body is at its deepest (metres, at scale 1).
const LENGTH := 20.0
const DEPTH := 2.56
const WIDTH := 2.44
## How far its flukes reach from tip to tip, and how far out from its middle line the tip of a
## flipper reaches (metres, at scale 1).
const SPAN := 4.4
const FLIPPER_REACH := 2.4

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 4.5
## How many times in a beat its flukes beat (up and down again).
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send(&"tail_beats", float(tail_beats))
## How hard it swims: 1 cruising (the notch of its flukes rises and falls about 1.2 m either
## way), 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far its mouth is open: 0 shut, 1 its lower jaw dropped wide and its pleated throat ballooning (as it lunges into a school of fish or krill).
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
## The low model (about a twelfth of the triangles), for far off or for several of them.
@export var low := false:
	set(value):
		low = value
		_show()
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set
## it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)

static var _meshes := {}

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`): for
## drawing one without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase`
## (0..1 through one beat), `tail_beats`, `sculls`, `sway`, `scull`, `gape`, `curl`, `arch`,
## `wave` and the colours (the top of the shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_full = _instance_of(false)
	_low = _instance_of(true)
	_show()
	for setting: StringName in [&"sway", &"gape", &"curl", &"arch", &"phase"]:
		_send(setting, get(setting))
	_send(&"tail_beats", float(tail_beats))


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the fish are; its beat here does not change with
## its speed: set `sway` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `sculls` (how many times its flippers scull in a beat, a
## whole number), `scull` (how far), `wave` (the length of the wave down its body, in body
## lengths), and its colours (`back`, `belly`, `chevron`, `fin_under`, `baleen_pale`, `mouth_roof`,
## `tongue`, `mouth_wall`, `baleen`, `fringe`, `eye_dark`, `eye_iris`) and `chevron_show` (how
## strongly the chevron and the blaze show).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


func _show() -> void:
	if _full:
		_full.visible = not low
		_low.visible = low


func _instance_of(low_wanted: bool) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = mesh_of(low_wanted)
	mesh.material_override = _material
	# (its flukes swing, its jaw drops and its throat balloons out past where the still model ends)
	mesh.extra_cull_margin = 5.0
	mesh.name = "FinWhaleLo" if low_wanted else "FinWhale"
	add_child(mesh)
	return mesh


static func _mesh_at(path: String) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]
