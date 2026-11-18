class_name Pyrosome
extends Node3D
## A pyrosome (a giant one, as Pyrostremma spinosum), 2 m long: a hollow tube of a colony, closed at one end and
## open at the other, its wall bumpy with thousands of tiny members (zooids), pale blue-green, pulsing with waves of
## light that travel along it, swaying and bending gently like a windsock.
##
## IT SWIMS CLOSED END FIRST, as pyrosomes do (it jets water out of its open end): the closed end is ahead along its
## own -Z (Godot's forward, so `look_at` points it), the open end behind (+Z). Its origin is on its middle line half
## way along its length: the closed end 1 m ahead, the open end's lip 1 m behind. `scale` it for a bigger or smaller
## one. No sound.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it goes. Everything that
## moves runs on `phase`, 0 to 1 through one `beat`, in which a slow wave of sway runs back along it and `pulses`
## waves of light run along it, so its motion comes round again exactly every beat. Either call
## `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or set `phase` yourself.
##
## The models are creatures/pyrosome/models/pyrosome.glb (and _game, and _lo), built by tools/build_pyrosome.py;
## pyrosome.gdshader draws its members and their lights and sways it.

const MODEL := "res://creatures/pyrosome/models/pyrosome%s.glb"
const SHADER := preload("res://creatures/pyrosome/pyrosome.gdshader")
## As the model is built: from its closed end to its open end, and how wide it is at its widest (near the open end)
## (metres, at scale 1). The open end's opening, inside the diaphragm, is 0.23 m across.
const LENGTH := 2.0
const WIDTH := 0.35

## Seconds one beat takes (one wave of sway along it).
@export var beat := 6.0
## Waves of light that run along it in a beat (a whole number).
@export var pulses := 2:
	set(value):
		pulses = maxi(value, 0)
		_send(&"pulses", float(pulses))
## How much it sways: 1 a slow wave running back along it, the open end swinging about 0.08 m either way; 0 still;
## 2 twice as much.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Bent round to one side behind its closed end, radians from end to end (more than 0 the open end comes round to
## +X), as it turns.
@export var curl := 0.0:
	set(value):
		curl = value
		_send(&"curl", value)
## How strongly it glows (0 dark, 1 as made, 2 twice as bright).
@export_range(0.0, 2.0) var glow := 1.0:
	set(value):
		glow = clampf(value, 0.0, 2.0)
		_send(&"glow", glow)
## The low model (about a hundred-and-fiftieth of the full one's triangles), for far off.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about 3,600 triangles, spent on the outline, the closed end and the open mouth) in place of the
## full one: what a game draws near. `low` still shows the low model. With it on, the full model is never loaded
## (each model is loaded when it is first shown), so a game's export may leave the full .glb out.
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
## without this node.
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game")


## A new material for these meshes. Its shader settings are the game's to set: `phase` (0..1 through one beat),
## `pulses`, `light_waves`, `sway`, `sway_waves`, `curl`, `glow` and the colours (the top of the shader lists them).
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
	_send(&"pulses", float(pulses))
	for setting in [&"phase", &"sway", &"curl", &"glow"]:
		_send(setting, get(setting))


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat. (`velocity` is
## taken so that it is called as the other creatures are.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `light_waves`, `sway_waves`, its colours (`tunic`, `opening`, `inside`,
## `light_colour`) or any of the settings above.
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
		# (it sways and bends past the still model)
		made.extra_cull_margin = 0.6
		made.name = "Pyrosome" + which
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
