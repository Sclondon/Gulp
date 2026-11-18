class_name Life
extends Node3D
## Everything else that lives in the sea, and who eats whom.
##
## - Clouds of krill and schools of sardines: each a GameCommon Flock (one draw each).
## - The other swimmers, one by one (Creature): loaches, trout, flying fish, young salmon,
##   catfish, salmon, moray eels, tuna, Humboldt squid, sailfish, swordfish, sharks and one
##   giant squid, each keeping to its own depth.
## - Moon jellies (MoonJelly, from Moon Jellies), drifting about and glowing.
## - Sea nettles (SeaNettle), bigger, trailing long strands that sting.
##
## The one rule (`can_eat`): a mouth eats what is no more than `BITE` of its own length. So the
## player eats whatever is small enough (and not too small to bother with: `WORTH`) when its
## mouth reaches it, and is eaten by whatever is
## big enough that hunts it down; a moon jelly wider than the player can eat stings it instead
## (the run ends the same). The other fish do not eat each other. What is eaten comes back a
## little later somewhere far from the player, so the sea stays stocked.

## The biggest thing a mouth can eat, as a share of its owner's length.
const BITE := 0.8
## A hunter takes no notice of a player smaller than this share of its own length.
const TOO_SMALL := 0.3
## The player takes no notice of food smaller than this share of its own length (a shark does not
## graze on krill).
const WORTH := 0.08
## How much food a jelly is for its size (it is mostly water), and krill and fish.
const JELLY_RICH := 0.35

const KRILL_CLOUDS := 6
const KRILL_EACH := 60
const KRILL_LENGTH := 0.035
const SARDINE_SCHOOLS := 4
const SARDINES_EACH := 36
const SARDINE_LENGTH := 0.2
const JELLIES := 9
## Sea nettles: how many, how big beside the creature as built (its bell 1.8 m across, its strands
## 5 m), and how long one counts as for the eating rule.
const NETTLES := 2
const NETTLE_SIZE := 0.45
const NETTLE_LENGTH := 1.6
## How far off a school of sardines, a cloud of krill and a jelly are still moved and drawn (m).
const SARDINES_SEEN := 32.0
const KRILL_SEEN := 18.0
const JELLY_SEEN := 32.0
const FISH_SEEN := 55.0

var player: Player
## Off: nothing hunts (for trying things out: `-- --calm`).
var hunting := true
## How many fish are after the player just now.
var hunters := 0

## What it has cost so far, to be divided by `steps`: microseconds in the schools' eating and
## roaming, the fish, and the jellies; and milliseconds the flocks spent on themselves.
var cost_usec := Vector3.ZERO
var flock_ms := 0.0
var steps := 0

var creatures: Array[Creature] = []
var jellies: Array[MoonJelly] = []
var nettles: Array[SeaNettle] = []
## Each: {flock, length, rich, goal, radius, low, high, seen}.
var schools: Array[Dictionary] = []

var _rng := RandomNumberGenerator.new()
var _jelly_away: Array[float] = []
var _jelly_time: Array[float] = []
var _nettle_away: Array[float] = []
var _nettle_goal: Array[Vector3] = []


## Whether something `eater` metres long can eat something `prey` metres long.
static func can_eat(eater: float, prey: float) -> bool:
	return prey <= eater * BITE


## Whether something `prey` metres long is food for a player `eater` metres long: small enough
## to eat, and big enough to be worth it.
static func is_food(eater: float, prey: float) -> bool:
	return prey <= eater * BITE and prey >= eater * WORTH


func _ready() -> void:
	_rng.seed = 5
	for i in KRILL_CLOUDS:
		_school(_krill_rules(), _krill_mesh(), KRILL_LENGTH, "", 0.55, 0.92, i)
	for i in SARDINE_SCHOOLS:
		_school(_sardine_rules(), Fish.school_mesh(), SARDINE_LENGTH, "open" if i % 2 == 0 else "kelp", 0.4, 0.85, 100 + i)
	if Species.has("mackerel"):
		for i in 2:
			var rules := _sardine_rules()
			rules.size = 0.4 / 0.4
			rules.count = 24
			rules.max_speed = 3.0
			rules.cruise_speed = 1.7
			rules.bounds_size = Vector3(6.0, 5.0, 6.0)
			_school(rules, Fish.school_mesh("pacific_mackerel"), 0.4, "open", 0.5, 0.9, 200 + i)
	# Every kind Species has, where its creature is installed.
	for kind: String in Species.ALL:
		var entry := Species.of(kind)
		if int(entry.count) == 0 or not Species.has(kind):
			continue
		for i in int(entry.count):
			var made := Creature.new()
			made._rng.seed = _rng.randi()
			add_child(made)
			made.length = _rng.randf_range(entry.size[0], entry.size[1])
			made.become(kind)
			made.place(made.somewhere())
			creatures.append(made)
	for i in JELLIES:
		var jelly := MoonJelly.new()
		# (its bell's radius: the smallest are food for the youngest fish)
		jelly.size = lerpf(0.07, 0.45, pow(float(i) / (JELLIES - 1), 1.6))
		jelly.beat_seconds = _rng.randf_range(2.0, 2.9) * (0.8 + jelly.size)
		# (brighter than in Moon Jellies: this water is lighter)
		jelly.glow = 1.7
		add_child(jelly)
		jellies.append(jelly)
		_jelly_away.append(0.0)
		_jelly_time.append(0.0)
		_place_jelly(i, Sea.place(_rng, "open" if i % 2 == 0 else "sand", 1.0))
	for i in NETTLES:
		var nettle := SeaNettle.new()
		nettle.scale = Vector3.ONE * NETTLE_SIZE
		# (the game has no sound yet: its own is kept all but silent)
		nettle.volume_db = -80.0
		nettle.glow = 0.35
		add_child(nettle)
		nettles.append(nettle)
		_nettle_away.append(0.0)
		_nettle_goal.append(Vector3.ZERO)
		_place_nettle(i, Sea.place(_rng, "open", 3.0))


## A new run has begun at a place: whatever could hunt the player there leaves it alone a while.
func make_way(at: Vector3) -> void:
	for each in creatures:
		if each.global_position.distance_to(at) < 14.0:
			each.back_off()


func step(delta: float) -> void:
	var t0 := Time.get_ticks_usec()
	_step_schools(delta)
	var t1 := Time.get_ticks_usec()
	_step_creatures(delta)
	var t2 := Time.get_ticks_usec()
	_step_jellies(delta)
	_step_nettles(delta)
	cost_usec += Vector3(t1 - t0, t2 - t1, Time.get_ticks_usec() - t2)
	for school in schools:
		if (school.flock as Flock).visible:
			flock_ms += (school.flock as Flock).sim_ms
	steps += 1


## The nearest thing the player could eat just now (world), or Vector3.INF. For the bot.
func nearest_food() -> Vector3:
	var best := Vector3.INF
	var near := INF
	var at := player.global_position
	for school in schools:
		if not is_food(player.length, school.length):
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
		if each.away <= 0.0 and not each.giant and is_food(player.length, each.length):
			# (a fish that will run is worth less than one the same distance off that will not)
			var far := each.global_position.distance_to(at) * 1.5
			if far < near:
				near = far
				best = each.global_position
	for i in jellies.size():
		if _jelly_away[i] <= 0.0 and is_food(player.length, jellies[i].size * 2.0):
			var far := jellies[i].global_position.distance_to(at)
			if far < near:
				near = far
				best = jellies[i].global_position
	return best


## Everything that could end the player's run just now: each [where, how long it is]. For the bot.
func threats() -> Array:
	var found := []
	for each in creatures:
		if each.away <= 0.0 and each.hunts and can_eat(each.length, player.length) and player.length >= each.length * TOO_SMALL:
			found.append([each.global_position, each.length])
	for i in jellies.size():
		if _jelly_away[i] <= 0.0 and not can_eat(player.length, jellies[i].size * 2.0):
			found.append([jellies[i].global_position, jellies[i].size * 2.0])
	for i in nettles.size():
		if _nettle_away[i] <= 0.0 and not can_eat(player.length, NETTLE_LENGTH):
			# (its strands hang under it)
			found.append([nettles[i].global_position + Vector3.DOWN * 0.8, 3.0])
	return found


func _step_schools(delta: float) -> void:
	var at := player.global_position
	var mouth := player.mouth()
	for school in schools:
		var flock: Flock = school.flock
		# Too far off to be seen through the water, it is left as it is: not moved, not drawn.
		var seen := flock.global_position.distance_to(at) < float(school.seen)
		if seen != flock.visible:
			flock.visible = seen
			flock.set_process(seen)
		if not seen:
			continue
		# The school roams: its bounds drift after a place that changes now and then.
		var goal: Vector3 = school.goal
		if flock.global_position.distance_to(goal) < 2.0:
			goal = _school_place(school.zone, float(school.radius), float(school.low), float(school.high))
			school.goal = goal
		flock.global_position = flock.global_position.move_toward(goal, 0.35 * delta)
		if not player.alive:
			flock.predators = PackedVector3Array()
			continue
		var edible := is_food(player.length, school.length)
		flock.predators = PackedVector3Array([at]) if edible else PackedVector3Array()
		if not edible or flock.global_position.distance_to(at) > float(school.radius) + 3.0:
			continue
		var reach := player.length * 0.3 + float(school.length) * 0.5 + 0.03
		var all := flock.positions()
		for i in all.size():
			if all[i].distance_squared_to(mouth) < reach * reach:
				player.feed(school.length, school.rich)
				# (another comes in from beyond the far side of the school, out of reach)
				var behind := (flock.global_position - at).normalized()
				flock.move_boid(i, flock.global_position + behind * (float(school.radius) + reach + 2.0))


func _step_creatures(delta: float) -> void:
	hunters = 0
	var mouth := player.mouth()
	for each in creatures:
		if each.away > 0.0:
			each.away -= delta
			if each.away <= 0.0:
				each.place(each.somewhere(player.global_position, 24.0))
			continue
		var apart := each.global_position.distance_to(player.global_position)
		# Too far off to be seen through the water: not drawn, and moved only now and then.
		var seen := apart < FISH_SEEN + each.length * 2.0
		if each.visible != seen:
			each.visible = seen
		if not seen:
			if (steps + each.get_index()) % 8 != 0:
				continue
			each.step(delta * 8.0, player, hunting)
			continue
		each.step(delta, player, hunting)
		each.detail(apart < 5.0 + each.length * 4.0)
		if not player.alive:
			continue
		if each.mode == Creature.Mode.HUNT:
			hunters += 1
		if each.giant:
			continue
		if is_food(player.length, each.length):
			if each.global_position.distance_to(mouth) < player.length * 0.3 + each.length * 0.35:
				player.feed(each.length)
				each.visible = false
				each.away = _rng.randf_range(5.0, 12.0)
		elif hunting and each.hunts and not player.in_air and can_eat(each.length, player.length):
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
		# (too far off to be seen beating, it hangs where it is)
		if jelly.global_position.distance_to(player.global_position) > JELLY_SEEN:
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
		if is_food(player.length, wide):
			if jelly.global_position.distance_to(player.mouth()) < player.length * 0.3 + jelly.size * 0.8:
				player.feed(wide, JELLY_RICH)
				jelly.visible = false
				_jelly_away[i] = _rng.randf_range(8.0, 16.0)
		elif hunting and not can_eat(player.length, wide) and jelly.global_position.distance_to(player.global_position) < jelly.size * 0.85 + player.length * 0.25:
			player.die("jelly")


## The nettles drift from place to place, a push with each beat of the bell. Their strands sting
## whatever cannot eat them; what can, eats one by reaching its bell.
func _step_nettles(delta: float) -> void:
	for i in nettles.size():
		var nettle := nettles[i]
		if _nettle_away[i] > 0.0:
			_nettle_away[i] -= delta
			if _nettle_away[i] <= 0.0:
				_place_nettle(i, Sea.place(_rng, "open", 3.0, player.global_position, 24.0))
			continue
		var far := nettle.global_position.distance_to(player.global_position)
		if far > JELLY_SEEN:
			continue
		if nettle.global_position.distance_to(_nettle_goal[i]) < 1.5:
			_nettle_goal[i] = _nettle_place(Sea.place(_rng, "open", 3.0))
		var way := (_nettle_goal[i] - nettle.global_position).normalized()
		nettle.global_position += way * (0.12 + 0.5 * nettle.thrust) * delta
		nettle.step(Vector3.ZERO, delta)
		if not player.alive or far > 8.0:
			continue
		if is_food(player.length, NETTLE_LENGTH):
			if nettle.global_position.distance_to(player.mouth()) < player.length * 0.3 + SeaNettle.RADIUS * NETTLE_SIZE:
				player.feed(NETTLE_LENGTH, JELLY_RICH)
				nettle.visible = false
				_nettle_away[i] = _rng.randf_range(12.0, 20.0)
		elif hunting and not can_eat(player.length, NETTLE_LENGTH):
			var half := player.heading * player.length * 0.4
			var bell := far < SeaNettle.RADIUS * NETTLE_SIZE + player.length * 0.25
			if bell or nettle.touches(player.global_position - half, player.global_position + half, player.length * 0.12):
				nettle.sting(player.global_position)
				player.die("nettle")


## A place for a nettle: high enough that its strands hang clear of the floor.
func _nettle_place(at: Vector3) -> Vector3:
	at.y = maxf(at.y, Sea.ground(at.x, at.z) + SeaNettle.TENTACLE_LONG * NETTLE_SIZE + 0.5)
	return Sea.keep_in(at, 1.0)


func _place_nettle(i: int, at: Vector3) -> void:
	var nettle := nettles[i]
	nettle.global_position = _nettle_place(at)
	nettle.visible = true
	nettle.lay_ropes()
	_nettle_away[i] = 0.0
	_nettle_goal[i] = nettle.global_position


func _place_jelly(i: int, at: Vector3) -> void:
	var jelly := jellies[i]
	jelly.global_position = at
	jelly.velocity = Vector3.ZERO
	jelly.goal = at
	jelly.visible = true
	jelly.lay_arms()
	_jelly_away[i] = 0.0
	_jelly_time[i] = 0.0


## A place for a school in a zone, between two depths (0 the floor, 1 the surface).
func _school_place(zone: String, room: float, low: float, high: float) -> Vector3:
	var at := Sea.place(_rng, zone, room)
	var floor_at := Sea.ground(at.x, at.z) + room
	at.y = lerpf(floor_at, maxf(floor_at, Sea.SURFACE - room), _rng.randf_range(low, high))
	return at


func _school(rules: FlockRules, mesh: Mesh, length: float, zone: String, low: float, high: float, seed_of: int) -> void:
	var flock := Flock.new()
	flock.rules = rules
	flock.custom_mesh = mesh
	flock.flock_seed = 31 + seed_of
	# (a little thinking each a frame: there are ten of them)
	flock.budget_ms = 0.4
	flock.ground_at = func(p: Vector3) -> float: return Sea.ground(p.x, p.z)
	var at := _school_place(zone, rules.bounds_size.x, low, high)
	flock.position = at
	add_child(flock)
	schools.append({"flock": flock, "length": length, "rich": 1.0, "goal": at, "zone": zone, "radius": rules.bounds_size.x, "low": low, "high": high,
			"seen": KRILL_SEEN if length < 0.1 else SARDINES_SEEN})


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
	# (the school mesh is life size, and brings its own colours)
	r.size = SARDINE_LENGTH / Sardine.LENGTH
	r.colour = Color(1.0, 1.0, 1.0)
	r.colour_variation = 0.0
	r.max_speed = 2.3
	r.min_speed = 0.6
	r.cruise_speed = 1.3
	r.max_force = 5.0
	r.bounds_size = Vector3(4.5, 4.5, 4.5)
	r.bounds_margin = 2.0
	r.flee_radius = 3.0
	r.panic_speed = 1.4
	return r
