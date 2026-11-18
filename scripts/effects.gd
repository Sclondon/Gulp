class_name Effects
extends Node3D
## The water's small effects round the player, after Salmon Run 2's (its scripts/player/salmon.gd
## and scripts/fx/splash.gd, as of its a34aa80): round drops that shrink away to nothing, never
## squares.
##
## - A string of bubbles trailing from the fish while it bursts along under water (there: while
##   dived).
## - Small white dots of spray tossed up off each shoulder while it swims at the surface.
## - A burst of bubbles where something is eaten.
## - A Splash (scripts/splash.gd) where it leaves the water and where it comes back in; a few are
##   kept and used in turn.
##
## Everything is sized to the fish: Salmon Run 2's numbers are for a salmon `SALMON` metres long.

const SALMON := 1.8
const WATER := Color(0.1, 0.3, 0.56)
const FOAM := Color(0.92, 1.0, 0.96)

var player: Player

var _bubbles: CPUParticles3D
var _dots: Array[CPUParticles3D] = []
var _meal: CPUParticles3D
var _splashes: Array[Splash] = []
var _next := 0
var _sized := 0.0


func _ready() -> void:
	# a string of bubbles
	_bubbles = _particles(18, 0.45, Color(0.85, 0.97, 1.0), 0.1)
	_bubbles.emission_box_extents = Vector3(0.25, 0.1, 0.5)
	_bubbles.direction = Vector3(0, 1, 0)
	_bubbles.spread = 20.0
	_bubbles.initial_velocity_min = 1.5
	_bubbles.initial_velocity_max = 2.6
	_bubbles.gravity = Vector3.ZERO
	# spray off each shoulder (they travel with the fish, so that they stay round it)
	for side: float in [-1.0, 1.0]:
		var dots := _particles(10, 0.3, Color(0.96, 1.0, 1.0), 0.1)
		dots.direction = Vector3(side * 0.55, 1.0, 0.5)
		dots.spread = 20.0
		dots.initial_velocity_min = 1.4
		dots.initial_velocity_max = 2.8
		dots.emission_box_extents = Vector3(0.05, 0.03, 0.3)
		dots.gravity = Vector3(0, -18, 0)
		dots.set_meta(&"side", side)
		_dots.append(dots)
	# what is eaten goes in a burst of bubbles
	_meal = _particles(14, 0.6, Color(0.85, 0.97, 1.0), 0.1)
	_meal.one_shot = true
	_meal.explosiveness = 0.9
	_meal.emission_box_extents = Vector3(0.15, 0.15, 0.15)
	_meal.spread = 80.0
	_meal.initial_velocity_min = 0.6
	_meal.initial_velocity_max = 1.8
	_meal.gravity = Vector3(0, 2.0, 0)
	for i in 4:
		var splash := Splash.new()
		add_child(splash)
		_splashes.append(splash)
	# (a speck of a splash, so that what draws one is ready before the first leap needs it)
	_splashes[0].start(Vector3(0.0, Sea.SURFACE, 0.0), 0.02, WATER, FOAM)


func _process(_delta: float) -> void:
	if player == null:
		return
	var big := maxf(player.length / SALMON, 0.05)
	if absf(big - _sized) > 0.02 * _sized:
		_sized = big
		for p: CPUParticles3D in [_bubbles, _dots[0], _dots[1]]:
			p.scale_amount_min = 0.6 * big
			p.scale_amount_max = 1.2 * big
		_bubbles.initial_velocity_min = 1.5 * sqrt(big)
		_bubbles.initial_velocity_max = 2.6 * sqrt(big)
		_bubbles.emission_box_extents = Vector3(0.25, 0.1, 0.5) * big
		for dots in _dots:
			dots.initial_velocity_min = 1.4 * sqrt(big)
			dots.initial_velocity_max = 2.8 * sqrt(big)
			dots.emission_box_extents = Vector3(0.05, 0.03, 0.3) * big
	var at := player.global_position
	var under := player.alive and not player.in_air
	# bubbles from behind it while it bursts along
	_bubbles.global_position = at - player.heading * player.length * 0.3 + Vector3.UP * 0.05 * big
	_bubbles.emitting = under and player.boosting
	# spray while its back cuts the surface
	var cutting := under and at.y > Sea.SURFACE - maxf(player.length * 0.35, 0.15)
	var across := player.heading.cross(Vector3.UP).normalized()
	for dots in _dots:
		var side: float = dots.get_meta(&"side")
		dots.global_position = Vector3(at.x, Sea.SURFACE + 0.02, at.z) + across * side * 0.28 * big + player.heading * 0.35 * big
		dots.direction = (across * side * 0.55 + Vector3.UP - player.heading * 0.5).normalized()
		dots.emitting = cutting


## Something was eaten there.
func eat(at: Vector3) -> void:
	var big := maxf(player.length / SALMON, 0.05)
	_meal.global_position = at
	_meal.scale_amount_min = 0.6 * big
	_meal.scale_amount_max = 1.3 * big
	_meal.initial_velocity_min = 0.6 * sqrt(big)
	_meal.initial_velocity_max = 1.8 * sqrt(big)
	_meal.restart()
	_meal.emitting = true


## It has gone through the surface there (out or in). (A splash's width goes by the root of its
## strength and its height by the strength, so the square of the fish's size keeps it in proportion.)
func splash(at: Vector3, strength := 1.0) -> void:
	_next = (_next + 1) % _splashes.size()
	_splashes[_next].start(Vector3(at.x, Sea.SURFACE, at.z), pow(maxf(player.length / SALMON, 0.08), 2.0) * strength, WATER, FOAM)


## A stream of round drops (never squares) that shrink away to nothing. (Salmon Run 2's.)
func _particles(amount: int, life: float, col: Color, size: float) -> CPUParticles3D:
	var p := CPUParticles3D.new()
	p.amount = amount
	p.lifetime = life
	p.emitting = false
	p.local_coords = false
	p.top_level = true
	p.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	p.emission_box_extents = Vector3(0.6, 0.1, 0.6)
	p.direction = Vector3(0, 1, 0)
	p.spread = 40.0
	p.gravity = Vector3(0, -20, 0)
	p.scale_amount_min = 0.6
	p.scale_amount_max = 1.2
	var shrink := Curve.new()
	shrink.add_point(Vector2(0.0, 0.6))
	shrink.add_point(Vector2(0.2, 1.0))
	shrink.add_point(Vector2(1.0, 0.0))
	p.scale_amount_curve = shrink
	var drop := SphereMesh.new()
	drop.radius = size * 0.5
	drop.height = size
	drop.radial_segments = 8
	drop.rings = 4
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = col
	drop.material = mat
	p.mesh = drop
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(p)
	return p
