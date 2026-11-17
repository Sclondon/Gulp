class_name Creature
extends Fish
## One of the other fish. It wanders about the sea; it flees the player when the player is big
## enough to eat it; and when it is big enough to eat the player, and the player is worth the
## trouble and in sight, it hunts: a chase it gives up after a few seconds, tired for a while.
## Life steps it and settles who eats whom.

enum Mode { WANDER, FLEE, HUNT }

## How long a chase lasts before it gives up (s), and how long it then leaves the player alone.
const CHASE := 4.0
const TIRED := 9.0
## How far off it notices the player: this many metres, and this many more for each metre it is long.
const SIGHT := 2.5
const SIGHT_PER_LENGTH := 3.0

var mode := Mode.WANDER
## Seconds until it comes back, somewhere else (it has been eaten). 0: it is about.
var away := 0.0

var _goal := Vector3.ZERO
var _goal_time := 0.0
var _speed := 0.0
var _chase := 0.0
var _tired := 0.0
var _rng := RandomNumberGenerator.new()


## Puts it somewhere, wandering.
func place(at: Vector3) -> void:
	global_position = at
	heading = Vector3(_rng.randf_range(-1.0, 1.0), 0.0, _rng.randf_range(-1.0, 1.0)).normalized()
	if heading.length() < 0.5:
		heading = Vector3.FORWARD
	mode = Mode.WANDER
	_goal_time = 0.0
	_chase = 0.0
	_tired = _rng.randf_range(0.0, 6.0)
	_speed = Fish.pace(length) * 0.5
	away = 0.0
	visible = true


## Leaves the player alone for a while (a new run has begun next to it).
func back_off() -> void:
	_tired = TIRED
	mode = Mode.WANDER


func step(delta: float, player: Player, hunting: bool) -> void:
	var to_player := player.global_position - global_position
	var far := to_player.length()
	var was := mode
	mode = Mode.WANDER
	_tired = maxf(_tired - delta, 0.0)
	if player.alive:
		if Life.can_eat(player.length, length) and far < 2.5 + player.length * 3.0:
			mode = Mode.FLEE
		elif hunting and _tired <= 0.0 and player.safe <= 0.0 and Life.can_eat(length, player.length) \
				and player.length >= length * Life.TOO_SMALL and far < SIGHT + length * SIGHT_PER_LENGTH:
			mode = Mode.HUNT
	var want := heading
	var speed := Fish.pace(length)
	match mode:
		Mode.WANDER:
			_goal_time -= delta
			if _goal_time <= 0.0 or global_position.distance_to(_goal) < 1.0 + length:
				_goal = Sea.open_water(_rng, maxf(length * 0.5, 0.3))
				_goal_time = _rng.randf_range(6.0, 14.0)
			want = (_goal - global_position).normalized()
			speed *= 0.5
			_chase = maxf(_chase - delta, 0.0)
		Mode.FLEE:
			# away from the player, and back in from the edge of the sea
			var home := -global_position * Vector3(1.0, 0.0, 1.0) / Sea.RADIUS
			want = (-to_player.normalized() + home * home.length() * 2.0).normalized()
			speed *= 1.25
		Mode.HUNT:
			if was != Mode.HUNT:
				_chase = 0.0
			_chase += delta
			if _chase > CHASE:
				_tired = TIRED
			# at where the player will be by the time it gets there
			var lead := clampf(far / maxf(speed * 1.3, 0.1), 0.0, 1.2)
			want = (player.global_position + player.velocity * lead - global_position).normalized()
			speed *= 1.25
	# (never straight up or down)
	want.y = clampf(want.y, -0.7, 0.7)
	want = want.normalized() if want.length() > 0.001 else heading
	var nimble := clampf(pow(length, -0.2), 0.6, 1.4) * (1.9 if mode != Mode.WANDER else 1.1)
	var before := heading
	heading = Fish.turned(heading, want, nimble * delta)
	_speed = lerpf(_speed, speed, 1.0 - exp(-2.5 * delta))
	velocity = heading * _speed
	var room := maxf(length * 0.3, 0.12)
	global_position = Sea.clear_of_rocks(Sea.keep_in(global_position + velocity * delta, room), room)
	var side := before.cross(heading).y
	pose(delta, _speed / Fish.pace(length), -side / maxf(nimble * delta, 0.0001))
