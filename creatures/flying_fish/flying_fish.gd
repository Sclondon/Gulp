class_name FlyingFish
extends Node3D
## A four-winged flying fish, the Atlantic flyingfish (Cheilopogon melanurus), 0.3 m
## long: a slender torpedo of a body, flat across the back; a short blunt head with
## very large eyes and a small mouth whose lower jaw works; a low dorsal fin far back
## over the anal fin; a deeply forked tail whose lower lobe is the longer; and its
## wings: very long pectoral fins rooted high behind the gill covers, and enlarged
## pelvic fins low on the side behind the middle. Its nose points along its own -Z,
## its belly down; its origin is the middle of its length.
##
## `wings` (0 to 1) folds and spreads the wings: 0 the pectoral and pelvic fins
## folded back flat along the body (how it swims under water), 1 spread wide and held
## stiff (how it glides), and every place between. Its shaders turn each fin about
## its root, shut its fan of rays and lay it along the body (no bones).
##
## Dark blue above, silver on the sides and white beneath, with a bright blue line
## where back meets side; large scales; dusky tail. The wings, the dorsal and the
## anal fin are see-through, a thin film between darker rays. All of it is drawn by
## its shaders: no texture files. `set_shader_parameter` reaches every colour.
##
## It swims by a wave down its body, drawn by the shaders: the head nearly still, the
## tail swinging widest, its fins and tail carried and turned with the bend (a spread
## wing is carried stiff, as its root goes); its mouth and gill covers work as it
## breathes.
##
## Everything that moves by itself runs on `phase`, 0 to 1 through one `beat`: in a
## beat the tail beats `tail_beats` times and it breathes `breaths` times (whole
## numbers), so its motion comes round again exactly every beat. Either call
## `step(velocity, delta)` each frame, which moves `phase` on by delta / beat (and
## swims harder the faster it is going), or set `phase` yourself (for a picture that
## must loop: frame / frames in a beat). With `beat` 0, `step` leaves `phase` alone.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it
## the way it goes. `scale` it for a bigger or smaller one. No sound.
##
## The model is creatures/flying_fish/models/flying_fish.glb (and _lo), built by
## tools/build_flying_fish.py, wings spread; its shaders are flying_fish.gdshader (the
## body) and flying_fish_fins.gdshader (the see-through fins), which share
## flying_fish_motion.gdshaderinc.

const MODEL := "res://creatures/flying_fish/models/flying_fish%s.glb"
const SHADER := preload("res://creatures/flying_fish/flying_fish.gdshader")
const FIN_SHADER := preload("res://creatures/flying_fish/flying_fish_fins.gdshader")
## As the model is built (tools/build_flying_fish.py): snout to the tip of the tail's
## lower lobe, how deep and how wide its body is at the shoulder, and from wing tip
## to wing tip with the wings spread (metres, at scale 1).
const LENGTH := 0.3
const DEPTH := 0.041
const WIDTH := 0.031
const SPAN := 0.283

## The wings: 0 the pectoral and pelvic fins folded back flat along the body (as it
## swims under water), 1 spread wide and held stiff (as it glides).
@export_range(0.0, 1.0) var wings := 0.0:
	set(value):
		wings = clampf(value, 0.0, 1.0)
		_send(&"wings", wings)
## Seconds one beat takes: everything it does by itself comes round again each beat.
## 0: `step` does not move `phase` (the caller sets it).
@export var beat := 1.6
## How many times in a beat its tail beats and it breathes.
@export var tail_beats := 4:
	set(value):
		tail_beats = maxi(value, 0)
		_send(&"tail_beats", float(tail_beats))
@export var breaths := 2:
	set(value):
		breaths = maxi(value, 0)
		_send(&"breaths", float(breaths))
## How hard it swims when it is not going anywhere: 0 hangs still (as in a glide),
## 1 swings its tail a tenth of its length each way.
@export_range(0.0, 1.0) var swim := 0.4:
	set(value):
		swim = value
		_effort = value
		_send(&"swim", _effort)
## The speed (m/s, at scale 1) at which `step` has it swimming as hard as it can.
@export var top_speed := 2.0
## The low model (far off, phones) in place of the full one.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about 1,780 triangles, spent on the outline, the eye, the mouth and
## the wings' edges; the wings still see-through and still folded by `wings`) in place
## of the full one; `low` still shows the low model. Each model is loaded only when it
## is first shown, so with `game` on the full model is never loaded and a game's web
## export can leave its .glb out.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye (0 the eye as it was, 1 the cartoon eye: a wide startled stare, a
## huge pupil in a pale sky-blue iris, a highlight, no lid). Gulp sets it to 1.
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
## How far through a beat it is, 0 to 1. `step` moves it on; or set it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)

var _material: ShaderMaterial
var _fin_material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D
var _effort := 0.4
static var _meshes := {}


func _init() -> void:
	_material = ShaderMaterial.new()
	_material.shader = SHADER
	_fin_material = ShaderMaterial.new()
	_fin_material.shader = FIN_SHADER
	_effort = swim


func _ready() -> void:
	_show()
	for setting: StringName in [&"tail_beats", &"breaths"]:
		_send(setting, float(get(setting)))
	_send(&"wings", wings)
	_send(&"swim", _effort)
	_send(&"phase", phase)


## Each frame, after putting it where it is: moves its beat on by `delta` seconds
## (not when `beat` is 0), and has it swim harder the faster it is going (`velocity`,
## world, m/s; give Vector3.ZERO for one that holds its place, and it swims as `swim`
## says).
func step(velocity: Vector3, delta: float) -> void:
	if beat > 0.0:
		phase += delta / beat
	var size := maxf(global_basis.get_scale().z, 0.001) if is_inside_tree() else 1.0
	var wanted := maxf(swim, clampf(velocity.length() / (top_speed * size), 0.0, 1.0))
	_effort = move_toward(_effort, wanted, delta * 1.5)
	_send(&"swim", _effort)


## Sets one of the shaders' settings, on the body and the fins both: a colour of the
## body (back, back_line, side, belly, cheek, lip, mouth, tail_colour, eye_silver,
## sheen_colour), an amount (back_from, line_amount, sheen, scales, scale_size), a
## colour of the fins (ray, ray_pale, wing, wing_band, pelvic, dorsal, anal), how
## see-through they are (wing_alpha, pelvic_alpha, dorsal_alpha, anal_alpha,
## ray_alpha, folded_alpha, band_amount), or how it moves (curl, gape, gape_breath, gill_flare).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_send(setting, value)


## The material its body, jaw, eyes and tail are drawn with.
func material() -> ShaderMaterial:
	return _material


## The material its see-through fins (wings, dorsal, anal) are drawn with.
func fin_material() -> ShaderMaterial:
	return _fin_material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)
		_fin_material.set_shader_parameter(setting, value)


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


## The game model's mesh, for a game that draws meshes itself: two surfaces, the body
## (draw it with `material()`'s shader) and the see-through fins (`fin_material()`'s),
## told apart by their materials' names (the fins' ends in "_fins"). Loaded once and
## kept, without the importer's thinned LOD meshes.
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


## The mesh without the thinned LOD meshes Godot's importer makes (the shaders bend the
## fish, and a thinned mesh far off would bend in straight pieces); each surface keeps
## its material, by which the body and the fins are told apart.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
		plain.surface_set_material(surface, mesh.surface_get_material(surface))
	return plain


func _mesh_of(suffix: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = _load_mesh(suffix)
	# (two surfaces: the body, and the see-through fins, told apart by the names the
	# build gave their materials)
	for surface in mesh.mesh.get_surface_count():
		var named := mesh.mesh.surface_get_material(surface)
		var fins := named != null and named.resource_name.ends_with("_fins")
		mesh.set_surface_override_material(surface, _fin_material if fins else _material)
	# (its tail swings out past the still model's box, and a turn carries it further)
	mesh.extra_cull_margin = LENGTH * 0.3
	mesh.name = "FlyingFish" + suffix
	add_child(mesh)
	return mesh
