class_name SeaUrchin
extends Node3D
## A sea urchin, of one of three kinds (`kind`): a long-spined black one (after the crowned urchin,
## Centrostephanus coronatus, of the California coast), the short-spined purple urchin
## (Strongylocentrotus purpuratus), or a slate pencil urchin (Heterocentrotus mamillatus) with thirty
## thick blunt spines. A round flattened test (shell) thick with spines, a few tube feet reaching
## out as threads, five teeth at its mouth beneath.
##
## How it looks and moves only: whatever moves it puts it where it is. Up is +Y; **its origin is on
## the ground under the middle of its test** (its lowest spines stand on y = 0). `scale` it for a
## bigger or smaller one. No sound, no eyes.
##
## Every spine is turned in the shader about its own root (no bones): each sways a little in its own
## time, and all lean towards `threat`, a direction in the urchin's own space whose length is how
## alarmed it is (0..1): the spines on that side tip in towards it, as an urchin points its spines
## at what touches it. Everything that moves runs on `phase`, 0 to 1 through one `beat`, so it comes
## round again exactly every beat. Either call `step(velocity, delta)` each frame, which moves `phase`
## on by delta / beat, or set `phase` yourself. It has no `gape` and no `curl`.
##
## Three models of each kind: the full one, the game one (`game`: a Twilight Princess weight) and the
## low one (`low`). Each is loaded only when it is first shown, so with `game` on the full models
## are never loaded.
##
## A game that draws its own needs no SeaUrchin node: `SeaUrchin.mesh_of(kind, low)` or
## `SeaUrchin.game_mesh(kind)` and `SeaUrchin.new_material(kind)`.
##
## The models are creatures/sea_urchin/models/sea_urchin_<kind>.glb (and _game, _lo), built by
## tools/build_sea_urchin.py; sea_urchin.gdshader colours them and turns the spines.

enum Kind { LONG_SPINED, PURPLE, SLATE_PENCIL }

const MODEL := "res://creatures/sea_urchin/models/sea_urchin_%s%s.glb"
const SHADER := preload("res://creatures/sea_urchin/sea_urchin.gdshader")
## Each kind's name in its models' file names.
const NAMES := {Kind.LONG_SPINED: "long_spined", Kind.PURPLE: "purple", Kind.SLATE_PENCIL: "slate_pencil"}
## As the models are built (metres, at scale 1): the test's width (without spines), and how far its
## spines reach out from its middle line at rest, as a radius: it pricks what comes nearer than that.
const TEST := {Kind.LONG_SPINED: 0.064, Kind.PURPLE: 0.08, Kind.SLATE_PENCIL: 0.068}
const SPINE_REACH := {Kind.LONG_SPINED: 0.143, Kind.PURPLE: 0.065, Kind.SLATE_PENCIL: 0.087}
## How high it stands, to the tips of its highest spines.
const HEIGHT := {Kind.LONG_SPINED: 0.146, Kind.PURPLE: 0.069, Kind.SLATE_PENCIL: 0.078}
## What each kind sets in the shader: its test (as built: the build script's SHAPE line) and colours.
const KINDS := {
	Kind.LONG_SPINED: {"test_radius": 0.032, "test_top": 0.022, "test_bottom": 0.014, "test_middle": 0.03621,
		"below_lean": 0.45, "sink": 0.003,
		"test_colour": Color(0.1, 0.05, 0.1), "pores": Color(0.2, 0.25, 0.45), "mouth_skin": Color(0.15, 0.1, 0.12),
		"spine_root": Color(0.3, 0.22, 0.3), "spine": Color(0.06, 0.035, 0.07), "spine_tip": Color(0.14, 0.09, 0.2),
		"band": Color(0.28, 0.2, 0.42), "bands": 0.35, "band_count": 7.0, "foot": Color(0.3, 0.22, 0.32), "knob_amount": 0.3,
		"gloss": 0.8},
	Kind.PURPLE: {"test_radius": 0.04, "test_top": 0.024, "test_bottom": 0.015, "test_middle": 0.02112,
		"below_lean": 0.55, "sink": 0.002,
		"test_colour": Color(0.34, 0.07, 0.36), "pores": Color(0.42, 0.14, 0.42), "mouth_skin": Color(0.22, 0.14, 0.16),
		"spine_root": Color(0.6, 0.42, 0.58), "spine": Color(0.4, 0.09, 0.42), "spine_tip": Color(0.62, 0.3, 0.64),
		"band": Color(0.5, 0.2, 0.5), "bands": 0.0, "band_count": 6.0, "foot": Color(0.32, 0.08, 0.32), "knob_amount": 0.0,
		"gloss": 0.5},
	Kind.SLATE_PENCIL: {"test_radius": 0.034, "test_top": 0.026, "test_bottom": 0.016, "test_middle": 0.022,
		"below_lean": 0.5, "sink": 0.002,
		"test_colour": Color(0.42, 0.2, 0.15), "pores": Color(0.6, 0.42, 0.32), "mouth_skin": Color(0.3, 0.18, 0.15),
		"spine_root": Color(0.75, 0.6, 0.48), "spine": Color(0.5, 0.17, 0.09), "spine_tip": Color(0.62, 0.3, 0.18),
		"band": Color(0.82, 0.66, 0.52), "bands": 0.45, "band_count": 3.0, "short_spine": Color(0.58, 0.44, 0.3),
		"foot": Color(0.72, 0.52, 0.42), "gloss": 0.1, "knob_amount": 1.0},
}

static var _meshes := {}

## Which kind of urchin: its shape and colours.
@export var kind := Kind.PURPLE:
	set(value):
		kind = value
		_dress()
		_show()
## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 4.0
## How much its spines sway and its feet wave: 1 as it lives, 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Where the danger is, in its own space (a direction), and how alarmed it is (its length, 0..1):
## the spines on that side lean in towards it. For a world direction:
## `urchin.threat = urchin.global_basis.inverse() * world_direction`.
@export var threat := Vector3.ZERO:
	set(value):
		threat = value
		_send(&"threat", value)
## The low model (far off, many of them).
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (a Twilight Princess weight) in place of the full one; `low` still shows the low
## model. With it on, the full model is never loaded.
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


## `mesh` again without the lower levels of detail Godot's importer makes for it (they would drop
## spines that the shader then turns).
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


## A new material for a kind's meshes. Its shader settings are the game's to set: `phase` (0..1),
## `sway`, `threat`, and those `set_shader_parameter` lists.
static func new_material(kind_wanted: Kind) -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	_wear(made, kind_wanted)
	return made


static func _wear(on: ShaderMaterial, kind_wanted: Kind) -> void:
	var settings: Dictionary = KINDS[kind_wanted]
	for setting: String in settings:
		on.set_shader_parameter(setting, settings[setting])


func _init() -> void:
	_material = ShaderMaterial.new()
	_material.shader = SHADER
	_dress()


func _ready() -> void:
	_body = MeshInstance3D.new()
	_body.material_override = _material
	# (its spines lean out past the still model's box)
	_body.extra_cull_margin = 0.05
	_body.name = "SeaUrchin"
	add_child(_body)
	_show()
	_send(&"sway", sway)
	_send(&"threat", threat)
	_send(&"phase", phase)


## Each frame: moves it on through its beat (`velocity` is taken so that it is called as the fish
## are, and is not used).
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: its colours (`test_colour`, `pores`, `mouth_skin`,
## `spine_root`, `spine`, `spine_tip`, `band`, `short_spine`, `foot`, `tooth`), `bands`,
## `band_count`, `gloss`, or `lean` (how far the spines tip towards a threat). `kind` sets most of
## them again.
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
		_wear(_material, kind)


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
