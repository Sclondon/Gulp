class_name GardenEel
extends Node3D
## One garden eel, a spotted garden eel: a thin pale eel 0.4 m long and 1.2 cm thick with small dark
## specks and two larger black spots on each side, a big eye and a small upturned mouth. It stands
## up out of its burrow in the sand, curved like a question mark with its head into the current,
## swaying and turning its head to pick at what drifts by. This is the full model, for close looks;
## for a field of hundreds use GardenEelColony (garden_eel_colony.gd), which draws them all in one go.
##
## How it looks and moves only. **Its origin is at the mouth of its burrow, on the sand.** Up is +Y,
## and its head faces -Z (Godot's forward, so `look_at` turns it): point -Z at where the current comes
## from. Fully out (`out` 1) 0.3 m of it stands above the sand, its head about 0.19 m up and 0.11 m
## ahead of the burrow; the other 0.1 m stays in the burrow. Life size: `scale` it for a game. No sound.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which it sways `tail_beats`
## times (a whole number), so its motion comes round again exactly every beat. Call
## `step(velocity, delta)` each frame, or set `phase` yourself. The same names as GameCommon's fish.
##
## The model is creatures/garden_eel/models/garden_eel.glb (and _lo), built by
## tools/build_garden_eel.py; garden_eel.gdshader (with garden_eel.gdshaderinc) poses and colours it.

const MODEL := "res://creatures/garden_eel/models/garden_eel%s.glb"
const SHADER := preload("res://creatures/garden_eel/garden_eel.gdshader")
## As the model is built: from the tip of its snout to the tip of its tail, and how thick it is
## (metres, at scale 1).
const LENGTH := 0.4
const DEPTH := 0.012
const WIDTH := 0.012
## How much of it stands above the sand when it is all out (the rest stays in the burrow), and how
## much of that, from the snout, is curled over (as garden_eel.gdshaderinc has them).
const STANDS := 0.3
const HOOK_LENGTH := 0.2

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 3.2
## How many times in a beat it sways there and back.
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How strongly it sways: 1 as it lives, 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How much of it is out of its burrow: 0 all in (nothing shows), 1 all out.
@export_range(0.0, 1.0) var out := 1.0:
	set(value):
		out = clampf(value, 0.0, 1.0)
		_send(&"out_of_sand", out)
## The low model (about a tenth of the triangles), for far off.
@export var low := false:
	set(value):
		low = value
		_show()
## How far through a beat it is, 0 to 1 (only the fraction counts).
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()

static var _meshes := {}

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`).
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## A new material for `mesh_of()`'s meshes. Its settings: `phase`, `out_of_sand`, `sway`, and those
## `set_shader_parameter` lists.
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


## Where the tip of its snout is, in its own space, when it is `out` of its burrow (not swaying),
## with its top curled `hook` radians and its stalk leaning back `lean` radians (the shader's
## defaults). The same sums as eel_pose() in garden_eel.gdshaderinc.
static func head_at(out_amount: float, hook := 2.0, lean := 0.12) -> Vector3:
	var shown := clampf(out_amount, 0.0, 1.0) * STANDS
	var up := smoothstep(0.15, 0.7, out_amount)
	var total := hook * up
	var th0 := -lean * up
	var from := maxf(shown - HOOK_LENGTH, 0.0)
	var p := Vector2(cos(th0), -sin(th0)) * from
	var dh := (shown - from) * 0.1
	for i in 10:
		var h := from + (i + 0.5) * dh
		var a := th0 + total * smoothstep(shown - HOOK_LENGTH, shown - 0.012, h)
		p += Vector2(cos(a), -sin(a)) * dh
	return Vector3(0.0, p.x, p.y)


## `mesh` again without the lower levels of detail Godot's importer makes for it. They are made from
## the still model, a straight rod, which they thin to a few rings: bent in the shader, a far eel
## drawn with one came out as straight sticks with a sharp corner.
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


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_full = _instance_of(false)
	_low = _instance_of(true)
	_show()
	_send_phase()
	_send(&"sway", sway)
	_send(&"out_of_sand", out)


## Each frame: moves it on through its beat. (`velocity` is taken so that it is called as the
## fish's are, and is not used.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `hook` (radians its top is curled over, 2.0), `lean` (radians
## its stalk leans back, 0.12), its colours (`skin`, `skin_back`, `speck`, `spot`, `eye_ring`) and
## `specks` (0 none to 1 many).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


func _show() -> void:
	if _full:
		_full.visible = not low
		_low.visible = low


func _instance_of(low_wanted: bool) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = mesh_of(low_wanted)
	mesh.material_override = _material
	# (curled over, its head reaches ahead of where the still model stands)
	mesh.extra_cull_margin = 0.15
	mesh.name = "GardenEelLo" if low_wanted else "GardenEel"
	add_child(mesh)
	return mesh
