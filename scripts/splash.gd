class_name Splash
extends Node3D
## A splash where something goes through the surface: three tubes of water, one inside the other
## like the tiers of a cake (the outer one wide and low, the inner one narrow and tall), that
## shoot up with ragged crests and drop back, with ripples spreading across the water and a burst
## of splattery drops.
##
## This is Salmon Run 2's scripts/fx/splash.gd (as of its a34aa80) with its track taken out: there
## it is laid on the river's surface along the track; here `start` is told where on the sea's flat
## surface it is, and how big (1 is a splash for a salmon 1.8 m long, as there). Its meshes are
## Salmon Run 2's (scripts/world/props.gd) and its tubes' shader is shaders/splash.gdshader.

const Props := preload("res://scripts/world/props.gd")

const LIFE := 1.0
## Each tube, from the inside out: how far out, how tall, how many waves in its crest, and
## when it goes up.
const TUBES := [[0.5, 2.7, 5.0, 0.0], [1.15, 1.75, 7.0, 0.05], [1.9, 0.95, 10.0, 0.1]]
const TUBE_TIME := 0.62
## Each ripple: when it starts, and how wide it gets.
const RIPPLES := [[0.0, 3.2], [0.14, 4.4], [0.3, 5.6]]
const RIPPLE_TIME := 0.75
## Each burst of drops: which mesh, how many, how big, and how fast they are flung (slowest
## and fastest).
const BURSTS := [["drop", 12, 0.26, 5.0, 11.0], ["splat", 9, 0.34, 3.5, 8.0], ["dot", 26, 0.11, 4.0, 13.0]]

static var _meshes := {}
static var _mat: StandardMaterial3D

var strength := 1.0
## How big it is (1: for a salmon 1.8 m long).
var size := 1.0

var _t := 0.0
var _slow := 1.0
var _tubes: Array[MeshInstance3D] = []
var _ripples: Array[MeshInstance3D] = []
var _bursts: Array[CPUParticles3D] = []


## Plain white-and-blue water, unlit, coloured by the mesh.
static func material() -> StandardMaterial3D:
	if _mat == null:
		_mat = StandardMaterial3D.new()
		_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		_mat.vertex_color_use_as_albedo = true
	return _mat


static func mesh(key: String) -> Mesh:
	if _meshes.is_empty():
		var rng := RandomNumberGenerator.new()
		rng.seed = 77
		_meshes["tube"] = Props.splash_tube()
		_meshes["ring"] = Props.splash_ring()
		_meshes["drop"] = Props.droplet(rng)
		_meshes["splat"] = Props.splat(rng)
		var dot := SphereMesh.new()
		dot.radius = 0.5
		dot.height = 1.0
		dot.radial_segments = 6
		dot.rings = 3
		_meshes["dot"] = dot
	return _meshes[key]


## Everything a splash is made of is built once, here, and used again each time.
func _init() -> void:
	top_level = true
	visible = false
	set_process(false)
	for i in TUBES.size():
		var node := MeshInstance3D.new()
		node.mesh = mesh("tube")
		var mat := ShaderMaterial.new()
		mat.shader = preload("res://shaders/splash.gdshader")
		mat.set_shader_parameter("waves", TUBES[i][2])
		node.material_override = mat
		node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		node.visible = false
		add_child(node)
		_tubes.append(node)
	for i in RIPPLES.size():
		var node := MeshInstance3D.new()
		node.mesh = mesh("ring")
		var mat := StandardMaterial3D.new()
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		mat.albedo_color = Color(1, 1, 1, 0.0)
		mat.render_priority = 1
		node.material_override = mat
		node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(node)
		_ripples.append(node)
	for b: Array in BURSTS:
		_bursts.append(_burst(b[0], b[1], b[2]))


## Throws it up at a place on the surface, `how_big` (1: for a salmon), out of water of a colour
## with foam of another. `how_hard` (1: an ordinary landing) makes it taller and its drops fly
## further, not wider.
##
## (Gulp, tools/WATER_FX.md: here everything is scaled by `size` alone, in proportion: its width,
## its height, its drops, and its time by the root of it, as a splash of a bigger thing is slower.
## Salmon Run 2 made it wider by the root of its strength and taller by the strength, which is
## right for one salmon landing harder or softer; for a sardine and an orca it made one a speck
## and the other a column of water 40 m high with drops the size of boulders.)
func start(at: Vector3, how_big: float, water: Color, foam: Color, how_hard := 1.0) -> void:
	size = how_big
	strength = how_hard
	_slow = clampf(sqrt(size), 0.5, 1.9)
	_t = 0.0
	water = water.lerp(foam, 0.15)
	for node in _tubes:
		node.visible = false
		(node.material_override as ShaderMaterial).set_shader_parameter("phase", randf() * TAU)
		(node.material_override as ShaderMaterial).set_shader_parameter("white", foam)
		(node.material_override as ShaderMaterial).set_shader_parameter("pale", water.lerp(foam, 0.55))
		(node.material_override as ShaderMaterial).set_shader_parameter("blue", water)
	for node in _ripples:
		node.visible = false
	for i in _bursts.size():
		var p := _bursts[i]
		# (thrown up by the root of size and strength, they rise in proportion to both; drops do
		# not grow as fast as the splash: a bigger one has more of them, not boulders)
		var fling := sqrt(size * strength)
		p.initial_velocity_min = float(BURSTS[i][3]) * fling
		p.initial_velocity_max = float(BURSTS[i][4]) * fling
		p.scale_amount_min = float(BURSTS[i][2]) * 0.6 * pow(size, 0.6)
		p.scale_amount_max = float(BURSTS[i][2]) * 1.3 * pow(size, 0.6)
		p.emission_sphere_radius = 0.5 * size
		p.lifetime = 0.8 * _slow * sqrt(clampf(strength, 0.5, 2.0))
		p.color = water.lerp(Color.WHITE, 0.6)
		p.restart()
		p.emitting = true
	transform = Transform3D(Basis.IDENTITY, at + Vector3.UP * 0.03)
	visible = true
	set_process(true)


## A one-shot spray of drops, flung up and outwards.
func _burst(key: String, amount: int, size: float) -> CPUParticles3D:
	var p := CPUParticles3D.new()
	p.mesh = mesh(key)
	p.material_override = material()
	p.amount = amount
	p.emitting = false
	p.one_shot = true
	p.explosiveness = 0.95
	p.lifetime = 0.8
	p.local_coords = true
	p.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
	p.emission_sphere_radius = 0.5
	p.direction = Vector3.UP
	p.spread = 62.0
	p.gravity = Vector3(0, -24, 0)
	p.scale_amount_min = size * 0.6
	p.scale_amount_max = size * 1.3
	var shrink := Curve.new()
	shrink.add_point(Vector2(0.0, 1.0))
	shrink.add_point(Vector2(0.7, 0.8))
	shrink.add_point(Vector2(1.0, 0.0))
	p.scale_amount_curve = shrink
	add_child(p)
	return p


func _process(delta: float) -> void:
	_t += delta / _slow
	if _t > LIFE:
		visible = false
		set_process(false)
		return
	# (its drops are flung through the air: from under the water they are not drawn. They fell on
	# through the surface and rained past an eye that had followed the fish back in, as boulders.
	# Gulp's CLAUDE.md, "Decision: the camera at the surface")
	var eye := get_viewport().get_camera_3d()
	var dry := eye == null or eye.global_position.y > Sea.surface_height(eye.global_position.x, eye.global_position.z, eye.global_position.y)
	for p in _bursts:
		p.visible = dry
	for i in _tubes.size():
		var u := (_t - float(TUBES[i][3])) / TUBE_TIME
		var node := _tubes[i]
		node.visible = u > 0.0 and u < 1.0
		if not node.visible:
			continue
		# up fast, hang at the top, then drop back: the key pose is the top, a fifth of the way in
		var rise := sin(minf(u / 0.2, 1.0) * PI * 0.5) if u < 0.2 else 1.0 - pow((u - 0.2) / 0.8, 2.0)
		var r := float(TUBES[i][0]) * size * (1.0 + 0.3 * u)
		node.scale = Vector3(r, maxf(float(TUBES[i][1]) * size * strength * rise, 0.01), r)
		(node.material_override as ShaderMaterial).set_shader_parameter("spent", smoothstep(0.3, 1.0, u))
	for i in _ripples.size():
		var u := (_t - float(RIPPLES[i][0])) / RIPPLE_TIME
		var node := _ripples[i]
		node.visible = u > 0.0 and u < 1.0
		if not node.visible:
			continue
		var r := lerpf(0.5 * size, float(RIPPLES[i][1]) * size, 1.0 - pow(1.0 - u, 2.5))
		node.scale = Vector3(r, 1.0, r)
		(node.material_override as StandardMaterial3D).albedo_color.a = (1.0 - u) * 0.85
