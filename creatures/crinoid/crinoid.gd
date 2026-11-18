class_name Crinoid
extends Node3D
## A crinoid, of one of three kinds (`kind`): a feather star of ten arms (a comatulid, after
## Florometra of the California coast), one of twenty arms, or a stalked sea lily (an isocrinid) on a
## long jointed stem. Feathery arms round a small cup, each a jointed stem with a comb of pinnules
## along both sides; a feather star perches on a ring of curved jointed cirri gripping the ground;
## the sea lily has whorls of cirri up its stem.
##
## How it looks and moves only: whatever moves it puts it where it is (a game lifts a swimming feather
## star up off the bottom itself). Up is +Y; **its origin is on the ground under the middle of its cup**
## (the feather star's cirri, the sea lily's holdfast stand on y = 0). `scale` it for a bigger or
## smaller one. No sound, no eyes.
##
## Its arms bend in the shader (no bones). They sway and bend with the current on the global shader
## uniform `water_clock` (seconds; if the project does not declare it, the first crinoid adds it and runs
## it, as GameCommon's kelp does), each crinoid a little out of step by where it stands. `furl` rolls
## every arm up and in until it is a ball; `swim` has the arms beat down in turn, as a feather star
## swims, on `phase` (0 to 1 through one stroke of `beat` seconds), so a stroke loops exactly. Either
## call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or set `phase`
## yourself. It has no `gape` and no `curl`.
##
## Three models of each kind: the full one (every pinnule a strip of its own), the game one (`game`:
## a Twilight Princess weight, the pinnules drawn on cards) and the low one (`low`). Each is loaded
## only when it is first shown, so with `game` on the full models are never loaded.
##
## A game that draws its own needs no Crinoid node: `Crinoid.mesh_of(kind, low)` or
## `Crinoid.game_mesh(kind)` and `Crinoid.new_material(kind, colour)`.
##
## The models are creatures/crinoid/models/crinoid_<kind>.glb (and _game, _lo), built by
## tools/build_crinoid.py; crinoid.gdshader colours them, draws the cards' pinnules and moves them.

enum Kind { FEATHER_STAR, FEATHER_STAR_TWENTY, SEA_LILY }
enum Colour { YELLOW, RED, BLACK_WHITE }

const MODEL := "res://creatures/crinoid/models/crinoid_%s%s.glb"
# (loaded, not preloaded: the shader reads the global `water_clock`, which must be there first)
const SHADER := "res://creatures/crinoid/crinoid.gdshader"
const CLOCK := &"water_clock"
## Each kind's name in its models' file names.
const NAMES := {Kind.FEATHER_STAR: "feather_star", Kind.FEATHER_STAR_TWENTY: "feather_star_twenty", Kind.SEA_LILY: "sea_lily"}
## As the models are built and the shader lays them at rest (metres, at scale 1): across its arms'
## tips, and how high it stands.
const ACROSS := {Kind.FEATHER_STAR: 0.3, Kind.FEATHER_STAR_TWENTY: 0.28, Kind.SEA_LILY: 0.23}
const HEIGHT := {Kind.FEATHER_STAR: 0.063, Kind.FEATHER_STAR_TWENTY: 0.061, Kind.SEA_LILY: 0.5}
## What each kind sets in the shader: its shape (as built: the build script's SHAPE line) and how its
## arms lie at rest.
const KINDS := {
	Kind.FEATHER_STAR: {"arm_length": 0.15, "arms": 10.0, "arm_rise": 0.6, "root_radius": 0.0065,
		"root_height": 0.0205, "stalk_height": 0.0, "rest_bend": -0.55, "tip_bend": -0.45,
		"pin_length": 0.016, "pin_from": 0.0075, "card_width": 0.011937},
	Kind.FEATHER_STAR_TWENTY: {"arm_length": 0.14, "arms": 20.0, "arm_rise": 0.6, "root_radius": 0.0075,
		"root_height": 0.0205, "stalk_height": 0.0, "rest_bend": -0.5, "tip_bend": -0.45,
		"pin_length": 0.014, "pin_from": 0.007, "card_width": 0.010445},
	Kind.SEA_LILY: {"arm_length": 0.13, "arms": 10.0, "arm_rise": 0.75, "root_radius": 0.0075,
		"root_height": 0.4215, "stalk_height": 0.42, "rest_bend": -0.7, "tip_bend": 0.75,
		"pin_length": 0.014, "pin_from": 0.0065, "card_width": 0.010445},
}
## The built-in colours: arm, bands, pinnule, pinnule tip, cup, cirri, stalk, and how banded.
const COLOURS := {
	Colour.YELLOW: [Color(0.95, 0.72, 0.08), Color(0.72, 0.42, 0.04), Color(1.0, 0.84, 0.22), Color(1.0, 0.95, 0.6),
		Color(0.8, 0.58, 0.1), Color(0.72, 0.52, 0.14), Color(0.85, 0.7, 0.35), 0.3],
	Colour.RED: [Color(0.75, 0.1, 0.06), Color(0.95, 0.72, 0.58), Color(0.86, 0.16, 0.1), Color(1.0, 0.6, 0.5),
		Color(0.6, 0.08, 0.05), Color(0.55, 0.12, 0.08), Color(0.62, 0.26, 0.2), 0.35],
	Colour.BLACK_WHITE: [Color(0.05, 0.05, 0.06), Color(0.95, 0.95, 0.92), Color(0.07, 0.07, 0.08), Color(0.95, 0.95, 0.92),
		Color(0.1, 0.1, 0.1), Color(0.16, 0.16, 0.16), Color(0.22, 0.22, 0.22), 0.85],
}
const COLOUR_SETTINGS := ["arm_colour", "band_colour", "pinnule", "pinnule_tip", "cup_colour", "cirri_colour", "stalk_colour", "bands"]

static var _meshes := {}
## Whether a crinoid added `water_clock` (and so must run it), and the frame it last moved it.
static var _runs_clock := false
static var _clock := 0.0
static var _clock_frame := -1

## Which kind of crinoid: its shape.
@export var kind := Kind.FEATHER_STAR:
	set(value):
		kind = value
		_dress()
		_show()
## Its colours.
@export var colour := Colour.YELLOW:
	set(value):
		colour = value
		_dress()
## Seconds one swimming stroke takes.
@export var beat := 1.2
## How much the current sways it: 1 as it lives, 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## 0 its arms spread; 1 every arm rolled up and in, the whole animal a ball.
@export_range(0.0, 1.0) var furl := 0.0:
	set(value):
		furl = clampf(value, 0.0, 1.0)
		_send(&"furl", furl)
## 0 still; 1 swimming, its arms beating down in turn (the game lifts it).
@export_range(0.0, 1.0) var swim := 0.0:
	set(value):
		swim = clampf(value, 0.0, 1.0)
		_send(&"swim", swim)
## The low model (far off, many of them).
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (a Twilight Princess weight, its pinnules drawn on cards) in place of the full one;
## `low` still shows the low model. With it on, the full model is never loaded.
@export var game := false:
	set(value):
		game = value
		_show()
## How far through a stroke it is, 0 to 1 (only the fraction counts).
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


## A new material for a kind's meshes, in its colours. Its shader settings are the game's to set:
## `phase` (0..1), `sway`, `furl`, `swim`, and those `set_shader_parameter` lists. (It adds the
## global `water_clock` if the project has none; then a Crinoid node, or the game, must run it.)
static func new_material(kind_wanted: Kind, colour_wanted := Colour.YELLOW) -> ShaderMaterial:
	_add_clock()
	var made := ShaderMaterial.new()
	made.shader = load(SHADER)
	_wear(made, kind_wanted, colour_wanted)
	return made


static func _wear(on: ShaderMaterial, kind_wanted: Kind, colour_wanted: Colour) -> void:
	var settings: Dictionary = KINDS[kind_wanted]
	for setting: String in settings:
		on.set_shader_parameter(setting, settings[setting])
	var colours: Array = COLOURS[colour_wanted]
	for i in COLOUR_SETTINGS.size():
		on.set_shader_parameter(COLOUR_SETTINGS[i], colours[i])


static func _add_clock() -> void:
	if not ProjectSettings.has_setting("shader_globals/" + CLOCK) and not Engine.has_meta(CLOCK):
		RenderingServer.global_shader_parameter_add(CLOCK, RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.0)
		Engine.set_meta(CLOCK, true)
		_runs_clock = true


func _init() -> void:
	_material = new_material(kind, colour)


func _ready() -> void:
	_body = MeshInstance3D.new()
	_body.material_override = _material
	# (its arms sway, beat and its stalk leans out past the still model's box)
	_body.extra_cull_margin = 0.15
	_body.name = "Crinoid"
	add_child(_body)
	_show()
	_send(&"sway", sway)
	_send(&"furl", furl)
	_send(&"swim", swim)
	_send(&"phase", phase)


func _process(delta: float) -> void:
	# (runs the water's clock when no one else does: once a frame, whichever crinoid comes first)
	if _runs_clock and _clock_frame != Engine.get_process_frames():
		_clock_frame = Engine.get_process_frames()
		_clock += delta
		RenderingServer.global_shader_parameter_set(CLOCK, _clock)


## Each frame: moves its stroke on (`velocity` is taken so that it is called as the fish are, and is
## not used: set `swim` yourself).
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: its colours (`arm_colour`, `band_colour`, `pinnule`,
## `pinnule_tip`, `cup_colour`, `cirri_colour`, `stalk_colour`), `bands`, `band_count`, or how its
## arms lie at rest (`rest_bend`, `tip_bend`). `kind` and `colour` set most of them again.
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
