class_name GulperEel
extends Node3D
## A pelican eel, or gulper eel (Eurypharynx pelecanoides), 0.80 m long: a small-eyed head that is almost all an
## enormous loose pouch of a mouth, on a long thin whip of a black body ending in a small pink-red glowing tail
## organ.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it goes. Its nose
## points along its own -Z (Godot's forward), its belly down; its origin is on its middle line, half way along, so
## it reaches 0.40 m ahead and 0.40 m behind. `scale` it for a bigger one. No sound.
##
## The swimming (an eel's wave down the whole body), the mouth (`gape`: the jaw swings down and the pouch
## balloons out like a net) and the tail's light (`glow`) are all drawn by the shader (no bones), and run on
## `phase`, 0 to 1 through one `beat`, in which a wave runs down its body `tail_beats` times (a whole number), so
## its motion comes round again exactly every beat. Either call `step(velocity, delta)` each frame, which moves
## `phase` on by delta / beat, or set `phase` yourself (for a picture that must loop: frame / frames in a beat).
## The same names and meanings as GameCommon's yellowfin tuna and sardine, so they are driven the same way.
##
## The models are creatures/gulper_eel/models/gulper_eel.glb (and _lo), built by tools/build_gulper_eel.py;
## gulper_eel.gdshader draws the markings, swims it and lights it.

const MODEL := "res://creatures/gulper_eel/models/gulper_eel%s.glb"
const SHADER := preload("res://creatures/gulper_eel/gulper_eel.gdshader")
## As the model is built (tools/build_gulper_eel.py): from the tip of its snout to the tips of its tail organ's filaments, and
## how deep and how wide its body is at its deepest (metres, at scale 1).
const LENGTH := 0.80
const DEPTH := 0.036
const WIDTH := 0.030
## Where the middle of the tail organ's bulb is with the body straight (in the node's own space, at scale 1): for
## a game that puts a light there (it moves with the body's wave: see the README).
const ORGAN_AT := Vector3(0.0, 0.0, 0.3795)

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 2.0
## How many waves run down its body in a beat.
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it beats: 1 as one swimming slowly (the tip of its whip swings about 0.06 m either way), 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far its mouth is open: 0 shut, 1 wide open (the jaw swings down and the pouch balloons out like a net).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## How strongly its tail organ glows (0 none, 1 as made, 2 twice as bright).
@export_range(0.0, 2.0) var glow := 1.0:
	set(value):
		glow = clampf(value, 0.0, 2.0)
		_send(&"glow", glow)
## The low model (about a twelfth of the triangles), for far off or for several of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (spent on the outline, the eye, the mouth and the lights) in place of the full one: what a game
## draws near. `low` still shows the low model. With it on, the full model is never loaded (each model is loaded
## when it is first shown), so a game's export may leave the full .glb out.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye (0 the eye as made, 1 the cartoon one: a dim, dopey little eye, pale blue round a big round pupil, half shut under a sleepy lid).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where the cartoon eye looks: x towards the snout (more than 0) or the tail, y up or down; -1..1.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(Vector2(-1.0, -1.0), Vector2(1.0, 1.0))
		_send(&"eye_look", eye_look)
## The cartoon eye's lid: 0 open, 1 shut.
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()

static var _meshes := {}

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D
var _started := false


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`): for drawing one
## without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## The game model's mesh (one surface, to wear `new_material()`): for drawing one without this node.
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game")


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase` (0..1 through one
## wave), `sway`, `gape`, `curl`, `glow`, `wave` and the colours (the top of the
## shader lists them).
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
	_send(&"sway", sway)
	_send(&"gape", gape)
	_send(&"glow", glow)
	_send(&"cartoon_eyes", cartoon_eyes)
	_send(&"eye_look", eye_look)
	_send(&"blink", blink)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat. (`velocity` is
## taken so that it is called as the other fish's are; set `sway` and `beat` from its speed yourself.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `curl` (bent round into a turn: radians from the head to the tail, more than
## 0 the tail comes round to its left, +X), `wave` (the length of the wave along its body, in body lengths), its
## colours (`skin`, `stretched`, `fin`, `mouth_inside`, `organ`, `organ_light`).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one wave it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


func _show() -> void:
	if not _started:
		return
	var which := "_lo" if low else ("_game" if game else "")
	# (each model is loaded the first time it is shown, so that a game with `game` on never loads the full one)
	if which == "" and _full == null:
		_full = _instance_of(which)
	if which == "_lo" and _low == null:
		_low = _instance_of(which)
	if which == "_game" and _game == null:
		_game = _instance_of(which)
	if _full:
		_full.visible = which == ""
	if _low:
		_low.visible = which == "_lo"
	if _game:
		_game.visible = which == "_game"


func _instance_of(which: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = _mesh_at(MODEL % which)
	mesh.material_override = _material
	# (its whip swings out past where the still model ends, and the pouch balloons below it)
	mesh.extra_cull_margin = 0.08
	mesh.name = "GulperEel" + which
	add_child(mesh)
	return mesh


## The mesh as imported but without the thinned LOD meshes Godot's importer adds: those were made from the still
## model, and a body bent in the shader then bends in straight pieces far off.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


static func _mesh_at(path: String) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		# (the game model without the importer's LODs; the full and low ones as they always were)
		_meshes[path] = without_lods(found.mesh) if path.ends_with("_game.glb") else found.mesh
		made.free()
	return _meshes[path]
