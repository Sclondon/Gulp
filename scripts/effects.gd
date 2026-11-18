class_name Effects
extends Node3D
## The water's small effects round the player, after Salmon Run 2's (its scripts/player/salmon.gd
## and scripts/fx/splash.gd, as of its a34aa80): round drops that shrink away to nothing, never
## squares. (tools/WATER_FX.md has what each costs and whose calls they were.)
##
## - A trail of bubbles from the tail as it swims: a thin string of small ones cruising, a dense
##   stream of bigger ones while it bursts. They rise, wobble and shrink away, and are gone at
##   the surface. (the user, 2026-11-18: "you shloud leave a bubble trail / distortion in the
##   water, moras you swim and boost")
## - The water churned behind a fast fish: a shimmer in the picture (the post shader's `haze`),
##   from the last few places its tail has been.
## - While it bursts: the camera's view widens (`fov_kick`, which main adds to its field of view)
##   and pale streaks run past the edges (the post shader's `streaks`). ("boost should change fov
##   and speed lines")
## - Small white dots of spray tossed up off each shoulder while it swims at the surface.
## - A burst of bubbles where something is eaten.
## - A Splash (scripts/splash.gd) where it leaves the water and where it comes back in, sized to
##   the fish and as hard as it hit; a gush of bubbles under the water where it went in. A few
##   splashes are kept and used in turn.
##
## Everything is sized to the fish: Salmon Run 2's numbers are for a salmon `SALMON` metres long.

const SALMON := 1.8
const WATER := Color(0.1, 0.3, 0.56)
const FOAM := Color(0.92, 1.0, 0.96)
## How long the churned water shimmers behind the fish (s), and how many places of it are kept.
const HAZE_LIFE := 0.5
const HAZE_POINTS := 8
## How much wider the view gets in a full burst (degrees).
const FOV_KICK := 10.0

var player: Player
## The game's camera, and the post shader's material (main sets them).
var camera: Camera3D
var post: ShaderMaterial
## Degrees to add to the camera's field of view now (eased in and out with the burst).
var fov_kick := 0.0

var _trail: CPUParticles3D
var _stream: CPUParticles3D
var _plunge: CPUParticles3D
var _dots: Array[CPUParticles3D] = []
var _meal: CPUParticles3D
var _splashes: Array[Splash] = []
var _next := 0
var _sized := 0.0
var _bubble: ShaderMaterial
# The churned water: where the tail was (x, y, z) and how hard it was going (w), and when.
var _haze_at := PackedVector4Array()
var _haze_when := PackedFloat32Array()
var _haze_next := 0
var _haze_wait := 0.0
var _clock := 0.0
var _streaks := 0.0
var _warmed := false


func _ready() -> void:
	# every bubble is shaders/bubble.gdshader: a ring with a glint, facing the eye; none above the surface
	_bubble = ShaderMaterial.new()
	_bubble.shader = preload("res://shaders/bubble.gdshader")
	_bubble.set_shader_parameter(&"ceiling", Sea.SURFACE)
	_bubble.set_shader_parameter(&"near_cut", 0.45)
	# the trail: a thin string of bubbles cruising...
	_trail = _bubbles_of(26, 1.7)
	# ...and a dense stream of bigger ones while it bursts
	_stream = _bubbles_of(60, 1.3)
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
	_meal = _bubbles_of(14, 0.9)
	_meal.one_shot = true
	_meal.explosiveness = 0.9
	_meal.emission_box_extents = Vector3(0.15, 0.15, 0.15)
	_meal.spread = 80.0
	_meal.initial_velocity_min = 0.6
	_meal.initial_velocity_max = 1.8
	_meal.gravity = Vector3(0, 2.0, 0)
	# where it goes in, a gush of bubbles dragged down after it
	_plunge = _bubbles_of(40, 1.8)
	_plunge.one_shot = true
	_plunge.explosiveness = 0.85
	_plunge.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
	_plunge.spread = 50.0
	for i in 4:
		var splash := Splash.new()
		add_child(splash)
		_splashes.append(splash)
	# (a speck of a splash, so that what draws one is ready before the first leap needs it)
	_splashes[0].start(Vector3(0.0, Sea.SURFACE, 0.0), 0.02, WATER, FOAM)
	_haze_at.resize(HAZE_POINTS)
	_haze_when.resize(HAZE_POINTS)
	_haze_when.fill(-100.0)


func _process(delta: float) -> void:
	_clock += delta
	if player == null:
		return
	if not _warmed and camera and camera.is_inside_tree():
		# (a speck of bubbles in front of the eye on the first frame, so that the bubble's shader
		# is made then, and not when the first one is seen: a browser stops for it)
		_warmed = true
		_plunge.global_position = camera.global_position - camera.global_basis.z * 1.5
		_plunge.scale_amount_min = 0.002
		_plunge.scale_amount_max = 0.003
		_plunge.restart()
		_plunge.emitting = true
	var long := player.length
	var big := maxf(long / SALMON, 0.05)
	if absf(big - _sized) > 0.02 * _sized:
		_sized = big
		for dots in _dots:
			dots.scale_amount_min = 0.6 * big
			dots.scale_amount_max = 1.2 * big
			dots.initial_velocity_min = 1.4 * sqrt(big)
			dots.initial_velocity_max = 2.8 * sqrt(big)
			dots.emission_box_extents = Vector3(0.05, 0.03, 0.3) * big
		# (a sardine's bubbles are a couple of centimetres across; an orca's a hand's breadth)
		var bead := clampf(0.018 + long * 0.018, 0.02, 0.17)
		_trail.scale_amount_min = bead * 0.6
		_trail.scale_amount_max = bead * 1.1
		_stream.scale_amount_min = bead * 0.8
		_stream.scale_amount_max = bead * 2.0
		for p: CPUParticles3D in [_trail, _stream]:
			p.emission_box_extents = Vector3(0.12, 0.08, 0.12) * long
			p.initial_velocity_min = 0.05 * sqrt(long)
			p.initial_velocity_max = 0.3 * sqrt(long)
	var at := player.global_position
	var under := player.alive and not player.in_air and not player.caught
	var going := player.velocity.length() / maxf(Fish.pace(long), 0.01)
	# the trail, from the tail and the fins
	var tail := at - player.heading * long * 0.42
	_trail.global_position = tail
	_stream.global_position = tail
	_trail.emitting = under and going > 0.15
	_stream.emitting = under and player.boosting
	# (they leave it backwards a little, and rise)
	_trail.direction = (-player.heading + Vector3.UP * 0.6).normalized()
	_stream.direction = _trail.direction
	# spray while its back cuts the surface
	var top := Sea.surface_height(at.x, at.z)
	var cutting := under and at.y > top - maxf(long * 0.35, 0.15)
	var across := player.heading.cross(Vector3.UP).normalized()
	for dots in _dots:
		var side: float = dots.get_meta(&"side")
		dots.global_position = Vector3(at.x, top + 0.02, at.z) + across * side * 0.28 * big + player.heading * 0.35 * big
		dots.direction = (across * side * 0.55 + Vector3.UP - player.heading * 0.5).normalized()
		dots.emitting = cutting
	_churn(delta, under, going, tail, long)
	# The burst: the view widens and streaks run past (eased in quickly, out slowly).
	var burst := 1.0 if under and player.boosting else 0.0
	var hard := clampf((going - 1.0) / 0.8, 0.0, 1.0) * burst
	fov_kick = lerpf(fov_kick, FOV_KICK * burst, 1.0 - exp(-(5.0 if burst > fov_kick / FOV_KICK else 2.5) * delta))
	_streaks = lerpf(_streaks, hard, 1.0 - exp(-(6.0 if hard > _streaks else 3.0) * delta))
	if post:
		post.set_shader_parameter(&"streaks", _streaks if camera and camera.global_position.y < Sea.surface_height(camera.global_position.x, camera.global_position.z) else 0.0)


# The churned water behind the fish: every so often the place its tail is at is kept (with how
# hard it was going), and each frame the last few, as they fade, are put on the screen for the
# post shader to shimmer.
func _churn(delta: float, under: bool, going: float, tail: Vector3, long: float) -> void:
	_haze_wait -= delta
	if _haze_wait <= 0.0:
		_haze_wait = HAZE_LIFE / HAZE_POINTS
		_haze_next = (_haze_next + 1) % HAZE_POINTS
		# (none from a fish idling along; most in a burst)
		var hard := clampf((going - 0.6) / 1.2, 0.0, 1.0) if under else 0.0
		_haze_at[_haze_next] = Vector4(tail.x, tail.y, tail.z, hard)
		_haze_when[_haze_next] = _clock
	if post == null or camera == null:
		return
	var points := PackedVector4Array()
	points.resize(HAZE_POINTS)
	var seen := camera.get_viewport().get_visible_rect().size
	var wet := camera.global_position.y < Sea.surface_height(camera.global_position.x, camera.global_position.z)
	var tall := 2.0 * tan(deg_to_rad(camera.fov) * 0.5)
	for i in HAZE_POINTS:
		var h := _haze_at[i]
		var age := (_clock - _haze_when[i]) / HAZE_LIFE
		if not wet or h.w <= 0.0 or age >= 1.0:
			continue
		var p := Vector3(h.x, h.y, h.z)
		if camera.is_position_behind(p):
			continue
		var far := maxf(camera.global_position.distance_to(p), 0.3)
		var on := camera.unproject_position(p) / seen
		# (it spreads as it fades)
		var wide := (0.12 + long * 0.35) * (1.0 + age) / (far * tall)
		points[i] = Vector4(on.x, on.y, clampf(wide, 0.01, 0.35), h.w * (1.0 - age) * 0.8)
	post.set_shader_parameter(&"haze", points)


## Something was eaten there.
func eat(at: Vector3) -> void:
	var big := maxf(player.length / SALMON, 0.05)
	_meal.global_position = at
	_meal.scale_amount_min = 0.03 * big
	_meal.scale_amount_max = 0.07 * big
	_meal.initial_velocity_min = 0.6 * sqrt(big)
	_meal.initial_velocity_max = 1.8 * sqrt(big)
	_meal.restart()
	_meal.emitting = true


## It has gone through the surface there (out or in: the player is in the air when it has just
## come out). The splash is the fish's size, in proportion (never less than a sardine's can be
## seen); how hard it hits makes it taller. Where it went in, bubbles gush down after it.
func splash(at: Vector3, how_hard := 1.0) -> void:
	var long := player.length
	var size := pow(clampf(long / SALMON, 0.14, 4.0), 0.9)
	var out := player.in_air
	# (as Salmon Run 2: leaving the water is a smaller splash than landing in it; a landing is as
	# hard as it was falling, for its size)
	var falling := absf(player.velocity.y) / maxf(sqrt(9.0 * long), 0.6)
	var hard := (0.55 if out else clampf(0.6 + falling * 0.45, 0.7, 1.6)) * how_hard
	_next = (_next + 1) % _splashes.size()
	# (on the water as it is there: Sea.surface_height)
	var top := Sea.surface_height(at.x, at.z)
	_splashes[_next].start(Vector3(at.x, top, at.z), size, WATER, FOAM, hard)
	var bead := clampf(0.018 + long * 0.018, 0.02, 0.17)
	_plunge.global_position = Vector3(at.x, top - long * 0.4, at.z)
	_plunge.emission_sphere_radius = 0.25 * long + 0.05
	_plunge.scale_amount_min = bead * 0.8
	_plunge.scale_amount_max = bead * (1.9 if not out else 1.4)
	_plunge.amount = 40 if not out else 20
	var down := player.velocity.normalized() if not out else Vector3.UP
	_plunge.direction = down
	_plunge.initial_velocity_min = 0.3 * sqrt(long + 0.2)
	_plunge.initial_velocity_max = 1.6 * sqrt(long + 0.2)
	_plunge.restart()
	_plunge.emitting = true


## Bubbles (shaders/bubble.gdshader) that rise, slowing, and shrink away to nothing.
func _bubbles_of(amount: int, life: float) -> CPUParticles3D:
	var p := CPUParticles3D.new()
	p.amount = amount
	p.lifetime = life
	p.emitting = false
	p.local_coords = false
	p.top_level = true
	p.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	p.emission_box_extents = Vector3(0.05, 0.05, 0.05)
	p.direction = Vector3.UP
	p.spread = 35.0
	p.initial_velocity_min = 0.05
	p.initial_velocity_max = 0.3
	# (they float up, and the water holds them back)
	p.gravity = Vector3(0.0, 1.2, 0.0)
	p.damping_min = 0.8
	p.damping_max = 1.6
	p.scale_amount_min = 0.03
	p.scale_amount_max = 0.06
	var swell := Curve.new()
	swell.add_point(Vector2(0.0, 0.4))
	swell.add_point(Vector2(0.15, 1.0))
	swell.add_point(Vector2(0.7, 0.85))
	swell.add_point(Vector2(1.0, 0.0))
	p.scale_amount_curve = swell
	var quad := QuadMesh.new()
	quad.size = Vector2(1.0, 1.0)
	p.mesh = quad
	p.material_override = _bubble
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(p)
	return p


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
