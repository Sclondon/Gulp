class_name FireflySquid
extends Node3D
## A firefly squid (Watasenia scintillans), 0.07 m from the tips of its arms to the end of its mantle: a small
## slender squid, dusky red-violet, covered in tiny blue light organs (thick on its belly), with three big ones at
## the tip of each of its lowest arms and five round the lower rim of each eye. Its lights flash in waves that travel
## back along it (`colour_phase`).
##
## IT SWIMS ARMS FIRST: its arms point along its own -Z (Godot's forward, so `look_at` points it), the end of its
## mantle is towards +Z, its back is +Y. Its origin is on its middle line half way along its length, so the tips of
## its arms are 0.035 m ahead and the end of its mantle 0.035 m behind. `scale` it for a bigger or smaller one. No
## sound.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it goes. Everything that
## moves goes by `phase` (its arms' sway and its fins' ripples; 0 to 1 through one `beat`) and its lights by
## `colour_phase` (0 to 1 through one `colour_beat`): `step(velocity, delta)` moves them on, or set them yourself for
## a picture that must loop. Its arms, fins and mantle are bent by the shader (no bones, no ropes).
##
## For a school of hundreds, do not make hundreds of these nodes: draw `FireflySquid.school_mesh()` with one
## MultiMesh (GameCommon's Flock takes it as its `custom_mesh`), as the sardine's and the lanternfish's.
##
## The models are creatures/firefly_squid/models/firefly_squid.glb (and _game, _lo and _school), built by
## tools/build_firefly_squid.py; firefly_squid.gdshader draws it, moves it and lights it.

const MODEL := "res://creatures/firefly_squid/models/firefly_squid%s.glb"
const SHADER := preload("res://creatures/firefly_squid/firefly_squid.gdshader")
## As the model is built: from the tips of its arms to the end of its mantle, how deep and how wide its mantle is
## at its widest (without fins; its fins reach 0.0103 m out from its middle line) (metres, at scale 1).
const LENGTH := 0.07
const DEPTH := 0.0118
const WIDTH := 0.0114

## Seconds one beat takes (one sway of its arms).
@export var beat := 1.0
## How many ripples run along its fins in a beat (a whole number).
@export var flaps := 2:
	set(value):
		flaps = maxi(value, 0)
		_send(&"flaps", float(flaps))
## How much it moves: 1 swimming gently, 0 still, 2 twice as much.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Its arms: 0 drawn together ahead of it; 1 opened out wide and curled back.
@export_range(0.0, 1.0) var spread := 0.0:
	set(value):
		spread = clampf(value, 0.0, 1.0)
		_send(&"spread", spread)
## Its mantle bent round behind its head, radians from its collar to its end (more than 0 its end comes round to +X,
## its left), as it turns.
@export var curl := 0.0:
	set(value):
		curl = value
		_send(&"curl", value)
## How strongly its lights glow (0 dark, 1 as made, 2 twice as bright).
@export_range(0.0, 2.0) var glow := 1.0:
	set(value):
		glow = clampf(value, 0.0, 2.0)
		_send(&"glow", glow)
## Seconds a round of its lights takes. 0: the same as a beat (`colour_phase` is `phase`). Less than 0:
## `colour_phase` is yours to set.
@export var colour_beat := 3.0
## Waves of light that pass back along it in a round of its lights (a whole number).
@export var light_rounds := 2:
	set(value):
		light_rounds = value
		_send(&"light_rounds", float(value))
## The low model (about a twentieth of the full one's triangles), for far off.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about 830 triangles, spent on the outline, the eyes and the lights) in place of the full one:
## what a game draws near. `low` still shows the low model. With it on, the full model is never loaded (each model
## is loaded when it is first shown), so a game's export may leave the full .glb out.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye (0 the eye as made, 1 the cartoon one: bright and curious, a big deep-blue iris with a ring of
## light flecks round a big round pupil, wide open).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where the cartoon eyes look: x towards its arms (more than 0) or its mantle's end, y up or down; -1..1.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(Vector2(-1.0, -1.0), Vector2(1.0, 1.0))
		_send(&"eye_look", eye_look)
## The cartoon eye's lid: 0 open, 1 shut.
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## How far through a beat (0..1). `step` moves it on; or set it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)
		if colour_beat == 0.0:
			colour_phase = phase
## How far through a round of its lights (0..1).
var colour_phase := 0.0:
	set(value):
		colour_phase = fposmod(value, 1.0)
		_send(&"colour_phase", colour_phase)

static var _meshes := {}

var _material: ShaderMaterial
var _models := {}
var _ready_yet := false
var _flash_at := 1.0
var _flash_takes := 0.6


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`, without the importer's LOD
## meshes): for drawing one without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## The game model's mesh (one surface, to wear `new_material()`, without the importer's LOD meshes): for drawing
## one without this node.
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game")


## The school model's mesh: about 180 triangles, the same size and the same way round as the others (0.07 m long,
## arms at -Z, up +Y, origin half way along), its look in its vertex colours (a dusky red-violet back, a paler belly,
## a dark eye in a silver ring each side, its arms a bunch of thin sheets, its fins one sheet, its lights small
## bright blue plates: rows along its belly and lower flanks, the ventral arms' tips, the eyes' rims). Its vertex
## ALPHA is a glow mask: 1 on the lights, 0 elsewhere, so a shader can make just them glow (EMISSION = COLOR.rgb *
## COLOR.a). It has no UVs and does not wear this component's shader: it is for hundreds drawn by one MultiMesh
## whose shader reads COLOR (GameCommon's Flock: `custom_mesh`, body CUSTOM, motion SWIM, its colour white; Flock
## draws the lights bright but does not make them glow). Its fins and arms are single sheets, so draw it from both
## sides.
static func school_mesh() -> Mesh:
	return _mesh_at(MODEL % "_school")


## A new material for `mesh_of()`'s and `game_mesh()`'s meshes. Its shader settings are the game's to set: `phase`,
## `colour_phase`, `flaps`, `sway`, `spread`, `curl`, `glow`, `light_rounds`, `light_waves`, `twinkle`, `flash`, the
## cartoon eye's and the colours (the top of the shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	# (the first model is put off to the end of the frame, so that `game` or `low` set just after it is added is
	# heeded before any model is loaded)
	_first_show.call_deferred()
	_send(&"flaps", float(flaps))
	_send(&"light_rounds", float(light_rounds))
	for setting in [&"phase", &"colour_phase", &"sway", &"spread", &"curl", &"glow", &"cartoon_eyes", &"eye_look", &"blink"]:
		_send(setting, get(setting))


## Each frame, for one that is not having its phases set for it: moves it on through its beat and the round of its
## lights. (`velocity` is taken so that it is called as the other creatures are; its beat does not change with its
## speed: set `beat` and `sway` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)
	if colour_beat > 0.0:
		colour_phase += delta / colour_beat
	if _flash_at < 1.0:
		_flash_at = minf(_flash_at + delta / _flash_takes, 1.0)
		_send(&"flash", pow(1.0 - _flash_at, 2.0))


## All its lights at once, now, fading over `seconds` (as one startled). Not part of `colour_phase`: a picture that
## must loop should not call it.
func flash(seconds := 0.6) -> void:
	_flash_at = 0.0
	_flash_takes = maxf(seconds, 0.01)
	_send(&"flash", 1.0)


## Sets one of the shader's settings: `light_waves`, `twinkle`, its colours (`skin`, `belly`, `freckle`,
## `light_colour`, `eye_silver`, and the cartoon eye's `eye_white`, `eye_iris`) or any of the settings above.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


func _first_show() -> void:
	_ready_yet = true
	_show()


func _show() -> void:
	if not _ready_yet:
		return
	var which := "_lo" if low else ("_game" if game else "")
	if not _models.has(which):
		var made := MeshInstance3D.new()
		made.mesh = _mesh_at(MODEL % which)
		made.material_override = _material
		# (its arms spread and its mantle bends past the still model)
		made.extra_cull_margin = 0.03
		made.name = "FireflySquid" + which
		add_child(made)
		_models[which] = made
	for key: String in _models:
		(_models[key] as MeshInstance3D).visible = key == which


## The mesh as imported but without the thinned LOD meshes Godot's importer adds: those were made from the still
## model, and a body bent in the shader then bends in straight pieces far off.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


static func _mesh_at(path: String) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		# (the school model as imported; the others without the importer's LODs: they are bent in the shader)
		_meshes[path] = found.mesh if path.ends_with("_school.glb") else without_lods(found.mesh)
		made.free()
	return _meshes[path]
