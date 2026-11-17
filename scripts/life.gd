class_name Life
extends Node3D
## Everything else that lives in the sea, and who eats whom.
##
## - Clouds of krill and schools of sardines: each a GameCommon Flock (one draw each).
## - The other fish, one by one (Creature): small fish, young salmon, salmon, tuna, sharks.
## - Moon jellies (MoonJelly, from Moon Jellies), drifting about and glowing.
##
## The one rule (`can_eat`): a mouth eats what is no more than `BITE` of its own length. So the
## player eats whatever is small enough when its mouth reaches it, and is eaten by whatever is
## big enough that hunts it down; a moon jelly wider than the player can eat stings it instead
## (the run ends the same). The other fish do not eat each other. What is eaten comes back a
## little later somewhere far from the player, so the sea stays stocked.

## The biggest thing a mouth can eat, as a share of its owner's length.
const BITE := 0.8
## A hunter takes no notice of a player smaller than this share of its own length.
const TOO_SMALL := 0.3
## How much food a jelly is for its size (it is mostly water), and krill and fish.
const JELLY_RICH := 0.35

## The other fish: kind, how many, and how long (from, to).
const FISH := [
	["reef", 4, 0.3, 0.45], ["reef2", 4, 0.3, 0.45], ["reef3", 4, 0.32, 0.45],
	["smolt", 7, 0.5, 0.62],
	["salmon", 6, 0.9, 1.2],
	["tuna", 4, 2.0, 2.5],
	["shark", 3, 3.4, 4.6],
]
const KRILL_CLOUDS := 6
const KRILL_EACH := 60
const KRILL_LENGTH := 0.035
const SARDINE_SCHOOLS := 4
const SARDINES_EACH := 36
const SARDINE_LENGTH := 0.2
const JELLIES := 9

var player: Player
## Off: nothing hunts (for trying things out: `-- --calm`).
var hunting := true
## How many fish are after the player just now.
var hunters := 0

var creatures: Array[Creature] = []
var jellies: Array[MoonJelly] = []
## Each: {flock, length, rich, goal, radius, low, high}.
var schools: Array[Dictionary] = []

var _rng := RandomNumberGenerator.new()
var _jelly_away: Array[float] = []
var _jelly_time: Array[float] = []


## Whether something `eater` metres long can eat something `prey` metres long.
static func can_eat(eater: float, prey: float) -> bool:
	return prey <= eater * BITE


func _ready() -> void:
	_rng.seed = 5
	for i in KRILL_CLOUDS:
		_school(_krill_rules(), _krill_mesh(), KRILL_LENGTH, Sea.SURFACE - 7.0, Sea.SURFACE - 3.0, i)
	for i in SARDINE_SCHOOLS:
		_school(_sardine_rules(), Fish.mesh_of("sardine"), SARDINE_LENGTH, 6.0, Sea.SURFACE - 6.0, 100 + i)
	for each: Array in FISH:
		for i in int(each[1]):
			var made := Creature.new()
			made._rng.seed = _rng.randi()
			add_child(made)
			made.length = _rng.randf_range(each[2], each[3])
			made.set_kind(each[0])
			made.place(Sea.open_water(_rng, made.length * 0.5))
			creatures.append(made)
	for i in JELLIES:
		var jelly := MoonJelly.new()
		# (its bell's radius: the smallest are food for the youngest fish)
		jelly.size = lerpf(0.07, 0.45, pow(float(i) / (JELLIES - 1), 1.6))
		jelly.beat_seconds = _rng.randf_range(2.0, 2.9) * (0.8 + jelly.size)
		add_child(jelly)
		jellies.append(jelly)
		_jelly_away.append(0.0)
		_jelly_time.append(0.0)
		_place_jelly(i, Sea.open_water(_rng, 1.0))


## A new run has begun at a place: whatever could hunt the player there leaves it alone a while.
func make_way(at: Vector3) -> void:
	for each in creatures:
		if each.global_position.distance_to(at) < 14.0:
			each.back_off()


func step(delta: float) -> void:
	_step_schools(delta)
	_step_creatures(delta)
	_step_jellies(delta)


## The nearest thing the player could eat just now (world), or Vector3.INF. For the bot.
func nearest_food() -> Vector3:
	var best := Vector3.INF
	var near := INF
	var at := player.global_position
	for school in schools:
		if not can_eat(player.length, school.length):
			continue
		var flock: Flock = school.flock
		if flock.global_position.distance_to(at) - float(school.radius) > near:
			continue
		var i := flock.nearest(at)
		if i >= 0:
			var far := flock.boid_position(i).distance_to(at)
			if far < near:
				near = far
				best = flock.boid_position(i)
	for each in creatures:
		if each.away <= 0.0 and can_eat(player.length, each.length):
			# (a fish that will run is worth less than one the same distance off that will not)
			var far := each.global_position.distance_to(at) * 1.5
			if far < near:
				near = far
				best = each.global_position
	for i in jellies.size():
		if _jelly_away[i] <= 0.0 and can_eat(player.length, jellies[i].size * 2.0):
			var far := jellies[i].global_position.distance_to(at)
			if far < near:
				near = far
				best = jellies[i].global_position
	return best


## Everything that could end the player's run just now: each [where, how long it is]. For the bot.
func threats() -> Array:
	var found := []
	for each in creatures:
		if each.away <= 0.0 and can_eat(each.length, player.length) and player.length >= each.length * TOO_SMALL:
			found.append([each.global_position, each.length])
	for i in jellies.size():
		if _jelly_away[i] <= 0.0 and not can_eat(player.length, jellies[i].size * 2.0):
			found.append([jellies[i].global_position, jellies[i].size * 2.0])
	return found


func _step_schools(delta: float) -> void:
	var at := player.global_position
	var mouth := player.mouth()
	for school in schools:
		var flock: Flock = school.flock
		# The school roams: its bounds drift after a place that changes now and then.
		var goal: Vector3 = school.goal
		if flock.global_position.distance_to(goal) < 2.0:
			goal = Sea.open_water(_rng, float(school.radius))
			goal.y = clampf(goal.y, float(school.low), float(school.high))
			school.goal = goal
		flock.global_position = flock.global_position.move_toward(goal, 0.35 * delta)
		if not player.alive:
			flock.predators = PackedVector3Array()
			continue
		var edible := can_eat(player.length, school.length)
		flock.predators = PackedVector3Array([at]) if edible else PackedVector3Array()
		if not edible or flock.global_position.distance_to(at) > float(school.radius) + 3.0:
			continue
		var reach := player.length * 0.3 + float(school.length) * 0.5 + 0.03
		var all := flock.positions()
		for i in all.size():
			if all[i].distance_squared_to(mouth) < reach * reach:
				player.feed(school.length, school.rich)
				# (another turns up on the far side of the school)
				var behind := (flock.global_position - at).normalized()
				flock.move_boid(i, flock.global_position + behind * float(school.radius) * 0.8)


func _step_creatures(delta: float) -> void:
	hunters = 0
	var mouth := player.mouth()
	for each in creatures:
		if each.away > 0.0:
			each.away -= delta
			if each.away <= 0.0:
				each.place(Sea.open_water(_rng, each.length * 0.5, player.global_position, 24.0))
			continue
		each.step(delta, player, hunting)
		if not player.alive:
			continue
		if each.mode == Creature.Mode.HUNT:
			hunters += 1
		if can_eat(player.length, each.length):
			if each.global_position.distance_to(mouth) < player.length * 0.3 + each.length * 0.35:
				player.feed(each.length)
				each.visible = false
				each.away = _rng.randf_range(5.0, 12.0)
		elif hunting and can_eat(each.length, player.length):
			if each.mouth().distance_to(player.global_position) < each.length * 0.22 + player.length * 0.3:
				player.die(each.kind)


func _step_jellies(delta: float) -> void:
	for i in jellies.size():
		var jelly := jellies[i]
		if _jelly_away[i] > 0.0:
			_jelly_away[i] -= delta
			if _jelly_away[i] <= 0.0:
				_place_jelly(i, Sea.open_water(_rng, 1.0, player.global_position, 24.0))
			continue
		_jelly_time[i] -= delta
		if _jelly_time[i] <= 0.0 or jelly.global_position.distance_to(jelly.goal) < 1.0:
			jelly.goal = Sea.open_water(_rng, 1.0 + jelly.size)
			_jelly_time[i] = _rng.randf_range(20.0, 40.0)
		jelly.step(delta)
		jelly.global_position = Sea.keep_in(jelly.global_position, jelly.size + 0.2)
		if not player.alive:
			continue
		var wide := jelly.size * 2.0
		if can_eat(player.length, wide):
			if jelly.global_position.distance_to(player.mouth()) < player.length * 0.3 + jelly.size * 0.8:
				player.feed(wide, JELLY_RICH)
				jelly.visible = false
				_jelly_away[i] = _rng.randf_range(8.0, 16.0)
		elif hunting and jelly.global_position.distance_to(player.global_position) < jelly.size * 0.85 + player.length * 0.25:
			player.die("jelly")


func _place_jelly(i: int, at: Vector3) -> void:
	var jelly := jellies[i]
	jelly.global_position = at
	jelly.velocity = Vector3.ZERO
	jelly.goal = at
	jelly.visible = true
	jelly.lay_arms()
	_jelly_away[i] = 0.0
	_jelly_time[i] = 0.0


func _school(rules: FlockRules, mesh: Mesh, length: float, low: float, high: float, seed_of: int) -> void:
	var flock := Flock.new()
	flock.rules = rules
	flock.custom_mesh = mesh
	flock.flock_seed = 31 + seed_of
	# (a little thinking each a frame: there are ten of them)
	flock.budget_ms = 0.4
	flock.ground_at = func(p: Vector3) -> float: return Sea.ground(p.x, p.z)
	var at := Sea.open_water(_rng, rules.bounds_size.x)
	at.y = clampf(at.y, low, high)
	flock.position = at
	add_child(flock)
	schools.append({"flock": flock, "length": length, "rich": 1.0, "goal": at, "radius": rules.bounds_size.x, "low": low, "high": high})


## Krill: a loose cloud of tiny pink shrimps that takes no notice of anything (after Salmon
## Run 2's, which are the same small box).
func _krill_rules() -> FlockRules:
	var r := FlockRules.gnats()
	r.count = KRILL_EACH
	r.body = FlockRules.Body.CUSTOM
	r.motion = FlockRules.Motion.NONE
	r.size = KRILL_LENGTH
	r.size_variation = 0.3
	r.colour = Color(1.0, 0.62, 0.56)
	r.colour_variation = 0.1
	r.max_speed = 0.5
	r.min_speed = 0.05
	r.cruise_speed = 0.22
	r.max_force = 2.0
	r.perception = 0.5
	r.separation_distance = 0.15
	r.wander = 1.5
	r.wander_rate = 3.0
	r.bounds_size = Vector3(2.4, 2.4, 2.4)
	r.bounds_margin = 1.0
	r.ground_clearance = 0.5
	r.seek = 0.3
	r.arrive_radius = 1.5
	r.flee = 0.0
	r.wind_carry = 0.0
	return r


func _krill_mesh() -> Mesh:
	var box := BoxMesh.new()
	box.size = Vector3(0.24, 0.24, 1.0)
	return box


## Sardines: a tight school that bolts from the player once the player can eat them, a little
## slower than a young salmon in a hurry.
func _sardine_rules() -> FlockRules:
	var r := FlockRules.fish_school()
	r.count = SARDINES_EACH
	r.body = FlockRules.Body.CUSTOM
	r.size = SARDINE_LENGTH / 1.1
	r.colour = Color(1.0, 1.0, 1.0)
	r.colour_variation = 0.08
	r.max_speed = 2.3
	r.min_speed = 0.6
	r.cruise_speed = 1.3
	r.max_force = 5.0
	r.bounds_size = Vector3(4.5, 4.5, 4.5)
	r.bounds_margin = 2.0
	r.flee_radius = 3.0
	r.panic_speed = 1.4
	return r
