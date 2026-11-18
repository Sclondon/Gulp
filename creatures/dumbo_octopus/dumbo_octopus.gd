class_name DumboOctopus
extends Node3D
## A dumbo octopus (Grimpoteuthis), 0.3 m from the top of its mantle to the tips of its arms: a soft rounded bell
## of a body, two big ear-like fins high on its mantle that flap slowly, eight short arms joined by a web like an
## umbrella that opens and closes as it pulses, big dark eyes. Pale pink-orange, glowing faintly (it lives in the
## dark: `glow`).
##
## IT FLOATS UPRIGHT, FACING -Z: the top of its mantle is up (+Y), its face (between its eyes) looks along its own
## -Z (Godot's forward, so `look_at` points it), its fins stand out to its sides (+X its left). Its origin is on its
## middle line half way along its length: the top of its mantle 0.15 m above it, the tips of its arms 0.15 m below
## (as built, the web half open). `scale` it for a bigger or smaller one. No sound.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it goes. Everything that
## moves runs on `phase`, 0 to 1 through one `beat`, in which its web opens and closes once and its fins flap
## `flaps` times, so its motion comes round again exactly every beat. Either call `step(velocity, delta)` each
## frame, which moves `phase` on by delta / beat, or set `phase` yourself (for a picture that must loop). Its fins,
## web and arms are moved by the shader (no bones), so many can share one mesh (`game_mesh()`) and material.
##
## The models are creatures/dumbo_octopus/models/dumbo_octopus.glb (and _game, and _lo), built by
## tools/build_dumbo_octopus.py; dumbo_octopus.gdshader draws it, moves it and makes it glow.

const MODEL := "res://creatures/dumbo_octopus/models/dumbo_octopus%s.glb"
const SHADER := preload("res://creatures/dumbo_octopus/dumbo_octopus.gdshader")
## As the model is built (tools/build_dumbo_octopus.py), at rest: from the top of its mantle to the tips of its
## arms, how wide its body is at the eyes (its fins and web reach further: see the README), and how wide it is
## across the tips of its arms (metres, at scale 1).
const LENGTH := 0.3
const BODY_WIDTH := 0.14
const WIDTH := 0.326

## Seconds one beat takes (one pulse of its web).
@export var beat := 2.4
## How many strokes its fins make in a beat (a whole number).
@export var flaps := 2:
	set(value):
		flaps = maxi(value, 0)
		_send(&"flaps", float(flaps))
## How much it moves: 1 swimming gently (its web opening and shutting, its fins flapping), 0 still, 2 twice as much.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Its web held more open (up to 1: spread wide) or more shut (down to -1: hanging close in a bell), as well as
## its pulse.
@export_range(-1.0, 1.0) var open := 0.0:
	set(value):
		open = clampf(value, -1.0, 1.0)
		_send(&"open", open)
## Turning: its web and arms bent round below its head, radians from its head to its arms' tips (more than 0 they
## come round to +X, its left).
@export var curl := 0.0:
	set(value):
		curl = value
		_send(&"curl", value)
## How strongly it glows (0 none, 1 as made, 2 twice as bright): its skin faintly, its web's and fins' edges, the
## lights in its suckers.
@export_range(0.0, 2.0) var glow := 1.0:
	set(value):
		glow = clampf(value, 0.0, 2.0)
		_send(&"glow", glow)
## The low model (about a fiftieth of the full one's triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about 1,700 triangles, spent on the outline, the eyes and the web's edge) in place of the full
## one: what a game draws near. `low` still shows the low model. With it on, the full model is never loaded (each
## model is loaded when it is first shown), so a game's export may leave the full .glb out.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye (0 the eye as made, 1 the cartoon one: huge, round and sweet, a big warm brown iris round a big
## round pupil with two bright highlights).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where the cartoon eyes look: x towards its front (more than 0) or its back, y up or down; -1..1. Both look the
## same way.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(Vector2(-1.0, -1.0), Vector2(1.0, 1.0))
		_send(&"eye_look", eye_look)
## The cartoon eye's lid: 0 open, 1 shut.
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)

static var _meshes := {}

var _material: ShaderMaterial
var _models := {}
var _ready_yet := false


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`, without the importer's
## LOD meshes): for drawing one without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## The game model's mesh (one surface, to wear `new_material()`), without the importer's thinned LOD meshes: for
## drawing one without this node, or many with a MultiMesh (they then share their settings and phase).
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game")


## A new material for these meshes. Its shader settings are the game's to set: `phase` (0..1 through one beat),
## `flaps`, `sway`, `open`, `curl`, `glow`, the cartoon eye's, and the colours (the top of the shader lists them).
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
	_send(&"flaps", float(flaps))
	for setting in [&"phase", &"sway", &"open", &"curl", &"glow", &"cartoon_eyes", &"eye_look", &"blink"]:
		_send(setting, get(setting))


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat. (`velocity` is
## taken so that it is called as the other creatures are; its beat does not change with its speed: set `beat` and
## `sway` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: its colours (`skin`, `pale`, `web_under`, `freckle`, `light_colour`, `iris`,
## and the cartoon eye's `eye_white`, `eye_iris`) or any of the settings above.
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


## Shows the model it should wear (the full one, the game one with `game`, the low one with `low`), loading it the
## first time it is shown.
func _show() -> void:
	if not _ready_yet:
		return
	var which := "_lo" if low else ("_game" if game else "")
	if not _models.has(which):
		var made := MeshInstance3D.new()
		made.mesh = _mesh_at(MODEL % which)
		made.material_override = _material
		# (its web opens past the still model, its fins flap and it bends)
		made.extra_cull_margin = 0.12
		made.name = "DumboOctopus" + which
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
		# (every model without the importer's LODs: it is bent in the shader)
		_meshes[path] = without_lods(found.mesh)
		made.free()
	return _meshes[path]
