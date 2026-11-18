class_name CombJelly
extends Node3D
## A lobate comb jelly (a ctenophore, as Mnemiopsis or Bolinopsis), 0.1 m long: a clear oval body splitting in front
## into two broad lobes round its mouth, with eight rows of comb plates running its length that beat in waves and
## scatter running rainbow light. No stinging tentacles. Drawn see-through.
##
## IT SWIMS MOUTH FIRST: the lobes are ahead along its own -Z (Godot's forward, so `look_at` points it), above and
## below it (+Y, -Y); its aboral end is behind (+Z). Its origin is on its middle line half way along its length: the
## lobes' front edges 0.05 m ahead, the aboral end 0.05 m behind. `scale` it for a bigger or smaller one. No sound.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it goes. Everything that
## moves runs on `phase`, 0 to 1 through one `beat`, in which `rounds` waves run along its comb rows, so its motion
## comes round again exactly every beat. Either call `step(velocity, delta)` each frame, which moves `phase` on by
## delta / beat, or set `phase` yourself (for a picture that must loop).
##
## The models are creatures/comb_jelly/models/comb_jelly.glb (and _game, and _lo), built by
## tools/build_comb_jelly.py; comb_jelly.gdshader draws it clear, beats its plates and lights its rows.

const MODEL := "res://creatures/comb_jelly/models/comb_jelly%s.glb"
const SHADER := preload("res://creatures/comb_jelly/comb_jelly.gdshader")
## As the model is built: from the lobes' front edges to the aboral end, how deep it is across the lobes (Y), and
## how wide across its flatter sides (X) (metres, at scale 1).
const LENGTH := 0.1
const DEPTH := 0.053
const WIDTH := 0.037

## Seconds one beat takes.
@export var beat := 1.5
## How many waves run along its comb rows in a beat (a whole number).
@export var rounds := 2:
	set(value):
		rounds = maxi(value, 0)
		_send(&"rounds", float(rounds))
## How much it moves: 1 its plates beating and its lobes swaying gently, 0 still, 2 twice as much.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Its body bent round behind its lobes, radians from its lobes to its aboral end (more than 0 the aboral end comes
## round to +X), as it turns.
@export var curl := 0.0:
	set(value):
		curl = value
		_send(&"curl", value)
## How strongly its rows and edges shine (0 none, 1 as made, 2 twice as bright).
@export_range(0.0, 2.0) var glow := 1.0:
	set(value):
		glow = clampf(value, 0.0, 2.0)
		_send(&"glow", glow)
## The low model (about a sixtieth of the full one's triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (720 triangles, spent on the outline and the lobes' edges) in place of the full one: what a game
## draws near. `low` still shows the low model. With it on, the full model is never loaded (each model is loaded when
## it is first shown), so a game's export may leave the full .glb out.
@export var game := false:
	set(value):
		game = value
		_show()
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)

static var _meshes := {}

var _material: ShaderMaterial
var _models := {}
var _ready_yet := false


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`, without the importer's LOD
## meshes): for drawing one without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## The game model's mesh (one surface, to wear `new_material()`, without the importer's LOD meshes): for drawing one
## without this node, or many with a MultiMesh (they then share their settings and phase).
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game")


## A new material for these meshes. Its shader settings are the game's to set: `phase` (0..1 through one beat),
## `rounds`, `sway`, `curl`, `glow`, `cloudy` and the colours (the top of the shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	# (the first model is put off to the end of the frame, so that `game` or `low` set just after it is added is
	# heeded before any model is loaded)
	_first_show.call_deferred()
	_send(&"rounds", float(rounds))
	for setting in [&"phase", &"sway", &"curl", &"glow"]:
		_send(setting, get(setting))


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat. (`velocity` is
## taken so that it is called as the other creatures are; its beat does not change with its speed.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `cloudy` (how clear it is), its colours (`body`, `inside`, `edge_colour`,
## `statocyst`) or any of the settings above.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


func _first_show() -> void:
	_ready_yet = true
	_show()


func _show() -> void:
	if not _ready_yet:
		return
	var which := "_lo" if low else ("_game" if game else "")
	if not _models.has(which):
		var made := MeshInstance3D.new()
		made.mesh = _mesh_at(MODEL % which)
		made.material_override = _material
		made.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		# (its lobes sway and it bends past the still model)
		made.extra_cull_margin = 0.03
		made.name = "CombJelly" + which
		add_child(made)
		_models[which] = made
	for key: String in _models:
		(_models[key] as MeshInstance3D).visible = key == which


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
		_meshes[path] = without_lods(found.mesh)
		made.free()
	return _meshes[path]
