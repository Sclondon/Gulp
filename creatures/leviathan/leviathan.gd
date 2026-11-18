class_name Leviathan
extends Node3D
## The leviathan: an original sea monster, 40 m long, an immense armoured serpent-whale, massive and
## hunched. A huge deep head a quarter of its length, a heavy brow ridge over a small pale eye sunk in
## its socket, a great jaw of long uneven interlocking teeth (both rows show with the mouth shut), a
## thick neck rising to the hump of its shoulders (12 m deep there), a deep barrel body that tapers only
## in its last third, a long tail that can curl up and round (`coil`). Overlapping rows of big rounded
## scutes down its sides, keeled plates along its spine, heavy ribbed plates at the gill and over the
## jaw's hinge; tattered fins torn through with holes (long pectorals, pelvics, a dorsal sail, a tall
## tail fin, saw-toothed fringes along its tail); a crusted barnacle colony on its shoulders; old
## harpoons at all angles, their ropes wrapped round it and trailing; an anchor hooked in its flank.
## Its mouth opens very wide (`gape`: it swallows things whole).
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down; its origin is on its
## middle line, half way along, so it reaches 20 m ahead and 20 m behind. `scale` it for a bigger
## or smaller one. No sound.
##
## It swims SIDE TO SIDE, slowly, with its long tail, by a bend drawn by the shader (no bones);
## its ropes sway and its fins' torn edges ripple with it. `curl` bends it round for a turn,
## `coil` curls its tail up and round as in the concept picture.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat. Either
## call `step(velocity, delta)` each frame, or set `phase` yourself. The same names and meanings as
## GameCommon's fish.
##
## Its shader is creatures/sea_monster/sea_monster.gdshader, shared with the sea serpent (one
## shader program for both); this script sends it the leviathan's shape and colours.
## The models are creatures/leviathan/models/leviathan.glb (full), _game and _lo, built by
## tools/build_leviathan.py.

const MODEL := "res://creatures/leviathan/models/leviathan%s.glb"
const SHADER := preload("res://creatures/sea_monster/sea_monster.gdshader")
## As the model is built (tools/build_leviathan.py): from the tip of its snout to the tip of its
## tail fin, and how deep and how wide its body is at its deepest (metres, at scale 1), fins left out.
const LENGTH := 40.0
const DEPTH := 12.1
const WIDTH := 8.4

## Its shape, as the build script has it (sent to the shader): see sea_monster.gdshader.
const SHAPE := {
	&"kind": 0,
	&"body_length": 40.0,
	&"joint": 37.4,
	&"corner": 9.0,
	&"hinge_y": -1.7,
	&"hinge_spread": 1.3,
	&"gape_max": 1.05,
	&"lift_max": 0.22,
	&"jaw_from": 0.35,
	&"mouth_a": -0.8,
	&"mouth_b": -0.1,
	&"reach": 0.06,
	&"reach_poly": Vector4(0.06, -0.36, 0.62, 0.6),
	&"wave": 0.9,
	&"hump_height": 0.0,
	&"flap": 0.9,
	&"trail": 0.45,
	&"rope_sway": 1.4,
	&"weed_sway": 0.3,
	&"coil_at": 27.0,
	&"coil_span": 11.0,
	&"coil_max": 3.0,
	# (EYE_FRAME, as tools/build_leviathan.py prints it)
	&"eye_centre": Vector3(2.65097, 1.75, -13.45),
	&"eye_out": Vector3(0.9535, 0.2478, -0.1717),
	&"eye_fwd": Vector3(-0.1662, -0.0432, -0.9852),
	&"eye_up": Vector3(-0.2515, 0.9679, 0.0),
	# (the build script prints -2.17: the skin rises round the eye in its socket; 0 here lets the cartoon eye's rim
	# sink into the socket's walls, so it stays sunk under the brow)
	&"eye_sag": 0.0,
	&"eye_radius": 0.3,
	&"eye_grow": 1.35,
	&"eye_at_side": Vector2(6.55, 1.75),
}
## Its colours and its eye's look (sent to the shader; `set_shader_parameter` changes them).
const LOOK := {
	&"back": Color(0.1, 0.25, 0.23),
	&"flank": Color(0.22, 0.43, 0.39),
	&"belly": Color(0.62, 0.68, 0.57),
	&"seam": Color(0.03, 0.08, 0.07),
	&"moss": Color(0.21, 0.31, 0.12),
	&"fin": Color(0.24, 0.41, 0.37),
	&"fin_edge": Color(0.62, 0.68, 0.58),
	&"mouth": Color(0.42, 0.13, 0.13),
	&"tooth": Color(0.88, 0.84, 0.7),
	&"shell": Color(0.74, 0.72, 0.64),
	&"wood": Color(0.3, 0.2, 0.12),
	&"iron": Color(0.15, 0.1, 0.075),
	&"rope": Color(0.46, 0.37, 0.22),
	&"pattern": 1.0,
	# The eye: ancient and weary, small and sunk under its brow. A pale milky iris filling most of it
	# (no white button), a small dark pupil, the white a dull grey-green; a heavy lid down over its top.
	&"sclera": Color(0.5, 0.56, 0.48),
	&"iris_light": Color(0.86, 0.92, 0.84),
	&"iris_dark": Color(0.5, 0.62, 0.56),
	&"pupil_size": Vector2(0.13, 0.13),
	&"iris_size": 0.8,
	&"eye_glow": 0.35,
	&"lid_up_k": Vector3(0.12, -0.14, -0.1),
	&"lid_down_k": Vector3(-0.55, 0.05, 0.12),
	&"lid_line": Vector2(0.2, 0.08),
}

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 8.0
## How many times in a beat its tail beats (side to side and back).
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it beats: 1 cruising (its tail fin swings about 2 m each way), 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Its mouth: 0 shut, 1 wide open (the lower jaw drops 60 degrees about the corner of its mouth and
## the skull lifts 13 degrees: wide enough to swallow a whale).
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
## Its tail curled up and round, as in the concept picture: 0 straight, 1 hooked right over (three
## radians from 27 m behind its snout). Hold it while it idles or turns; 0 for swimming ahead.
@export_range(0.0, 1.0) var coil := 0.0:
	set(value):
		coil = clampf(value, 0.0, 1.0)
		_send(&"coil", coil)
## The low model (about a seventh of the full one's triangles), for far off.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model: about 7,900 triangles, Twilight Princess boss weight (spent on the head, the jaw,
## the teeth, the eyes, the scutes that break its outline, the fins' torn edges and the barnacles), shown in place of the
## full one (`low` still shows the low one). Each model is loaded only when it is first shown, so
## with `game` on (set before it enters the tree) the full model is never loaded.
@export var game := false:
	set(value):
		game = value
		_show()
## Its eyes: 0 as in life, 1 cartoon eyes (small and weary still: pale and milky, a heavy lid).
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


## A new material for these meshes, with the leviathan's shape and colours set. Its driven settings
## are the game's to set: `phase`, `sway`, `curl`, `gape`, `cartoon_eyes`, `eye_look`, `blink`.
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
	_send(&"gape", gape)
	_send(&"curl", curl)
	_send(&"coil", coil)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the fish are; set `sway` and `beat` for its speed.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: its colours (see LOOK), `pattern` (how strongly the grooves
## and belly scutes show), or any of its shape (see SHAPE; only to try things: the model is built for those numbers).
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
	# (its tail swings past where the still model ends, it bends, and its jaw drops)
	mesh.extra_cull_margin = 0.35 * LENGTH
	mesh.name = "Leviathan" + ending
	add_child(mesh)
	return mesh
