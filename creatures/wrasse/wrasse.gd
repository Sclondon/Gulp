class_name Wrasse
extends Node3D
## A wrasse, of either of two kinds (`kind`), each a model of its own, both built 0.25 m long
## (`SIZE` says how long each really is):
##
## - CLEANER (the default): the bluestreak cleaner wrasse (Labroides dimidiatus), about 11 cm: a
##   slim cigar with a pointed head, a small mouth with thick lips, and a black stripe from the
##   tip of its snout through its eye along its flank, widening to the tail; pale yellow-white in
##   front turning to bright blue behind above the stripe, white below; a rounded tail.
## - MOON: the moon wrasse (Thalassoma lunare), about 25 cm: a stouter cigar, green with an
##   upright magenta bar on every scale, a blue head banded with magenta from the eye, magenta
##   fins edged with blue, and a crescent tail with long lobes, yellow in the middle.
##
## Both swim as wrasses do: they row with their pectoral fins, both together, the body bobbing
## up and down with each stroke, the tail trailing; with `sway` up the tail beats too, as when
## they hurry.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down; its origin is on
## its middle line, half way along its length. `scale` it for a bigger or smaller one. No sound.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its pectoral fins
## row `tail_beats` times (a whole number) and its tail swings as often, so its motion comes
## round again exactly every beat. Either call `step(velocity, delta)` each frame, which moves
## `phase` on by delta / beat, or set `phase` yourself (for a picture that must loop). The same
## names and meanings as GameCommon's yellowfin tuna, snapper and parrotfish.
##
## Its mouth opens: `gape` 0 shut to 1 wide, as when it bites (the lower jaw swings down about
## its hinge, the snout lifts a little and the thick upper lip pushes forward, the dark inside of
## the mouth shows).
##
## A game that keeps its own MeshInstance3Ds needs no Wrasse node: `Wrasse.mesh_of(kind, low)` is
## a kind's mesh and `Wrasse.new_material(kind)` a material for it.
##
## The models are creatures/wrasse/models/wrasse_<kind>.glb (and _lo), built by
## tools/build_wrasse.py; wrasse.gdshader draws the markings of both and moves them (no bones).

enum Kind { CLEANER, MOON }

const MODEL := "res://creatures/wrasse/models/wrasse_%s%s.glb"
const SHADER := preload("res://creatures/wrasse/wrasse.gdshader")
## As the models are built (tools/build_wrasse.py): from the tip of the snout to the tips of the
## tail, every kind (metres, at scale 1).
const LENGTH := 0.25
## Each kind's name in its model's file name.
const NAMES := {Kind.CLEANER: "cleaner", Kind.MOON: "moon"}
## How long each kind really is beside the model's 0.25 m (1): multiply a fish's `scale` by this
## for one of its true size.
const SIZE := {Kind.CLEANER: 0.45, Kind.MOON: 1.0}
## How deep and how wide each kind's body is at its deepest, without fins (metres, at scale 1).
const DEPTH := {Kind.CLEANER: 0.048, Kind.MOON: 0.06}
const WIDTH := {Kind.CLEANER: 0.024, Kind.MOON: 0.026}
## What each kind sets in the shader: which markings (`kind`), its pectoral root and its tail's
## hinge as its model is built (the build script prints the root), and its colours.
const KINDS := {
	Kind.CLEANER: {
		"kind": 0.0, "pec_root": Vector3(0.041, -0.006, 0.215), "joint": 0.835,
		"back": Color(0.16, 0.42, 0.95), "flank": Color(0.93, 0.9, 0.66), "belly": Color(0.95, 0.96, 0.98),
		"mark": Color(0.02, 0.02, 0.05), "head": Color(0.85, 0.85, 0.72), "lips": Color(0.08, 0.08, 0.14),
		"fin": Color(0.1, 0.22, 0.65), "fin_edge": Color(0.45, 0.78, 1.0), "tail_main": Color(0.02, 0.02, 0.05),
		"iris": Color(0.12, 0.16, 0.35), "iris_ring": Color(0.5, 0.7, 1.0),
		# the cartoon eye: an eager little helper, wide open, all white round a bright blue iris
		"eye_grow": 1.75, "sclera": Color(1.0, 1.0, 1.0), "eye_iris": Color(0.15, 0.45, 1.0),
		"lid": Color(0.03, 0.03, 0.06), "iris_size": 0.42, "pupil_size": 0.6, "pupil_shape": 0,
		"lid_top": 1.4, "lid_slant": 0.0, "lid_low": -1.4,
		"eye_mid": Vector3(0.0328, 0.022, 0.092), "eye_facing": Vector3(0.9317, 0.2994, -0.2059),
		"eye_sink": 0.0012, "eye_radius": 0.017,
	},
	Kind.MOON: {
		"kind": 1.0, "pec_root": Vector3(0.045, -0.004, 0.215), "joint": 0.815,
		"back": Color(0.06, 0.48, 0.38), "flank": Color(0.2, 0.7, 0.44), "belly": Color(0.5, 0.8, 0.72),
		"mark": Color(0.86, 0.2, 0.52), "head": Color(0.3, 0.42, 0.8), "lips": Color(0.55, 0.35, 0.75),
		"fin": Color(0.86, 0.24, 0.55), "fin_edge": Color(0.25, 0.62, 0.98), "tail_main": Color(1.0, 0.84, 0.2),
		"iris": Color(0.72, 0.84, 0.3), "iris_ring": Color(0.86, 0.22, 0.2),
		# the cartoon eye: cheeky and curious, the upper lid cocked up towards the front over a
		# lime-green iris
		"eye_grow": 1.5, "sclera": Color(0.98, 0.97, 0.9), "eye_iris": Color(0.55, 0.85, 0.2),
		"lid": Color(0.3, 0.42, 0.8), "iris_size": 0.5, "pupil_size": 0.5, "pupil_shape": 0,
		"lid_top": 0.62, "lid_slant": -0.35, "lid_low": -0.9,
		"eye_mid": Vector3(0.0383, 0.022, 0.092), "eye_facing": Vector3(0.9607, 0.1987, -0.194),
		"eye_sink": 0.0008, "eye_radius": 0.017,
	},
}

## Which wrasse.
@export var kind := Kind.CLEANER:
	set(value):
		kind = value
		if _material:
			for setting: String in KINDS[kind]:
				_material.set_shader_parameter(setting, KINDS[kind][setting])
		_build()
## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 1.0
## How many strokes of its pectoral fins (and swings of its tail) in a beat.
@export var tail_beats := 2:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely its body and tail beat: 1 cruising (the tail trailing), 2 hurrying, 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How hard its pectoral fins row: 1 as it cruises, 0 folded back and still (and no bob).
@export_range(0.0, 1.5) var scull := 1.0:
	set(value):
		scull = value
		_send(&"scull", value)
## Its mouth: 0 shut, 1 wide open, as when it bites.
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = value
		_send(&"gape", value)
## How far its dorsal fin is raised: 1 up, 0 folded down.
@export_range(0.0, 1.0) var dorsal := 1.0:
	set(value):
		dorsal = value
		_send(&"dorsal", value)
## The low model (about a tenth of the triangles), for far off or for many of them. It wins
## over `game`.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (1,114 triangles for the cleaner, 1,714 for the moon wrasse, against the full
## models' 13,884 and 14,228): the same fish, its
## triangles spent where they show (the outline, the eye, the mouth), for games. With `game` on
## (and `low` off) the full model is never loaded, so a game's export may leave its .glb out.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 the eye as it is (the default), 1 a bigger cartoon eye (a white, an
## iris, a big pupil, a highlight, a dark outline; each kind its own; see the README).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = value
		_send(&"cartoon_eyes", value)
## Where its eyes look, each -1..1: x towards its nose (+) or its tail (-), y up (+) or down (-).
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value
		_send(&"eye_look", value)
## A blink: 0 open, 1 shut (a lid the colour of the skin about it closes over each eye).
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

## Each kind's game model's triangles.
const GAME_TRIANGLES := {Kind.CLEANER: 1114, Kind.MOON: 1714}

static var _meshes := {}

var _material: ShaderMaterial
# (each model's MeshInstance3D, made when it is first shown: "", "_lo", "_game")
var _shown := {}


## A kind's full model's mesh, or its low one's (each one surface, to wear
## `new_material(kind)`): for drawing one without this node.
static func mesh_of(which: Kind, low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % [NAMES[which], "_lo" if low_wanted else ""], false)


## A kind's game model's mesh (one surface, to wear `new_material(kind)`; no automatic LODs,
## which would bend in straight pieces far off): for drawing one without this node.
static func game_mesh(which: Kind) -> Mesh:
	return _mesh_at(MODEL % [NAMES[which], "_game"], true)


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


## A new material for a kind's meshes, its markings and colours set. Its other shader settings
## are the game's to set: `phase` (0..1 through one stroke), `sway`, `scull`, `gape`, `dorsal`,
## `curl`, `wave` (the top of the shader lists them).
static func new_material(which: Kind) -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	for setting: String in KINDS[which]:
		made.set_shader_parameter(setting, KINDS[which][setting])
	return made


func _init() -> void:
	_material = new_material(kind)


func _ready() -> void:
	_build()


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the other fish's are; its beat here does not
## change with its speed: set `sway`, `scull` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `curl` (bends the body round to one side behind the head,
## radians from gills to tail; more than 0 and the tail comes round to +X), `wave` (the length
## of the wave along its body), `mouth` (the colour inside its mouth) and its colours (`back`,
## `flank`, `belly`, `mark`, `head`, `lips`, `fin`, `fin_edge`, `tail_main`, `iris`,
## `iris_ring`), and the cartoon eye's (`sclera`, `eye_iris`, `lid`, `eye_grow`...). A change of
## `kind` sets the colours and the eye back to that kind's.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (all its models wear it; it is kept when `kind` changes).
func material() -> ShaderMaterial:
	return _material


func _build() -> void:
	if not is_inside_tree():
		return
	for which: String in _shown:
		_shown[which].queue_free()
	_shown.clear()
	_show()
	_send_phase()
	for setting: StringName in [&"sway", &"scull", &"gape", &"dorsal", &"cartoon_eyes", &"eye_look", &"blink"]:
		_send(setting, get(setting))


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one stroke it is)
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
	mesh.mesh = game_mesh(kind) if which == "_game" else mesh_of(kind, which == "_lo")
	mesh.material_override = _material
	# (its tail and fins swing out past where the still model ends)
	mesh.extra_cull_margin = LENGTH * 0.3
	mesh.name = "Wrasse%s%s" % [NAMES[kind].capitalize(), {"": "", "_lo": "Lo", "_game": "Game"}[which]]
	add_child(mesh)
	return mesh
