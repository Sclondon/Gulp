class_name Betta
extends Node3D
## A male betta, the Siamese fighting fish (Betta splendens), of the long-finned halfmoon kind,
## 0.065 m long from the tip of its jaw to the end of its tail: a stout body, a short blunt head
## with a big eye and a small upturned mouth, and very long flowing fins: a halfmoon tail as long as
## the body, a tall long-based dorsal fin and a long deep anal fin running back beside it, two long
## thread-like pelvic fins, two small clear pectorals. In colour `type`s:
##
## - ROYAL_BLUE (the default): a deep iridescent blue body and fins, the fins dark red at the root,
##   paler blue at the edge, the pelvic threads tipped white.
## - RED: deep red all over, the fins with darker rays and a brighter edge.
## - MARBLE: a pale pink-white ground blotched with red, blue and black, each one its own
##   (`pattern_seed`, a random number when the node is made: set it for one that must stay the
##   same).
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it goes.
## Its nose points along its own -Z (Godot's forward), its belly down; its origin is on its middle
## line, half way along its length (tail included). `scale` it for a bigger one. No sound.
##
## It swims by a slow wave down its body, drawn by the shader (no bones); its long fins trail behind,
## billow and ripple like cloth. Its mouth opens: `gape`. It flares: `flare` 0 calm (fins folded,
## drooping and trailing, gill covers shut), 1 the full display (gill covers swung out, the dark
## beard out round them, every fin spread out stiff into the halfmoon).
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats
## `tail_beats` times, its fins swell out and back `billows` times and `ripples` ripples run across
## them (whole numbers), so its motion comes round again exactly every beat. Either call
## `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or set `phase`
## yourself (for a picture that must loop: frame / frames in a beat). The same names and meanings
## as GameCommon's yellowfin tuna and sardine.
##
## The models are creatures/betta/models/betta.glb (and _lo and _game), built by
## tools/build_betta.py; betta.gdshader draws the markings, swims it and flares it. Only the models
## shown are ever loaded: with `game` (or `low`) set, the full model is never loaded.

enum Type { ROYAL_BLUE, RED, MARBLE }

const MODEL := "res://creatures/betta/models/betta%s.glb"
const SHADER := preload("res://creatures/betta/betta.gdshader")
## As the model is built (tools/build_betta.py): from the tip of its jaw to the end of its tail
## (fins spread), and how deep and how wide its body is at its deepest (metres, at scale 1).
const LENGTH := 0.065
const DEPTH := 0.0101
const WIDTH := 0.0070
## Each type's colours in the shader.
const TYPES := {
	Type.ROYAL_BLUE: {
		"body_main": Color(0.08, 0.18, 0.55), "body_dark": Color(0.04, 0.05, 0.16), "sheen": Color(0.25, 0.5, 1.0), "shine": 1.0,
		"fin_main": Color(0.1, 0.22, 0.65), "fin_root": Color(0.22, 0.06, 0.18), "fin_edge": Color(0.35, 0.6, 1.0),
		"fin_ray": Color(0.04, 0.08, 0.3), "pelvic_tip": Color(0.85, 0.88, 0.95), "marble": 0.0,
		"beard": Color(0.06, 0.03, 0.05), "gill_inside": Color(0.35, 0.06, 0.08),
	},
	Type.RED: {
		"body_main": Color(0.6, 0.05, 0.05), "body_dark": Color(0.26, 0.02, 0.03), "sheen": Color(0.6, 0.3, 0.6), "shine": 0.5,
		"fin_main": Color(0.75, 0.05, 0.04), "fin_root": Color(0.45, 0.03, 0.03), "fin_edge": Color(0.88, 0.16, 0.1),
		"fin_ray": Color(0.35, 0.02, 0.02), "pelvic_tip": Color(0.9, 0.2, 0.12), "marble": 0.0,
		"beard": Color(0.12, 0.02, 0.03), "gill_inside": Color(0.4, 0.05, 0.06),
	},
	Type.MARBLE: {
		"body_main": Color(0.9, 0.8, 0.77), "body_dark": Color(0.72, 0.58, 0.58), "sheen": Color(0.6, 0.7, 1.0), "shine": 0.6,
		"fin_main": Color(0.92, 0.88, 0.86), "fin_root": Color(0.86, 0.7, 0.7), "fin_edge": Color(0.96, 0.95, 0.95),
		"fin_ray": Color(0.76, 0.7, 0.7), "pelvic_tip": Color(0.95, 0.95, 0.95), "marble": 1.0,
		"blotch_a": Color(0.75, 0.06, 0.06), "blotch_b": Color(0.1, 0.2, 0.6), "blotch_c": Color(0.05, 0.05, 0.06),
		"beard": Color(0.1, 0.05, 0.06), "gill_inside": Color(0.45, 0.1, 0.12),
	},
}

## Which colours it wears.
@export var type := Type.ROYAL_BLUE:
	set(value):
		type = value
		_set_type(_material, type)
## A number that makes this one's marble blotches its own.
@export var pattern_seed := 0.0:
	set(value):
		pattern_seed = value
		_send(&"pattern_seed", value)
## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 1.6
## In one beat: how many times its tail beats, how many times its fins swell out and back, and how
## many ripples run across them.
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send(&"tail_beats", float(tail_beats))
@export var billows := 1:
	set(value):
		billows = maxi(value, 0)
		_send(&"billows", float(billows))
@export var ripples := 2:
	set(value):
		ripples = maxi(value, 0)
		_send(&"ripples", float(ripples))
## How widely its body beats: 1 cruising, 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How much its long fins trail, billow and ripple: 1 a betta drifting, 0 still.
@export_range(0.0, 2.0) var flow := 1.0:
	set(value):
		flow = value
		_send(&"flow", value)
## How far its mouth is open: 0 shut, 1 wide open (as when it bites).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## How far it flares: 0 calm, 1 the full display (gill covers out, the beard out, fins spread stiff).
@export_range(0.0, 1.0) var flare := 0.0:
	set(value):
		flare = clampf(value, 0.0, 1.0)
		_send(&"flare", flare)
## The low model (about a tenth of the triangles), for far off or for several of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (Twilight Princess weight: under nine hundred triangles, spent on the outline,
## the eye, the mouth and the long fins' edges) in place of the full one. Only the model shown is
## ever loaded, so a game that always has this (or `low`) set can leave the full model's .glb out of
## its export. `low` still shows the low model.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 the eye as it is in life, 1 a bigger cartoon eye of its own character (a proud,
## fierce little fighter: a heavy scowling brow, lower still as it flares, a fiery red-gold iris).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where the cartoon eyes look: x towards the snout (+1) or back (-1), y up (+1) or down (-1), in
## each eye's own plane, so both look the same way.
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
		_send(&"phase", phase)

static var _meshes := {}

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D


## The full model's mesh, or the low one's (each one surface, to wear `new_material(type)`): for
## drawing a betta without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## The game model's mesh (one surface, to wear `new_material(type)`; loaded without Godot's
## automatic LODs, which would bend in straight pieces far off): for drawing a game model without
## this node.
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game")


## A new material for `mesh_of()`'s meshes, with a type's colours set. Its other shader settings
## are the game's to set: `phase` (0..1 through one beat), `tail_beats`, `billows`, `ripples`,
## `sway`, `flow`, `gape`, `flare`, `curl`, `wave`, `pattern_seed` (the top of the shader lists
## them).
static func new_material(which := Type.ROYAL_BLUE) -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	_set_type(made, which)
	return made


static func _set_type(material_to: ShaderMaterial, which: int) -> void:
	if material_to == null:
		return
	for setting: String in TYPES[which]:
		material_to.set_shader_parameter(setting, TYPES[which][setting])


func _init() -> void:
	_material = new_material(type)
	pattern_seed = randf() * 100.0


func _ready() -> void:
	_show()
	_send(&"phase", phase)
	for setting: StringName in [&"tail_beats", &"billows", &"ripples"]:
		_send(setting, float(get(setting)))
	for setting: StringName in [&"sway", &"flow", &"gape", &"flare", &"pattern_seed", &"cartoon_eyes", &"eye_look", &"blink"]:
		_send(setting, get(setting))


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the other fish's are; its beat does not change
## with its speed: set `sway` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `curl` (bent round into a turn: radians from gills to tail,
## more than 0 the tail comes round to its left, +X), `wave` (the length of the wave along its
## body, in body lengths), `shine`, `marble`, and the colours (`body_main`, `body_dark`, `sheen`,
## `fin_main`, `fin_root`, `fin_edge`, `fin_ray`, `pelvic_tip`, `blotch_a`, `blotch_b`, `blotch_c`,
## `beard`, `gill_inside`, `mouth_inside`, `fin_clear`, `gill_red`, `gill_raker`, `eye_iris`). A new
## `type` sets its colours again.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (each model is made, and loaded, only when it is first shown)
func _show() -> void:
	if not is_inside_tree():
		return
	if low and not _low:
		_low = _instance_of("_lo")
	elif not low and game and not _game:
		_game = _instance_of("_game")
	elif not low and not game and not _full:
		_full = _instance_of("")
	if _full:
		_full.visible = not low and not game
	if _low:
		_low.visible = low
	if _game:
		_game.visible = game and not low


func _instance_of(which: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = game_mesh() if which == "_game" else mesh_of(which == "_lo")
	mesh.material_override = _material
	# (its fins swing and swell out past where the still model ends)
	mesh.extra_cull_margin = LENGTH * 0.3
	mesh.name = "Betta" + {"": "", "_lo": "Lo", "_game": "Game"}[which]
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


## The mesh with only its own triangles: none of the thinned LOD meshes Godot's importer makes,
## which a body bent in the vertex shader would show in straight pieces far off.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain
