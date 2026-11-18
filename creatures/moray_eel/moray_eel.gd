class_name MorayEel
extends Node3D
## A green moray (Gymnothorax funebris), 1.8 m long: a deep muscular ribbon of a
## body with no paired fins, one tall fin from its nape round its tail to its
## vent, a blunt head with small pale eyes, tube nostrils and a wide mouth of
## needle teeth that gapes open and shut as it breathes. Yellow-green,
## wrinkled, wet.
##
## Its whole body is one simulated spine: a chain of points simulated here, in
## the world, hung from its head. So it is dragged after the head however the
## eel is moved or turned, trails, curves and settles like a heavy rope (much
## drag, no flicking: `body_drag`, `body_hold`, `body_sink`). On top of that a
## swimming wave runs down the body, growing towards the tail (`swim`), and
## the jaw gapes (`jaw_gape`). After the sea nettle's ropes (godot/sea-nettle,
## "Decision: ropes"): Verlet points on the CPU, sent to the vertex shader in a
## small picture, and the still mesh laid along a smooth curve through them.
##
## How it looks and moves only: whatever moves it puts it where it is each
## frame (the origin is the tip of its snout; it faces -Z, its back is +Y) and
## calls `step(velocity, delta)`. After putting it somewhere new all at once,
## `lay_ropes()` lays its body out afresh, straight behind its head (a jump of
## more than two of its own metres in one step does so by itself, and so does
## its being seen again after being hidden).
##
## Everything that comes round runs on `phase`, in beats: a whole number is the
## same pose. `step` moves it on by delta / `beat`; with `beat` 0 it is left
## alone, for whoever is making a picture that loops to set it each frame.
##
## The models are creatures/moray_eel/models/moray_eel.glb (the full model),
## moray_eel_game.glb (the game model: about 3,800 triangles, `game`) and
## moray_eel_lo.glb, built by tools/build_moray_eel.py; its shader
## (moray_eel.gdshader) lays them along the spine, swings the jaw and draws the
## skin. Each model is loaded only when it is first shown: with `game` on, the
## full model is never loaded.

const MODEL := "res://creatures/moray_eel/models/moray_eel%s.glb"
const GAME_MODEL := "res://creatures/moray_eel/models/moray_eel_game.glb"
const SHADER := preload("res://creatures/moray_eel/moray_eel.gdshader")
## As the model is built (tools/build_moray_eel.py) and as the shader has them: keep them in step.
const LENGTH := 1.8
## The spine: how many points, snout to tail tip, and how many of them, from the snout, are
## the head (they are not simulated: they go with the eel).
const POINTS := 25
const HEAD_POINTS := 4
## The sharpest the spine may bend from one piece to the next (radians): a circle a third of a
## metre across, at size 1. A body, not a string: it never kinks.
const BEND := 0.45

## Seconds a beat takes: one wave of its body, tail to tail. 0, and `phase` is left to the caller.
@export var beat := 1.6
## How far the body's line swings from side to side at the tail (radians), and how many waves
## lie along the body at once. 0 and it does not swim: it only trails.
@export_range(0.0, 1.2) var swim := 0.5
@export var swim_waves := 1.6
## The jaw: how far open it rests (degrees), how much further each gape opens it, and how many
## beats one gape takes.
@export var jaw_rest := 5.0
@export var jaw_gape := 13.0
@export_range(1, 8) var gape_beats := 1
## The body's weight. How much the water slows it (/s: the more, the less it flicks and the
## further it is left behind); how strongly it is drawn back to lie straight out behind the head
## (/s², all of it at the neck, a seventh of it at the tail); how stiff it is, each piece eased
## into line with the two before it (/s: a body, not a string, so it bends in long curves and
## does not kink); how fast it sinks (m/s², straight down in the world).
@export var body_drag := 6.0
@export var body_hold := 18.0
@export var body_stiff := 1.5
@export var body_sink := 0.06
## Full detail within this of the camera; the low model further off.
@export var detail_range := 14.0
## Within `detail_range`, the game model (about 3,800 triangles, as a Twilight Princess figure
## spends them) in place of the full one; the low model further off as ever. With it on, the full
## model is never loaded.
@export var game := false:
	set(value):
		game = value
		if is_node_ready():
			_show(_near)
## The cartoon eye: 0 the eye as the species has it, 1 a cartoon eye (a moray's small mean one: a
## pale icy iris, a small pupil, a heavy scowling lid).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send_eyes()
## Where it looks: the iris and pupil slide that way (x towards its snout, y up; -1..1).
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value
		_send_eyes()
## 0 eyes open, 1 shut (squashed flat, the lid drawn down).
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send_eyes()
## A round tank it is kept inside (the user, 2026-11-17, of a tube of water it swam in: "make sure
## the squid and eel dont clip out the sides of the tank"): the tank's radius (world metres; 0
## none) about the upright line through `tank_at`. Its ropes are put back inside the wall.
var tank := 0.0
var tank_at := Vector3.ZERO
## Where everything that comes round is, in beats (see above).
var phase := 0.0
## How far open the jaw is now, of a whole gape (0..1).
var gape := 0.0

# The MeshInstance3Ds made so far, by model ("", "_lo", "_game"): each made when first shown.
var _shown := {}
var _near := true
var _material: ShaderMaterial
# The spine's points (world), where each was a step ago, the body as it is drawn (the spine with
# the swimming wave on it: its points, world, and which way the eel's back is at each), and the
# picture that carries those to the shader.
var _spine := PackedVector3Array()
var _spine_before := PackedVector3Array()
var _drawn := PackedVector3Array()
var _backs := PackedVector3Array()
var _data := PackedFloat32Array()
var _picture: ImageTexture
var _laid := false
var _was_at := Vector3.ZERO


static var _meshes := {}


func _ready() -> void:
	_material = ShaderMaterial.new()
	_material.shader = SHADER
	_send_eyes()
	_show(true)


## The game model's mesh, loaded once and kept, without the importer's automatic LODs (a body laid
## along the spine in the vertex shader would bend in straight pieces far off). For a game that
## draws its own meshes; its material needs the spine picture MorayEel sends.
static func game_mesh() -> Mesh:
	if not _meshes.has(GAME_MODEL):
		var made := (load(GAME_MODEL) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		var plain := ArrayMesh.new()
		for surface in found.mesh.get_surface_count():
			plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, found.mesh.surface_get_arrays(surface))
		_meshes[GAME_MODEL] = plain
		made.free()
	return _meshes[GAME_MODEL]


## The near (full or game) model, or the far one, made the first time it is shown.
func _show(near: bool) -> void:
	_near = near
	var wanted := ("_game" if game else "") if near else "_lo"
	if not _shown.has(wanted):
		_shown[wanted] = _mesh_of(wanted)
	for which: String in _shown:
		_shown[which].visible = which == wanted


## The MeshInstance3D showing now (the full, game or low model).
func shown_mesh() -> MeshInstance3D:
	return _shown.get(("_game" if game else "") if _near else "_lo")


func _mesh_of(suffix: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	if suffix == "_game":
		mesh.mesh = game_mesh()
	else:
		var scene := load(MODEL % suffix) as PackedScene
		var made := scene.instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		mesh.mesh = found.mesh
		made.free()
	# (the full model has a second surface, the throat and gills: the same material)
	for surface in mesh.mesh.get_surface_count():
		mesh.set_surface_override_material(surface, _material)
	# (its body may lie anywhere within its length of its head)
	mesh.extra_cull_margin = LENGTH * 1.1
	mesh.name = "Eel" + suffix
	add_child(mesh)
	return mesh


func _send_eyes() -> void:
	if _material:
		_material.set_shader_parameter(&"cartoon_eyes", cartoon_eyes)
		_material.set_shader_parameter(&"eye_look", eye_look)
		_material.set_shader_parameter(&"blink", blink)


## Each frame, after putting it where it is. Its body follows however it has been moved and
## turned since the last step. `velocity` (world, m/s) is how fast it is going through the
## water: where that is more than it has really moved (an eel held on the spot in a picture,
## swimming against water that runs past it), the body is carried back by the difference; give
## Vector3.ZERO when there is nothing to add.
func step(velocity: Vector3, delta: float) -> void:
	delta = minf(delta, 0.05)
	if beat > 0.0:
		phase = fposmod(phase + delta / beat, float(maxi(gape_beats, 1)))
	gape = 0.5 - 0.5 * cos(phase / maxi(gape_beats, 1) * TAU)
	set_shader_parameter(&"jaw", deg_to_rad(jaw_rest + jaw_gape * gape))
	set_shader_parameter(&"gape", gape)
	set_shader_parameter(&"phase", fposmod(phase, 1.0))
	if not is_inside_tree():
		return
	if not is_visible_in_tree():
		# (unseen, its spine is not worked out: it is laid afresh when it is next seen)
		_laid = false
	elif not _laid or global_position.distance_to(_was_at) > 2.0 * _size():
		lay_ropes()
	elif delta > 0.0:
		_swing(velocity, delta)
		_send()
	var camera := get_viewport().get_camera_3d()
	if camera:
		var near := camera.global_position.distance_to(global_position) < detail_range
		if near != _near:
			_show(near)


## Sets one of the shader's settings (its colours: `skin`, `skin_deep`, `mouth`, `tooth`, `iris`;
## how deep its wrinkles are: `wrinkles`; how much its fin ripples: `fin_ripple`). The eye's
## settings are the properties `cartoon_eyes`, `eye_look`, `blink`.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Lays the body out afresh, straight behind the head where it is now (after putting the eel
## somewhere new all at once: its body would otherwise be dragged there from where it was).
func lay_ropes() -> void:
	if _spine.is_empty():
		_spine.resize(POINTS)
		_spine_before.resize(POINTS)
		_drawn.resize(POINTS)
		_backs.resize(POINTS)
		_data.resize(POINTS * 2 * 4)
	var piece := LENGTH * _size() / (POINTS - 1)
	var back := global_basis.orthonormalized().z
	for i in POINTS:
		_spine[i] = global_position + back * piece * i
		_spine_before[i] = _spine[i]
	_laid = true
	_was_at = global_position
	_send()


## Where `s` (0 the snout .. 1 the tail tip) along the body is now, in the world: on its
## spine with the swimming wave on it, on the same curve the shader lays it along.
func body_point(s: float) -> Vector3:
	if not _laid:
		lay_ropes()
	var f := clampf(s, 0.0, 1.0) * (POINTS - 1)
	var i := mini(int(f), POINTS - 2)
	var t := f - i
	var p0 := _drawn[maxi(i - 1, 0)]
	var p1 := _drawn[i]
	var p2 := _drawn[i + 1]
	var p3 := _drawn[mini(i + 2, POINTS - 1)]
	return 0.5 * (2.0 * p1 + (p2 - p0) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t * t + (3.0 * (p1 - p2) + p3 - p0) * t * t * t)


## The simulated spine's points (world), snout to tail tip, without the swimming wave: for
## whoever wants to check it or hang something on it.
func spine_points() -> PackedVector3Array:
	if not _laid:
		lay_ropes()
	return _spine


func _size() -> float:
	return maxf(global_basis.get_scale().x, 0.0001)


## A step of the spine (Verlet): each point behind the head keeps going as it was, slowed by
## the water, drawn back towards lying straight out behind the head (strongly at the neck,
## hardly at the tail), sinking; then the spine is held to its length from the head back, and
## kept from bending more sharply than a body can. The water stands still in the world, but
## for `velocity` more than the eel has really moved: that much runs past it the other way
## and carries the body with it.
func _swing(velocity: Vector3, delta: float) -> void:
	var size := _size()
	var piece := LENGTH * size / (POINTS - 1)
	var keep := exp(-body_drag * delta)
	var water := Vector3.ZERO
	if velocity != Vector3.ZERO:
		water = (global_position - _was_at) / delta - velocity
	_was_at = global_position
	var carried := water * delta * (1.0 - keep)
	var back := global_basis.orthonormalized().z
	var sink := Vector3.DOWN * body_sink * size * delta * delta
	for i in HEAD_POINTS:
		_spine[i] = global_position + back * piece * i
		_spine_before[i] = _spine[i]
	var was_1 := _spine[HEAD_POINTS - 1]
	var was_2 := _spine[HEAD_POINTS - 2]
	var straighten := 1.0 - exp(-body_stiff * delta)
	for i in range(HEAD_POINTS, POINTS):
		var p := _spine[i]
		var share := float(i - HEAD_POINTS + 1) / (POINTS - HEAD_POINTS)
		var held := 1.0 - 0.86 * smoothstep(0.0, 0.9, share)
		var rest := global_position + back * piece * i
		var moved := (p - _spine_before[i]) * keep + carried + (rest - p) * body_hold * held * delta * delta + sink
		# (eased into line with the two points before it, as they were before this step: it is
		# put there, not thrown there, so that this gives it no speed of its own to swing on with)
		var eased := (was_1 * 2.0 - was_2 - p) * straighten
		was_2 = was_1
		was_1 = p
		_spine_before[i] = p + eased
		_spine[i] = p + eased + moved
	# Held to its length, from the head back, and kept from bending more sharply than a body
	# can. (A point moved for that is put there, not thrown there: it gets no speed from it.
	# Thrown, the pieces swung one another on, and the body whipped round after a turning head.)
	for i in range(HEAD_POINTS, POINTS):
		var from := _spine[i - 1]
		var way := _spine[i] - from
		var before := (from - _spine[i - 2]).normalized()
		var long := way.length()
		way = way / long if long > 0.00001 else before
		var over := way.angle_to(before) - BEND
		if over > 0.0:
			var about := way.cross(before)
			if about.length() > 0.00001:
				way = way.rotated(about.normalized(), over)
				_spine_before[i] += from + way * piece - _spine[i]
		_spine[i] = from + way * piece
		var inside := _in_tank(_spine[i])
		_spine_before[i] += inside - _spine[i]
		_spine[i] = inside


## `p` (world), put back inside the round tank if it is outside it (see `tank`).
func _in_tank(p: Vector3) -> Vector3:
	if tank <= 0.0:
		return p
	var out := Vector2(p.x - tank_at.x, p.z - tank_at.z)
	var far := out.length()
	if far <= tank:
		return p
	out *= tank / far
	return Vector3(tank_at.x + out.x, p.y, tank_at.z + out.y)

## The body as it is drawn: the spine with the swimming wave on it (each piece turned from the
## spine's line, about the eel's back, by a wave that runs tailwards and grows; every piece
## keeps its length), and which way its back is at each point (carried along the spine from
## the head with the least turning). Then to the shader: a picture, the points along its top
## row and the backs along its bottom row, in the eel's own space.
func _send() -> void:
	var turned := global_basis.orthonormalized()
	var up := turned.y
	var size := _size()
	var piece := LENGTH * size / (POINTS - 1)
	var before := turned.z
	_drawn[0] = _spine[0]
	for i in POINTS - 1:
		var way := (_spine[i + 1] - _spine[i]).normalized()
		# (the eel's back, carried on to this piece)
		var axis := before.cross(way)
		up = up + axis.cross(up) + axis.cross(axis.cross(up)) / (1.0 + maxf(before.dot(way), -0.98))
		up = (up - way * up.dot(way)).normalized()
		before = way
		var s := float(i) / (POINTS - 1)
		var behind := clampf((i - HEAD_POINTS + 1.0) / (POINTS - HEAD_POINTS), 0.0, 1.0)
		var grows := 0.25 * smoothstep(0.0, 0.2, behind) + 0.75 * behind
		var angle := swim * grows * sin((phase - swim_waves * s) * TAU)
		var side := up.cross(way)
		_backs[i] = up
		_drawn[i + 1] = _drawn[i] + (way * cos(angle) + side * sin(angle)) * piece
	_backs[POINTS - 1] = up
	var to_local := global_transform.affine_inverse()
	var back_local := turned.inverse()
	for i in POINTS:
		var p := to_local * _drawn[i]
		var b := back_local * _backs[i]
		_data[i * 4] = p.x
		_data[i * 4 + 1] = p.y
		_data[i * 4 + 2] = p.z
		_data[(POINTS + i) * 4] = b.x
		_data[(POINTS + i) * 4 + 1] = b.y
		_data[(POINTS + i) * 4 + 2] = b.z
	var image := Image.create_from_data(POINTS, 2, false, Image.FORMAT_RGBAF, _data.to_byte_array())
	if _picture == null:
		_picture = ImageTexture.create_from_image(image)
		set_shader_parameter(&"spine", _picture)
	else:
		_picture.update(image)
