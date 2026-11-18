class_name SeaSlug
extends Node3D
## A sea slug, of one of three kinds (`kind`):
## - a SEA_HARE (Aplysia californica, 0.30 m): plump, mottled olive brown with pale spots, two ear-like
##   rhinophores and two broad oral tentacles on its head, and two wing flaps (parapodia) folded up over its
##   back, which it flaps to swim;
## - a BLUE_DRAGON (Glaucus atlanticus, 0.035 m): silver-blue, with three pairs of arms each ending in a fan of
##   finger-like cerata; it floats UPSIDE DOWN at the surface, its blue foot up;
## - a SPANISH_DANCER (Hexabranchus sanguineus, 0.30 m): big and scarlet, a frilled skirt (its mantle) all round
##   its body, which it ripples in waves to swim, and a rosette of gills on its back.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it goes. Its head
## points along its own -Z. **Its origin is on the ground under its middle** (its foot lies on y = 0), except
## the blue dragon's, which is **at the waterline over its middle**: its foot is just at y = 0, facing up,
## and the rest of it hangs below. It is life size: `scale` it up for a game. No sound.
##
## `swim` 0..1 blends from crawling (the blue dragon: drifting) to swimming: the sea hare flaps its
## parapodia, the dancer heaves its body and runs waves along its skirt, the blue dragon paddles its fans.
## A game lifts it off the bottom itself to swim.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which it ripples (or strokes)
## `tail_beats` times (a whole number), so its motion comes round again exactly every beat. Either call
## `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or set `phase` yourself. The
## same names as GameCommon's fish, so it is driven the same way. It has no `gape` and no `curl`, and no eyes
## worth drawing (no `cartoon_eyes`).
##
## The models are creatures/sea_slug/models/<kind>.glb (and _game, _lo), built by
## tools/build_sea_slug.py; sea_slug.gdshader colours and moves them.

enum Kind { SEA_HARE, BLUE_DRAGON, SPANISH_DANCER }

const MODEL := "res://creatures/sea_slug/models/%s%s.glb"
const SHADER := preload("res://creatures/sea_slug/sea_slug.gdshader")
## Each kind's name in its models' file names.
const NAMES := {Kind.SEA_HARE: "sea_hare", Kind.BLUE_DRAGON: "blue_dragon", Kind.SPANISH_DANCER: "spanish_dancer"}
## As the models are built (tools/build_sea_slug.py), life size, metres: from the front of the head to the tip
## of the tail, and how high and how wide the body is without what stands on it or spreads from it (the sea
## hare's height is over its flaps; the dancer's width is its body's, its skirt reaching 0.05 m further out
## each side).
const LENGTHS := {Kind.SEA_HARE: 0.3, Kind.BLUE_DRAGON: 0.035, Kind.SPANISH_DANCER: 0.3}
const DEPTHS := {Kind.SEA_HARE: 0.092, Kind.BLUE_DRAGON: 0.0044, Kind.SPANISH_DANCER: 0.037}
const WIDTHS := {Kind.SEA_HARE: 0.108, Kind.BLUE_DRAGON: 0.0048, Kind.SPANISH_DANCER: 0.094}
## The sea hare's (the default kind's) length, depth and width.
const LENGTH := 0.3
const DEPTH := 0.092
const WIDTH := 0.108
## What each kind sets in the shader: its length and middle, how it moves, its colours.
const KINDS := {
	Kind.SEA_HARE: {
		"kind": 0, "body_length": 0.3, "body_half": 0.15, "flex": 0.5, "ripples": 1.5,
		"body": Color(0.3, 0.25, 0.11), "body_second": Color(0.66, 0.63, 0.5), "body_dark": Color(0.1, 0.08, 0.04),
		"edge": Color(0.06, 0.04, 0.03), "parts": Color(0.34, 0.24, 0.12), "tips": Color(0.14, 0.09, 0.05),
		"vivid": 0.05,
	},
	Kind.BLUE_DRAGON: {
		"kind": 1, "body_length": 0.035, "body_half": 0.0175, "flex": 0.9, "ripples": 1.0,
		"body": Color(0.06, 0.22, 0.75), "body_second": Color(0.78, 0.84, 0.9), "body_dark": Color(0.02, 0.06, 0.32),
		"edge": Color(0.02, 0.05, 0.3), "parts": Color(0.45, 0.62, 0.92), "tips": Color(0.03, 0.08, 0.42),
		"vivid": 0.2,
	},
	Kind.SPANISH_DANCER: {
		"kind": 2, "body_length": 0.3, "body_half": 0.15, "flex": 0.7, "ripples": 2.0,
		"body": Color(0.78, 0.06, 0.05), "body_second": Color(0.95, 0.42, 0.42), "body_dark": Color(0.4, 0.02, 0.02),
		"edge": Color(0.98, 0.93, 0.9), "parts": Color(0.9, 0.3, 0.3), "tips": Color(1.0, 0.82, 0.78),
		"vivid": 0.12,
	},
}
## Seconds a beat takes for each kind as it crawls (drifts) and as it swims (`step` goes between them).
const BEATS := {Kind.SEA_HARE: Vector2(3.2, 1.6), Kind.BLUE_DRAGON: Vector2(4.0, 1.4), Kind.SPANISH_DANCER: Vector2(3.0, 1.8)}

static var _meshes := {}

## Which kind of sea slug it is: its shape and colours.
@export var kind := Kind.SEA_HARE:
	set(value):
		kind = value
		_dress()
		_fit()
## Seconds one beat takes: everything it does comes round again each beat. 0 for a caller that sets `phase`
## itself (`step` then leaves `phase` alone). Changing `kind` sets it to that kind's crawling beat.
@export var beat := 3.2
## How many times in a beat it ripples (crawling) or strokes (swimming).
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How strongly it moves: 1 as it lives, 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## 0 crawling on the bottom (the blue dragon: drifting), 1 swimming.
@export_range(0.0, 1.0) var swim := 0.0:
	set(value):
		swim = clampf(value, 0.0, 1.0)
		_send(&"swim", swim)
## The low model (a few hundred triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (Twilight Princess weight: about 1,600 triangles for the sea hare and the dancer, 800 for the
## blue dragon, spent on the outline; the same shader and settings) in place of the full one; `low` still shows
## the low model. Each model is loaded only when it is first shown, so with `game` on the full models are never
## loaded and a game's web export may leave them out.
@export var game := false:
	set(value):
		game = value
		_show()
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D


## A kind's full model's mesh, or its low one's (each one surface, to wear `new_material(kind)`): for drawing
## one without this node. Loaded once and kept.
static func mesh_of(kind_wanted: Kind, low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % [NAMES[kind_wanted], "_lo" if low_wanted else ""])


## A kind's game model's mesh (see `game`). Loaded once and kept.
static func game_mesh(kind_wanted: Kind) -> Mesh:
	return _mesh_at(MODEL % [NAMES[kind_wanted], "_game"])


static func _mesh_at(path: String) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh)
		made.free()
	return _meshes[path]


## `mesh` again without the lower levels of detail Godot's importer makes for it: they are made from the
## still model, and bent in the shader they would bend in straight pieces far off.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


## A new material for a kind's meshes, dressed in that kind's colours. Its other shader settings are the
## game's to set: `phase` (0..1 through one ripple or stroke), `swim`, `sway`, and those
## `set_shader_parameter` lists.
static func new_material(kind_wanted: Kind = Kind.SEA_HARE) -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	_wear(made, kind_wanted)
	return made


static func _wear(on: ShaderMaterial, kind_wanted: Kind) -> void:
	var wears: Dictionary = KINDS[kind_wanted]
	for setting: String in wears:
		on.set_shader_parameter(setting, wears[setting])


func _init() -> void:
	_material = new_material(kind)


func _ready() -> void:
	_full = _instance_of("SeaSlug")
	_low = _instance_of("SeaSlug_lo")
	_game = _instance_of("SeaSlug_game")
	_show()
	_send_phase()
	_send(&"sway", sway)
	_send(&"swim", swim)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat. (`velocity`
## is taken so that it is called as the fish's are, and is not used: set `swim`, `sway` and `beat` yourself.)
func step(_velocity: Vector3, delta: float) -> void:
	if beat > 0.0:
		phase += delta / beat


## Sets one of the shader's settings: `flex` (how far it bends at the height of a swimming stroke, radians
## from head to tail), `ripples` (how many lie along it as it crawls), `flap_open` (the sea hare's flaps, how
## far they open at the top of a stroke, radians), `skirt_waves`, `frills`, `frill_depth` (the dancer's
## skirt), the colours (`body`, `body_second`, `body_dark`, `edge`, `parts`, `tips`) and `vivid` (how much of
## its colour shows with no light on it). `kind` sets most of them again.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_send(setting, value)


## Its one material (all its models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


func _dress() -> void:
	if _material:
		_wear(_material, kind)
	beat = (BEATS[kind] as Vector2).x


func _fit() -> void:
	if _full == null:
		return
	# (only the model shown is loaded; the others are given theirs when they are first shown)
	_full.mesh = mesh_of(kind, false) if _full.visible else null
	_low.mesh = mesh_of(kind, true) if _low.visible else null
	_game.mesh = game_mesh(kind) if _game.visible else null


func _show() -> void:
	if _full:
		_full.visible = not low and not game
		_low.visible = low
		_game.visible = game and not low
		_fit()


func _instance_of(called: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.material_override = _material
	# (its skirt, flaps and fans move out past the still model's box)
	mesh.extra_cull_margin = 0.06
	mesh.name = called
	add_child(mesh)
	return mesh
