class_name Arowana
extends Node3D
## A silver arowana (Osteoglossum bicirrhosum), 0.9 m long: a long blade of a body, deep and very
## flattened from side to side, with very large scales; a big upturned trapdoor mouth with two
## chin barbels; a long dorsal and a longer anal fin set far back that almost join the small
## rounded tail; long narrow pectoral fins.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down; its origin is on its
## middle line (the height of the tail), half way along, so it reaches 0.45 m ahead (the barbels
## 0.04 m more) and 0.45 m behind. Its back is 0.07 m above the origin, its belly 0.083 below.
## `scale` it for a bigger or smaller one. No sound.
##
## It swims as arowanas do, a long slow wave down most of the body, drawn by the shader (no
## bones). Its mouth opens: `gape`. It cruises just under the surface and leaps for prey: the
## leap itself is the game's to move (a jump along an arc, pitched to the way it goes); `arch`
## bends the body for it (less than 0 as it springs out, head and tail raised; more than 0 at the
## top and as it falls, its back bowed up), and `gape` opens the mouth at the top.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat.
## Either call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or
## set `phase` yourself (for a picture that must loop: frame / frames in a beat). The same
## names and meanings as GameCommon's yellowfin tuna and sardine, so they are driven the same way.
##
## The models are creatures/arowana/models/arowana.glb (the full one), arowana_game.glb (the game one,
## its triangles spent where they show: `game`) and arowana_lo.glb, built by tools/build_arowana.py;
## arowana.gdshader draws the markings and swims it. Each model is loaded only when it is first
## shown, so with `game` on the full one is never loaded.

const MODEL := "res://creatures/arowana/models/arowana%s.glb"
const SHADER := preload("res://creatures/arowana/arowana.gdshader")
## As the model is built (tools/build_arowana.py): from the tip of its lower jaw to the end of its
## tail (not counting the barbels), and how deep and how wide its body is at its deepest (metres,
## at scale 1).
const LENGTH := 0.9
const DEPTH := 0.15
const WIDTH := 0.052

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 2.0
## How many times in a beat its tail beats (there and back).
@export var tail_beats := 2:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it beats: 1 an arowana cruising (its tail swings about 0.06 m either way), 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far its mouth is open: 0 shut, 1 wide open (the lower jaw and its barbels drop like a
## trapdoor).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## How far the body is bent in the up-and-down plane for a leap, in radians from nose to tail:
## more than 0 the back bowed up, head and tail down; less than 0 head and tail raised.
@export_range(-1.5, 1.5) var arch := 0.0:
	set(value):
		arch = value
		_send(&"arch", value)
## The low model (about a fourteenth of the triangles), for far off or for several of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model in place of the full one (about as light as the low one, but its triangles are
## spent on the outline, the eye, the mouth and the fins' edges). `low` still shows the low one.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 as in life, 1 bigger, a white round a gold iris, a round pupil, a level haughty lid.
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where its eyes look: x towards its snout (less than 0 back), y up; -1..1.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(Vector2(-1.0, -1.0), Vector2(1.0, 1.0))
		_send(&"eye_look", eye_look)
## 0 its eyes open, 1 shut (squashed, a lid of its skin's colour drawn over them).
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set
## it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()

static var _meshes := {}

var _material: ShaderMaterial
# (each model's MeshInstance3D, made when it is first shown: "", "_game" or "_lo")
var _shown := {}
var _ready_done := false


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`): for
## drawing an arowana without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## The game model's mesh (one surface, to wear `new_material()`), without the importer's
## automatic LODs (they would bend in straight pieces). Loading it does not load the full model.
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game")


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase`
## (0..1 through one beat of the tail), `sway`, `gape`, `arch`, `curl`, `wave` and the colours (the
## top of the shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_ready_done = true
	_show()
	_send_phase()
	_send(&"sway", sway)
	_send(&"gape", gape)
	_send(&"cartoon_eyes", cartoon_eyes)
	_send(&"eye_look", eye_look)
	_send(&"blink", blink)
	_send(&"arch", arch)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the other fish's are; its beat here does not
## change with its speed: set `sway` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `curl` (bent round into a turn: radians from gills to tail,
## more than 0 the tail comes round to its left, +X), `wave` (the length of the wave along its
## body, in body lengths), its colours (`back`, `silver`, `belly`, `scale_rim`, `sheen`, `fin`,
## `fin_dark`, `mouth_inside`) and `scales_show` (how strongly the great scales show).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one beat of the tail it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


func _show() -> void:
	if not _ready_done:
		return
	var which := "_lo" if low else "_game" if game else ""
	if not _shown.has(which):
		_shown[which] = _instance_of(which)
	for key: String in _shown:
		(_shown[key] as MeshInstance3D).visible = key == which


func _instance_of(which: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = _mesh_at(MODEL % which)
	mesh.material_override = _material
	# (its tail swings out past where the still model ends, its jaw drops below it, and arched it
	# bends above and below it)
	mesh.extra_cull_margin = 0.2
	mesh.name = {"": "Arowana", "_lo": "ArowanaLo", "_game": "ArowanaGame"}[which]
	add_child(mesh)
	return mesh


static func _mesh_at(path: String) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		# (the game model without the importer's automatic LODs: thinned, it would bend in straight
		# pieces far off; the full and the low models are kept as they always were)
		_meshes[path] = without_lods(found.mesh) if path.ends_with("_game.glb") else found.mesh
		made.free()
	return _meshes[path]


## A copy of `mesh` without its automatic LODs.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain
