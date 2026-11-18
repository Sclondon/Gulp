class_name Trilobite
extends Node3D
## Trilobites, three kinds (`kind`), each a model of its own:
##
## - SMOOTH (0.15 m): smooth, rounded and very domed (as Bumastus): a big head shield and a big
##   tail shield, ten narrow body segments between, its three lobes all but smoothed away, big
##   eyes at the back of its cheeks; glossy amber-brown.
## - SPINY (0.2 m, its spines not counted): a narrow body with a strong middle lobe, long spines
##   out and back from every body segment, long cheek spines, a row of short spines up its back,
##   two long spines behind its tail shield, raised eyes (as the odontopleurids); grey-brown.
## - CHEEKS (0.3 m): a broad half-moon head shield with long crescent eyes and long cheek spines
##   sweeping back along its body, fourteen body segments ending in short points (the third in
##   long ones), a tiny tail shield and a long spine back from its last segment (as Olenellus);
##   reddish tan.
##
## Each has a head shield with crescent compound eyes, a ribbed body of segments in three lobes, a
## tail shield, and beneath them many small walking legs, each with a feathery gill, and two
## antennae out of the front of its head. All of its markings are drawn by its shader: no texture
## files.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it
## faces. Its head points along its own -Z (Godot's forward), its back up; its origin is ON THE
## GROUND under the middle of its shell (half way from the front of its head shield to the back of
## its tail shield), so put it where the sea floor is. `scale` it for a bigger or smaller one. No
## sound.
##
## Everything moves in the shader (no bones), on `phase`, 0 to 1 through one `beat`, in which each
## leg steps `steps` times (a whole number), so it comes round again exactly every beat. `walk`
## strides its legs (+ forwards), in waves running from back to front, its gills swinging with
## them; its antennae feel about; `enroll` rolls it up into a ball, head and tail shields meeting
## beneath (a ball resting on the ground). Either call `step(velocity, delta)` each frame, which
## moves `phase` on by how far it has walked (so its feet do not slide) or, standing, by `beat`,
## or set `phase` yourself.
##
## A game that keeps its own MeshInstance3Ds needs no Trilobite node: `Trilobite.mesh_of(kind,
## low)` and `Trilobite.game_mesh(kind)` are a kind's meshes and `Trilobite.new_material(kind)` a
## material for them, whose shader settings (phase, walk, enroll, feel, cartoon_eyes, eye_look,
## blink) the game sets itself.
##
## The models are creatures/trilobite/models/trilobite_<kind>.glb (and _lo, and _game), built by
## tools/build_trilobite.py; trilobite.gdshader draws the markings and moves it.

enum Kind { SMOOTH, SPINY, CHEEKS }

const MODEL := "res://creatures/trilobite/models/trilobite_%s%s.glb"
const SHADER := preload("res://creatures/trilobite/trilobite.gdshader")
## Each kind's name in its models' file names.
const NAMES := {Kind.SMOOTH: "smooth", Kind.SPINY: "spiny", Kind.CHEEKS: "cheeks"}
## How long each kind is (metres at scale 1): from the front of its head shield to the back of its
## tail shield (spines not counted).
const LENGTHS := {Kind.SMOOTH: 0.15, Kind.SPINY: 0.2, Kind.CHEEKS: 0.3}
## As the models are built (tools/build_trilobite.py), for each kind: what the shader is told of it
## (its size, where its head shield ends and its tail shield begins and the rest, as shares of its
## length: the top of trilobite.gdshader says what each is), its colours, and its cartoon eye.
const KINDS := {
	Kind.SMOOTH: {
		"size": 0.15, "venter": 0.06, "head_back": -0.12, "tail_front": 0.12, "segments": 10.0,
		"top_height": 0.224, "lobe": 0.13, "tail_rings": 0.0,
		"shell": Color(0.62, 0.4, 0.2), "dark": Color(0.3, 0.16, 0.07), "under": Color(0.86, 0.76, 0.6),
		"limb": Color(0.8, 0.5, 0.4),
		# a wide, innocent stare: a sea-green iris round a big round pupil, plenty of white, no lid
		"eye_gaze": Vector3(1.0, 0.75, 0.05), "eye_grow": 1.6, "iris": Color(0.2, 0.62, 0.58),
		"iris_size": 0.56, "pupil_size": 0.32, "pupil_shape": Vector2(1.0, 1.0), "lid_rest": 1.05, "lid_slope": 0.0,
	},
	Kind.SPINY: {
		"size": 0.2, "venter": 0.07, "head_back": -0.2, "tail_front": 0.3, "segments": 9.0,
		"top_height": 0.133, "lobe": 0.1, "tail_rings": 0.6,
		"shell": Color(0.42, 0.36, 0.31), "dark": Color(0.17, 0.14, 0.12), "under": Color(0.78, 0.72, 0.64),
		"limb": Color(0.72, 0.45, 0.38),
		# a suspicious squint: a small pupil in a red iris under a low, level lid
		"eye_gaze": Vector3(1.0, 0.9, -0.1), "eye_grow": 1.7, "iris": Color(0.85, 0.22, 0.1),
		"iris_size": 0.5, "pupil_size": 0.17, "pupil_shape": Vector2(1.0, 1.0), "lid_rest": 0.22, "lid_slope": 0.0,
	},
	Kind.CHEEKS: {
		"size": 0.3, "venter": 0.05, "head_back": -0.17, "tail_front": 0.43, "segments": 14.0,
		"top_height": 0.092, "lobe": 0.075, "tail_rings": 0.8,
		"shell": Color(0.64, 0.42, 0.3), "dark": Color(0.34, 0.19, 0.12), "under": Color(0.84, 0.74, 0.62),
		"limb": Color(0.78, 0.48, 0.38),
		# a sleepy droop: a long amber eye with a bar of a pupil, the lid half down and lower at the back
		"eye_gaze": Vector3(1.0, 0.85, 0.15), "eye_grow": 1.5, "iris": Color(0.95, 0.68, 0.18),
		"iris_size": 0.6, "pupil_size": 0.3, "pupil_shape": Vector2(1.6, 0.5), "lid_rest": 0.12, "lid_slope": -0.3,
	},
}
## How far one foot moves in one step at `walk` 1, and how much of a step a foot is on the ground
## (shares of its length, as the shader has them).
const STRIDE := 0.05
const ON_GROUND := 0.6

## Which kind it is (its model and its look).
@export var kind := Kind.SMOOTH:
	set(value):
		kind = value
		_set_kind()
		_show()
## Seconds one beat takes (used by `step` when it is not walking).
@export var beat := 0.6
## How many times each leg steps in a beat.
@export var steps := 1:
	set(value):
		steps = maxi(value, 0)
		_send_phase()
## Walking: 0 standing, 1 a walk forwards, -1 backwards; more is a longer stride.
@export_range(-2.0, 2.0) var walk := 0.0:
	set(value):
		walk = value
		_send(&"walk", value)
## Rolled up: 0 spread out, 1 a ball (resting on the ground, its legs and antennae drawn in).
@export_range(0.0, 1.0) var enroll := 0.0:
	set(value):
		enroll = clampf(value, 0.0, 1.0)
		_send(&"enroll", enroll)
## The low model (a twentieth of the full one's triangles or less), for far off or for several.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about a twelfth of the full one's triangles, spent where the eye looks: the
## shell's outline, its eyes, its spines), shown in place of the full one; `low` still shows the
## low model. Each model is loaded only when it is first shown: with `game` on, the full model is
## never loaded.
@export var game := false:
	set(value):
		game = value
		_show()
## 0 its eyes as they are; 1 cartoon eyes (each kind its own: see the README).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where its cartoon eyes look, -1..1 each way: x towards its front (+) or its tail, y up or down.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(-Vector2.ONE, Vector2.ONE)
		_send(&"eye_look", eye_look)
## A blink: 0 open, 1 shut (a lid the colour of its shell comes down over each eye).
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## How far through a beat it is, 0 to 1 (only the fraction counts).
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()

static var _meshes := {}

var _material: ShaderMaterial
# (each kind's models as they are made: {"full": .., "low": .., "game": ..})
var _shown := {}


## A kind's full mesh, or its low one (each one surface, to wear `new_material(kind)`).
static func mesh_of(which: Kind, low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % [NAMES[which], "_lo" if low_wanted else ""])


## A kind's game mesh (one surface, to wear `new_material(kind)`), without the importer's automatic
## LODs (a body bent in the shader would bend in straight pieces far off).
static func game_mesh(which: Kind) -> Mesh:
	return _mesh_at(MODEL % [NAMES[which], "_game"], true)


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


## A new material for a kind's meshes, its look set. Its other settings are the game's to set:
## `phase` (0..1 through one cycle of steps), `walk`, `enroll`, `feel`, `cartoon_eyes`,
## `eye_look`, `blink`.
static func new_material(which: Kind) -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	var settings: Dictionary = KINDS[which]
	for setting: String in settings:
		made.set_shader_parameter(setting, settings[setting])
	return made


func _init() -> void:
	_material = ShaderMaterial.new()
	_material.shader = SHADER
	_set_kind()


func _ready() -> void:
	_show()
	_send_phase()
	_send(&"walk", walk)
	_send(&"enroll", enroll)
	_send(&"cartoon_eyes", cartoon_eyes)
	_send(&"eye_look", eye_look)
	_send(&"blink", blink)


## Each frame. Walking (`walk` not 0): moves `phase` on by how far it has gone forwards or
## backwards (`velocity` in the world's metres a second), so that its feet keep still on the
## ground, and points `walk` the way it is going (keeping its size). Not walking: moves `phase` on
## by delta / beat (its antennae feel about).
func step(velocity: Vector3, delta: float) -> void:
	if steps == 0:
		return
	if is_zero_approx(walk):
		phase += delta / maxf(beat, 0.01)
		return
	var speed := -(global_basis.inverse() * velocity).z
	if absf(speed) < 0.00005:
		return
	var size := absf(walk)
	walk = size * signf(speed)
	# (a foot moves STRIDE * length * size while it is on the ground, which is ON_GROUND of a step)
	phase += absf(speed) * delta * ON_GROUND / (STRIDE * float(LENGTHS[kind]) * size) / steps


## Sets one of the shader's settings: its colours (`shell`, `dark`, `under`, `limb`), `feel` (how
## far its antennae swing and its gills beat), or `walk`, `enroll`, `cartoon_eyes`, `eye_look`,
## `blink` for a game's own material. (Changing `kind` sets its look again.)
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (every model of it wears it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one cycle of steps it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * steps, 1.0))


func _set_kind() -> void:
	var settings: Dictionary = KINDS[kind]
	for setting: String in settings:
		_send(StringName(setting), settings[setting])


# Shows the model wanted, making (and loading) it the first time it is wanted.
func _show() -> void:
	if not is_inside_tree():
		return
	var which := "low" if low else ("game" if game else "full")
	var made: Dictionary = _shown.get(kind, {})
	if not made.has(which):
		var mesh: Mesh
		if which == "low":
			mesh = mesh_of(kind, true)
		elif which == "game":
			mesh = game_mesh(kind)
		else:
			mesh = mesh_of(kind, false)
		made[which] = _instance_of(mesh, "Trilobite%s%s" % [NAMES[kind].capitalize(), "" if which == "full" else which.capitalize()])
		_shown[kind] = made
	for k: Kind in _shown:
		for model: String in _shown[k]:
			(_shown[k][model] as MeshInstance3D).visible = k == kind and model == which


func _instance_of(mesh_wanted: Mesh, named: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = mesh_wanted
	mesh.material_override = _material
	# (it rolls up and its antennae swing past where the still model ends)
	mesh.extra_cull_margin = 0.1
	mesh.name = named
	add_child(mesh)
	return mesh
