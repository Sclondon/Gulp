class_name Lionfish
extends Node3D
## A red lionfish (Pterois volitans), 0.35 m long: a big head with a large upturned mouth and
## big high eyes, banded all over in red-brown and cream (broad upright bars on the body, thin
## lines between them, rings round the eye and a dark bar down through it); thirteen long,
## separate, banded dorsal spines, each with its own flag of membrane; huge feathery pectoral
## fins spread to either side like wings, their rays running on free beyond the membrane; long
## pelvic fins; rounded soft dorsal, anal and tail fins, pale with rows of dark spots; a leaf-like
## tab standing over each eye and small tabs on the lower jaw.
##
## It hovers almost still, fins spread (`spread` 1), its pectoral fins and soft fins waving
## slowly (`scull`) and its tail beating gently (`sway`). With `spread` 0 the pectoral fans close
## and lie back along the body and the spines lie back.
##
## The spines sting: `SPINE_REACH` is how far their tips stand above its middle line (metres at
## scale 1), for a game that wants them to hurt.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down; its origin is on
## its middle line, half way along its length. `scale` it for a bigger or smaller one. No sound.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats and
## its fins wave `tail_beats` times (a whole number), so its motion comes round again exactly
## every beat. Either call `step(velocity, delta)` each frame, which moves `phase` on by
## delta / beat, or set `phase` yourself (for a picture that must loop). The same names and
## meanings as GameCommon's yellowfin tuna, snapper and parrotfish.
##
## Its mouth opens: `gape` 0 shut to 1 wide, as when it gulps its prey (the lower jaw and its
## tabs swing down about the hinge, the snout lifts a little, the dark inside of the mouth shows).
##
## The model is creatures/lionfish/models/lionfish.glb (and _lo), built by
## tools/build_lionfish.py; lionfish.gdshader draws its markings and moves it (no bones).

const MODEL := "res://creatures/lionfish/models/lionfish%s.glb"
const SHADER := preload("res://creatures/lionfish/lionfish.gdshader")
## As the model is built (tools/build_lionfish.py): from the tip of its snout to the edge of its
## tail, and how deep and how wide its body is at its deepest, without fins (metres, at scale 1).
const LENGTH := 0.35
const DEPTH := 0.099
const WIDTH := 0.048
## How far the tips of its dorsal spines stand above its middle line with `spread` 1 (metres, at
## scale 1): the spines sting.
const SPINE_REACH := 0.143
## How far its spread pectoral fins reach out to each side of its middle line, and below it
## (metres, at scale 1).
const FIN_REACH := 0.127
const FIN_BELOW := 0.118

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 3.0
## How many times in a beat its tail beats and its fins wave.
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely its body and tail beat: about 0.3 hovering, 1 swimming, 0 still.
@export_range(0.0, 2.0) var sway := 0.3:
	set(value):
		sway = value
		_send(&"sway", value)
## How much its pectoral fins and soft fins wave: 1 as it hovers, 0 held still.
@export_range(0.0, 2.0) var scull := 1.0:
	set(value):
		scull = value
		_send(&"scull", value)
## Its fins and spines: 1 fanned out and raised, 0 folded back along the body.
@export_range(0.0, 1.0) var spread := 1.0:
	set(value):
		spread = value
		_send(&"spread", value)
## Its mouth: 0 shut, 1 wide open, as when it gulps its prey.
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = value
		_send(&"gape", value)
## The low model (about a fourteenth of the triangles), for far off or for many of them. It
## wins over `game`.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (2,402 triangles, against the full model's 22,197): the same fish, its
## triangles spent where they show (the outline, the eye, the mouth), for games. With `game` on
## (and `low` off) the full model is never loaded, so a game's export may leave its .glb out.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 the eye as it is (the default), 1 a bigger cartoon eye (a white, an
## iris, a big pupil, a highlight, a dark outline; see the README for its character).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = value
		_send(&"cartoon_eyes", value)
## Where its eyes look, each -1..1: x towards its nose (+) or its tail (-), y up (+) or down (-).
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value
		_send(&"eye_look", value)
## A blink: 0 open, 1 shut (a lid the colour of its head closes over each eye).
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = value
		_send(&"blink", value)
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set
## it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()

## The game model's triangles.
const GAME_TRIANGLES := 2402

static var _meshes := {}

var _material: ShaderMaterial
# (each model's MeshInstance3D, made when it is first shown: "", "_lo", "_game")
var _shown := {}


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`): for
## drawing one without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""), false)


## The game model's mesh (one surface, to wear `new_material()`; no automatic LODs, which would
## bend in straight pieces far off): for drawing one without this node.
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game", true)


## `mesh` without the thinned LOD meshes Godot's importer made for it.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


static func _mesh_at(path: String, plain: bool) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh) if plain else found.mesh
		made.free()
	return _meshes[path]


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase`
## (0..1 through one beat), `sway`, `scull`, `spread`, `gape`, `curl`, `wave` and the colours
## (the top of the shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_show()
	_send_phase()
	for setting: StringName in [&"sway", &"scull", &"spread", &"gape", &"cartoon_eyes", &"eye_look", &"blink"]:
		_send(setting, get(setting))


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the other fish's are; its beat here does not
## change with its speed: set `sway`, `spread` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `curl` (bends the body round to one side behind the head,
## radians from gills to tail; more than 0 and the tail comes round to +X), `wave` (the length
## of the wave along its body), `mouth` (the colour inside its mouth) and its colours (`bar`,
## `pale`, `belly`, `fin_clear`, `fin_spot`, `iris`, `iris_ring`), and the cartoon eye's (`sclera`, `eye_iris`,
## `lid`, `eye_grow`).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (all its models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one beat of the tail it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


# (only the model shown is ever loaded)
func _show() -> void:
	if not is_inside_tree():
		return
	var wanted := "_lo" if low else ("_game" if game else "")
	if not _shown.has(wanted):
		_shown[wanted] = _instance_of(wanted)
	for which: String in _shown:
		_shown[which].visible = which == wanted


func _instance_of(which: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = game_mesh() if which == "_game" else mesh_of(which == "_lo")
	mesh.material_override = _material
	# (its fins wave out past where the still model ends)
	mesh.extra_cull_margin = LENGTH * 0.2
	mesh.name = "Lionfish" + {"": "", "_lo": "Lo", "_game": "Game"}[which]
	add_child(mesh)
	return mesh
