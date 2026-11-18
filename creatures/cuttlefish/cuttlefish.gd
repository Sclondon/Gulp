class_name Cuttlefish
extends Node3D
## A common cuttlefish (Sepia officinalis), 0.4 m long: a broad oval mantle, flattened, with a thin
## fin skirt all round its sides that ripples in a travelling wave; a short head with big eyes,
## their pupils W-shaped; eight short arms drawn together into a point ahead of the head; and two
## feeding tentacles kept hidden until it strikes. Mottled sandy camouflage by default; it can show
## the zebra bands, pass dark clouds down its body, blanch, and flash.
##
## IT SWIMS ARMS FIRST: its arms point along its own -Z (Godot's forward), its mantle's end is
## towards +Z, its back is +Y. Its origin is on its middle line half way along its length, so its
## arms' tips are 0.2 m ahead and its mantle's end 0.2 m behind. `scale` it for a bigger or smaller
## one. No sound. (To back away, as cuttlefish do too, move it towards +Z: the fin works both ways;
## `fin_ripples` below 0 runs its wave forwards.)
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it goes.
## Everything that moves goes by `phase` (its fin's waves and its arms' sway; 0 to 1 through one
## `beat`) and its colours by `colour_phase`: `step(velocity, delta)` moves them on, or set them
## yourself for a picture that must loop. Its arms, fin, tentacles and mantle are bent by the shader
## (no bones, no ropes), so many can share one mesh (`mesh_of()`) and material (`new_material()`).
##
## The model is creatures/cuttlefish/models/cuttlefish.glb (and _lo, and _game: `game`), built by
## tools/build_cuttlefish.py; cuttlefish.gdshader moves it and draws its skin.

const MODEL := "res://creatures/cuttlefish/models/cuttlefish%s.glb"
const SHADER := preload("res://creatures/cuttlefish/cuttlefish.gdshader")
static var _game_cache: Mesh
## As the model is built: from the arms' tips to the mantle's end, how deep its body is and how
## wide with its fin (metres, at scale 1). Struck, its tentacles reach 0.2 m past its arms.
const LENGTH := 0.4
const DEPTH := 0.068
const WIDTH := 0.152

## Seconds one round of its fin's waves takes.
@export var beat := 1.2
## Waves that pass back along its fin in a beat (a whole number, so that it comes round; less than
## 0 runs them forwards, for backing away; 0 still).
@export var fin_ripples := 2:
	set(value):
		fin_ripples = value
		_send(&"fin_ripples", float(value))
## Seconds a round of its colours takes (the passing cloud). 0: the same as a beat
## (`colour_phase` is `phase`). Less than 0: `colour_phase` is yours to set.
@export var colour_beat := 3.6
## Its arms: 0 drawn together into a point; 1 opened wide and curled back.
@export_range(0.0, 1.0) var spread := 0.0:
	set(value):
		spread = value
		_send(&"spread", value)
## Its tentacles: 0 folded away out of sight; 1 shot out to their full length (0.2 m past the arms
## at size 1). Drive it from 0 to 1 in about a tenth of a second for a strike.
@export_range(0.0, 1.0) var strike := 0.0:
	set(value):
		strike = value
		_send(&"strike", value)
## Its mantle bent round behind its head, in radians from the collar to its end (0 straight; more
## than 0 its end comes round to +X), as it turns.
@export var curl := 0.0:
	set(value):
		curl = value
		_send(&"curl", value)
## Its skin, 0..1 each, laid over its mottled sandy camouflage: the black and white bands of a
## displaying male; dark clouds passing down its body (`cloud_rounds` a round of its colours, a
## whole number); pale all over.
@export_range(0.0, 1.0) var zebra := 0.0:
	set(value):
		zebra = value
		_send(&"zebra", value)
@export_range(0.0, 1.0) var cloud := 0.0:
	set(value):
		cloud = value
		_send(&"cloud", value)
@export var cloud_rounds := 2:
	set(value):
		cloud_rounds = value
		_send(&"cloud_rounds", float(value))
@export_range(0.0, 1.0) var blanch := 0.0:
	set(value):
		blanch = value
		_send(&"blanch", value)
## The low model (about a tenth of the triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about 1,800 triangles, an eighth of the full one's) in place of the full one;
## `low` still shows the low one. With it the full model is never loaded: each model is loaded
## only when it is first shown.
@export var game := false:
	set(value):
		game = value
		_show()
## Cartoon eyes (0 its own eye; 1 the cartoon eye: bigger, a white, a green-gold iris, its W of a
## pupil, a highlight, a dark outline, and a low, scheming upper lid with the lower lid pushed up:
## a sly look).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = value
		_send(&"cartoon_eyes", value)
## Where its eyes look (-1..1 each way, in each eye's own plane): x towards its arms (+1) or its
## mantle's end (-1), y up its back. Both eyes look the same way.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value
		_send(&"eye_look", value)
## Its eyes' lids: 0 open, 1 shut.
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = value
		_send(&"blink", value)
## How far through a beat (0..1). `step` moves it on; or set it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)
		if colour_beat == 0.0:
			colour_phase = phase
## How far through a round of its colours (0..1).
var colour_phase := 0.0:
	set(value):
		colour_phase = fposmod(value, 1.0)
		_send(&"colour_phase", colour_phase)

var _material: ShaderMaterial
# Its models, by suffix ("", "_game", "_lo"), each made when it is first shown.
var _models := {}
var _ready_yet := false
var _flash_at := 1.0
var _flash_takes := 0.8


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	# (the first model is put off to the end of the frame, so that `game` or `low` set just after it
	# is added is heeded before any model is loaded)
	_first_show.call_deferred()
	for setting in [&"fin_ripples", &"cloud_rounds"]:
		_send(setting, float(get(setting)))
	for setting in [&"spread", &"strike", &"curl", &"zebra", &"cloud", &"blanch", &"phase", &"colour_phase", &"cartoon_eyes", &"eye_look", &"blink"]:
		_send(setting, get(setting))


## The model's mesh (the full one, or the low one), as imported: for a MultiMesh of many.
static func mesh_of(low_model := false) -> Mesh:
	return _load_mesh("_lo" if low_model else "")


## The game model's mesh, as imported, without the thinned LOD meshes Godot's importer makes (it is
## bent in the shader: a thinned one would bend in straight pieces): for a MultiMesh of many.
static func game_mesh() -> Mesh:
	return _load_mesh("_game")


static func _load_mesh(suffix: String) -> Mesh:
	if suffix == "_game" and _game_cache != null:
		return _game_cache
	var scene := load(MODEL % suffix) as PackedScene
	var made := scene.instantiate()
	var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
	var mesh := found.mesh
	made.free()
	if suffix == "_game":
		# (made once, shared by every cuttlefish)
		_game_cache = _without_lods(mesh)
		mesh = _game_cache
	return mesh


## `mesh` built again from its own arrays, without its LOD meshes.
static func _without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
		plain.surface_set_material(surface, mesh.surface_get_material(surface))
	return plain


## A new material of its shader, with its settings at their defaults.
static func new_material() -> ShaderMaterial:
	var material := ShaderMaterial.new()
	material.shader = SHADER
	return material


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


## Sets one of the shader's settings: its colours (`sand`, `brown`, `white`, `black`, `belly`,
## `iris`), `fin_waves` (how many waves stand on its fin at once), `fin_lift` (how high they are),
## `arm_sway`.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## A startle, once, now: it goes pale with two dark eyespots on its back and its fin's edge dark,
## and fades back over `seconds`. Not part of `phase`: a picture that must loop should not call it.
func flash(seconds := 0.8) -> void:
	_flash_at = 0.0
	_flash_takes = maxf(seconds, 0.01)


## Each frame, for one that is not having its phases set for it: moves it on through its beat and
## its colours. (`velocity` is taken so that it is called as the other creatures are; its fin's
## beat does not change with its speed: set `beat` and `fin_ripples` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)
	if colour_beat > 0.0:
		colour_phase += delta / colour_beat
	_flash_at = minf(_flash_at + delta / _flash_takes, 1.0)
	# (quickly pale, slowly back)
	_send(&"flash_now", 0.0 if _flash_at >= 1.0 else minf(_flash_at * 8.0, 1.0) * pow(1.0 - _flash_at, 1.5))


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


func _first_show() -> void:
	_ready_yet = true
	_show()


## Shows the model it should wear (the full one, the game one with `game`, the low one with `low`),
## loading it the first time.
func _show() -> void:
	if not _ready_yet:
		return
	var wear := "_lo" if low else ("_game" if game else "")
	if not _models.has(wear):
		_models[wear] = _instance(_load_mesh(wear), wear)
	for suffix: String in _models:
		(_models[suffix] as MeshInstance3D).visible = suffix == wear


func _instance(mesh: Mesh, suffix: String) -> MeshInstance3D:
	var made := MeshInstance3D.new()
	made.mesh = mesh
	made.material_override = _material
	# (its arms spread, its fin lifts, its mantle bends and its tentacles reach past the model)
	made.extra_cull_margin = 0.25
	made.name = "Cuttlefish" + suffix
	add_child(made)
	return made
