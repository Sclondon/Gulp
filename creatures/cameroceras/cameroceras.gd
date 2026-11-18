class_name Cameroceras
extends Node3D
## A cameroceras, a giant straight-shelled nautiloid of the Ordovician seas, 6 m from the point
## of its shell to the tips of its arms: a long, slowly widening cone of a shell, pale with growth
## bands and faint brown zigzag stripes, and out of its wide open end a reddish squid-like head
## with two big eyes, a thick leathery hood over it, a funnel beneath and a crown of ten arms
## trailing back.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it
## goes. IT JETS SHELL FIRST: its -Z (Godot's forward, so `look_at` points it) is the way it goes,
## the point of the shell leading; the opening, the head and the arms face +Z, behind it. Up is +Y.
## Its origin is on the shell's axis half way from the shell's point to the arms' tips. `scale` it
## for a bigger or smaller one. No sound.
##
## Everything moves in the shader (no bones), on `phase`, 0 to 1 through one `beat`: one jet, in
## which it rocks and bobs a little, its head draws in and its arms bunch, then trail and curl
## again. `withdraw` (0 to 1) pulls its head and arms back into the shell and turns the hood down
## over the opening. Either call `step(velocity, delta)` each frame, which moves `phase` on by
## delta / beat, or set `phase` yourself.
##
## The models are creatures/cameroceras/models/cameroceras.glb (and _lo, and _game), built by
## tools/build_cameroceras.py; cameroceras.gdshader draws the markings and moves it.

const MODEL := "res://creatures/cameroceras/models/cameroceras%s.glb"
const SHADER := preload("res://creatures/cameroceras/cameroceras.gdshader")
## As the model is built (tools/build_cameroceras.py), metres at scale 1: from the point of its
## shell to the tips of its arms, and how deep and how wide the shell is at its opening.
const LENGTH := 6.0
const DEPTH := 0.72
const WIDTH := 0.72
## How long the shell is (from its point at z -3 to its opening at z 1.75), and how far behind the
## origin the arms reach (+Z).
const SHELL_LENGTH := 4.75
const ARM_REACH := 3.0

## Seconds one beat takes (one jet).
@export var beat := 2.4
## How strongly it rocks, bobs and jets and its arms trail and curl: 1 swimming, 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Its head and arms: 0 out, 1 pulled right into the shell behind the hood.
@export_range(0.0, 1.0) var withdraw := 0.0:
	set(value):
		withdraw = clampf(value, 0.0, 1.0)
		_send(&"withdraw", withdraw)
## The low model (about a sixth of the game model's triangles), for far off or for several.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about a thirteenth of the full one's triangles, spent where the eye looks: the
## shell's round outline, the eyes, the hood's edge, the arms), shown in place of the full one;
## `low` still shows the low model. Each model is loaded only when it is first shown: with `game`
## on, the full model is never loaded.
@export var game := false:
	set(value):
		game = value
		_show()
## 0 its eyes as they are; 1 cartoon eyes (an old giant's calm, heavy-lidded stare: see the
## README).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where its cartoon eyes look, -1..1 each way: x towards its face and arms (+) or its shell, y up
## or down.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(-Vector2.ONE, Vector2.ONE)
		_send(&"eye_look", eye_look)
## A blink: 0 open, 1 shut (a lid the colour of its skin comes down over each eye).
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## How far through a beat it is, 0 to 1 (only the fraction counts).
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)

static var _meshes := {}

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`).
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## The game model's mesh (one surface, to wear `new_material()`), without the importer's automatic
## LODs (arms bent in the shader would bend in straight pieces far off).
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game", true)


## A copy of `mesh` without its automatic LODs.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


static func _mesh_at(path: String, plain := false) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh) if plain else found.mesh
		made.free()
	return _meshes[path]


## A new material for these meshes. Its shader settings are the game's to set: `phase` (0..1
## through one beat), `sway`, `withdraw`, `cartoon_eyes`, `eye_look`, `blink` and the colours (the
## top of the shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_show()
	_send(&"phase", phase)
	_send(&"sway", sway)
	_send(&"withdraw", withdraw)
	_send(&"cartoon_eyes", cartoon_eyes)
	_send(&"eye_look", eye_look)
	_send(&"blink", blink)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the other animals' are; set `beat` and `sway` from
## its speed yourself.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: its colours (`shell_colour`, `stripe`, `skin`, `hide`,
## `arm`), `stripes_show`, or `sway`, `withdraw`, `cartoon_eyes`, `eye_look`, `blink` for a game's
## own material.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# Shows the model wanted, making (and loading) it the first time it is wanted.
func _show() -> void:
	if not is_inside_tree():
		return
	if low and not _low:
		_low = _instance_of(mesh_of(true), "CamerocerasLo")
	elif not low and game and not _game:
		_game = _instance_of(game_mesh(), "CamerocerasGame")
	elif not low and not game and not _full:
		_full = _instance_of(mesh_of(false), "Cameroceras")
	for shown: MeshInstance3D in [_full, _low, _game]:
		if shown:
			shown.visible = shown == (_low if low else (_game if game else _full))


func _instance_of(mesh_wanted: Mesh, named: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = mesh_wanted
	mesh.material_override = _material
	# (it rocks and bobs, and its arms swing, past where the still model ends)
	mesh.extra_cull_margin = 0.4
	mesh.name = named
	add_child(mesh)
	return mesh
