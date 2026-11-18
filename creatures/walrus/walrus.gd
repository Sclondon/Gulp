class_name Walrus
extends Node3D
## A Pacific walrus (Odobenus rosmarus divergens), 3 m from the front of its muzzle to the tips
## of its hind flippers: a huge wrinkled cinnamon-brown bulk with thick folds of hide round the
## neck and shoulders, a small head with a broad flat muzzle and a pad of stiff pale whiskers,
## two long ivory tusks (`tusks`: their length), small bloodshot eyes, no ear flaps, broad
## square fore flippers held to its sides and hind flippers that point straight back.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down; its origin is on
## its middle line, half way along, so it reaches 1.5 m ahead and 1.5 m behind (its tusks hang
## 0.7 m below its middle line). `scale` it for a bigger or smaller one. No sound.
##
## It swims as walruses do: it sculls its hind flippers and the rear of its body from side to
## side, like a fish, each flipper fanned open as it pushes; its fore flippers stay at its sides.
## All of that is drawn by the shader (no bones).
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which it sculls
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat.
## Either call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or
## set `phase` yourself. The same names and meanings as GameCommon's fish (YellowfinTuna).
##
## The model is creatures/walrus/models/walrus.glb (and _lo, _game), built by
## tools/build_walrus.py; walrus.gdshader draws its hide and moves it.

const MODEL := "res://creatures/walrus/models/walrus%s.glb"
const SHADER := preload("res://creatures/walrus/walrus.gdshader")
## As the model is built (tools/build_walrus.py): from the front of its muzzle to the tips of
## its hind flippers, and how deep and how wide its body is at its fattest, the shoulders
## (metres, at scale 1).
const LENGTH := 3.0
const DEPTH := 0.99
const WIDTH := 1.1
## How far below its middle line the tips of its tusks reach at `tusks` 1.
const TUSK_REACH := 0.73
## A cow's tusks: shorter and thinner than a bull's (for `tusks`).
const COW_TUSKS := 0.55

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 3.2
## How many times in a beat it sculls its hind flippers (there and back).
@export var tail_beats := 2:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it sculls: 1 a walrus cruising (its flipper tips swing about 0.35 m either way), 0
## gliding still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Its mouth: 0 shut, 1 wide open.
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = value
		_send(&"gape", value)
## Its tusks' length: 1 a bull's (they reach about 0.6 m out of its lip), `COW_TUSKS` a cow's
## (shorter and thinner), 0 none (a calf).
@export_range(0.0, 1.2) var tusks := 1.0:
	set(value):
		tusks = value
		_send(&"tusks", value)
## Turning: how far its body is bent round to one side behind its head, radians from neck to
## hind flippers (more than 0 and its tail comes round to +X).
@export_range(-1.6, 1.6) var curl := 0.0:
	set(value):
		curl = value
		_send(&"curl", value)
## The same, up or down (more than 0 and its tail comes up, as when it dives).
@export_range(-1.6, 1.6) var arch := 0.0:
	set(value):
		arch = value
		_send(&"arch", value)
## The low model (about a fifteenth of the triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (models/walrus_game.glb, about a tenth of the full model's triangles, spent
## on its outline, face, eyes, tusks and flippers) in place of the full one. `low` still shows
## the low one. Each model is loaded only when it is first shown, so with `game` on the full
## .glb is never loaded (a game's web export can leave it out).
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 the eye as it is, 1 bigger and drawn as a cartoon (small, rheumy and
## grumpy under heavy lids).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = value
		_send(&"cartoon_eyes", value)
## Where both eyes look, -1..1: x towards its nose, y up (the cartoon eye's iris slides that way).
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value
		_send(&"eye_look", value)
## Its lids: 0 open, 1 shut.
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

static var _meshes := {}

var _material: ShaderMaterial
# (the models shown so far, by their ending: "" the full one, "_lo", "_game")
var _shown := {}
var _made := false


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`): for
## drawing a walrus without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## The game model's mesh (one surface, to wear `new_material()`), without the thinned LOD meshes
## Godot's importer makes (bent in the shader, they would bend in straight pieces far off).
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game", true)


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase`
## (0..1 through one scull), `sway`, `gape`, `tusks`, `curl`, `arch` and the rest (the top of the
## shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_made = true
	_show()
	_send_phase()
	_send(&"sway", sway)
	_send(&"gape", gape)
	_send(&"tusks", tusks)
	_send(&"curl", curl)
	_send(&"arch", arch)
	_send(&"cartoon_eyes", cartoon_eyes)
	_send(&"eye_look", eye_look)
	_send(&"blink", blink)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the fish's are; its beat here does not change
## with its speed: set `sway` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `wave` (the length of the wave along its body, in body
## lengths), `flush` (0..1, how pink it is flushed), `wrinkles` (how deep the fine wrinkles are),
## `scars`, `wet` (1 just out of a dive, 0 dry), `iris` and its colours (`hide`, `hide_back`,
## `belly`, `hide_pink`, `crease`, `flipper`, `nose`, `mouth_inside`, `tooth`, `ivory`,
## `whiskers`, `claw`).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one scull it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


func _show() -> void:
	if not _made:
		return
	var wanted := "_lo" if low else ("_game" if game else "")
	if not _shown.has(wanted):
		_shown[wanted] = _instance_of(wanted)
	for ending: String in _shown:
		(_shown[ending] as MeshInstance3D).visible = ending == wanted


func _instance_of(ending: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = game_mesh() if ending == "_game" else mesh_of(ending == "_lo")
	mesh.material_override = _material
	# (its flippers swing out past where the still model ends; `curl` and `arch` further)
	mesh.extra_cull_margin = 0.25 * LENGTH
	mesh.name = "Walrus" + {"": "", "_lo": "Lo", "_game": "Game"}[ending]
	add_child(mesh)
	return mesh


static func _mesh_at(path: String, plain := false) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh) if plain else found.mesh
		made.free()
	return _meshes[path]


## A copy of `mesh` without the LOD meshes Godot's importer made for it.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain
