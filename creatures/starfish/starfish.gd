class_name Starfish
extends Node3D
## A sea star, of one of three kinds (`kind`): a classic five-armed star with a knobbly skin (after
## the ochre star, Pisaster ochraceus, of the California coast), a sunflower star (Pycnopodia
## helianthoides) with twenty arms round a broad soft disc, or a brittle star (after the spiny
## brittle star, Ophiothrix spiculata) with a small disc and five long thin spiny arms that writhe.
## Rows of tube feet beneath every arm (seen when it is turned over).
##
## How it looks and moves only: whatever moves it puts it where it is and turns it. Arm 0 points
## along its own -Z, up is +Y; **its origin is on the ground under the middle of its disc** (its
## tube feet stand on y = 0). `scale` it for a bigger or smaller one. No sound, no eyes.
##
## Its arms bend in the shader (no bones): as it creeps their tips lift and fall and they snake
## a little from side to side (a brittle star's writhe), and `curl_up` lifts them all and rolls
## their tips over. Everything that moves runs on `phase`, 0 to 1 through one `beat`, so its motion
## comes round again exactly every beat. Either call `step(velocity, delta)` each frame, which moves
## `phase` on by delta / beat, or set `phase` yourself. It has no `gape` and no `curl`.
##
## Three models of each kind: the full one (close pictures), the game one (`game`: a Twilight
## Princess weight, its triangles spent on its outline) and the low one (`low`). Each is loaded only
## when it is first shown, so with `game` on the full models are never loaded.
##
## A game that draws its own needs no Starfish node: `Starfish.mesh_of(kind, low)` or
## `Starfish.game_mesh(kind)` and `Starfish.new_material(kind, colour)`.
##
## The models are creatures/starfish/models/starfish_<kind>.glb (and _game, _lo), built by
## tools/build_starfish.py; starfish.gdshader colours them and bends their arms.

enum Kind { CLASSIC, SUNFLOWER, BRITTLE }
## Built-in colours. NATURAL is the kind's own (the classic purple, the sunflower purple and
## orange, the brittle star orange banded with brown).
enum Colour { NATURAL, PURPLE, ORANGE, OCHRE, RED, PINK, BLUE, BROWN }

const MODEL := "res://creatures/starfish/models/starfish_%s%s.glb"
const SHADER := preload("res://creatures/starfish/starfish.gdshader")
## Each kind's name in its models' file names.
const NAMES := {Kind.CLASSIC: "classic", Kind.SUNFLOWER: "sunflower", Kind.BRITTLE: "brittle"}
## As the models are built (metres, at scale 1): from tip to tip at its widest, how high it stands
## (the top of its disc), and from the middle to an arm's tip.
const ACROSS := {Kind.CLASSIC: 0.26, Kind.SUNFLOWER: 0.58, Kind.BRITTLE: 0.19}
const HEIGHT := {Kind.CLASSIC: 0.0345, Kind.SUNFLOWER: 0.0305, Kind.BRITTLE: 0.0068}
const ARM := {Kind.CLASSIC: 0.135, Kind.SUNFLOWER: 0.29, Kind.BRITTLE: 0.1}
## What each kind sets in the shader: its shape (as built), how it moves, its knobs and bands.
const KINDS := {
	Kind.CLASSIC: {"arm_length": 0.135, "arms": 5.0, "lift_from": 0.3, "tip_wave": 0.35, "writhe": 0.08,
		"knob_cell": 0.0075, "knob_size": 0.0019, "knob_amount": 1.0, "mottle": 0.3, "bands": 0.0},
	Kind.SUNFLOWER: {"arm_length": 0.29, "arms": 20.0, "lift_from": 0.38, "tip_wave": 0.6, "writhe": 0.25,
		"knob_cell": 0.0075, "knob_size": 0.0019, "knob_amount": 0.55, "mottle": 0.55, "bands": 0.0},
	Kind.BRITTLE: {"arm_length": 0.1, "arms": 5.0, "lift_from": 0.12, "tip_wave": 0.5, "writhe": 1.1,
		"knob_cell": 0.0075, "knob_size": 0.0019, "knob_amount": 0.0, "mottle": 0.15, "bands": 0.8,
		"band_gap": 0.012},
}
## Each kind's own colours (skin, skin_dark, knob, under, foot).
const NATURAL := {
	Kind.CLASSIC: [Color(0.36, 0.12, 0.38), Color(0.2, 0.06, 0.22), Color(0.92, 0.88, 0.8), Color(0.88, 0.72, 0.52), Color(0.95, 0.78, 0.58)],
	Kind.SUNFLOWER: [Color(0.62, 0.3, 0.45), Color(0.88, 0.45, 0.18), Color(0.95, 0.75, 0.8), Color(0.9, 0.72, 0.62), Color(0.98, 0.8, 0.7)],
	Kind.BRITTLE: [Color(0.82, 0.42, 0.16), Color(0.36, 0.14, 0.1), Color(0.95, 0.85, 0.7), Color(0.85, 0.7, 0.55), Color(0.9, 0.75, 0.6)],
}
## The built-in colours: skin and its darker mottle (the knobs, underside and feet keep the kind's).
const COLOURS := {
	Colour.PURPLE: [Color(0.36, 0.12, 0.38), Color(0.2, 0.06, 0.22)],
	Colour.ORANGE: [Color(0.9, 0.42, 0.08), Color(0.7, 0.25, 0.05)],
	Colour.OCHRE: [Color(0.78, 0.56, 0.18), Color(0.55, 0.36, 0.1)],
	Colour.RED: [Color(0.72, 0.1, 0.08), Color(0.45, 0.05, 0.05)],
	Colour.PINK: [Color(0.92, 0.5, 0.58), Color(0.75, 0.32, 0.42)],
	Colour.BLUE: [Color(0.18, 0.32, 0.72), Color(0.1, 0.18, 0.45)],
	Colour.BROWN: [Color(0.45, 0.28, 0.16), Color(0.28, 0.16, 0.09)],
}

static var _meshes := {}

## Which kind of sea star: its shape and how it moves.
@export var kind := Kind.CLASSIC:
	set(value):
		kind = value
		_dress()
		_show()
## Its colour (NATURAL: the kind's own).
@export var colour := Colour.NATURAL:
	set(value):
		colour = value
		_dress()
## Seconds one beat takes: everything it does comes round again each beat (a sea star is slow).
@export var beat := 6.0
## How strongly it moves: 1 as it lives, 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## 0 lying flat; 1 every arm lifted and its tip rolled over.
@export_range(0.0, 1.0) var curl_up := 0.0:
	set(value):
		curl_up = clampf(value, 0.0, 1.0)
		_send(&"curl_up", curl_up)
## The low model (far off, many of them).
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (a Twilight Princess weight: 1,500 to 2,800 triangles, spent on the outline) in
## place of the full one; `low` still shows the low model. With it on, the full model is never loaded.
@export var game := false:
	set(value):
		game = value
		_show()
## How far through a beat it is, 0 to 1 (only the fraction counts).
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)

var _material: ShaderMaterial
var _body: MeshInstance3D


## A kind's full mesh, or its low one, for a game that draws its own (loaded once and kept).
static func mesh_of(kind_wanted: Kind, low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % [NAMES[kind_wanted], "_lo" if low_wanted else ""])


## A kind's game mesh (loaded once and kept).
static func game_mesh(kind_wanted: Kind) -> Mesh:
	return _mesh_at(MODEL % [NAMES[kind_wanted], "_game"])


static func _mesh_at(path: String) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh)
		made.free()
	return _meshes[path]


## `mesh` again without the lower levels of detail Godot's importer makes for it: made from the
## still model, they would bend in straight pieces.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


## A new material for a kind's meshes, in its colour. Its shader settings are the game's to set:
## `phase` (0..1), `sway`, `curl_up` and those `set_shader_parameter` lists.
static func new_material(kind_wanted: Kind, colour_wanted := Colour.NATURAL) -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	_wear(made, kind_wanted, colour_wanted)
	return made


static func _wear(on: ShaderMaterial, kind_wanted: Kind, colour_wanted: Colour) -> void:
	var settings: Dictionary = KINDS[kind_wanted]
	for setting: String in settings:
		on.set_shader_parameter(setting, settings[setting])
	var own: Array = NATURAL[kind_wanted]
	var names := ["skin", "skin_dark", "knob", "under", "foot"]
	for i in names.size():
		on.set_shader_parameter(names[i], own[i])
	if colour_wanted != Colour.NATURAL:
		on.set_shader_parameter(&"skin", COLOURS[colour_wanted][0])
		on.set_shader_parameter(&"skin_dark", COLOURS[colour_wanted][1])


func _init() -> void:
	_material = ShaderMaterial.new()
	_material.shader = SHADER
	_dress()


func _ready() -> void:
	_body = MeshInstance3D.new()
	_body.material_override = _material
	# (its arms lift and snake out past the still model's box)
	_body.extra_cull_margin = 0.3
	_body.name = "Starfish"
	add_child(_body)
	_show()
	_send(&"sway", sway)
	_send(&"curl_up", curl_up)
	_send(&"phase", phase)


## Each frame: moves it on through its beat (`velocity` is taken so that it is called as the fish
## are, and is not used).
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: its colours (`skin`, `skin_dark`, `knob`, `under`, `foot`),
## `mottle`, `bands`, `knob_amount`, `vivid`, or how it moves (`tip_wave`, `writhe`). `kind` and
## `colour` set most of them again.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_send(setting, value)


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


func _dress() -> void:
	if _material:
		_wear(_material, kind, colour)


func _show() -> void:
	if _body == null:
		return
	# (only the model shown is loaded)
	if low:
		_body.mesh = mesh_of(kind, true)
	elif game:
		_body.mesh = game_mesh(kind)
	else:
		_body.mesh = mesh_of(kind, false)
