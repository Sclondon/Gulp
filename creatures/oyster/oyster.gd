class_name Oyster
extends Node3D
## A Pacific oyster (Magallana gigas, 0.16 m from hinge to bill), or a CLUMP of five grown together as one piece
## for building an oyster bed (`kind`). A rough, irregular, layered grey shell, frilled where each layer ends: the
## lower valve a deep cup, the upper flatter. It opens a little (`open`): inside, mother-of-pearl (drawn by the
## shader) and the soft body lying in the cup with its dark frilled mantle edge; `pearl` on, a pearl lies on the
## body (in the clump, in the biggest oyster).
##
## How it looks and moves only. Its bill points along its own -Z (the clump's biggest oyster's). **Its origin is on
## the ground under its middle.** It is life size: `scale` it for a game. No sound, no eyes (no `cartoon_eyes`).
## Its body breathes a little on `phase` (0 to 1 through one `beat`), so it loops exactly; call `step(velocity,
## delta)` each frame, or set `phase` yourself. It has no `gape` and no `curl`.
##
## The models are creatures/oyster/models/oyster.glb and oyster_clump.glb (and _game, _lo), built by
## tools/build_oyster.py; oyster.gdshader colours and opens them.

enum Kind { SINGLE, CLUMP }

const MODEL := "res://creatures/oyster/models/%s%s.glb"
const SHADER := preload("res://creatures/oyster/oyster.gdshader")
const NAMES := {Kind.SINGLE: "oyster", Kind.CLUMP: "oyster_clump"}
## As the models are built (tools/build_oyster.py), shut, metres: how long, how high, how wide.
const LENGTHS := {Kind.SINGLE: 0.165, Kind.CLUMP: 0.184}
const DEPTHS := {Kind.SINGLE: 0.047, Kind.CLUMP: 0.145}
const WIDTHS := {Kind.SINGLE: 0.087, Kind.CLUMP: 0.096}
## One oyster's length, depth and width.
const LENGTH := 0.165
const DEPTH := 0.047
const WIDTH := 0.087
## How far an upper valve turns at `open` 1 (radians): oysters open only a little.
const UPPER_TURN := 0.16
## Each model's hinges and pearl, as the build script prints them (its HINGE and PEARL lines: keep in step), and
## each oyster's share of the opening.
const KINDS := {
	Kind.SINGLE: {
		"hinge_at": [Vector3(0.0, 0.03528, 0.08266)],
		"hinge_axis": [Vector3(1.0, 0.0, 0.0)],
		"opens": [1.0],
		"pearl_at": Vector3(-0.01981, 0.03068, 0.00509),
	},
	Kind.CLUMP: {
		"hinge_at": [Vector3(-0.00607, 0.02772, 0.05694), Vector3(0.01593, 0.03572, 0.01894),
			Vector3(-0.03207, 0.03172, 0.02294), Vector3(0.02793, 0.03772, 0.04894), Vector3(-0.02807, 0.04372, 0.05294)],
		"hinge_axis": [Vector3(0.99875, 0.04877, 0.01091), Vector3(-0.24386, 0.25301, -0.93622),
			Vector3(-0.07422, -0.21747, 0.97324), Vector3(0.79315, 0.41314, -0.44746), Vector3(0.86444, -0.10812, 0.49097)],
		"opens": [1.0, 0.7, 0.9, 0.55, 0.8],
		"pearl_at": Vector3(-0.02379, 0.03772, -0.01294),
	},
}

static var _meshes := {}

## One oyster or the clump of five.
@export var kind := Kind.SINGLE:
	set(value):
		kind = value
		_dress()
		_fit()
## Seconds one beat (one slow breath of its body) takes. 0 for a caller that sets `phase` itself.
@export var beat := 5.0
## How strongly its body breathes: 1 as it lives, 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far open it is: 0 shut, 1 as far as it opens (a little).
@export_range(0.0, 1.0) var open := 0.0:
	set(value):
		open = clampf(value, 0.0, 1.0)
		_send(&"open", open)
## A pearl lying on its body (seen when it is open).
@export var pearl := false:
	set(value):
		pearl = value
		_send(&"pearl", 1.0 if value else 0.0)
## The low model (a few hundred triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (Twilight Princess weight: about 1,300 triangles for one oyster, 1,700 for the clump; the same
## shader and settings) in place of the full one; `low` still shows the low model. Each model is loaded only when
## it is first shown, so with `game` on the full models are never loaded and a game's web export may leave them
## out.
@export var game := false:
	set(value):
		game = value
		_show()
## How far through a beat it is, 0 to 1.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D


## A kind's full model's mesh, or its low one's (one surface, to wear `new_material(kind)`). Loaded once.
static func mesh_of(kind_wanted: Kind, low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % [NAMES[kind_wanted], "_lo" if low_wanted else ""])


## A kind's game model's mesh (see `game`). Loaded once and kept.
static func game_mesh(kind_wanted: Kind) -> Mesh:
	return _mesh_at(MODEL % [NAMES[kind_wanted], "_game"])


static func _mesh_at(path: String) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh)
		made.free()
	return _meshes[path]


## `mesh` again without the lower levels of detail Godot's importer makes for it (made from the shut model, they
## would open in pieces).
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


## A new material for a kind's meshes (its hinges and pearl set). Its other settings are the game's: `open`,
## `pearl` (0 or 1), `phase`, `sway`.
static func new_material(kind_wanted: Kind = Kind.SINGLE) -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	_wear(made, kind_wanted)
	return made


static func _wear(on: ShaderMaterial, kind_wanted: Kind) -> void:
	var wears: Dictionary = KINDS[kind_wanted]
	var at := PackedVector3Array()
	var axis := PackedVector3Array()
	var opens := PackedFloat32Array()
	for i in 5:
		var have := i < (wears["opens"] as Array).size()
		at.append(wears["hinge_at"][i] if have else Vector3.ZERO)
		axis.append(wears["hinge_axis"][i] if have else Vector3.RIGHT)
		opens.append(wears["opens"][i] if have else 0.0)
	on.set_shader_parameter(&"hinge_at", at)
	on.set_shader_parameter(&"hinge_axis", axis)
	on.set_shader_parameter(&"opens", opens)
	on.set_shader_parameter(&"pearl_at", wears["pearl_at"])
	on.set_shader_parameter(&"upper_turn", UPPER_TURN)


func _init() -> void:
	_material = new_material(kind)


func _ready() -> void:
	_full = _instance_of("Oyster")
	_low = _instance_of("Oyster_lo")
	_game = _instance_of("Oyster_game")
	_show()
	_send(&"phase", phase)
	_send(&"sway", sway)
	_send(&"open", open)
	_send(&"pearl", 1.0 if pearl else 0.0)


## Each frame: moves its breathing on (`velocity` is not used).
func step(_velocity: Vector3, delta: float) -> void:
	if beat > 0.0:
		phase += delta / beat


## Sets one of the shader's settings: the colours (`shell`, `shell_dark`, `shell_tint`, `lip`, `nacre`, `scar`,
## `flesh`, `mantle_edge`, `pearl_colour`), `pearly` (how strong the mother-of-pearl's colours are), `upper_turn`.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_send(setting, value)


## Its one material (all its models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


func _dress() -> void:
	if _material:
		_wear(_material, kind)


func _fit() -> void:
	if _full == null:
		return
	# (only the model shown is loaded; the others are given theirs when they are first shown)
	_full.mesh = mesh_of(kind, false) if _full.visible else null
	_low.mesh = mesh_of(kind, true) if _low.visible else null
	_game.mesh = game_mesh(kind) if _game.visible else null


func _show() -> void:
	if _full:
		_full.visible = not low and not game
		_low.visible = low
		_game.visible = game and not low
		_fit()


func _instance_of(called: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.material_override = _material
	# (open, its upper valves reach a little past the shut model's box)
	mesh.extra_cull_margin = 0.03
	mesh.name = called
	add_child(mesh)
	return mesh
