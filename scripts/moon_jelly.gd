class_name MoonJelly
extends Node3D
## A moon jelly (Aurelia aurita), after the user's aquarium photographs and a film of them
## swimming: a clear saucer of a bell that beats, veined with forking canals, four horseshoe
## gonads glowing through it, a long fine fringe streaming back from its rim, and four frilled
## oral arms lying out along the underside of the bell with loose ends near its rim.
##
## It swims by itself towards `goal`, bell first, at whatever tilt that takes: each beat of its
## bell is a push along the way its bell points, the water slows it between beats, and it turns
## slowly towards where it is going. Or it is steered (`steered`: the swim mode): it turns towards
## `aim` and beats only when told to (`pulse()`).
##
## The oral arms are simulated like ropes: each a chain of points (Verlet; held to length; dragged
## by the water it moves through, so they lag and swing behind it), after GameCommon's rope
## (godot/rope), which also sends its chain to the vertex shader to draw. The fringe is too many
## and too fine for that: the shader sways it and swings it back by how the jelly is moving.
##
## It gives off a little light of its own (a real light on the sand and rocks near it), which
## swells with `Sea.music` and with each beat of its bell.
##
## The model is models/moon_jelly.glb (tools/build_moon_jelly.py); shaders/moon_jelly.gdshader
## beats the bell and lays the arms along their chains.

const MODEL := "res://models/moon_jelly.glb"
const SHADER := preload("res://shaders/moon_jelly.gdshader")
const AURA := preload("res://shaders/aura.gdshader")
## The beat of the bell, as the shader has it (SWING, LAG, CLOSING there): keep them in step.
const SWING := 0.9
const LAG := 0.3
const CLOSING := 0.36
## As the model is built (tools/build_moon_jelly.py) and the shader draws it: keep them in step.
const ARMS := 4
const ARM_POINTS := 10
const ARM_ROOT := 0.07
const ARM_Y := 0.08
const ARM_LONG := 0.85

## The radius of its bell (metres).
@export var size := 0.25
## Seconds a beat of its bell takes.
@export var beat_seconds := 2.4
## How hard a beat pushes it (m/s² while the bell closes), and how much the water slows it (/s).
@export var push := 0.8
@export var water_drag := 1.1
## How fast it turns towards where it is going (/s).
@export var turn := 0.4
## How much it keeps its bell upwards whatever way it is going (0 points straight at its goal).
@export var upright := 0.15
## The arms lie out from the middle along the underside of the bell, one to each quarter, held
## to it for most of their length with loose ends near the rim (the user, 2026-11-17: "4 ridges
## with loose ends along the dome"). How much the water slows them (/s), how strongly they are
## held to the bell, how much they dip below level on their way out, and how fast the loose
## ends sink (m/s²).
@export var arm_drag := 2.5
@export var arm_spring := 70.0
@export var arm_dip := 0.2
@export var arm_sink := 0.05
## How long its fringe of tentacles is, for 1 as the model has it.
@export var fringe := 1.0
## Its own light: how bright at rest, and how much the music adds.
@export var glow := 0.75
@export var glow_music := 0.9

## Where it is trying to go (world), and how fast it is going.
var goal := Vector3.ZERO
var velocity := Vector3.ZERO
## A slow current everything drifts in.
var current := Vector3.ZERO
## How loud the music is just now (0..1), from Sea.
var music := 0.0
## Steered by a player: it turns towards `aim` (a direction) and beats only on `pulse()`.
var steered := false
var aim := Vector3.UP
## Carried: something else puts it where it is each frame (Sea, for the two that spin as one);
## it only beats, and its arms and fringe follow.
var carried := false
## How much of its light shows (0 dark and unseen, 1 all of it): Sea fades jellies in with it.
var fade := 1.0

var _mesh: MeshInstance3D
var _material: ShaderMaterial
var _lamp: OmniLight3D
var _aura: ShaderMaterial
var _clock := 0.0
var _beat := 0.0
var _beating := false
# How far the bell opens between beats (see `open` in the shader): eased towards what this
# beat is to have, so that it never jumps.
var _open := 0.3
var _open_goal := 0.3
var _trail := Vector3.ZERO
var _points := PackedVector3Array()
var _before := PackedVector3Array()
var _local := PackedVector3Array()

static var _shared: Mesh


func _ready() -> void:
	_clock = randf() * 30.0
	_beat = randf()
	scale = Vector3.ONE * size
	if _shared == null:
		var made := (load(MODEL) as PackedScene).instantiate()
		_shared = (made.find_children("*", "MeshInstance3D", true, false)[0] as MeshInstance3D).mesh
		made.free()
	_material = ShaderMaterial.new()
	_material.shader = SHADER
	_material.set_shader_parameter(&"fringe", fringe)
	_mesh = MeshInstance3D.new()
	_mesh.mesh = _shared
	_mesh.material_override = _material
	_mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	# (the arms swing well outside the box the still model was made in)
	_mesh.custom_aabb = AABB(Vector3(-2.5, -2.5, -2.5), Vector3(5.0, 5.0, 5.0))
	add_child(_mesh)
	_lamp = OmniLight3D.new()
	_lamp.light_color = Color(0.5, 0.72, 1.0)
	_lamp.omni_range = 2.2 / size
	_lamp.omni_attenuation = 1.6
	_lamp.shadow_enabled = false
	_lamp.light_specular = 0.2
	add_child(_lamp)
	# its aura: a soft halo and sparkles, on a square that faces the camera
	_aura = ShaderMaterial.new()
	_aura.shader = AURA
	_aura.set_shader_parameter(&"seed", randf() * 100.0)
	var square := QuadMesh.new()
	square.size = Vector2(5.0, 5.0)
	var halo := MeshInstance3D.new()
	halo.mesh = square
	halo.material_override = _aura
	halo.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	halo.position = Vector3(0.0, 0.1, 0.0)
	add_child(halo)
	lay_arms()


## A beat of the bell, now (when `steered`). Ignored while one is under way.
func pulse() -> void:
	if not _beating:
		_beating = true
		_beat = 0.0


## Whether its bell is closing just now (the part of a beat that pushes).
func closing() -> bool:
	return _beat < CLOSING


## How far its bell is drawn in just now (0..1).
func drawn_in() -> float:
	return _squeeze(_beat)


## Beats in time with another from now on.
func beat_with(other: MoonJelly) -> void:
	beat_seconds = other.beat_seconds
	_beat = other._beat


## A knock (two jellies meeting): its bell closes at once.
func bump() -> void:
	_beat = 0.0


## How far the bell is drawn in, through a beat (0..1): as `squeeze` in the shader.
func _squeeze(x: float) -> float:
	x = fposmod(x, 1.0)
	var through := 0.5 * x / CLOSING if x < CLOSING else 0.5 + 0.5 * (x - CLOSING) / (1.0 - CLOSING)
	return 0.5 - 0.5 * cos(through * TAU)


## A point of the bell (its own space) as the beat has bent it: as `bend` in the shader.
func _bend(p: Vector3) -> Vector3:
	var reach := Vector2(p.x, p.z).length()
	var rim := smoothstep(0.12, 1.0, reach)
	var q := _squeeze(_beat - LAG * rim)
	var round_it := atan2(p.z, p.x)
	var lump := 1.0 + 0.07 * sin(round_it * 3.0 + _beat * TAU) + 0.04 * sin(round_it * 5.0 - _clock * 0.9)
	var swing := SWING * (q * (1.0 + _open) - _open) * rim * lump
	var arm := Vector2(reach - 0.25, p.y - 0.15)
	var swung := Vector2(arm.x * cos(swing) + arm.y * sin(swing), arm.y * cos(swing) - arm.x * sin(swing))
	var grown := (0.25 + swung.x) / maxf(reach, 0.0001)
	return Vector3(p.x * grown, 0.15 + swung.y + 0.07 * _squeeze(_beat) + 0.012 * sin(reach * 9.0 - _beat * TAU * 2.0) * rim * (0.4 + 0.6 * q), p.z * grown)


## Puts the arms out under the bell, at rest (after moving it somewhere new).
func lay_arms() -> void:
	_points.resize(ARMS * ARM_POINTS)
	_before.resize(ARMS * ARM_POINTS)
	_local.resize(ARMS * ARM_POINTS)
	for k in ARMS:
		for i in ARM_POINTS:
			var p := _arm_rest(k, i)
			_points[k * ARM_POINTS + i] = p
			_before[k * ARM_POINTS + i] = p
	_send()


## Each frame: it swims, and its arms follow.
func step(delta: float) -> void:
	delta = minf(delta, 0.05)
	_clock += delta
	_open = lerpf(_open, _open_goal, 1.0 - exp(-1.6 * delta))
	var was := global_position
	if carried:
		_beat += delta / beat_seconds
		if _beat >= 1.0:
			_beat = fposmod(_beat, 1.0)
			_open_goal = randf_range(0.95, 1.25) if randf() < 0.35 else randf_range(0.25, 0.45)
	else:
		_swim(delta)
	_arms(delta)
	# (the fringe streams back the faster it goes: a share of each tentacle's length)
	var moved := (global_position - was) / maxf(delta, 0.0001)
	var back := -(global_basis.orthonormalized().inverse() * moved) * 3.2
	_trail = _trail.lerp(back.limit_length(1.1), 1.0 - exp(-1.0 * delta))
	_send()


func _swim(delta: float) -> void:
	var up := global_basis.y.normalized()
	var want := aim.normalized()
	var keen := 1.5
	if not steered:
		var to_goal := goal - global_position
		var far := to_goal.length()
		# It turns towards its goal, bell first, keeping only a little of "up".
		want = (to_goal.normalized() * (1.0 - upright) + Vector3.UP * upright).normalized() if far > 0.05 else Vector3.UP
		# (near its goal it beats lazily)
		keen = clampf(far / 1.2, 0.25, 2.2)
	var turned := up.slerp(want, 1.0 - exp(-turn * (3.0 if steered else 1.0) * delta)).normalized()
	var around := up.cross(turned)
	if around.length() > 0.00001:
		global_basis = Basis(around.normalized(), up.angle_to(turned)) * global_basis
	global_basis = global_basis.orthonormalized().scaled(Vector3.ONE * size)
	# A beat pushes it while the bell closes.
	if not steered or _beating:
		_beat += delta / beat_seconds
		if _beat >= 1.0:
			# (about one beat in three it opens right out, all but inside out)
			_open_goal = randf_range(0.95, 1.25) if randf() < 0.35 else randf_range(0.25, 0.45)
			_beat = fposmod(_beat, 1.0) if not steered else 0.0
			_beating = false
		if _beat < CLOSING and (not steered or _beating):
			velocity += turned * push * keen * delta
	velocity *= exp(-water_drag * delta)
	global_position += (velocity + current) * delta


func _arms(delta: float) -> void:
	var piece := _piece()
	var keep := exp(-arm_drag * delta)
	for k in ARMS:
		var base := k * ARM_POINTS
		var root := _arm_rest(k, 0)
		_points[base] = root
		_before[base] = root
		for i in range(1, ARM_POINTS):
			var p := _points[base + i]
			var share := float(i) / (ARM_POINTS - 1)
			# drawn back to hang out under the bell (most near the root), sinking a little, and
			# stirred by the water
			var rest := _arm_rest(k, i)
			# (held fast along the bell, all but free at the end)
			var pull := (rest - p) * arm_spring * lerpf(1.0, 0.0, smoothstep(0.72, 1.0, share))
			var stir := Vector3(sin(_clock * 0.7 + p.z * 2.1 + k), 0.0, cos(_clock * 0.6 + p.x * 1.9 + k * 2.0)) * 0.12 * share
			var moved := (p - _before[base + i]) * keep + (pull + stir + Vector3.DOWN * arm_sink) * delta * delta
			_before[base + i] = p
			_points[base + i] = p + moved + current * delta
		# held to length, from the root down (three times over, so that it settles)
		for again in 3:
			for i in range(1, ARM_POINTS):
				var from := _points[base + i - 1]
				var to := _points[base + i] - from
				var long := to.length()
				if long > 0.00001:
					_points[base + i] = from + to * (piece / long)


func _send() -> void:
	var to_local := global_transform.affine_inverse()
	for i in _points.size():
		_local[i] = to_local * _points[i]
	_material.set_shader_parameter(&"arm_pts", _local)
	_material.set_shader_parameter(&"clock", _clock)
	_material.set_shader_parameter(&"beat", _beat)
	_material.set_shader_parameter(&"open", _open)
	_material.set_shader_parameter(&"trail", _trail)
	# Its light: a little always, more as its bell closes, more with the music.
	var bright := (glow * (1.0 + 0.25 * _squeeze(_beat)) + glow_music * music) * fade
	_aura.set_shader_parameter(&"brightness", bright)
	_aura.set_shader_parameter(&"clock", _clock)
	_material.set_shader_parameter(&"brightness", bright)
	_lamp.light_energy = 0.5 * bright * size / 0.25


## Where point i of arm k lies at rest (world): on the underside of the bell, from the middle out
## towards the rim, as the ribs of an umbrella lie under its cloth (the user, 2026-11-17: "the 4
## center tentaclesa are still wrong, they need to be like the ribs of an umbrella"), and bent
## with the bell as it beats. The underside is as tools/build_moon_jelly.py makes it.
func _arm_rest(k: int, i: int) -> Vector3:
	var a := PI * 0.25 + k * PI * 0.5
	var reach := lerpf(ARM_ROOT, 0.86, float(i) / (ARM_POINTS - 1))
	var tilt := asin(pow(reach, 1.25))
	var at := Vector3(cos(a) * reach, 0.2 * pow(cos(tilt), 0.8) - 0.02, sin(a) * reach)
	return global_transform * _bend(at)


func _piece() -> float:
	return ARM_LONG * size / (ARM_POINTS - 1)
