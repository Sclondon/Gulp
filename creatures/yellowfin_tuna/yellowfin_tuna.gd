class_name YellowfinTuna
extends Node3D
## A yellowfin tuna (Thunnus albacares), 1.5 m long: a deep, round, rigid torpedo with a
## blue-black back, a gold band under a thin blue line, a silver-white belly marked with rows of
## pale dots and broken lines, long yellow sickle fins, yellow finlets edged with black back to a
## narrow keeled tail wrist, and a tall dark crescent tail.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down; its origin is on
## its middle line, half way along, so it reaches 0.75 m ahead and 0.75 m behind. `scale` it for
## a bigger or smaller one. No sound.
##
## It swims stiffly, as tunas do: the body barely bends and the tail does the work, by a bend
## drawn by the shader (no bones). Its mouth opens: `gape`.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat.
## Either call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or
## set `phase` yourself (for a picture that must loop: frame / frames in a beat). The same
## names and meanings as GameCommon's cutthroat trout, so the two fish are driven the same way.
##
## The model is creatures/yellowfin_tuna/models/yellowfin_tuna.glb (and _lo), built by
## tools/build_yellowfin_tuna.py; yellowfin_tuna.gdshader draws its markings and swims it.

const MODEL := "res://creatures/yellowfin_tuna/models/yellowfin_tuna%s.glb"
const SHADER := preload("res://creatures/yellowfin_tuna/yellowfin_tuna.gdshader")
## As the model is built (tools/build_yellowfin_tuna.py): from the tip of its snout to the tips
## of its tail, and how deep and how wide its body is at its deepest (metres, at scale 1).
const LENGTH := 1.5
const DEPTH := 0.39
const WIDTH := 0.28

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 1.65
## How many times in a beat its tail beats (there and back).
@export var tail_beats := 3:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it beats: 1 a tuna cruising (its tail tips swing about 0.12 m either way), 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far its first dorsal fin is raised: 1 up (as in a portrait), 0 folded into its groove (as
## when it swims fast).
@export_range(0.0, 1.0) var first_dorsal := 1.0:
	set(value):
		first_dorsal = value
		_send(&"first_dorsal", value)
## How far its mouth is open: 0 shut (as it always was before 2026-11-17), 1 wide open, as when
## it bites (its lower jaw swung down about its hinge at the corner of the mouth, its tip about
## 0.07 m; the inside of the mouth is dark).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## The low model (about a twelfth of the triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (added 2026-11-18): about 3,600 triangles (with its gills) against the full model's 73,000, spent
## where they show (the outline, the head, the eye, the fins' edges), for a game; it looks and works
## as the full one does, and is lighter than the low model (6,700, an even coarse grid).
## `low` still shows the low model. Each model is loaded only when it is first shown, so a game
## that sets this before the node enters the tree never loads the full one.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye (added 2026-11-18): 0 the eye as it always was, 1 a bigger cartoon eye with a
## white, a gold iris, a teardrop pupil and a level, intent lid (the yellowfin as the keen, sporty
## one). Any model.
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

static var _game_mesh: Mesh

var _material: ShaderMaterial
# (the models shown so far, by suffix: "", "_lo", "_game")
var _shown := {}


## The game model's mesh (one surface, to wear a copy of `material()`), for a game that draws them
## itself, without the importer's automatic LODs (they would bend in straight pieces far off, the
## swimming being drawn by the shader).
static func game_mesh() -> Mesh:
	if _game_mesh == null:
		var made := (load(MODEL % "_game") as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		var bare := ArrayMesh.new()
		for surface in found.mesh.get_surface_count():
			bare.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, found.mesh.surface_get_arrays(surface))
		_game_mesh = bare
		made.free()
	return _game_mesh


func _init() -> void:
	_material = ShaderMaterial.new()
	_material.shader = SHADER


func _ready() -> void:
	_show()
	_send_phase()
	_send(&"sway", sway)
	_send(&"first_dorsal", first_dorsal)
	_send(&"gape", gape)
	_send(&"cartoon_eyes", cartoon_eyes)
	_send(&"eye_look", eye_look)
	_send(&"blink", blink)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the cutthroat trout's is; a tuna's beat here
## does not change with its speed: set `sway` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: its colours (`back`, `back_blue`, `line_blue`, `gold`,
## `silver`, `belly`, `marks`, `fin_yellow`, `fin_edge`, `tail_dark`, `fin_dusk`, `mouth_inside`), `marks_show`
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
		_shown[wanted] = _mesh_of(wanted)
	for suffix: String in _shown:
		(_shown[suffix] as MeshInstance3D).visible = suffix == wanted


func _mesh_of(suffix: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	if suffix == "_game":
		mesh.mesh = game_mesh()
	else:
		var made := (load(MODEL % suffix) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		mesh.mesh = found.mesh
		made.free()
	mesh.material_override = _material
	# (its tail swings out past where the still model ends)
	mesh.extra_cull_margin = 0.3
	mesh.name = "Tuna" + suffix
	add_child(mesh)
	return mesh
