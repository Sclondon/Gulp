class_name Creature
extends Fish
## One of the other animals. It wanders about its own part of the sea at its own depth; it flees
## the player when the player is big enough to eat it; and when it is big enough to eat the
## player, and the player is worth the trouble and in sight, it hunts: a chase it gives up after
## a few seconds, tired for a while. Life steps it and settles who eats whom.
##
## Species says how each kind lives: `how` "floor" keeps it on or just over the bottom, "giant"
## has it cruise and take no notice of anything; `hunts` off, it never goes for the player.

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
## Where it lives (Sea.ZONES names; none: anywhere) and the depth it keeps to when it wanders:
## from and to, 0 the floor, 1 the surface.
var zones: Array = []
var band := Vector2(0.0, 1.0)
## It keeps to the bottom; it is a giant (see above); it goes for the player.
var on_floor := false
var giant := false
## How fast it goes beside a fish of its length (Species: a starfish creeps, a sea lily stays).
var slow := 1.0
## It has its model (see `become`).
var dressed := true
var hunts := true

var _goal := Vector3.ZERO
var _goal_time := 0.0
var _speed := 0.0
var _chase := 0.0
var _tired := 0.0
var _rng := RandomNumberGenerator.new()


## Makes it one of a kind, as Species has it. With `bare`, it is not given its model yet (`dress`
## does that, when it is first near enough to be seen): making every kind's model and shader at once
## froze a browser for minutes at the start (each shader is compiled when first made).
func become(of_kind: String, bare := false) -> void:
	var entry := Species.of(of_kind)
	zones = entry.get("zones", [])
	var depth: Array = entry.get("band", [0.0, 1.0])
	band = Vector2(depth[0], depth[1])
	on_floor = entry.get("how", "swim") == "floor"
	giant = entry.get("how", "swim") == "giant"
	slow = float(entry.get("slow", 1.0))
	hunts = bool(entry.get("hunts", true)) and not giant
	if bare:
		kind = of_kind
		dressed = false
		if _body == null:
			_body = Node3D.new()
			add_child(_body)
		return
	dress(of_kind)


## Gives it its model (see `become`).
func dress(of_kind := "") -> void:
	dressed = true
	set_kind(of_kind if of_kind != "" else kind)
	# (each koi, guppy or other patterned fish its own pattern)
	if _look and &"pattern_seed" in _look:
		_look.set(&"pattern_seed", _rng.randi() % 1000)


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


## A place in the water where it lives, at its own depth, no nearer than `apart` to `from` if
## that can be had.
func somewhere(from := Vector3.INF, apart := 0.0) -> Vector3:
	var room := maxf(length * 0.5, 0.3)
	var zone: String = zones[_rng.randi() % zones.size()] if not zones.is_empty() else ""
	var p := Sea.place(_rng, zone, room, from, apart)
	var low := _floor_at(p.x, p.z)
	p.y = lerpf(low, maxf(low, Sea.SURFACE - maxf(length * 0.3, 0.6)), _rng.randf_range(band.x, band.y))
	return Sea.clear_of_rocks(p, room)


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
	if player.alive and not giant:
		if Life.is_food(player.length, length) and far < 2.5 + player.length * 3.0:
			mode = Mode.FLEE
		elif hunting and hunts and _tired <= 0.0 and player.safe <= 0.0 and not player.in_air and Life.can_eat(length, player.length) \
				and player.length >= length * Life.TOO_SMALL and far < SIGHT + length * SIGHT_PER_LENGTH:
			mode = Mode.HUNT
	var want := heading
	var speed := Fish.pace(length) * slow
	bite = 0.0
	match mode:
		Mode.WANDER:
			_goal_time -= delta
			if _goal_time <= 0.0 or global_position.distance_to(_goal) < 1.0 + length:
				_goal = somewhere()
				_goal_time = _rng.randf_range(6.0, 14.0) * (3.0 if giant else 1.0)
			want = (_goal - global_position).normalized()
			speed *= 0.3 if giant or on_floor else 0.5
			_chase = maxf(_chase - delta, 0.0)
		Mode.FLEE:
			# away from the player, and back towards where it lives
			var home := (_home() - global_position) * Vector3(1.0, 0.0, 1.0) / 60.0
			want = (-to_player.normalized() + home * home.length() * 2.0).normalized()
			speed *= 1.25
		Mode.HUNT:
			if was != Mode.HUNT:
				_chase = 0.0
				# (a Humboldt squid flashes white as it goes for something)
				if _look and _look.has_method(&"flash"):
					_look.call(&"flash")
			_chase += delta
			if _chase > CHASE:
				_tired = TIRED
			# at where the player will be by the time it gets there
			var lead := clampf(far / maxf(speed * 1.3, 0.1), 0.0, 1.2)
			want = (player.global_position + player.velocity * lead - global_position).normalized()
			speed *= 1.25
			# (its mouth opens as it closes in)
			bite = 1.0 if far < length * 1.5 + 1.0 else 0.0
	# (never straight up or down)
	want.y = clampf(want.y, -0.7, 0.7)
	if on_floor and mode != Mode.HUNT:
		want.y = clampf((_floor_at(global_position.x, global_position.z) - global_position.y) * 2.0, -0.7, 0.3)
	want = want.normalized() if want.length() > 0.001 else heading
	var nimble := clampf(pow(length, -0.2), 0.3, 1.4) * (1.9 if mode != Mode.WANDER else 1.1)
	var before := heading
	heading = Fish.turned(heading, want, nimble * delta)
	_speed = lerpf(_speed, speed, 1.0 - exp(-2.5 * delta))
	velocity = heading * _speed
	var room := maxf(length * 0.3, 0.12)
	if on_floor:
		room = minf(room, 0.1)
	global_position = Sea.clear_of_rocks(Sea.keep_in(global_position + velocity * delta, room), room)
	var side := before.cross(heading).y
	pose(delta, _speed / Fish.pace(length), -side / maxf(nimble * delta, 0.0001))


# The lowest it goes at a place: the floor, and room for itself over it.
func _floor_at(x: float, z: float) -> float:
	return Sea.ground(x, z) + (0.03 if on_floor else maxf(length * 0.3, 0.3))


# The middle of where it lives.
func _home() -> Vector3:
	if zones.is_empty():
		return Vector3(0.0, global_position.y, 0.0)
	var at: Vector2 = Sea.ZONES[zones[0]].at
	return Vector3(at.x, global_position.y, at.y)
