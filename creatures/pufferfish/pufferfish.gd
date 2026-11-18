class_name Pufferfish
extends Node3D
## A spotted pufferfish, after the bullseye puffer (Sphoeroides annulatus) of the Californian and
## Mexican coast, 0.3 m long: a blunt boxy body, a broad head, a small mouth with a beak of four
## teeth fused into two plates, big round eyes set high, tiny dorsal and anal fins far back that
## buzz, small pectoral fins that fan, and a rounded tail; sandy with dark spots and a pale belly.
## Small spines lie flat along its skin, pointing back.
##
## `puff` (0 to 1) blows it up into a ball: its body swells about its middle, its tail and fins
## are left sticking out small, and every spine stands straight out. Fully puffed it is
## `PUFFED_WIDTH` across (`PUFFED_REACH` with its spines): a game can make it too big to swallow,
## and its spines hurt. `gape` opens its beak (0 shut, 1 wide open).
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z, its belly down; its origin is on its middle line, half
## way along its length (puffed, the ball's middle is 0.036 m ahead of it). `scale` it for a
## bigger or smaller one. No sound.
##
## It swims slowly by sculling with its dorsal and anal fins and fanning its pectoral fins; its
## body is stiff, and its tail steers. Everything that moves runs on `phase`, 0 to 1 through one
## `beat`: in a beat its tail beats `tail_beats` times, its pectoral fins fan `strokes` times and
## its dorsal and anal fins buzz `buzzes` times (whole numbers), so its motion comes round again
## exactly every beat. Either call `step(velocity, delta)` each frame, which moves `phase` on by
## delta / beat (and works its fins and tail harder the faster it is going), or set `phase`
## yourself (for a picture that must loop).
##
## Three models: the full one, the game one (`game`: about 1,800 triangles, the same outline) and
## the low one (`low`). `cartoon_eyes`, `eye_look` and `blink` give it a cartoon eye: huge, round
## and permanently alarmed.
##
## A game that keeps its own MeshInstance3Ds needs no Pufferfish node: `Pufferfish.mesh_of(low)`
## (or `Pufferfish.game_mesh()`) is the mesh and `Pufferfish.new_material()` a material for it,
## whose shader settings (phase, puff, gape, sway, row, curl and the rest) the game sets itself.
##
## The models are creatures/pufferfish/models/pufferfish.glb (and _game, _lo), built by
## tools/build_pufferfish.py; pufferfish.gdshader moves it and draws its markings.

const MODEL := "res://creatures/pufferfish/models/pufferfish%s.glb"
const SHADER := preload("res://creatures/pufferfish/pufferfish.gdshader")
## As the model is built (tools/build_pufferfish.py): from the front of its beak to the tip of its
## tail, and how deep and how wide its body is at its deepest, fins and spines left out (metres,
## at scale 1).
const LENGTH := 0.3
const DEPTH := 0.098
const WIDTH := 0.087
## Fully puffed (`puff` 1): how wide the ball of its body is across (metres, at scale 1), and how
## far it reaches across from spine tip to spine tip. Its tail still sticks out behind: puffed,
## it is about 0.29 m from its beak to its tail tip.
const PUFFED_WIDTH := 0.21
const PUFFED_REACH := 0.253
## Where the ball's middle is, puffed (metres, at scale 1, from its origin).
const PUFFED_MIDDLE := Vector3(0.0, 0.0, -0.036)

static var _meshes := {}

## Seconds one beat takes: everything it does comes round again each beat. 0 for a caller that
## sets `phase` itself (`step` then leaves `phase` alone).
@export var beat := 2.0
## How many times in a beat its tail beats, its pectoral fins fan and its dorsal and anal fins
## buzz.
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send(&"tail_beats", float(tail_beats))
@export var strokes := 4:
	set(value):
		strokes = maxi(value, 0)
		_send(&"strokes", float(strokes))
@export var buzzes := 8:
	set(value):
		buzzes = maxi(value, 0)
		_send(&"buzzes", float(buzzes))
## How widely its tail swings when it is going nowhere: 0 still, 1 a tenth of its length each
## way. `step` swings it wider the faster it goes.
@export_range(0.0, 1.5) var sway := 0.2:
	set(value):
		sway = value
		_effort = value
		_send(&"sway", _effort)
## How hard its fins work: 1 as it potters about, 0 held still. `step` works them harder the
## faster it goes.
@export_range(0.0, 1.5) var row := 1.0:
	set(value):
		row = value
		_rowing = value
		_send(&"row", value)
## Its mouth: 0 shut, 1 wide open (its lower jaw and beak swing down, its upper lip lifts).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## Blown up: 0 as it swims, 1 a ball `PUFFED_WIDTH` across with every spine standing straight
## out. Ease it in and out (a real one takes about a second to blow up).
@export_range(0.0, 1.0) var puff := 0.0:
	set(value):
		puff = clampf(value, 0.0, 1.0)
		_send(&"puff", puff)
## The speed (m/s, at scale 1) at which `step` has it working its hardest.
@export var top_speed := 0.4
## The low model (far off, phones, many at once) in place of the full one (or the game one).
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about 1,800 triangles, built to keep the full model's outline) in place of the
## full one (about 11,700). With `game` on, the full model is never loaded: each model is loaded
## only when it is first shown. `low` still shows the low model.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye (0 the eye as it is; 1 huge and round, a white all round a small iris and a
## pinprick pupil: permanently alarmed).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where the cartoon eyes look (-1..1 each way): x towards the nose (+) or the tail (-), y up (+)
## or down (-). Both eyes look the same way.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(Vector2(-1.0, -1.0), Vector2(1.0, 1.0))
		_send(&"eye_look", eye_look)
## The cartoon eyes' lids: 0 open, 1 shut (the lids come together and the eye squashes).
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## How far through a beat it is, 0 to 1. `step` moves it on; or set it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D
var _effort := 0.2
var _rowing := 1.0


## The mesh (`low` for the low one), for a game that keeps its own MeshInstance3Ds. Each is
## loaded once and kept.
static func mesh_of(low_wanted := false) -> Mesh:
	var path := MODEL % ("_lo" if low_wanted else "")
	if not _meshes.has(path):
		_meshes[path] = _load_mesh(path)
	return _meshes[path]


## The game model's mesh (about 1,800 triangles, the full model's outline), for a game that keeps
## its own MeshInstance3Ds: loaded once and kept, without the importer's automatic LODs (thinned
## meshes bend in straight pieces in the shader). Loading it never loads the full one.
static func game_mesh() -> Mesh:
	var path := MODEL % "_game"
	if not _meshes.has(path):
		_meshes[path] = without_lods(_load_mesh(path))
	return _meshes[path]


## A mesh with the same surfaces and none of the importer's LODs.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


## A new material for its mesh. Its shader settings are the game's to set: phase (0..1),
## tail_beats, strokes, buzzes, sway, row, gape (0..1), puff (0..1), curl, flash, rim, tint, the
## colours and the cartoon eye's (the top of the shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


static func _load_mesh(path: String) -> Mesh:
	var made := (load(path) as PackedScene).instantiate()
	var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
	var mesh := found.mesh
	made.free()
	return mesh


func _init() -> void:
	_material = new_material()
	_effort = sway


func _ready() -> void:
	_show()
	for setting: StringName in [&"tail_beats", &"strokes", &"buzzes"]:
		_send(setting, float(get(setting)))
	for setting: StringName in [&"gape", &"puff", &"cartoon_eyes", &"eye_look", &"blink", &"phase"]:
		_send(setting, get(setting))
	_send(&"sway", _effort)
	_send(&"row", _rowing)


## Each frame, after putting it where it is: moves its beat on by `delta` seconds (unless `beat`
## is 0), and works its fins and tail harder the faster it is going (`velocity`, world, m/s;
## Vector3.ZERO for one that hovers, and it moves as `sway` and `row` say).
func step(velocity: Vector3, delta: float) -> void:
	if beat > 0.0:
		phase += delta / beat
	var size := maxf(global_basis.get_scale().z, 0.001) if is_inside_tree() else 1.0
	var speed := clampf(velocity.length() / (top_speed * size), 0.0, 1.0)
	_effort = move_toward(_effort, maxf(sway, speed), delta * 1.5)
	_rowing = move_toward(_rowing, maxf(row, row + 0.5 * speed), delta * 1.5)
	_send(&"sway", _effort)
	_send(&"row", _rowing)


## Sets one of the shader's settings: how it moves (curl), a game's effects (flash, rim, tint),
## its colours (back, spot_colour, belly, fin_colour, beak_colour, mouth), spots, sheen, or the
## cartoon eye's (eye_size, iris, iris_size, pupil_size, lid, lower_lid).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_send(setting, value)


## The material it is drawn with (all three models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# Only the model shown is loaded and put in, when it is first shown.
func _show() -> void:
	if not is_node_ready():
		return
	if low and not _low:
		_low = _instance_of("Pufferfish_lo", mesh_of(true))
	elif not low and game and not _game:
		_game = _instance_of("Pufferfish_game", game_mesh())
	elif not low and not game and not _full:
		_full = _instance_of("Pufferfish", mesh_of(false))
	if _full:
		_full.visible = not low and not game
	if _low:
		_low.visible = low
	if _game:
		_game.visible = not low and game


func _instance_of(called: String, model: Mesh) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = model
	mesh.material_override = _material
	# (puffed, it is a ball with its spines out, far past the still model's box)
	mesh.extra_cull_margin = PUFFED_REACH * 0.6
	mesh.name = called
	add_child(mesh)
	return mesh
