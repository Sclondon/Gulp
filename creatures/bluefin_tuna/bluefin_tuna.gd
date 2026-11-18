class_name BluefinTuna
extends Node3D
## A Pacific bluefin tuna (Thunnus orientalis), 2.5 m long: the heaviest of the tunas, a deep,
## very round, rigid torpedo with a blue-black back shading into silver and a white belly
## (faint pale lines and dots low on it), a long first dorsal fin, a short reddish-brown second
## dorsal, dusky yellow finlets edged with black back to a narrow black-keeled tail wrist, a
## tall dark crescent tail and short pectoral fins. Its mouth opens (`gape`).
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down; its origin is on
## its middle line, half way along, so it reaches 1.25 m ahead and 1.25 m behind. `scale` it
## for a bigger or smaller one. No sound.
##
## It swims stiffly, as tunas do: the body barely bends and the tail does the work, by a bend
## drawn by the shader (no bones).
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat.
## Either call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or
## set `phase` yourself (for a picture that must loop: frame / frames in a beat). The same
## names and meanings as GameCommon's yellowfin tuna, so they are driven the same way.
##
## The model is creatures/bluefin_tuna/models/bluefin_tuna.glb (and _lo), built by
## tools/build_bluefin_tuna.py; bluefin_tuna.gdshader draws its markings, swims it and works
## its jaw.

const MODEL := "res://creatures/bluefin_tuna/models/bluefin_tuna%s.glb"
const SHADER := preload("res://creatures/bluefin_tuna/bluefin_tuna.gdshader")
## As the model is built (tools/build_bluefin_tuna.py): from the tip of its snout to the tips
## of its tail, and how deep and how wide its body is at its deepest (metres, at scale 1).
const LENGTH := 2.5
const DEPTH := 0.70
const WIDTH := 0.53

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 2.4
## How many times in a beat its tail beats (there and back).
@export var tail_beats := 3:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it beats: 1 a tuna cruising (its tail tips swing about 0.2 m either way), 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Its mouth: 0 shut, 1 wide open, as when it bites (the lower jaw swings down about its hinge).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## How far its body is bent round to one side behind the head, as when it turns tightly:
## radians from the gills to the tail (more than 0, the tail comes round to +X, its left).
@export_range(-1.5, 1.5) var curl := 0.0:
	set(value):
		curl = value
		_send(&"curl", value)
## How far its first dorsal fin is raised: 1 up (as in a portrait), 0 folded into its groove (as
## when it swims fast).
@export_range(0.0, 1.0) var first_dorsal := 1.0:
	set(value):
		first_dorsal = value
		_send(&"first_dorsal", value)
## The low model (about a tenth of the triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (added 2026-11-18): about 3,700 triangles (with its gills) against the full model's 62,000, spent
## where they show (the outline, the head, the eye, the fins' edges), for a game; it looks and works
## as the full one does, and is lighter than the low model (6,000, an even coarse grid).
## `low` still shows the low model. Each model is loaded only when it is first shown, so a game
## that sets this before the node enters the tree never loads the full one.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye (added 2026-11-18): 0 the eye as it always was, 1 a bigger cartoon eye with a
## white, a steel-blue iris and a heavy lid (the bluefin as a heavy, unbothered old boss). Any model.
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where the cartoon eye looks: x towards the snout (+) or the tail (-), y up (+) or down (-), each
## -1 to 1.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value
		_send(&"eye_look", value)
## The cartoon eye's lid: 0 open, 1 shut (a blink is a quick 0, 1, 0).
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set
## it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()

static var _meshes := {}

var _material: ShaderMaterial
# (the models shown so far, by suffix: "", "_lo", "_game")
var _shown := {}


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`): for
## drawing one without this node (many of them in a MultiMesh, say).
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""), false)


## The game model's mesh (one surface, to wear `new_material()`), without the importer's automatic
## LODs (they would bend in straight pieces far off, the swimming being drawn by the shader).
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game", true)


static func _mesh_at(path: String, plain: bool) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		var mesh: Mesh = found.mesh
		if plain:
			var bare := ArrayMesh.new()
			for surface in mesh.get_surface_count():
				bare.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
			mesh = bare
		_meshes[path] = mesh
		made.free()
	return _meshes[path]


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase`
## (0..1 through one beat of the tail), `sway`, `curl`, `gape`, `first_dorsal`, `wave` and the
## colours (the top of the shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_show()
	_send_phase()
	_send(&"sway", sway)
	_send(&"gape", gape)
	_send(&"curl", curl)
	_send(&"first_dorsal", first_dorsal)
	_send(&"cartoon_eyes", cartoon_eyes)
	_send(&"eye_look", eye_look)
	_send(&"blink", blink)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the other fish are; its beat here does not
## change with its speed: set `sway` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: its colours (`back`, `back_blue`, `silver`, `belly`,
## `marks`, `fin_red`, `fin_yellow`, `fin_edge`, `tail_dark`, `fin_dusk`, `mouth`), `marks_show`
## (how strongly the belly's pale marks show) and `wave` (the length of the wave along its body).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one beat of the tail it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


# (shows the model asked for, loading it the first time it is shown)
func _show() -> void:
	if not is_node_ready():
		return
	var wanted := "_lo" if low else "_game" if game else ""
	if not _shown.has(wanted):
		_shown[wanted] = _instance_of(wanted)
	for suffix: String in _shown:
		(_shown[suffix] as MeshInstance3D).visible = suffix == wanted


func _instance_of(suffix: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = game_mesh() if suffix == "_game" else mesh_of(suffix == "_lo")
	mesh.material_override = _material
	# (its tail swings out past where the still model ends, and its jaw drops below it)
	mesh.extra_cull_margin = 0.2 * LENGTH
	mesh.name = "BluefinTuna" + suffix
	add_child(mesh)
	return mesh
