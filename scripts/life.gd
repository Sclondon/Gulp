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
## How far a mouth reaches round its point, as a share of its owner's length, measured to the
## nearest of the other's body (`Fish.gap_to`): the player's mouth (`TAKES`, and `TAKES_LEAST` metres
## more for the smallest: a little suction) and a hunter's (`JAWS`: a hunter's mouth must be on the
## player, as drawn). tools/QUALITY.md: they were 0.3 of the player's length plus 0.35 of the other's,
## and 0.22 of a hunter's length plus 0.3 of the player's, from the middles, so that a big shark's mouth
## could take a sardine a metre off and a fish crossing ahead was eaten by its middle.
const TAKES := 0.2
const TAKES_LEAST := 0.03
const JAWS := 0.1
## What is this many times the player's length (and cannot be eaten) is solid to it; its body is a
## rounded rod `BODY` of its length thick (the whales, the leviathan and the submarine are drawn
## 0.2 to 0.3 of their length across, not counting fins: tests/hitboxes.gd).
const SOLID := 1.5
const BODY := 0.11
## How much food a jelly is for its size (it is mostly water), and krill and fish.
const JELLY_RICH := 0.35

const KRILL_CLOUDS := 6
const KRILL_EACH := 60
const KRILL_LENGTH := 0.035
const SARDINE_SCHOOLS := 4
const SARDINES_EACH := 36
const SARDINE_LENGTH := 0.2
const JELLIES := 9
const KRILL := "res://creatures/krill/krill.gd"
const PLANKTON := "res://creatures/plankton/plankton_cloud.gd"
## Clouds of plankton: how many, how many specks in each, how wide (m), and how long a speck counts
## as (m). Only a small fish feeds on them (`PLANKTON_EATER`: no longer than this).
const PLANKTON_CLOUDS := 8
const PLANKTON_SPECKS := 260
const PLANKTON_RADIUS := 2.6
const PLANKTON_LENGTH := 0.012
const PLANKTON_EATER := 0.45
## Sea nettles: how many, how big beside the creature as built (its bell 1.8 m across, its strands
## 5 m), and how long one counts as for the eating rule.
const NETTLES := 2
const NETTLE_SIZE := 0.45
const NETTLE_LENGTH := 1.6
## How far off a school of sardines, a cloud of krill and a jelly are still moved and drawn (m).
const SARDINES_SEEN := 32.0
const KRILL_SEEN := 18.0
const JELLY_SEEN := 32.0
## Beyond this a jelly is not drawn (m).
const JELLY_DRAWN := 48.0
## (the fog leaves a quarter of a thing's colour at 40 m and a fifth at 45: 55 m drew a third more
## animals than this at the reef, each one stepped every frame or two)
const FISH_SEEN := 45.0
## Nearer than this (m, and two of its own lengths more) a fish is stepped every frame; further,
## every other frame; beyond STEP_MID every third.
const STEP_NEAR := 20.0
const STEP_MID := 32.0
## How many steps apart kinds new to the run are given their models.
const NEW_EVERY := 3
## Only the animals near the player live (CLAUDE.md, "Decision: only nearby animals are awake"):
## within WAKE metres (less two of its lengths) an animal, or the group it keeps with, wakes; beyond
## SLEEP it sleeps where it is: hidden, not stepped, its model given back. Each animal (or group)
## is looked at once every WAKE_EVERY frames.
const WAKE := 55.0
const SLEEP := 65.0
const WAKE_EVERY := 10
## The most animals given their models in one frame (each makes a creature's nodes: a hitch on a phone).
const DRESS_EACH := 2
## On a phone (Tier.phone(): CLAUDE.md, "Decision: a phone tier") the bubble is smaller and the far
## ones are stepped less: what is drawn and stepped are most of a phone frame. Fog leaves a quarter
## of a thing at 38 m. [FISH_SEEN, STEP_NEAR, STEP_MID, WAKE, SLEEP, DRESS_EACH] there.
const PHONE := [38.0, 14.0, 24.0, 48.0, 58.0, 1]
var fish_seen := FISH_SEEN
var step_near := STEP_NEAR
var step_mid := STEP_MID
var wake_at := WAKE
var sleep_at := SLEEP
var dress_each := DRESS_EACH
## The swarms (tools/SCHOOLING.md): each a Flock of a few dozen guides that are not drawn, with
## riders round each one, all drawn by one MultiMesh and placed by its shader, so the CPU pays for
## the guides only. Each: [guides, riders round each, how far round its guide a rider keeps (m)].
const KRILL_SWARM := [16, 18, 0.45]
## The first school of sardines is a bait ball of 1,600 in the open water; the others 640 each.
const SARDINE_BALL := [40, 40, 0.75]
const SARDINE_SWARM := [32, 20, 0.7]
const ANCHOVY_SWARM := [28, 16, 0.5]
const LANTERN_SWARM := [24, 14, 0.6]
const MACKEREL_SWARM := [20, 8, 0.9]
## A swarm draws all its riders nearer than the first of these (m), 60% of them nearer than the
## second, and 35% beyond (thinned evenly).
const SWARM_NEAR := Vector2(12.0, 22.0)
## Cleaning stations on the reef.
const STATIONS := 3
## Seconds between two fish the player takes from a swarm.
const GULP := 0.12

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
## Those of `creatures` that are awake (near the player): the only ones stepped, drawn or looked at.
var awake: Array[Creature] = []
# What wakes and sleeps together: each a Creature.Group or a Creature that keeps to itself.
var _units: Array = []
var jellies: Array[MoonJelly] = []
var nettles: Array[SeaNettle] = []
var plankton: Array[Node3D] = []
## Each: {flock, length, rich, goal, radius, low, high, seen, swarm (it has riders), mid (its
## middle, swarms only), gather (its rules' own), hunters (where the hunters at it are: they make it
## ball up, and it flees them)}.
var schools: Array[Dictionary] = []
## The groups the creatures keep together in (Creature.Group).
var groups: Array = []
## The cleaning stations on the reef, and the fish being cleaned at each (or null).
var stations: Array[Vector3] = []
var station_client: Array = []
## How many times a lionfish has stung the player this run (for the tests).
var stings := 0

const DAY := "res://scripts/day.gd"
static var _day: GDScript
static var _day_looked := false
static var _night := 0.0
static var _night_read := -100000

# Each station's cleaners.
var _cleaners: Array = []
var _gulp := 0.0

var _rng := RandomNumberGenerator.new()
# The kinds that have been given their models this run, and the step at which another new kind
# may be (see _step_creatures).
var _dressed := {}
var _next_new := 0
var _jelly_away: Array[float] = []
var _jelly_time: Array[float] = []
var _nettle_away: Array[float] = []
var _nettle_goal: Array[Vector3] = []
var _checked_at := Vector3.INF


## Whether something `eater` metres long can eat something `prey` metres long.
static func can_eat(eater: float, prey: float) -> bool:
	return prey <= eater * BITE


## Whether something `prey` metres long is food for a player `eater` metres long: small enough
## to eat, and big enough to be worth it.
static func is_food(eater: float, prey: float) -> bool:
	return prey <= eater * BITE and prey >= eater * WORTH


func _ready() -> void:
	_rng.seed = 5
	if Tier.phone():
		fish_seen = PHONE[0]
		step_near = PHONE[1]
		step_mid = PHONE[2]
		wake_at = PHONE[3]
		sleep_at = PHONE[4]
		dress_each = PHONE[5]
	for i in KRILL_CLOUDS:
		_school(_swarm_rules(_krill_rules(), KRILL_SWARM), _krill_mesh(), KRILL_LENGTH, Layout.school_zone("krill", i), 0.55, 0.92, i)
		if i == 0:
			# (this one, and the first school of anchovies, keep near where a run starts: `keep_home`)
			schools[-1].home = Vector3.INF
	for i in SARDINE_SCHOOLS:
		_school(_swarm_rules(_sardine_rules(), SARDINE_BALL if i == 0 else SARDINE_SWARM), Fish.school_mesh(), SARDINE_LENGTH,
				Layout.school_zone("sardines", i), 0.4, 0.85, 100 + i)
	if ResourceLoader.exists("res://creatures/anchovy/anchovy.gd"):
		for i in 3:
			var rules := _sardine_rules()
			rules.size = 1.0
			# (slow enough in a fright that the smallest fish can run one down)
			rules.max_speed = 1.3
			rules.cruise_speed = 0.9
			_school(_swarm_rules(rules, ANCHOVY_SWARM), Fish.school_mesh("anchovy"), 0.14, Layout.school_zone("anchovies", i), 0.4, 0.85, 300 + i)
			if i == 0:
				schools[-1].home = Vector3.INF
	if Species.has("piranha"):
		var pack := _sardine_rules()
		pack.size = 1.0
		pack.count = 22
		pack.bounds_size = Vector3(3.0, 2.0, 3.0)
		_school(pack, Fish.school_mesh("piranha"), 0.3, Layout.school_zone("piranhas", 0), 0.3, 0.8, 400)
	if ResourceLoader.exists("res://creatures/lanternfish/lanternfish.gd"):
		for i in 2:
			var lights := _sardine_rules()
			lights.size = 2.0
			_school(_swarm_rules(lights, LANTERN_SWARM), Fish.school_mesh("lanternfish"), 0.16, Layout.school_zone("lanternfish", i), 0.1, 0.6, 500 + i)
			schools[-1].nocturnal = true
	if ResourceLoader.exists("res://creatures/neon_tetra/neon_tetra.gd"):
		var neons := _sardine_rules()
		# (three times life size: a neon tetra is 3.5 cm)
		neons.size = 3.0
		neons.count = 36
		neons.max_speed = 1.4
		neons.cruise_speed = 0.8
		neons.bounds_size = Vector3(2.5, 1.6, 2.5)
		_school(neons, Fish.school_mesh("neon_tetra"), 0.1, Layout.school_zone("neons", 0), 0.3, 0.8, 600)
	if ResourceLoader.exists("res://creatures/zebra_danio/zebra_danio.gd"):
		var danios := _sardine_rules()
		# (twice life size: a zebra danio is 4.5 cm)
		danios.size = 2.0
		danios.count = 26
		danios.max_speed = 1.6
		danios.cruise_speed = 0.9
		danios.bounds_size = Vector3(2.5, 1.6, 2.5)
		_school(danios, Fish.school_mesh("zebra_danio"), 0.09, Layout.school_zone("danios", 0), 0.4, 0.9, 700)
	if Species.has("mackerel"):
		for i in 2:
			var rules := _sardine_rules()
			rules.size = 0.4 / 0.4
			rules.max_speed = 3.0
			rules.cruise_speed = 1.7
			_school(_swarm_rules(rules, MACKEREL_SWARM), Fish.school_mesh("pacific_mackerel"), 0.4, Layout.school_zone("mackerel", i), 0.5, 0.9, 200 + i)
	if ResourceLoader.exists(PLANKTON):
		for i in PLANKTON_CLOUDS:
			var cloud: Node3D = (load(PLANKTON) as GDScript).new()
			add_child(cloud)
			cloud.global_position = _school_place(Layout.school_zone("plankton", i), PLANKTON_RADIUS, 0.4, 0.9)
			cloud.call(&"fill", Vector3.ZERO, PLANKTON_RADIUS, PLANKTON_SPECKS)
			plankton.append(cloud)
	# Every kind Species has, where its creature is installed; those that keep together are put
	# in groups of their own kind, or of every kind with the same `mix`.
	var pools := {}
	for kind: String in Species.ALL:
		var entry := Species.of(kind)
		if int(entry.count) == 0 or not Species.has(kind) or entry.get("monster", false):
			continue
		for i in int(entry.count):
			var made := Creature.new()
			made._rng.seed = _rng.randi()
			add_child(made)
			made.length = _rng.randf_range(entry.size[0], entry.size[1])
			made.become(kind, true)
			made.visible = false
			made.place(made.somewhere())
			creatures.append(made)
			if entry.get("social", "solo") != "solo":
				var key: String = entry.get("mix", kind)
				if not pools.has(key):
					pools[key] = []
				pools[key].append(made)
	for key: String in pools:
		_make_groups(pools[key])
	_make_stations()
	for each in creatures:
		each.asleep = true
		if each.group == null:
			_units.append(each)
	_units.append_array(groups)
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
		_place_jelly(i, Sea.place(_rng, Layout.school_zone("jellies", i), 1.0))
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
		_place_nettle(i, Sea.place(_rng, Layout.school_zone("nettles", i), 3.0))


## A kind's model has already been shown once (Main's warm-up behind the title): it need not wait
## its turn when it is first seen.
func mark_dressed(kind: String) -> void:
	_dressed[kind] = true


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
	_step_solids()
	var t2 := Time.get_ticks_usec()
	_step_jellies(delta)
	_step_nettles(delta)
	_step_plankton()
	cost_usec += Vector3(t1 - t0, t2 - t1, Time.get_ticks_usec() - t2)
	for school in schools:
		if (school.flock as Flock).visible:
			flock_ms += (school.flock as Flock).sim_ms
	steps += 1


## The nearest thing the player could eat just now (world), or Vector3.INF. For the bot.
func nearest_food(only_schools := false) -> Vector3:
	var best := Vector3.INF
	var near := INF
	var at := player.global_position
	for school in schools:
		if not is_food(player.length, school.length):
			continue
		# (given up on what runs: only what drifts, the krill)
		if only_schools and float(school.length) > 0.06:
			continue
		var flock: Flock = school.flock
		if flock.global_position.distance_to(at) - float(school.radius) > near:
			continue
		if not flock.visible:
			# (too far off to be moved or drawn: its fish are wherever they were left, so make for
			# the school itself, and count it further off than anything in sight)
			var off := flock.global_position.distance_to(at) + 20.0
			if off < near:
				near = off
				best = flock.global_position
			continue
		var i := flock.nearest(at)
		if i >= 0:
			var far := flock.boid_position(i).distance_to(at)
			if far < near:
				near = far
				best = flock.boid_position(i)
	if only_schools:
		return best
	for each in awake:
		if each.away <= 0.0 and not each.giant and not each.guarded() and is_food(player.length, each.length):
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
	for each in awake:
		if each.away <= 0.0 and each.hunts and each.visible and can_eat(each.length, player.length) and player.length >= each.length * TOO_SMALL \
				and (each.mode == Creature.Mode.HUNT or each.mode == Creature.Mode.STALK or each.global_position.distance_to(player.global_position) < 2.0 + each.length):
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
	_gulp -= delta
	var at := player.global_position
	var mouth := player.mouth()
	for school in schools:
		var flock: Flock = school.flock
		var hunters_at: Array = school.hunters
		# Too far off to be seen through the water, it is left as it is: not moved, not drawn.
		var far := flock.global_position.distance_to(at)
		var seen := far < float(school.seen)
		if seen != flock.visible:
			flock.visible = seen
			flock.set_process(seen)
		if not seen:
			hunters_at.clear()
			continue
		var swarm: bool = school.swarm
		var hunted := not hunters_at.is_empty()
		if hunted:
			# Hunted, it holds where it is and is driven up towards the light, balled up and turning.
			flock.global_position.y = move_toward(flock.global_position.y, Sea.SURFACE - float(school.radius) * 0.6 - 0.5, 0.25 * delta)
		else:
			# The school roams: its bounds drift after a place that changes now and then.
			var goal: Vector3 = school.goal
			if flock.global_position.distance_to(goal) < 2.0:
				var zone: String = "open" if school.nocturnal and night() > 0.5 else school.zone
				if school.get("home", Vector3.INF) != Vector3.INF:
					goal = _home_spot(school.home, float(school.radius))
				else:
					goal = _school_place(zone, float(school.radius), float(school.low), float(school.high))
				school.goal = goal
			flock.global_position = flock.global_position.move_toward(goal, 0.35 * delta)
		if swarm:
			school.mid = flock.middle()
			var rules := flock.rules
			rules.gather = float(school.gather) + (1.4 if hunted else 0.0)
			rules.orbit = 1.2 if hunted else 0.0
			rules.orbit_radius = float(school.radius) * 0.3
			# (fewer drawn the further off it is, thinned evenly)
			var layers: int = rules.riders
			if far > SWARM_NEAR.y:
				layers = ceili(layers * 0.35)
			elif far > SWARM_NEAR.x:
				layers = ceili(layers * 0.6)
			flock.rider_layers = layers
			# (they part round the player's body)
			flock.shove[0] = Vector4.ZERO
			if player.alive:
				var hole := at - player.heading * player.length * 0.2
				flock.shove[0] = Vector4(hole.x, hole.y, hole.z, player.length * 0.55 + 0.05)
		if not player.alive:
			flock.predators = PackedVector3Array(hunters_at)
			hunters_at.clear()
			continue
		var edible := is_food(player.length, school.length)
		# (a swarm keeps clear of anything that could eat it; a small school only of a player that would)
		var feared := edible or (swarm and can_eat(player.length, school.length))
		var flee_from := PackedVector3Array(hunters_at)
		if feared:
			flee_from.append(at)
		flock.predators = flee_from
		hunters_at.clear()
		if not edible or far > float(school.radius) + 3.0:
			continue
		var reach := player.length * 0.3 + float(school.length) * 0.5 + 0.03
		if swarm:
			# the one nearest the mouth is taken, and comes back a while later on the far side (one a
			# gulp: in the middle of a ball of a thousand there is always another at the mouth)
			if _gulp <= 0.0:
				var i := flock.nearest_rider(mouth, reach)
				if i >= 0:
					player.feed(school.length, school.rich)
					flock.take_rider(i, _rng.randf_range(6.0, 14.0))
					_gulp = GULP
			continue
		var all := flock.positions()
		for i in all.size():
			if all[i].distance_squared_to(mouth) < reach * reach:
				player.feed(school.length, school.rich)
				# (another comes in from beyond the far side of the school, out of reach)
				var behind := (flock.global_position - at).normalized()
				flock.move_boid(i, flock.global_position + behind * (float(school.radius) + reach + 2.0))


## Takes from a swarm or school whatever is within `reach` of a mouth (a hunter, a whale, a net):
## at most `most`. Returns how many.
func take_from(school: Dictionary, mouth: Vector3, reach: float, most := 1) -> int:
	var flock: Flock = school.flock
	if not flock.visible:
		return 0
	var taken := 0
	if school.swarm:
		for n in most:
			var i := flock.nearest_rider(mouth, reach)
			if i < 0:
				break
			flock.take_rider(i, _rng.randf_range(6.0, 14.0))
			taken += 1
		return taken
	var all := flock.positions()
	for i in all.size():
		if taken < most and all[i].distance_squared_to(mouth) < reach * reach:
			flock.move_boid(i, flock.global_position + (flock.global_position - mouth).normalized() * (float(school.radius) + 2.0))
			taken += 1
	return taken


## For Fishers (a trawl's mouth, a net): whatever of the schools is within `reach` of a point is
## caught (at most `most` from each), and the rest scatter. Returns how many.
func catch_schools(at: Vector3, reach: float, most := 2) -> int:
	var taken := 0
	for school in schools:
		var flock: Flock = school.flock
		if not flock.visible or flock.global_position.distance_to(at) > float(school.radius) + reach + 2.0:
			continue
		var got := take_from(school, at, reach, most)
		if got > 0:
			flock.scatter(at, 1.0, reach + 1.5)
		taken += got
	return taken


func _step_creatures(delta: float) -> void:
	hunters = 0
	var mouth := player.mouth()
	# Who wakes and who sleeps: a tenth of them a frame, or all of them when the player has jumped
	# (a new run, a test putting it somewhere).
	var jumped := steps == 0 or player.global_position.distance_to(_checked_at) > 10.0
	_checked_at = player.global_position
	for k in range(0 if jumped else steps % WAKE_EVERY, _units.size(), 1 if jumped else WAKE_EVERY):
		_wake_or_sleep(_units[k])
	for group: Creature.Group in groups:
		if not group.members[0].asleep:
			group.update(delta)
	_step_stations()
	# (a fifteenth of them each frame look about for a swarm to hunt or a cleaner to visit)
	var slice := steps % 15
	for k in range(slice, awake.size(), 15):
		_look_about(awake[k])
	var dress_left := dress_each
	for each in awake:
		if each.away > 0.0:
			each.away -= delta
			if each.away <= 0.0:
				each.place(_back_place(each))
			continue
		if each.prey is Dictionary:
			each.prey_at = each.prey.mid
		elif each.prey is Node3D:
			each.prey_at = (each.prey as Node3D).global_position
		var apart := each.global_position.distance_to(player.global_position)
		# Too far off to be seen through the water: not drawn, and moved only now and then.
		var seen := apart < fish_seen + each.length * 2.0
		# (it gets its model when it is first seen: kinds new to this run a few frames apart, since
		# each one's shader is compiled then, which is slow in a browser)
		if seen and not each.dressed:
			if dress_left > 0 and _dressed.has(each.kind):
				each.dress()
				dress_left -= 1
			elif dress_left > 0 and steps >= _next_new:
				_dressed[each.kind] = true
				_next_new = steps + NEW_EVERY
				each.dress()
				dress_left -= 1
			else:
				seen = false
		if each.visible != seen:
			each.visible = seen
		if not seen:
			if (steps + each.get_index()) % 8 != 0:
				continue
			each.step(delta * 8.0, player, hunting)
			continue
		# (beyond STEP_NEAR, half of them a frame, each with two frames' time: a fish that far off
		# moves less than a pixel of the half-size picture in a frame. tools/PERF.md)
		# (and beyond STEP_MID, a third of them a frame)
		if apart < step_near + each.length * 2.0:
			each.step(delta, player, hunting)
		elif apart < step_mid + each.length * 2.0:
			if (steps + each.get_index()) % 2 == 0:
				each.step(delta * 2.0, player, hunting)
		elif (steps + each.get_index()) % 3 == 0:
			each.step(delta * 3.0, player, hunting)
		# (a rogue wave tumbles what swims near the top along with it: Surf.surge, tools/WATER_FX.md)
		if Surf.rogue_on and each.global_position.y > Sea.SURFACE - 8.0:
			each.global_position += Surf.surge(each.global_position) * delta
		each.detail(apart < 5.0 + each.length * 4.0)
		# A pack hunter or a filter feeder at a swarm or a cloud: the swarm balls up and flees it,
		# and what its open mouth passes is taken.
		if each.prey_r > 0.0 and each.prey is Dictionary:
			var school: Dictionary = each.prey
			school.hunters.append(each.global_position)
			if each.feeding:
				var flock: Flock = school.flock
				flock.shove[1] = Vector4(each.global_position.x, each.global_position.y, each.global_position.z, each.length * 0.45 + 0.2)
				if _rng.randf() < delta * (12.0 if each.habit == "filter" else 4.0):
					take_from(school, each.mouth(), each.length * 0.35 + float(school.length), 3 if each.habit == "filter" else 1)
		elif each.feeding and each.prey is Node3D:
			(each.prey as Node3D).call(&"bite", each.mouth(), each.length * 0.3)
		if not player.alive:
			continue
		if each.mode == Creature.Mode.HUNT or each.mode == Creature.Mode.STALK:
			hunters += 1
		# (an animal much bigger than the player that it cannot eat is solid: it is swum round, not
		# through. CLAUDE.md, "Decision: solid giants")
		if each.length >= player.length * SOLID and not player.in_air and not each.airborne \
				and apart < each.length * 0.6 + player.length \
				and not (hunting and each.hunts and can_eat(each.length, player.length)):
			push_off(each.global_position, each.heading, each.length * (0.5 - BODY), each.length * BODY)
		if each.giant:
			continue
		if is_food(player.length, each.length):
			if not each.guarded() and each.gap_to(mouth) < player.length * TAKES + TAKES_LEAST:
				player.feed(each.length)
				each.visible = false
				each.away = _rng.randf_range(5.0, 12.0)
		elif hunting and each.hunts and not player.in_air and not each.airborne and can_eat(each.length, player.length):
			if player.gap_to(each.mouth()) < each.length * JAWS:
				player.die(each.kind)
		if each.stings() and hunting and not player.in_air and not can_eat(player.length, each.length) \
				and apart < each.length * 0.45 + player.length * 0.35:
			_sting(each)


## Wakes an animal now, and the group it keeps with (for whatever puts one beside the player: the
## tests). It sleeps again by the usual rule if it is far off.
func wake(each: Creature) -> void:
	if not each.asleep:
		return
	for m: Creature in (each.group.members if each.group else [each]):
		m.asleep = false
		awake.append(m)


## Wakes a group (or a lone animal) near the player, or puts one far off to sleep.
func _wake_or_sleep(unit: Variant) -> void:
	var members: Array = (unit as Creature.Group).members if unit is Creature.Group else [unit]
	var first: Creature = members[0]
	# (by its nearest member: a group wakes when any of it comes near, and sleeps when all are far)
	var far := INF
	for m: Creature in members:
		far = minf(far, m.global_position.distance_to(player.global_position) - m.length * 2.0)
	if first.asleep and far < wake_at:
		for m: Creature in members:
			m.asleep = false
			awake.append(m)
		# (it wakes out of sight, so a group that went to sleep straggling, or was never let gather
		# since the sea was stocked, closes up round its leader now)
		if unit is Creature.Group:
			var group: Creature.Group = unit
			for m: Creature in members:
				var room := maxf(m.length * group.space, 0.3)
				if m != first and m.away <= 0.0 and m.global_position.distance_to(first.global_position) > room * 3.0:
					var off := Vector3(_rng.randf_range(-1.0, 1.0), _rng.randf_range(-0.4, 0.4), _rng.randf_range(-1.0, 1.0)) * room * 1.5
					var keep := maxf(m.length * 0.5, 0.3)
					m.place(Sea.clear_of_rocks(Sea.keep_in(first.global_position + off, keep), keep))
					m.heading = first.heading
					m.visible = false
	elif not first.asleep and far > sleep_at:
		for m: Creature in members:
			_sleep(m)


# It sleeps where it is (one that was eaten is back already, with its group).
func _sleep(each: Creature) -> void:
	each.asleep = true
	awake.erase(each)
	if each.away > 0.0:
		each.place(_back_place(each))
	if each.visit_at != Vector3.INF:
		each.visit_at = Vector3.INF
	each.prey = null
	each.prey_r = 0.0
	each.feeding = false
	each.visible = false
	each.undress()


## Pushes the player out of a body: a rounded rod from `middle` `half` metres either way along
## `along`, `radius` thick (and the player's own room more). Its way into the body is lost, its way
## along it kept.
func push_off(middle: Vector3, along: Vector3, half: float, radius: float) -> void:
	var p := player.global_position
	var on := clampf((p - middle).dot(along), -half, half)
	var axis := middle + along * on
	var off := p - axis
	var clear := radius + player.length * 0.25
	var far_sq := off.length_squared()
	if far_sq >= clear * clear:
		return
	var far := sqrt(far_sq)
	var out := off / far if far > 0.001 else Vector3.UP
	player.global_position = Sea.keep_in(axis + out * clear, maxf(player.length * 0.3, 0.12))
	pushed += 1


## The set-piece giants that move (the reef-back): each [node, its body's middle in its own space,
## the half-length along its -z, the radius]. Main fills it.
var solids: Array = []
## How many times the player was pushed off a body (for tests).
var pushed := 0


func _step_solids() -> void:
	if not player.alive or player.in_air:
		return
	for solid: Array in solids:
		var node: Node3D = solid[0]
		if node == null or not is_instance_valid(node):
			continue
		var t := node.global_transform
		var middle: Vector3 = t * (solid[1] as Vector3)
		if middle.distance_to(player.global_position) > float(solid[2]) + float(solid[3]) + 6.0:
			continue
		push_off(middle, -t.basis.z.normalized(), float(solid[2]) * t.basis.get_scale().z, float(solid[3]) * t.basis.get_scale().x)


# A lionfish's spines: touching one costs the player its burst and most of its speed, and pushes
# it off (Claude's call: a hurt, not a death, since nothing warns a new player that it stings but
# its fanned spines).
func _sting(by: Creature) -> void:
	by.stung()
	player.stamina = 0.0
	player._speed *= 0.2
	var off := player.global_position - by.global_position
	player.global_position = Sea.keep_in(player.global_position + off.normalized() * 0.3, maxf(player.length * 0.3, 0.12))
	stings += 1


# Where a creature that was eaten comes back: with its group, if the group is out of the player's
# sight, or else somewhere far from the player (it rejoins its group from there).
func _back_place(each: Creature) -> Vector3:
	var g: Creature.Group = each.group
	if g and g.present > 0 and g.mid.distance_to(player.global_position) > 24.0:
		var spread := maxf(each.length * g.space, 0.3) * 2.0
		var at := g.mid + Vector3(_rng.randf_range(-1.0, 1.0), _rng.randf_range(-0.5, 0.5), _rng.randf_range(-1.0, 1.0)) * spread
		return Sea.clear_of_rocks(Sea.keep_in(at, maxf(each.length * 0.5, 0.3)), maxf(each.length * 0.5, 0.3))
	return each.somewhere(player.global_position, 24.0)


# A creature now and then looks about: a pack hunter or a filter feeder for the nearest swarm or
# cloud it could feed on (only those in sight: the others are not being moved), a client for a free
# cleaning station near it.
func _look_about(each: Creature) -> void:
	if each.away > 0.0 or not each.visible:
		each.prey_r = 0.0
		each.prey = null
		return
	if each.habit == "pack" or each.habit == "filter":
		var best: Variant = null
		var best_r := 0.0
		var near := 30.0
		var at := each.global_position
		for school in schools:
			var flock: Flock = school.flock
			if not flock.visible or not school.swarm:
				continue
			var fits: bool = school.length <= 0.25 if each.habit == "filter" else \
					(can_eat(each.length, school.length) and school.length >= each.length * 0.04)
			if not fits:
				continue
			var d: float = (school.mid as Vector3).distance_to(at)
			if d < near:
				near = d
				best = school
				best_r = float(school.radius) * 0.6
		if each.habit == "filter":
			for cloud in plankton:
				var d := cloud.global_position.distance_to(at)
				if cloud.visible and d < near:
					near = d
					best = cloud
					best_r = PLANKTON_RADIUS
		each.prey = best
		each.prey_r = best_r if best != null else 0.0
		if best is Dictionary:
			each.prey_at = best.mid
		elif best is Node3D:
			each.prey_at = (best as Node3D).global_position
	if each.visits and each.visit_at == Vector3.INF and each._visit_t <= 0.0:
		for i in stations.size():
			if station_client[i] == null and stations[i].distance_to(each.global_position) < 30.0:
				station_client[i] = each
				each.visit_at = stations[i]
				return
		each._visit_t = _rng.randf_range(10.0, 20.0)


# The cleaning stations: a client that has gone (cleaned, eaten, called off) frees its station; the
# station's cleaners attend to whoever is there.
func _step_stations() -> void:
	for i in stations.size():
		var client: Creature = station_client[i]
		if client and (client.away > 0.0 or client.visit_at != stations[i]):
			station_client[i] = null
			client = null
		_cleaners_at(i, client)


func _cleaners_at(i: int, client: Creature) -> void:
	for each: Creature in _cleaners[i]:
		each.client = client if client and client.global_position.distance_to(stations[i]) < client.length + 1.0 else null


# Groups of `pool` (of one kind, or of the kinds of one mix): as many as the counts make, each of a
# size Species gives, placed together.
func _make_groups(pool: Array) -> void:
	for k in range(pool.size() - 1, 0, -1):
		var j := _rng.randi_range(0, k)
		var swap: Variant = pool[k]
		pool[k] = pool[j]
		pool[j] = swap
	var first := Species.of((pool[0] as Creature).kind)
	var social: String = first.get("social", "school")
	var sizes: Array = first.get("group", [3, 5])
	var k := 0
	while k < pool.size():
		var n := _rng.randi_range(int(sizes[0]), int(sizes[1]))
		var some := pool.slice(k, k + n)
		k += n
		if some.size() < 2:
			continue
		some.sort_custom(func(a: Creature, b: Creature) -> bool: return a.length > b.length)
		var group := Creature.Group.new(social)
		var lead: Creature = some[0]
		var at := lead.global_position
		for m: Creature in some:
			group.members.append(m)
			m.group = group
			if m != lead:
				var room := maxf(m.length * 0.5, 0.3)
				var off := Vector3(_rng.randf_range(-1.0, 1.0), _rng.randf_range(-0.4, 0.4), _rng.randf_range(-1.0, 1.0)) * maxf(m.length * group.space, 0.3) * 1.5
				m.place(Sea.clear_of_rocks(Sea.keep_in(at + off, room), room))
				m.heading = lead.heading
		group.goal = at
		group.mid = at
		groups.append(group)


# The cleaning stations, on the reef (over the floor, where a cleaner bobs to show it is open), and
# which cleaners keep each.
func _make_stations() -> void:
	for i in STATIONS:
		var at := Sea.place(_rng, "reef", 0.6)
		at.y = Sea.ground(at.x, at.z) + 0.5
		stations.append(Sea.clear_of_rocks(at, 0.4))
		station_client.append(null)
		_cleaners.append([])
	var n := 0
	for each in creatures:
		if each.habit == "cleaner":
			var i := n % STATIONS
			n += 1
			each.station_at = stations[i]
			(_cleaners[i] as Array).append(each)
			each.place(stations[i] + Vector3(_rng.randf_range(-0.5, 0.5), 0.2, _rng.randf_range(-0.5, 0.5)))


## How dark it is (0 day, 1 night), from scripts/day.gd's `Day.now()` (0..1 through the day, taken
## to be midnight at 0 and noon at 0.5) when that script is there; always day without it. Read
## once a second at most.
static func night() -> float:
	var now := Time.get_ticks_msec()
	if now - _night_read < 1000:
		return _night
	_night_read = now
	if not _day_looked:
		_day_looked = true
		if ResourceLoader.exists(DAY):
			_day = load(DAY)
	if _day == null:
		return 0.0
	var t := float(_day.call(&"now"))
	_night = clampf((absf(t - 0.5) - 0.3) / 0.1, 0.0, 1.0)
	return _night


func _step_jellies(delta: float) -> void:
	for i in jellies.size():
		var jelly := jellies[i]
		if _jelly_away[i] > 0.0:
			_jelly_away[i] -= delta
			if _jelly_away[i] <= 0.0:
				_place_jelly(i, Sea.open_water(_rng, 1.0, player.global_position, 24.0))
			continue
		# (too far off to be seen beating, it hangs where it is; further still, the water hides it,
		# and it is not drawn: a jelly is 18,000 triangles and a lamp, tools/PERF.md)
		var far := jelly.global_position.distance_to(player.global_position)
		var drawn := far < JELLY_DRAWN
		if jelly.visible != drawn:
			jelly.visible = drawn
			if drawn:
				Hitches.note("jelly %d shown (its lamp on)" % i)
		if far > JELLY_SEEN:
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


## Plankton: a small fish swimming through a cloud with its mouth open takes what its mouth
## passes. Too far off to be seen, a cloud is not drawn.
func _step_plankton() -> void:
	var at := player.global_position
	for cloud in plankton:
		var far := cloud.global_position.distance_to(at)
		var seen := far < KRILL_SEEN + PLANKTON_RADIUS
		if cloud.visible != seen:
			cloud.visible = seen
		if not seen or not player.alive or player.length > PLANKTON_EATER or far > PLANKTON_RADIUS + 1.0:
			continue
		var taken: int = cloud.call(&"bite", player.mouth(), player.length * 0.35 + 0.05)
		for i in mini(taken, 6):
			player.feed(PLANKTON_LENGTH)


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
		var drawn := far < JELLY_DRAWN
		if nettle.visible != drawn:
			nettle.visible = drawn
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


## Food within easy reach of where a run starts (the user, 2026-11-20: "its extremely unclear what you
## can eat and how to find it"; as a sardine there was no food a sardine could reach within 30 m): the
## first krill cloud and the first school of anchovies keep within HOME_ROOM of `at`, between
## HOME_DEPTH metres under the surface (inside the starting depth limit: the static begins at 12 m).
## They are moved there now if they are far off (a new run).
static var HOME_ROOM: Vector2 = Layout.point("home.room")
static var HOME_DEPTH: Vector2 = Layout.point("home.depth")
var _home_rng := RandomNumberGenerator.new()


func keep_home(at: Vector3) -> void:
	for school in schools:
		if not school.has("home"):
			continue
		school.home = at
		var flock: Flock = school.flock
		if flock.global_position.distance_to(at) > HOME_ROOM.y + 6.0:
			var spot := _home_spot(at, float(school.radius))
			var shift := spot - flock.global_position
			flock.global_position = spot
			for i in flock.positions().size():
				flock.move_boid(i, flock.boid_position(i) + shift)
			school.goal = spot
			school.mid = spot


# A place near a run's start for a school that keeps there.
func _home_spot(at: Vector3, room: float) -> Vector3:
	# (its own dice: the rest of the sea's draws stay as they were)
	var a := _home_rng.randf() * TAU
	var spot := at + Vector3(cos(a), 0.0, sin(a)) * _home_rng.randf_range(HOME_ROOM.x, HOME_ROOM.y)
	spot.y = Sea.SURFACE - _home_rng.randf_range(HOME_DEPTH.x, HOME_DEPTH.y)
	spot.y = maxf(spot.y, Sea.ground(spot.x, spot.z) + room * 0.6 + 0.5)
	return Sea.clear_of_rocks(Sea.keep_in(spot, room * 0.5), room * 0.5)


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
	# (a little thinking each a frame: there are ten of them; a swarm's few guides less still)
	flock.budget_ms = 0.05 if rules.riders > 0 else 0.4
	flock.ground_at = func(p: Vector3) -> float: return Sea.ground(p.x, p.z)
	var at := _school_place(zone, rules.bounds_size.x, low, high)
	flock.position = at
	add_child(flock)
	schools.append({"flock": flock, "length": length, "rich": 1.0, "goal": at, "zone": zone, "radius": rules.bounds_size.x, "low": low, "high": high,
			"seen": KRILL_SEEN if length < 0.1 else SARDINES_SEEN, "swarm": rules.riders > 0, "mid": at, "gather": rules.gather,
			"hunters": [], "nocturnal": false})


## A school's rules made a swarm's: `spec` [guides, riders round each, how far round its guide a
## rider keeps]. The guides keep a cloud's width apart and all together in one body.
func _swarm_rules(r: FlockRules, spec: Array) -> FlockRules:
	r.count = int(spec[0])
	r.riders = int(spec[1])
	var spread: float = spec[2]
	r.rider_spread = spread
	r.rider_drift = spread * 0.12
	r.rider_fright = 0.7
	r.separation_distance = spread * 1.25
	r.perception = spread * 3.0
	r.max_neighbours = 6
	r.gather = maxf(r.gather, 0.8)
	r.bounds = FlockRules.Bounds.SPHERE
	r.bounds_size = Vector3.ONE * (spread * sqrt(float(spec[0])) * 0.9 + 1.5)
	r.bounds_margin = r.bounds_size.x * 0.4
	if r.flee > 0.0:
		r.flee_radius = maxf(r.flee_radius, 3.5)
		r.alarm_spread = 0.85
	return r


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
	if ResourceLoader.exists(KRILL):
		# (GameCommon's krill: life size, 3 cm, and in its own colours)
		r.size = KRILL_LENGTH / 0.03
		r.colour = Color.WHITE
		r.colour_variation = 0.0
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
	if ResourceLoader.exists(KRILL):
		return Fish.school_mesh("krill")
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

