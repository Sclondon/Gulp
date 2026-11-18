class_name ClownLoach
extends Node3D
## A clown loach (Chromobotia macracanthus), 0.2 m long: a deep, flat-sided body with an arched
## back and a flat belly, a long pointed snout with a small mouth under its tip and four pairs
## of short barbels round it, small eyes high on the head, a dorsal fin at mid-body, a deeply
## forked tail, an anal fin and a pair each of pelvic and pectoral fins. Orange, paler
## underneath, with three broad black wedge-shaped bands (through the eye, in front of the
## dorsal fin, and from the dorsal fin back to the anal fin and the tail wrist); red fins, the
## tail and the pelvic fins the reddest.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down; its origin is on
## its middle line, half way along, so it reaches 0.1 m ahead and 0.1 m behind. `scale` it for
## a bigger or smaller one. No sound.
##
## It swims with a quick wriggle, drawn by the shader (no bones): a wave down its whole body,
## the tail swinging wide; its pectoral fins fan; its barbels twitch. Loaches also loaf on their
## sides: `tilt` leans it over, `roll` rocks it slowly. Its small mouth opens downwards: `gape`.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`: in a beat its tail beats
## `tail_beats` times, its pectoral fins fan `fans` times, its barbels twitch `twitches` times
## and it rocks `rolls` times (whole numbers), so its motion comes round again exactly every
## beat. Either call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat,
## or set `phase` yourself (for a picture that must loop: frame / frames in a beat). The same
## names and meanings as GameCommon's cutthroat trout and yellowfin tuna.
##
## The model is creatures/clown_loach/models/clown_loach.glb (and _lo), built by
## tools/build_clown_loach.py; clown_loach.gdshader draws its markings and moves it.

const MODEL := "res://creatures/clown_loach/models/clown_loach%s.glb"
const SHADER := preload("res://creatures/clown_loach/clown_loach.gdshader")
## As the model is built (tools/build_clown_loach.py): from the tip of its snout to the tips of
## its tail, and how deep and how wide its body is at its deepest (metres, at scale 1).
const LENGTH := 0.2
const DEPTH := 0.055
const WIDTH := 0.026

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 2.0
## How many times in a beat its tail beats (there and back), its pectoral fins fan and its
## barbels twitch.
@export var tail_beats := 4:
	set(value):
		tail_beats = maxi(value, 0)
		_send(&"tail_beats", float(tail_beats))
@export var fans := 3:
	set(value):
		fans = maxi(value, 0)
		_send(&"fans", float(fans))
@export var twitches := 2:
	set(value):
		twitches = maxi(value, 0)
		_send(&"twitches", float(twitches))
## How widely it wriggles: 1 a loach on its way somewhere (its tail tips swing about a tenth of
## its length either way), 0 still (hanging in the water, or lying up).
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far it leans over onto its side, in degrees (0 upright; 90 flat on its left side, -90 on
## its right: loaches rest like that). It leans about its own middle line.
@export_range(-180.0, 180.0) var tilt := 0.0:
	set(value):
		tilt = value
		_lean()
## How far it rocks from side to side as it goes, in degrees either way of `tilt` (0: none),
## and how many times in a beat.
@export_range(0.0, 90.0) var roll := 0.0:
	set(value):
		roll = value
		_lean()
@export var rolls := 1:
	set(value):
		rolls = maxi(value, 0)
		_lean()
## How far its mouth is open: 0 shut (as it always was before 2026-11-17), 1 wide open (its
## lower jaw and the chin's barbels swung down about the corners of the mouth, the front lip about
## 3 mm, the small mouth opening downwards; the inside of the mouth is dark).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## The low model (about a tenth of the triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about 1,740 triangles, spent on the outline, the eye, the mouth and the
## fins' edges) in place of the full one; `low` still shows the low model. Each model is
## loaded only when it is first shown, so with `game` on the full model is never loaded and
## a game's web export can leave its .glb out.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye (0 the eye as it was, 1 the cartoon eye: bigger, a white, an orange iris,
## a keyhole pupil, a highlight, a cheeky raised lid). Gulp sets it to 1.
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = value
		_send(&"cartoon_eyes", value)
## Where the cartoon eye's pupil looks: x forward (towards the snout), y up, -1..1.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value
		_send(&"eye_look", value)
## 0 open, 1 shut: the eye squashes and a lid closes over it (a fish has no lids:
## this is for a game that wants one).
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = value
		_send(&"blink", value)
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set
## it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)
		_lean()

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D
static var _meshes := {}


## The game model's mesh, for a game that draws meshes itself (with `material()`'s
## shader). Loaded once and kept, without the importer's thinned LOD meshes.
static func game_mesh() -> Mesh:
	return _load_mesh("_game")


static func _load_mesh(suffix: String) -> Mesh:
	var path := MODEL % suffix
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh) if suffix == "_game" else found.mesh
		made.free()
	return _meshes[path]


## The mesh without the thinned LOD meshes Godot's importer makes: the shader bends the
## fish, and a thinned mesh far off would bend in straight pieces.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


func _init() -> void:
	_material = ShaderMaterial.new()
	_material.shader = SHADER


func _ready() -> void:
	_show()
	for setting: StringName in [&"tail_beats", &"fans", &"twitches"]:
		_send(setting, float(get(setting)))
	_send(&"sway", sway)
	_send(&"gape", gape)
	_send(&"phase", phase)
	_lean()


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the cutthroat trout's is; the loach's wriggle
## does not change with its speed: set `sway` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: its colours (`orange`, `pale`, `ridge`, `band`,
## `band_glance`, `fin_red`, `fin_orange`, `fin_dark`, `barbel`, `mouth_inside`), `bands_show` (how much of its
## bands shows), `wave` (the length of the wave along its body, in body lengths), `fan` (how far
## its pectoral fins fan) and `twitch` (how far its barbels twitch).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (it leans and rocks about its own middle line: the models are turned, not this node, so that
# whatever places it can still turn it as it likes)
func _lean() -> void:
	var turned := deg_to_rad(tilt + roll * sin(TAU * rolls * phase))
	for shown: MeshInstance3D in [_full, _low, _game]:
		if shown:
			shown.rotation.z = turned


func _show() -> void:
	if not is_inside_tree():
		return
	# (each model is made only when it is first shown)
	if low:
		if _low == null:
			_low = _mesh_of("_lo")
	elif game:
		if _game == null:
			_game = _mesh_of("_game")
	elif _full == null:
		_full = _mesh_of("")
	if _full:
		_full.visible = not low and not game
	if _low:
		_low.visible = low
	if _game:
		_game.visible = game and not low
	_lean()


func _mesh_of(suffix: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = _load_mesh(suffix)
	mesh.material_override = _material
	# (its tail swings out past where the still model ends)
	mesh.extra_cull_margin = 0.05
	mesh.name = "Loach" + suffix
	add_child(mesh)
	return mesh
