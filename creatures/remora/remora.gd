class_name Remora
extends Node3D
## A remora (the sharksucker, Echeneis naucrates), 0.6 m long: a slender dark fish with a black
## band edged in pale stripes along each side, a broad flat head with the ridged oval sucker disc
## on top of it, a lower jaw jutting past the upper, and a long dorsal and anal fin facing each
## other over its back half.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down; its origin is on
## its middle line, half way along, so it reaches 0.3 m ahead and 0.3 m behind. `scale` it for
## a bigger or smaller one. No sound.
##
## It swims with a wave along its slender body, drawn by the shader (no bones). Its mouth opens:
## `gape`. `riding` lays it straight and still against a host, only its tail tip and fins
## trembling; `DISC_AT` and `DISC_UP` (or `riding_transform`) say where to put it so that its disc
## is on the host's skin.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat.
## Either call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or
## set `phase` yourself (for a picture that must loop: frame / frames in a beat). The same
## names and meanings as GameCommon's yellowfin tuna, wahoo and sardine.
##
## The models are creatures/remora/models/remora.glb (and _lo, _game), built by
## tools/build_remora.py; remora.gdshader draws the markings, swims it and works its jaw.

const MODEL := "res://creatures/remora/models/remora%s.glb"
const SHADER := preload("res://creatures/remora/remora.gdshader")
## As the model is built (tools/build_remora.py): from the tip of its lower jaw to the tips of
## its tail, and how deep and how wide its body is at its deepest (metres, at scale 1).
const LENGTH := 0.6
const DEPTH := 0.048
const WIDTH := 0.052
## The middle of the sucker disc's face (at the crests of its slats, half way along it), in the
## node's own space at scale 1 (metres): the point that touches a host's skin.
const DISC_AT := Vector3(0.0, 0.0182, -0.207)
## The way the disc faces (a unit vector in the node's own space: up, tipped a little forward,
## as the top of its head slopes). Riding, this points into the host.
const DISC_UP := Vector3(0.0, 0.9962, -0.0866)
## The disc's length and its width (metres at scale 1).
const DISC_SIZE := Vector2(0.14, 0.034)

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 1.0
## How many times in a beat its tail beats (there and back).
@export var tail_beats := 3:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it beats: 1 a remora cruising (its tail tips swing about 0.05 m either way), 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far its mouth is open: 0 shut, 1 wide open.
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## Riding on a host: 0 swimming, 1 held by its disc, lying straight and still (its sway and curl
## let go of), only the tip of its tail and its fins trembling. In between, it settles. It still
## needs `step` (or `phase`) for the trembling.
@export_range(0.0, 1.0) var riding := 0.0:
	set(value):
		riding = clampf(value, 0.0, 1.0)
		_send(&"riding", riding)
## The low model (about a twentieth of the triangles), for far off or for several of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (a few hundred triangles, spent on the outline, the disc's slats, the eye, the
## mouth and the fins' edges) in place of the full one. Only the model shown is ever loaded, so a
## game that always has this (or `low`) set can leave the full model's .glb out of its export.
## `low` still shows the low model.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 the eye as it is in life, 1 a bigger cartoon eye with a white, an iris, a
## pupil, a highlight and lids of its own character (half-lidded and lazy: the README says more).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where the cartoon eyes look: x forward (towards the snout, +1) or back (-1), y up (+1) or down
## (-1), in each eye's own plane, so both look the same way.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(Vector2(-1.0, -1.0), Vector2.ONE)
		_send(&"eye_look", eye_look)
## A blink: 0 open, 1 shut (a lid the colour of the skin over each eye, on the cartoon eye and the
## eye in life alike).
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
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D


## The full model's mesh, or the low one's (each one surface but the full one, whose gills are a
## second; all wear `new_material()`): for drawing a remora without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## The game model's mesh (one surface, to wear `new_material()`; loaded without Godot's automatic
## LODs, which would bend in straight pieces far off): for drawing a game model without this node.
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game")


## A new material for the meshes. Its shader settings are the game's to set: `phase` (0..1
## through one beat of the tail), `sway`, `gape`, `riding`, `curl`, `wave` and the colours (the
## top of the shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


## Where to put a remora so that its disc holds on to a host: `spot` a point on the host's skin,
## `skin_up` the skin's outward normal there, `heading` the way its nose should point (along the
## host, usually the host's forward), all in one space (the host's own, to make the remora its
## child, or the world's); `size` its scale. The remora's DISC_UP points into the skin and DISC_AT
## sits on `spot`: under a host's belly it hangs right way up, on its back or flank upside down
## or on its side, as remoras do. (The disc faces a little forward of straight up, as the top of its
## head slopes, so riding its body tips back a few degrees from the skin.)
static func riding_transform(spot: Vector3, skin_up: Vector3, heading: Vector3, size := 1.0) -> Transform3D:
	var into := -skin_up.normalized()
	var ahead := heading - into * heading.dot(into)
	if ahead.length() < 0.0001:
		ahead = into.cross(Vector3.RIGHT if absf(into.x) < 0.9 else Vector3.UP)
	ahead = ahead.normalized()
	# (its own frame: the disc's way up, and its forward square to that)
	var own_ahead := (Vector3.FORWARD - DISC_UP * Vector3.FORWARD.dot(DISC_UP)).normalized()
	var own := Basis(own_ahead.cross(DISC_UP), DISC_UP, -own_ahead)
	var there := Basis(ahead.cross(into), into, -ahead)
	var basis := (there * own.inverse()).scaled_local(Vector3.ONE * size)
	return Transform3D(basis, spot - basis * DISC_AT)


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_show()
	_send(&"cartoon_eyes", cartoon_eyes)
	_send(&"eye_look", eye_look)
	_send(&"blink", blink)
	_send_phase()
	_send(&"sway", sway)
	_send(&"gape", gape)
	_send(&"riding", riding)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the other fish's are; its beat here does not
## change with its speed: set `sway` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `curl` (bent round into a turn: radians from gills to tail,
## more than 0 the tail comes round to its left, +X), `wave` (the length of the wave along its
## body, in body lengths), its colours (`body`, `band`, `stripe`, `fin_dark`, `fin_edge`, `slat`,
## `groove`, `teeth`, `mouth_inside`, `gill_red`, `gill_raker`) and `stripes_show`.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one beat of the tail it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


# (each model is loaded only when it is first shown)
func _show() -> void:
	if not is_node_ready():
		return
	if low and not _low:
		_low = _instance_of("_lo")
	elif not low and game and not _game:
		_game = _instance_of("_game")
	elif not low and not game and not _full:
		_full = _instance_of("")
	for shown: MeshInstance3D in [_full, _low, _game]:
		if shown:
			shown.visible = (shown == _low and low) or (shown == _game and game and not low) or (shown == _full and not game and not low)


func _instance_of(which: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = game_mesh() if which == "_game" else mesh_of(which == "_lo")
	mesh.material_override = _material
	# (its tail swings out past where the still model ends, and its jaw opens below it)
	mesh.extra_cull_margin = 0.12
	mesh.name = "Remora" + {"": "", "_lo": "Lo", "_game": "Game"}[which]
	add_child(mesh)
	return mesh


static func _mesh_at(path: String) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		# (the game model without the automatic LODs; the others as they always were)
		_meshes[path] = without_lods(found.mesh) if path.ends_with("_game.glb") else found.mesh
		made.free()
	return _meshes[path]


## The mesh with only its own triangles: none of the thinned LOD meshes Godot's importer makes, which a
## body bent in the vertex shader would show in straight pieces far off.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain
