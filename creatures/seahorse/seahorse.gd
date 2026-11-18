class_name Seahorse
extends Node3D
## A seahorse, of one of three types (`type`), each a model of its own, all built 0.15 m tall
## (`SIZE` is how tall each really is beside that):
##
## - COMMON (the default): the Pacific seahorse (Hippocampus ingens) of the Californian and
##   Mexican coast, golden yellow-orange, with bony ringed ridges, white flecks and dusky saddles.
## - SPINY: a thorny seahorse (Hippocampus histrix): slimmer, a longer snout, a spike on every
##   ridge where the rings cross it; sandy cream with broad red-brown bands.
## - PYGMY: a pygmy seahorse (Hippocampus bargibanti): tiny, plump, a short snout, pale
##   lilac-pink, covered in round red-pink tubercles.
##
## **Which way is which.** It hangs upright: +Y is up, and it faces -Z, the same forward as every
## other GameCommon creature (its snout points along -Z; its belly bulges that way too, its dorsal
## fin and back are towards +Z); +X is its right side. LENGTH is its HEIGHT, from the tip of its
## tail (hanging straight down, as built) to the top of its coronet. **Its origin is half way up
## that height, on the line of its tail**: the tail hangs straight down the Y axis below its root
## (0.009 m below the origin), the trunk rises above, and the head is held at right angles on top
## with its snout pointing forward, 0.039 m ahead of the origin (common).
##
## Its head is a horse's on an arched neck, with a tube of a snout (whose tip opens for `gape`)
## and a star of a coronet on its crown; its body is bony ringed plates with a round belly; its
## prehensile tail curls forward (`grip`: 0 nearly straight, 1 a tight spiral); a small fan of a
## dorsal fin on its back buzzes and tiny ear-like pectoral fins behind its head flutter. It drifts
## upright and bobs (`bob`). It has no `curl`: it does not swim by bending.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`: in a beat its dorsal fin
## buzzes `buzzes` times, its pectoral fins flutter `strokes` times and it bobs `bobs` times (whole
## numbers), so its motion comes round again exactly every beat. Either call
## `step(velocity, delta)` each frame, which moves `phase` on by delta / beat (and works its fins
## harder the faster it goes), or set `phase` yourself (for a picture that must loop).
##
## Three models of each type: the full one, the game one (`game`: about 1,500 to 1,800
## triangles, the same outline) and the low one (`low`). `cartoon_eyes`, `eye_look`,
## `eye_look_other` and `blink` give it cartoon eyes of its type's own character, which swivel each
## on its own, as a seahorse's do.
##
## A game that keeps its own MeshInstance3Ds needs no Seahorse node: `Seahorse.mesh_of(type,
## low)` (or `Seahorse.game_mesh(type)`) is a type's mesh and `Seahorse.new_material(type)` a
## material for it, whose shader settings the game sets itself.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it
## faces. `scale` it for a bigger or smaller one. No sound.
##
## The models are creatures/seahorse/models/seahorse_<type>.glb (and _game, _lo), built by
## tools/build_seahorse.py; its shader is seahorse.gdshader.

enum Type { COMMON, SPINY, PYGMY }

const MODEL := "res://creatures/seahorse/models/seahorse_%s%s.glb"
const SHADER := preload("res://creatures/seahorse/seahorse.gdshader")
## As the models are built (tools/build_seahorse.py): every type's height, tail tip to coronet
## (metres, at scale 1). `REACH` has how far each reaches forward, back and to the sides.
const LENGTH := 0.15
## Each type's name in its model's file name.
const NAMES := {Type.COMMON: "common", Type.SPINY: "spiny", Type.PYGMY: "pygmy"}
## How tall each type really is beside `LENGTH` (a grown one: the Pacific seahorse about 18 cm
## tall, the thorny seahorse 15 cm, the pygmy 2 cm). Multiply `scale` by it for true sizes.
const SIZE := {Type.COMMON: 1.2, Type.SPINY: 1.0, Type.PYGMY: 0.13}
## How far each type's still model reaches from its origin (metres, at scale 1, its tail
## hanging straight): x forward (towards -Z, its snout's tip) and y back (towards +Z, its dorsal
## fin), z to each side. Up and down it reaches LENGTH / 2 each way. Curled (`grip`), its tail
## reaches less far down and comes forward under its belly.
const REACH := {
	Type.COMMON: Vector3(0.039, 0.0152, 0.0111),
	Type.SPINY: Vector3(0.0428, 0.0175, 0.0142),
	Type.PYGMY: Vector3(0.0278, 0.015, 0.0156),
}
## What each type sets in the shader: its markings (`kind`) and the places on its model the shader
## needs (as its model is built: the build script's SHAPE lines; heights): where its jaw hinges
## (z, y), where its right eye sits on the skin, its right pectoral fin's root, where its dorsal
## fin's root runs (y, z at each end) and where its tail meets its trunk. The rest is its cartoon
## eye, its character: how much bigger than life, the iris's colour and width (of the eye), the
## pupil's width (of the iris), where the upper lid rests (eye radii up from its middle: 1 or more
## none of it shows) and how it slants (more than 0: higher at the snout), and where the lower lid
## rests (-1 or less: none of it shows).
const TYPES := {
	Type.COMMON: {
		"kind": 0, "hinge": Vector2(-0.232, 0.3785), "eye_skin": Vector3(0.0411, 0.404, -0.068),
		"pec_root": Vector3(0.0325, 0.338, 0.0388), "dorsal_root": Vector4(-0.0188, 0.0363, 0.0722, 0.0315),
		"tail_root": -0.06,
		# gentle and curious: a big amber eye, a round pupil, the lid resting calmly over its top
		"eye_size": 1.75, "iris": Color(0.95, 0.6, 0.1), "iris_size": 0.6, "pupil_size": 0.55,
		"lid": 0.55, "lid_tilt": 0.1, "lower_lid": -1.15,
	},
	Type.SPINY: {
		"kind": 1, "hinge": Vector2(-0.257, 0.3785), "eye_skin": Vector3(0.0388, 0.405, -0.07),
		"pec_root": Vector3(0.0289, 0.338, 0.0388), "dorsal_root": Vector4(-0.0195, 0.0343, 0.068, 0.0289),
		"tail_root": -0.06,
		# wary and grumpy: a smaller red-orange eye under a heavy lid that frowns down to the snout,
		# the lower lid raised
		"eye_size": 1.55, "iris": Color(0.9, 0.35, 0.08), "iris_size": 0.52, "pupil_size": 0.5,
		"lid": 0.22, "lid_tilt": -0.3, "lower_lid": -0.72,
	},
	Type.PYGMY: {
		"kind": 2, "hinge": Vector2(-0.157, 0.3785), "eye_skin": Vector3(0.0473, 0.41, -0.064),
		"pec_root": Vector3(0.0432, 0.338, 0.0388), "dorsal_root": Vector4(-0.0112, 0.0391, 0.0643, 0.0361),
		"tail_root": -0.06,
		# shy and sweet: a huge soft dark eye, nearly all iris and pupil, no lid
		"eye_size": 1.9, "iris": Color(0.45, 0.12, 0.18), "iris_size": 0.8, "pupil_size": 0.7,
		"lid": 1.3, "lid_tilt": 0.0, "lower_lid": -1.3,
	},
}

static var _meshes := {}

## Which type it is: its shape and its markings.
@export var type := Type.COMMON:
	set(value):
		type = value
		_dress()
		_show()
## Seconds one beat takes: everything it does comes round again each beat. 0 for a caller that
## sets `phase` itself (`step` then leaves `phase` alone).
@export var beat := 2.0
## How many times in a beat its dorsal fin buzzes, its pectoral fins flutter and it bobs.
@export var buzzes := 12:
	set(value):
		buzzes = maxi(value, 0)
		_send(&"buzzes", float(buzzes))
@export var strokes := 6:
	set(value):
		strokes = maxi(value, 0)
		_send(&"strokes", float(strokes))
@export var bobs := 1:
	set(value):
		bobs = maxi(value, 0)
		_send(&"bobs", float(bobs))
## How hard its fins work: 1 as it hangs about, 0 held still. `step` works them harder the faster
## it goes.
@export_range(0.0, 1.5) var row := 1.0:
	set(value):
		row = value
		_rowing = value
		_send(&"row", value)
## How much it bobs up and down and rocks as it hangs there: 1 gently, 0 still.
@export_range(0.0, 2.0) var bob := 1.0:
	set(value):
		bob = value
		_send(&"bob", value)
## How much its tail sways from side to side.
@export_range(0.0, 1.5) var sway := 0.3:
	set(value):
		sway = value
		_send(&"sway", value)
## Its tail: 0 nearly straight (hanging down, its tip turned a little forward), 1 curled forward
## into a tight spiral, as when it holds on to a stem.
@export_range(0.0, 1.0) var grip := 0.0:
	set(value):
		grip = clampf(value, 0.0, 1.0)
		_send(&"grip", grip)
## The mouth at the tip of its snout: 0 shut, 1 open (as it snaps up a shrimp).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## The speed (m/s, at scale 1) at which `step` has its fins working their hardest.
@export var top_speed := 0.15
## The low model (far off, phones, many at once) in place of the full one (or the game one).
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about 1,500 to 1,800 triangles, built to keep the full model's outline) in
## place of the full one (14,000 to 17,000). With `game` on, the full model is never loaded: each
## model is loaded only when it is first shown. `low` still shows the low model.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eyes (0 the eyes as they are; 1 bigger, a white with a coloured iris, a big pupil,
## a highlight, a dark outline and a lid that gives each type its own character).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where its right eye looks (-1..1 each way): x towards the snout (+) or back (-), y up (+) or
## down (-). Its eyes swivel each on its own: `eye_look_other` is its left eye's. Set both alike
## for both eyes to look the same way.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(Vector2(-1.0, -1.0), Vector2(1.0, 1.0))
		_send(&"eye_look", eye_look)
## Where its left eye looks (as `eye_look`).
@export var eye_look_other := Vector2.ZERO:
	set(value):
		eye_look_other = value.clamp(Vector2(-1.0, -1.0), Vector2(1.0, 1.0))
		_send(&"eye_look_other", eye_look_other)
## The cartoon eyes' lids: 0 open, 1 shut (the lids come together and the eye squashes).
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## How far through a beat it is, 0 to 1. `step` moves it on; or set it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)

var _material: ShaderMaterial
var _shown := {}
var _rowing := 1.0


## A type's mesh (`low` for the low one), for a game that keeps its own MeshInstance3Ds. Each is
## loaded once and kept.
static func mesh_of(type_wanted := Type.COMMON, low_wanted := false) -> Mesh:
	var path := MODEL % [NAMES[type_wanted], "_lo" if low_wanted else ""]
	if not _meshes.has(path):
		_meshes[path] = _load_mesh(path)
	return _meshes[path]


## A type's game model (about 1,500 to 1,800 triangles, the full model's outline), for a game
## that keeps its own MeshInstance3Ds: loaded once and kept, without the importer's automatic LODs
## (thinned meshes bend in straight pieces in the shader). Loading it never loads the full one.
static func game_mesh(type_wanted := Type.COMMON) -> Mesh:
	var path := MODEL % [NAMES[type_wanted], "_game"]
	if not _meshes.has(path):
		_meshes[path] = without_lods(_load_mesh(path))
	return _meshes[path]


## A mesh with the same surfaces and none of the importer's LODs.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


## A new material for a type's mesh, with that type's markings, places and cartoon eye. Its
## shader settings are the game's to set: phase (0..1), buzzes, strokes, bobs, row, bob, sway,
## grip (0..1), gape (0..1), cartoon_eyes, eye_look, eye_look_other, blink, flash, rim, tint (the
## top of the shader lists them). **A mesh must be drawn with a material made for its own type.**
static func new_material(type_wanted := Type.COMMON) -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	_wear(made, type_wanted)
	return made


static func _wear(on: ShaderMaterial, type_wanted: Type) -> void:
	var wears: Dictionary = TYPES[type_wanted]
	for setting: String in wears:
		on.set_shader_parameter(setting, wears[setting])


static func _load_mesh(path: String) -> Mesh:
	var made := (load(path) as PackedScene).instantiate()
	var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
	var mesh := found.mesh
	made.free()
	return mesh


func _init() -> void:
	_material = ShaderMaterial.new()
	_material.shader = SHADER
	_dress()


func _ready() -> void:
	_show()
	for setting: StringName in [&"buzzes", &"strokes", &"bobs"]:
		_send(setting, float(get(setting)))
	for setting: StringName in [&"bob", &"sway", &"grip", &"gape", &"cartoon_eyes", &"eye_look",
			&"eye_look_other", &"blink", &"phase"]:
		_send(setting, get(setting))
	_send(&"row", _rowing)


## Each frame, after putting it where it is: moves its beat on by `delta` seconds (unless `beat`
## is 0), and works its fins harder the faster it is going (`velocity`, world, m/s; Vector3.ZERO
## for one that hangs still).
func step(velocity: Vector3, delta: float) -> void:
	if beat > 0.0:
		phase += delta / beat
	var size := maxf(global_basis.get_scale().y, 0.001) if is_inside_tree() else 1.0
	var speed := clampf(velocity.length() / (top_speed * size), 0.0, 1.0)
	_rowing = move_toward(_rowing, row + 0.5 * speed, delta * 1.5)
	_send(&"row", _rowing)


## Sets one of the shader's settings: a game's effects (flash, rim, tint), mouth (the colour
## inside it), sheen, or the cartoon eye's (eye_size, iris, iris_size, pupil_size, lid, lid_tilt,
## lower_lid). `type` sets kind, the places and the eye again.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_send(setting, value)


## The material it is drawn with.
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


func _dress() -> void:
	if _material:
		_wear(_material, type)


# Only the model shown is loaded and put in, when it is first shown (one MeshInstance3D for each
# model and type shown so far).
func _show() -> void:
	if not is_node_ready():
		return
	var key := "%s%s" % [NAMES[type], "_lo" if low else ("_game" if game else "")]
	if not _shown.has(key):
		var mesh := MeshInstance3D.new()
		mesh.mesh = mesh_of(type, true) if low else (game_mesh(type) if game else mesh_of(type, false))
		mesh.material_override = _material
		# (its tail curls and its fins move out past the still model's box)
		mesh.extra_cull_margin = LENGTH * 0.3
		mesh.name = "Seahorse_" + key
		add_child(mesh)
		_shown[key] = mesh
	for each: String in _shown:
		(_shown[each] as MeshInstance3D).visible = each == key
