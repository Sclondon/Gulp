class_name CutthroatTrout
extends Node3D
## A cutthroat trout (Oncorhynchus clarkii), 0.4 m long: a trout's body, deep at the
## shoulder and narrow at the wrist of the tail; a head with a lower jaw that works,
## the long upper lip plate (maxilla) reaching back past the eye, gill covers and
## eyes; a dorsal fin, the small adipose fin, a broad barely forked tail, an anal fin
## and a pair each of pelvic and pectoral fins. Its nose points along its own -Z, its
## belly down; its origin is the middle of its length.
##
## Two looks (`look`): the GREENBACK (O. c. stomias, Colorado's state fish: dark green
## back, yellow-green sides, a red-orange flush along the lower side and belly, rosy
## gill covers, heavy round black spots crowded towards the tail) and a GOLDEN one
## after the Colorado River and Yellowstone cutthroats (golden yellow, bigger spots
## spread further forward, an orange gill cover). All of its markings are drawn by
## its shader: no texture files. `set_shader_parameter` reaches every colour.
##
## It swims by a wave down its body, drawn by the shader (no bones): the head nearly
## still, the tail swinging widest, its fins and tail carried and turned with the
## bend; its mouth and gill covers work as it breathes; its pectoral fins scull.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`: in a beat the
## tail beats `tail_beats` times, it breathes `breaths` times and its fins scull
## `sculls` times (whole numbers), so its motion comes round again exactly every
## beat. Either call `step(velocity, delta)` each frame, which moves `phase` on by
## delta / beat (and swims harder the faster it is going), or set `phase` yourself
## (for a picture that must loop: frame / frames in a beat).
##
## How it looks and moves only: whatever moves it puts it where it is and turns it
## the way it goes. `scale` it for a bigger or smaller one. No sound.
##
## The model is creatures/cutthroat_trout/models/cutthroat_trout.glb (and _lo), built
## by tools/build_cutthroat_trout.py; its shader is cutthroat_trout.gdshader.

enum Look { GREENBACK, GOLDEN }

const MODEL := "res://creatures/cutthroat_trout/models/cutthroat_trout%s.glb"
const SHADER := preload("res://creatures/cutthroat_trout/cutthroat_trout.gdshader")
## As the model is built (tools/build_cutthroat_trout.py): snout to tail tip, how deep
## and how wide its body is at the shoulder (metres, at scale 1).
const LENGTH := 0.4
const DEPTH := 0.088
const WIDTH := 0.05
## What each look sets in the shader (colours as they are seen).
const LOOKS := {
	Look.GREENBACK: {
		"back": Color(0.1, 0.17, 0.09), "side": Color(0.52, 0.55, 0.2), "flush": Color(0.9, 0.27, 0.1),
		"belly": Color(0.95, 0.5, 0.28), "band": Color(0.86, 0.42, 0.36), "gill": Color(0.84, 0.3, 0.3),
		"fin_low": Color(0.93, 0.36, 0.14), "fin_top": Color(0.58, 0.52, 0.2), "fin_tail": Color(0.42, 0.5, 0.24),
		"parr": Color(0.3, 0.4, 0.48), "flush_amount": 1.0, "band_amount": 0.3, "parr_amount": 0.22,
		"spot_cell": 0.0092, "spot_size": 1.0, "spot_fore": 0.4, "spot_low": 0.5,
		"lid_colour": Color(0.26, 0.32, 0.13),
	},
	Look.GOLDEN: {
		"back": Color(0.3, 0.25, 0.1), "side": Color(0.84, 0.6, 0.2), "flush": Color(0.93, 0.56, 0.16),
		"belly": Color(0.96, 0.8, 0.56), "band": Color(0.9, 0.5, 0.3), "gill": Color(0.86, 0.36, 0.14),
		"fin_low": Color(0.92, 0.52, 0.18), "fin_top": Color(0.86, 0.62, 0.22), "fin_tail": Color(0.84, 0.62, 0.24),
		"parr": Color(0.5, 0.52, 0.5), "flush_amount": 0.7, "band_amount": 0.12, "parr_amount": 0.4,
		"spot_cell": 0.0135, "spot_size": 1.05, "spot_fore": 0.4, "spot_low": 0.66,
		"lid_colour": Color(0.56, 0.44, 0.16),
	},
}

## Which cutthroat it is.
@export var look := Look.GREENBACK:
	set(value):
		look = value
		_dress()
## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 2.4
## How many times in a beat its tail beats, it breathes, and its pectoral fins scull.
@export var tail_beats := 3:
	set(value):
		tail_beats = maxi(value, 0)
		_send(&"tail_beats", float(tail_beats))
@export var breaths := 2:
	set(value):
		breaths = maxi(value, 0)
		_send(&"breaths", float(breaths))
@export var sculls := 2:
	set(value):
		sculls = maxi(value, 0)
		_send(&"sculls", float(sculls))
## How hard it swims when it is not going anywhere (holding its place in a current):
## 0 hangs still, 1 swings its tail a tenth of its length each way.
@export_range(0.0, 1.0) var swim := 0.5:
	set(value):
		swim = value
		_effort = value
		_send(&"swim", _effort)
## The speed (m/s, at scale 1) at which `step` has it swimming as hard as it can.
@export var top_speed := 1.2
## The low model (far off, phones) in place of the full one.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about 1,800 triangles, spent on the outline, the eye, the mouth and
## the fins' edges) in place of the full one; `low` still shows the low model. Each
## model is loaded only when it is first shown, so with `game` on the full model is
## never loaded and a game's web export can leave its .glb out.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye (0 the eye as it was, 1 the cartoon eye: bigger, a white, a gold
## iris, a big pupil, a highlight, a steady half-lidded look). Gulp sets it to 1.
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = value
		_send(&"cartoon_eyes", value)
## Where the cartoon eye's pupil looks: x forward (towards the snout), y up, -1..1.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value
		_send(&"eye_look", value)
## 0 open, 1 shut: the eye squashes and a lid closes over it (a fish has no lids:
## this is for a game that wants one).
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = value
		_send(&"blink", value)
## How far through a beat it is, 0 to 1. `step` moves it on; or set it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D
var _effort := 0.5
static var _meshes := {}


## The game model's mesh, for a game that draws meshes itself (with `material()`'s
## shader). Loaded once and kept.
static func game_mesh() -> Mesh:
	return _load_mesh("_game")


static func _load_mesh(suffix: String) -> Mesh:
	var path := MODEL % suffix
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh) if suffix == "_game" else found.mesh
		made.free()
	return _meshes[path]


## The mesh without the thinned LOD meshes Godot's importer makes: the shader bends the
## fish, and a thinned mesh far off would bend in straight pieces.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


func _init() -> void:
	_material = ShaderMaterial.new()
	_material.shader = SHADER
	_effort = swim
	_dress()


func _ready() -> void:
	_show()
	for setting: StringName in [&"tail_beats", &"breaths", &"sculls"]:
		_send(setting, float(get(setting)))
	_send(&"swim", _effort)
	_send(&"phase", phase)


## Each frame, after putting it where it is: moves its beat on by `delta` seconds,
## and has it swim harder the faster it is going (`velocity`, world, m/s; give
## Vector3.ZERO for one that holds its place, and it swims as `swim` says).
func step(velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)
	var size := maxf(global_basis.get_scale().z, 0.001) if is_inside_tree() else 1.0
	var wanted := maxf(swim, clampf(velocity.length() / (top_speed * size), 0.0, 1.0))
	_effort = move_toward(_effort, wanted, delta * 1.5)
	_send(&"swim", _effort)


## Sets one of the shader's settings: a colour (back, side, flush, belly, band, gill,
## jaw_pale, slash, mouth, spot, parr, fin_low, fin_edge, fin_top, fin_tail, eye_gold,
## sheen_colour), an amount (flush_amount, band_amount, parr_amount, sheen), the spots
## (spot_cell, spot_size, spot_fore, spot_low), or how it moves (gape, gape_breath,
## gill_flare, scull). `look` sets most of the colours and the spots again.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_send(setting, value)


## The material it is drawn with.
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


func _dress() -> void:
	if _material == null:
		return
	var wears: Dictionary = LOOKS[look]
	for setting: String in wears:
		_material.set_shader_parameter(setting, wears[setting])


func _show() -> void:
	if not is_inside_tree():
		return
	# (each model is made only when it is first shown)
	if low:
		if _low == null:
			_low = _mesh_of("_lo")
	elif game:
		if _game == null:
			_game = _mesh_of("_game")
	elif _full == null:
		_full = _mesh_of("")
	if _full:
		_full.visible = not low and not game
	if _low:
		_low.visible = low
	if _game:
		_game.visible = game and not low


func _mesh_of(suffix: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = _load_mesh(suffix)
	mesh.material_override = _material
	# (its tail swings out past the still model's box)
	mesh.extra_cull_margin = LENGTH * 0.25
	mesh.name = "Trout" + suffix
	add_child(mesh)
	return mesh
