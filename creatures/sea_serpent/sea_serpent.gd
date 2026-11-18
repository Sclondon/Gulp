class_name SeaSerpent
extends Node3D
## The sea serpent of old sailors' charts: an original sea monster, 25 m long. A head like a
## horse's (a long muzzle, a deep round cheek, nostrils at the tip, an eye high under a brow) with
## two spiky ear-fins and a spined frill behind each cheek; a mane of ragged weed down its neck and
## a beard of it under its throat; a slender neck thickening into a long body, scaled above, pale
## plates across its belly; a low ragged fin along its back, two front flippers, a frayed tail fin.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down; its origin is on its
## middle line, half way along, so it reaches 12.5 m ahead and 12.5 m behind. `scale` it for a
## bigger or smaller one. No sound.
##
## It swims in LONG HUMPS: a wave up and down that runs back along its body behind the neck (the
## humps the old charts show), with a little side to side; drawn by the shader (no bones). `humps`
## sets how high they stand, `rear` holds its neck up out of the line of its body with its head
## looking ahead (as in the concept picture), `curl` bends it round for a turn. Its mane sways.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which the humps pass
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat. Either
## call `step(velocity, delta)` each frame, or set `phase` yourself. The same names and meanings as
## GameCommon's fish.
##
## Its shader is creatures/sea_monster/sea_monster.gdshader, shared with the leviathan (one shader
## program for both); this script sends it the serpent's shape and colours.
## The models are creatures/sea_serpent/models/sea_serpent.glb (full), _game and _lo, built by
## tools/build_sea_serpent.py.

const MODEL := "res://creatures/sea_serpent/models/sea_serpent%s.glb"
const SHADER := preload("res://creatures/sea_monster/sea_monster.gdshader")
## As the model is built (tools/build_sea_serpent.py): from the tip of its muzzle to the end of its
## tail fin, and how deep and how wide its body is at its thickest (metres, at scale 1), fins and
## mane left out.
const LENGTH := 25.0
const DEPTH := 1.92
const WIDTH := 1.52

## Its shape, as the build script has it (sent to the shader): see sea_monster.gdshader.
const SHAPE := {
	&"kind": 1,
	&"body_length": 25.0,
	&"joint": 23.4,
	&"corner": 1.74,
	&"hinge_y": -0.247,
	&"hinge_spread": 0.26,
	&"gape_max": 0.7,
	&"lift_max": 0.14,
	&"jaw_from": 0.07,
	&"mouth_a": -0.143,
	&"mouth_b": -0.0596,
	&"reach": 0.02,
	&"reach_poly": Vector4(0.25, 0.0, 0.5, 0.6),
	&"wave": 0.5,
	&"hump_height": 0.85,
	&"hump_from": 9.0,
	&"hump_rise": 4.0,
	&"hump_wave": 0.45,
	&"rear_at": 10.2,
	&"rear_span": 3.0,
	&"rear_max": 1.75,
	&"neck_at": 6.2,
	&"neck_span": 2.2,
	&"neck_keep": 0.55,
	&"head_at": 3.3,
	&"head_span": 1.0,
	&"head_keep": 0.42,
	&"coil_at": 19.5,
	&"coil_span": 4.8,
	&"coil_max": 3.4,
	&"flap": 0.3,
	&"trail": 0.07,
	&"rope_sway": 0.0,
	&"weed_sway": 0.22,
	&"plate_from": 100.0,
	&"plate_to": 100.0,
	# (EYE_FRAME, as tools/build_sea_serpent.py prints it)
	&"eye_centre": Vector3(0.40189, 0.39, -10.27),
	&"eye_out": Vector3(0.9686, 0.2483, -0.0097),
	&"eye_fwd": Vector3(-0.0094, -0.0024, -1.0),
	&"eye_up": Vector3(-0.2483, 0.9687, 0.0),
	&"eye_sag": 0.3022,
	&"eye_radius": 0.09,
	&"eye_grow": 2.3,
	&"eye_at_side": Vector2(2.23, 0.39),
}
## Its colours and its eye's look (sent to the shader; `set_shader_parameter` changes them).
const LOOK := {
	&"back": Color(0.11, 0.22, 0.22),
	&"flank": Color(0.22, 0.38, 0.36),
	&"belly": Color(0.62, 0.65, 0.48),
	&"seam": Color(0.05, 0.09, 0.09),
	&"moss": Color(0.22, 0.3, 0.12),
	&"fin": Color(0.32, 0.47, 0.45),
	&"fin_edge": Color(0.62, 0.68, 0.6),
	&"weed": Color(0.25, 0.31, 0.1),
	&"mouth": Color(0.45, 0.18, 0.18),
	&"tooth": Color(0.9, 0.87, 0.74),
	&"pattern": 1.0,
	# The eye: wary and old. A gold iris filling most of it, a round black pupil, the lids open
	# and level, a thin dark line (the concept's eye looks out calmly from under a brow).
	&"sclera": Color(0.9, 0.88, 0.76),
	&"iris_light": Color(0.96, 0.8, 0.34),
	&"iris_dark": Color(0.58, 0.36, 0.1),
	&"pupil_size": Vector2(0.2, 0.2),
	&"iris_size": 0.68,
	&"eye_glow": 0.15,
	&"lid_up_k": Vector3(0.36, -0.12, -0.14),
	&"lid_down_k": Vector3(-0.66, 0.05, 0.12),
	&"lid_line": Vector2(0.14, 0.06),
}

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 6.0
## How many times in a beat the humps pass along its body.
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it swings side to side: 1 cruising, 0 still (the humps are `humps`).
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How high its humps stand: 1 cruising (about 0.85 m above and below its line), 0 straight.
@export_range(0.0, 2.0) var humps := 1.0:
	set(value):
		humps = value
		_send(&"humps", value)
## Its neck held up in an S: 0 in line with its body (swimming ahead), 1 reared up (its base rising
## past upright, its top bending forward again, its head looking ahead), as in the concept picture.
@export_range(0.0, 1.0) var rear := 0.0:
	set(value):
		rear = clampf(value, 0.0, 1.0)
		_send(&"rear", rear)
## Its mouth: 0 shut, 1 wide open (the lower jaw drops 40 degrees, the skull lifts 8).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## How far its body is bent round to one side behind the head, as when it turns: radians from behind
## the head to the tail (more than 0, the tail comes round to +X, its right).
@export_range(-1.5, 1.5) var curl := 0.0:
	set(value):
		curl = value
		_send(&"curl", value)
## Its tail hooked up and round, as in the concept picture: 0 straight, 1 hooked right over (from
## 19.5 m behind its muzzle).
@export_range(0.0, 1.0) var coil := 0.0:
	set(value):
		coil = clampf(value, 0.0, 1.0)
		_send(&"coil", coil)
## The low model (about an eighth of the full one's triangles), for far off.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model: about 4,800 triangles, Twilight Princess boss weight (spent on the head, the jaw,
## the eyes, the frill and mane and the fins' ragged edges), shown in place of the full one (`low`
## still shows the low one). Each model is loaded only when it is first shown, so with `game` on
## (set before it enters the tree) the full model is never loaded.
@export var game := false:
	set(value):
		game = value
		_show()
## Its eyes: 0 as in life, 1 big cartoon eyes (wary and old: gold, round-pupilled).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where its cartoon eyes look: x +1 towards its nose, -1 towards its tail; y +1 up, -1 down.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(Vector2(-1.0, -1.0), Vector2(1.0, 1.0))
		_send(&"eye_look", eye_look)
## Its cartoon eyes' lids: 0 open, 1 shut.
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()

static var _meshes := {}

var _material: ShaderMaterial
var _shown := {}
var _started := false


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`).
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at("_lo" if low_wanted else "")


## The game model's mesh (one surface, to wear `new_material()`).
static func game_mesh() -> Mesh:
	return _mesh_at("_game")


## A mesh rebuilt from its surfaces alone, without the importer's automatic LODs (they would bend
## in straight pieces).
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
		_meshes[path] = without_lods(found.mesh)
		made.free()
	return _meshes[path]


## A new material for these meshes, with the serpent's shape and colours set. Its driven settings
## are the game's to set: `phase`, `sway`, `humps`, `rear`, `curl`, `gape`, `cartoon_eyes`,
## `eye_look`, `blink`.
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	for setting: StringName in SHAPE:
		made.set_shader_parameter(setting, SHAPE[setting])
	for setting: StringName in LOOK:
		made.set_shader_parameter(setting, LOOK[setting])
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
	_send(&"humps", humps)
	_send(&"rear", rear)
	_send(&"gape", gape)
	_send(&"curl", curl)
	_send(&"coil", coil)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the fish are; set `sway`, `humps` and `beat` for
## its speed.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: its colours (see LOOK), `pattern` (how strongly the scales
## show), or any of its shape (see SHAPE; only to try things: the model is built for those numbers).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (all its models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


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
	# (its humps and tail swing past where the still model ends, its neck rears, it bends)
	mesh.extra_cull_margin = 0.35 * LENGTH
	mesh.name = "SeaSerpent" + ending
	add_child(mesh)
	return mesh
