class_name Creature
extends Fish
## One of the other animals. It wanders about its own part of the sea at its own depth; it flees
## the player when the player is big enough to eat it; and when it is big enough to eat the
## player, and the player is worth the trouble and in sight, it hunts: a chase it gives up after
## a few seconds, tired for a while. Life steps it and settles who eats whom.
##
## Species says how each kind lives: `how` "floor" keeps it on or just over the bottom, "giant"
## has it cruise and take no notice of anything; `hunts` off, it never goes for the player.
##
## Keeping together (tools/SCHOOLING.md): a kind with `social` other than "solo" is put by Life in a
## small Group of its own kind (or of every kind with the same `mix`), and steers by the others of
## its group only (keep clear, line up, keep together, make for the group's goal): no look at any
## other creature. `habit` gives it one way of living of its own (see `_wander` and `_show`), and
## `breathes`, `leaps` and `visits` three more (up for air, out of the water, to a cleaner).

enum Mode { WANDER, FLEE, HUNT, STALK }

## How long a chase lasts before it gives up (s), and how long it then leaves the player alone.
const CHASE := 4.0
const TIRED := 9.0
## How far off it notices the player: this many metres, and this many more for each metre it is long.
const SIGHT := 2.5
const SIGHT_PER_LENGTH := 3.0
## Ambushers: the player this near (m, and this many of its own lengths more), ahead of it, and it
## opens its mouth wide for LUNGE_WARN seconds (the warning), then lunges for LUNGE_LASTS.
const LUNGE_REACH := 0.7
const LUNGE_PER_LENGTH := 1.1
const LUNGE_WARN := 0.6
const LUNGE_LASTS := 0.55
const LUNGE_PACE := 2.3
## Stalkers circle the player this long (s) before they run in.
const STALK_FOR := Vector2(2.5, 4.0)
## How each kind of group keeps together: spacing (in the member's lengths), the weights of keeping
## together, lining up and making for the group's goal, and how fast it wanders (× its pace).
const SOCIAL := {
	"school": [1.4, 1.0, 1.3, 0.7, 0.6],
	"shoal": [2.4, 0.7, 0.3, 0.45, 0.4],
	"pair": [1.3, 1.3, 0.7, 0.6, 0.45],
	"harem": [2.2, 0.9, 0.3, 0.5, 0.4],
	"pod": [1.8, 1.0, 1.1, 0.7, 0.55],
}

## A few of its kind (or of a mix of kinds) that keep together: Life makes them at stocking and
## updates each once a frame (its middle, its heading, its goal); members read it.
class Group:
	var members: Array[Creature] = []
	var social := "school"
	var space := 1.4
	var cohere := 1.0
	var align := 1.0
	var pull := 0.6
	var pace := 0.5
	var goal := Vector3.ZERO
	var goal_time := 0.0
	var mid := Vector3.ZERO
	var way := Vector3.FORWARD
	var present := 0
	## Seconds a fright lasts that one member took: the others flee too.
	var alarm := 0.0
	## Pods: seconds until they all go up for air together.
	var air := 20.0
	var leader: Creature

	func _init(how: String) -> void:
		social = how
		var s: Array = SOCIAL.get(how, SOCIAL.school)
		space = s[0]
		cohere = s[1]
		align = s[2]
		pull = s[3]
		pace = s[4]

	func update(delta: float) -> void:
		var sum := Vector3.ZERO
		var dir := Vector3.ZERO
		present = 0
		leader = null
		for m in members:
			if m.away > 0.0:
				continue
			if leader == null:
				leader = m
			sum += m.global_position
			dir += m.heading
			present += 1
		if present == 0:
			return
		mid = sum / present
		way = dir.normalized() if dir.length() > 0.05 else leader.heading
		# (a harem follows its biggest: the members are kept biggest first)
		if social == "harem":
			mid = leader.global_position
		alarm = maxf(alarm - delta, 0.0)
		goal_time -= delta
		if goal_time <= 0.0 or mid.distance_to(goal) < 1.5 + leader.length * 2.0:
			goal = leader.somewhere()
			goal_time = leader._rng.randf_range(8.0, 16.0) * (2.0 if leader.giant else 1.0)
		if social == "pod" and leader.breathes:
			air -= delta
			if air <= 0.0:
				air = leader._dive_time()
				for m in members:
					m._air = minf(m._air, 0.0)


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
## Far from the player it sleeps where it is (Life wakes it): not stepped, not drawn, no model.
var asleep := false
var hunts := true
## Species' `habit` ("" none), and whether it goes up for air, leaps, visits cleaners, comes up at night.
var habit := ""
var breathes := false
var leaps := false
var visits := false
var nocturnal := false
## Its group (Life sets it), or null.
var group: Group
## What Life has found for a pack hunter or a filter feeder to go for: the middle of a swarm or a
## cloud, and its radius (0: nothing); `feeding` is set while its mouth is in it.
var prey_at := Vector3.ZERO
var prey_r := 0.0
var prey: Variant = null
var feeding := false
## A cleaner's station, and the fish it is cleaning (Life sets both); a client's station while it
## visits (Vector3.INF: not visiting).
var station_at := Vector3.INF
var client: Creature
var visit_at := Vector3.INF
## Out of the water just now (a leap).
var airborne := false

var _goal := Vector3.ZERO
var _goal_time := 0.0
var _speed := 0.0
var _chase := 0.0
var _tired := 0.0
var _rng := RandomNumberGenerator.new()
# Habits' own clocks and states.
var _clock := 0.0
var _alarm := 0.0
var _lair := Vector3.ZERO
var _lair_time := 0.0
var _warn := 0.0
var _lunge := 0.0
var _stalk := 0.0
var _stalk_for := 3.0
var _turn_way := 1.0
var _air := 30.0
var _surfacing := 0
var _breath := 0.0
var _vel := Vector3.ZERO
var _leap_cool := 5.0
var _graze_at := Vector3.INF
var _graze_t := 3.0
var _pack_t := 3.0
var _dash := false
var _visit_t := 30.0
var _strike := 0.0
var _strike_cool := 0.0
var _hop := Vector3.ZERO
var _hop_t := 0.0
var _hops := 0
var _arch := 0.0
var _sting_cool := 0.0
var _base_open := -1.0
# Which settings its creature has (a bit each; see _LOOKS), found once when it is dressed.
var _has := 0
var _sent := PackedFloat32Array()

const _LOOKS: Array[StringName] = [&"puff", &"open", &"furl", &"tuck", &"threat", &"grip", &"sit", &"lure",
	&"scoops", &"flare", &"spread", &"strike", &"snap", &"arch", &"afloat", &"swim", &"wings", &"eye_look", &"dig"]
enum { L_PUFF, L_OPEN, L_FURL, L_TUCK, L_THREAT, L_GRIP, L_SIT, L_LURE, L_SCOOPS, L_FLARE, L_SPREAD, L_STRIKE,
	L_SNAP, L_ARCH, L_AFLOAT, L_SWIM, L_WINGS, L_EYES, L_DIG }


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
	habit = entry.get("habit", "")
	breathes = bool(entry.get("breathes", false))
	leaps = bool(entry.get("leaps", false))
	visits = bool(entry.get("visits", false))
	nocturnal = bool(entry.get("nocturnal", false))
	var sets: Dictionary = entry.get("set", {})
	_base_open = float(sets.get("open", -1.0))
	_mouth_back = float(entry.get("mouth", MOUTH))
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
	Hitches.note("dress " + (of_kind if of_kind != "" else kind))
	set_kind(of_kind if of_kind != "" else kind)
	# (each koi, guppy or other patterned fish its own pattern)
	if _look and &"pattern_seed" in _look:
		_look.set(&"pattern_seed", _rng.randi() % 1000)
	_has = 0
	_sent.resize(_LOOKS.size())
	_sent.fill(-99.0)
	if _look:
		for k in _LOOKS.size():
			if _LOOKS[k] in _look:
				_has |= 1 << k
	if on_floor and _look and not _belows.has(kind):
		_belows[kind] = _reach_below()


## Gives its model back (it has gone to sleep far off): `dress` gives it again when it is next seen.
func undress() -> void:
	if not dressed:
		return
	dressed = false
	_has = 0
	if _look:
		_body.remove_child(_look)
		_look.queue_free()
		_look = null
	_material = null


## What keeps to the floor stands on it: how far its drawn body reaches below its middle, as a share
## of its length, by kind (tools/QUALITY.md: they were held 0.1 m up whatever their size, so a shrimp
## or a nudibranch hovered and a big crab or a horseshoe crab sank in).
static var _belows := {}


func _reach_below() -> float:
	var lowest := 0.0
	var to_me := global_transform.affine_inverse()
	for mesh: MeshInstance3D in _look.find_children("*", "MeshInstance3D", true, false):
		if mesh.mesh == null or not mesh.visible:
			continue
		var box: AABB = to_me * mesh.global_transform * mesh.mesh.get_aabb()
		lowest = minf(lowest, box.position.y)
	return -lowest / maxf(length, 0.001)


## How high its middle stands over the floor when it keeps to it.
func _stands() -> float:
	return maxf(float(_belows.get(kind, 0.15)) * length, 0.005) + 0.005


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
	airborne = false
	_surfacing = 0
	_air = _rng.randf_range(0.2, 1.0) * _dive_time()
	_lair = at
	_lair_time = _rng.randf_range(40.0, 80.0)
	_warn = 0.0
	_lunge = 0.0
	_graze_at = Vector3.INF
	_hop = Vector3.ZERO
	feeding = false
	if visit_at != Vector3.INF:
		visit_at = Vector3.INF
		_visit_t = _rng.randf_range(20.0, 50.0)


## A place in the water where it lives, at its own depth, no nearer than `apart` to `from` if
## that can be had. (Night-time things rise into the open water when it is dark: scripts/day.gd,
## when there is one.)
func somewhere(from := Vector3.INF, apart := 0.0) -> Vector3:
	var room := maxf(length * 0.5, 0.3)
	var zone: String = zones[_rng.randi() % zones.size()] if not zones.is_empty() else ""
	var depth := band
	if nocturnal and Life.night() > 0.5:
		zone = "open"
		depth = Vector2(0.55, 0.95)
	var p := Sea.place(_rng, zone, room, from, apart)
	var low := _floor_at(p.x, p.z)
	p.y = lerpf(low, maxf(low, Sea.SURFACE - maxf(length * 0.3, 0.6)), _rng.randf_range(depth.x, depth.y))
	return Sea.clear_of_rocks(p, room)


## Leaves the player alone for a while (a new run has begun next to it).
func back_off() -> void:
	_tired = TIRED
	_warn = 0.0
	_lunge = 0.0
	_stalk = 0.0
	mode = Mode.WANDER


## It cannot be eaten just now: a pufferfish blown up, a razor clam dug in.
func guarded() -> bool:
	if not dressed or _look == null:
		return false
	if _has & (1 << L_PUFF):
		return float(_look.get(&"puff")) > 0.5
	if _has & (1 << L_DIG):
		return _alarm > 0.9
	return false


## Its stinging spines are up (a lionfish): touching it hurts.
func stings() -> bool:
	return habit == "sting" and _sting_cool <= 0.0


## A sting has just been given: not another for a while.
func stung() -> void:
	_sting_cool = 2.0


func step(delta: float, player: Player, hunting: bool) -> void:
	_clock += delta
	_tick(delta)
	if airborne:
		_fly(delta)
		return
	var to_player := player.global_position - global_position
	var far := to_player.length()
	var was := mode
	mode = Mode.WANDER
	_tired = maxf(_tired - delta, 0.0)
	var edible := player.alive and Life.is_food(player.length, length)
	if player.alive and not giant:
		if edible and far < 2.5 + player.length * 3.0 and not _holds_ground():
			mode = Mode.FLEE
		elif hunting and hunts and _tired <= 0.0 and player.safe <= 0.0 and not player.in_air and Life.can_eat(length, player.length) \
				and player.length >= length * Life.TOO_SMALL and far < SIGHT + length * SIGHT_PER_LENGTH and not edible:
			mode = _hunt_mode(was, to_player, far, delta)
		if mode == Mode.WANDER and group and group.alarm > 0.0 and edible and far < 12.0 and not _holds_ground():
			mode = Mode.FLEE
	if mode != Mode.STALK and mode != Mode.HUNT:
		_stalk = 0.0
	if _lunge > 0.0 and player.alive:
		mode = Mode.HUNT
	elif _warn > 0.0:
		mode = Mode.STALK
	if mode == Mode.FLEE and group:
		group.alarm = 1.5
	# (a fright of its own: something big and near)
	var scared := player.alive and player.length > length * 0.8 and far < 1.0 + length * 4.0 + player.length
	_alarm = move_toward(_alarm, 1.0 if scared else 0.0, delta * (0.9 if habit == "shy" else 2.0))
	var want := heading
	var speed := Fish.pace(length) * slow
	bite = 0.0
	feeding = false
	match mode:
		Mode.WANDER:
			var w := _wander(delta, to_player, far)
			want = Vector3(w.x, w.y, w.z)
			speed *= w.w
			_chase = maxf(_chase - delta, 0.0)
		Mode.FLEE:
			# away from the player, and back towards where it lives (with its group, if it has one)
			var home := (_home() - global_position) * Vector3(1.0, 0.0, 1.0) / 60.0
			want = (-to_player.normalized() + home * home.length() * 2.0).normalized()
			if group and group.present > 1:
				want = (want * 1.5 + group.way * 0.5 + _keep_apart() * 1.5).normalized()
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
			speed *= LUNGE_PACE if _lunge > 0.0 else 1.25
			# (its mouth opens as it closes in)
			bite = 1.0 if far < length * 1.5 + 1.0 or _lunge > 0.0 else 0.0
			if far < length * 1.2 + 0.4 and _strike_cool <= 0.0:
				_strike = 1.0
				_strike_cool = 0.8
		Mode.STALK:
			if _warn > 0.0:
				# the warning: still, facing it, its mouth wide (and backing a little, to spring)
				want = to_player.normalized()
				speed *= -0.05
				bite = 1.0
			else:
				# round and round it, closer each time, then in
				var flat := Vector3(-to_player.x, 0.0, -to_player.z)
				var fl := maxf(flat.length(), 0.01)
				var ring := 2.5 + length * 0.8 - _stalk / maxf(_stalk_for, 0.1) * 1.2
				var round_way := Vector3(-flat.z, 0.0, flat.x) / fl * _turn_way
				want = (round_way + flat / fl * clampf((ring - fl) * 0.5, -1.0, 1.0)).normalized()
				want.y = clampf(to_player.y * 0.3, -0.4, 0.4)
				speed *= 0.95
	# (never straight up or down)
	want.y = clampf(want.y, -0.7, 0.7)
	if on_floor and mode != Mode.HUNT:
		want.y = clampf((_floor_at(global_position.x, global_position.z) - global_position.y) * 2.0, -0.7, 0.3)
	want = want.normalized() if want.length() > 0.001 else heading
	var nimble := clampf(pow(length, -0.2), 0.3, 1.4) * (1.9 if mode != Mode.WANDER else 1.1)
	var before := heading
	heading = Fish.turned(heading, want, nimble * delta)
	_speed = lerpf(_speed, speed, 1.0 - exp(-(6.0 if _lunge > 0.0 else 2.5) * delta))
	velocity = heading * _speed + _hop
	var room := maxf(length * 0.3, 0.12)
	if on_floor:
		room = minf(room, _stands())
	var next := global_position + velocity * delta
	if habit == "hop" and _hop.length_squared() < 0.0001:
		# (a scallop sinks back to the floor after a hop)
		next.y = maxf(_floor_at(next.x, next.z), next.y - 0.6 * delta)
	var kept := Sea.keep_in(next, room)
	global_position = Sea.clear_of_rocks(kept, room)
	if on_floor and mode != Mode.HUNT and _hop.length_squared() < 0.0001 and global_position == kept:
		# (what keeps to the floor walks on it: down a slope or off a ledge it stays on the floor, not
		# in the water over it; on a rock it is left where the rock holds it. tools/QUALITY.md)
		global_position.y = minf(global_position.y, _floor_at(global_position.x, global_position.z))
	if _has & (1 << L_DIG) and _alarm > 0.0:
		# (a razor clam digs itself into the sand)
		global_position.y -= _alarm * length * 0.6
	_arch = lerpf(_arch, clampf((heading.y - before.y) / maxf(delta, 0.001) * 0.8, -1.0, 1.0), 1.0 - exp(-3.0 * delta))
	# Up through the surface: a leap.
	if leaps and _leap_cool <= 0.0 and global_position.y > Sea.SURFACE - room - 0.5 and heading.y > -0.1 \
			and (mode == Mode.FLEE or _rng.randf() < delta * 0.3):
		_leap_start()
	var side := before.cross(heading).y
	pose(delta, _speed / Fish.pace(length), -side / maxf(nimble * delta, 0.0001))
	if on_floor and global_position.y < Sea.ground(global_position.x, global_position.z) + _stands() + 0.05:
		_lie_on_floor()
	_show(delta, to_player, far, player)


## Resting on the floor it lies along the floor's slope (tools/QUALITY.md: level on a slope, a
## starfish's or a crab's far side went into the sand and its near side stood off it).
func _lie_on_floor() -> void:
	var p := global_position
	var r := maxf(length * 0.4, 0.1)
	var up := Vector3(Sea.ground(p.x - r, p.z) - Sea.ground(p.x + r, p.z), 2.0 * r, Sea.ground(p.x, p.z - r) - Sea.ground(p.x, p.z + r)).normalized()
	var ahead := (heading - up * heading.dot(up))
	if ahead.length_squared() < 0.0001:
		return
	global_basis = Basis.looking_at(ahead.normalized(), up)


# Its clocks.
func _tick(delta: float) -> void:
	_sting_cool = maxf(_sting_cool - delta, 0.0)
	_strike_cool = maxf(_strike_cool - delta, 0.0)
	_strike = maxf(_strike - delta * 6.0, 0.0)
	_leap_cool -= delta
	if breathes:
		_air -= delta
	if visits and visit_at == Vector3.INF:
		_visit_t -= delta
	if _warn > 0.0:
		_warn -= delta
		if _warn <= 0.0:
			_lunge = LUNGE_LASTS
	elif _lunge > 0.0:
		_lunge -= delta
		if _lunge <= 0.0:
			_tired = TIRED * 0.6
	if _hop.length_squared() > 0.0:
		_hop = _hop.move_toward(Vector3.ZERO, delta * 2.5)


# How it goes for the player, as its habit has it: an ambusher waits for it to come close and
# warns before it lunges; a stalker circles first; anything else simply gives chase.
func _hunt_mode(was: Mode, to_player: Vector3, far: float, delta: float) -> Mode:
	match habit:
		"ambush":
			if _lunge > 0.0 or _warn > 0.0:
				return Mode.HUNT
			if far < LUNGE_REACH + length * LUNGE_PER_LENGTH and to_player.dot(heading) > far * 0.2:
				_warn = LUNGE_WARN
				return Mode.STALK
			return Mode.WANDER
		"stalk":
			if was == Mode.HUNT:
				return Mode.HUNT
			if was != Mode.STALK:
				_stalk_for = _rng.randf_range(STALK_FOR.x, STALK_FOR.y)
				_turn_way = 1.0 if _rng.randf() < 0.5 else -1.0
			_stalk += delta
			return Mode.HUNT if _stalk >= _stalk_for else Mode.STALK
	return Mode.HUNT


# It stays where it is when frightened instead of running: blown up, shut, clinging, drifting.
func _holds_ground() -> bool:
	return habit == "shy" or habit == "drift" or habit == "cling" or slow <= 0.05


# Where it makes for, and how fast (w: × its pace), when nothing is after it and it is after nothing.
func _wander(delta: float, to_player: Vector3, far: float) -> Vector4:
	if breathes:
		var b := _breathe(delta)
		if b.w >= 0.0:
			return b
	if visits and visit_at != Vector3.INF:
		return _visit(delta)
	match habit:
		"ambush":
			return _ambush(delta, to_player, far)
		"graze":
			if not on_floor:
				return _graze(delta)
		"cleaner":
			if station_at != Vector3.INF:
				return _clean()
		"pack":
			if prey_r > 0.0:
				return _pack(delta)
		"filter":
			if prey_r > 0.0:
				return _filter()
		"drift":
			return _drift(delta)
		"cling", "home":
			return _stay(delta)
		"sting", "display":
			# (a lionfish turns to face what comes near, fins out; a betta flares at it)
			if far < 1.5 + length * 6.0:
				return Vector4(to_player.x, 0.0, to_player.z, 0.1)
		"hop":
			# (a few claps and it is spent: a scallop tires quickly, and rests on the floor a while)
			if _alarm > 0.5 and _hop_t <= _clock:
				_hops += 1
				_hop_t = _clock + (0.55 if _hops % 4 != 0 else 8.0)
				var off := -to_player
				off.y = 0.0
				_hop = (off.normalized() * 0.7 + Vector3.UP * 0.5)
	return _roam(delta)


# The common way: to its own goal, or with its group to the group's.
func _roam(delta: float) -> Vector4:
	var k := (0.3 if giant or on_floor else 0.5)
	# (a bait it has been tempted to, by Fishers: its own goal for a while)
	if group and group.present > 1 and _goal_time <= 0.0:
		var to_goal := (group.goal - global_position).normalized()
		return _with_group(to_goal, k)
	_goal_time -= delta
	if _goal_time <= 0.0 or global_position.distance_to(_goal) < 1.0 + length:
		_goal = somewhere()
		_goal_time = _rng.randf_range(6.0, 14.0) * (3.0 if giant else 1.0)
	var to := (_goal - global_position).normalized()
	return Vector4(to.x, to.y, to.z, k)


# Steering among its group's members only: clear of each, lined up with the group, towards its
# middle when it falls behind, and on to the goal; it hurries to catch up and idles when ahead.
func _with_group(to_goal: Vector3, k: float) -> Vector4:
	var g := group
	var spacing := maxf(length * g.space, 0.25)
	var to_mid := g.mid - global_position
	var d := to_mid.length()
	var w := to_goal * g.pull + g.way * g.align + _keep_apart() * 2.0
	if g.social == "harem" and g.leader == self:
		w = to_goal + _keep_apart()
	elif d > spacing:
		w += to_mid / d * g.cohere * minf(d / (spacing * 2.0), 3.0)
	var hurry := clampf(to_mid.dot(heading) / (spacing * 2.0), -0.4, 1.0)
	if d > spacing * 6.0:
		hurry = 1.0
	w = w.normalized() if w.length() > 0.001 else heading
	return Vector4(w.x, w.y, w.z, g.pace * (1.0 + hurry) * (k / 0.5))


# Away from the members too close to it.
func _keep_apart() -> Vector3:
	var sep := Vector3.ZERO
	if group == null:
		return sep
	var spacing := maxf(length * group.space, 0.25)
	for m in group.members:
		if m == self or m.away > 0.0:
			continue
		var off := global_position - m.global_position
		var l := off.length()
		if l < spacing and l > 0.001:
			sep += off / l * (1.0 - l / spacing)
	return sep


# Up for air (when its breath is out), a while at the surface, and down again.
func _breathe(delta: float) -> Vector4:
	var room := maxf(length * 0.3, 0.12)
	var top := Sea.SURFACE - room
	match _surfacing:
		0:
			if _air > 0.0:
				return Vector4(0.0, 0.0, 0.0, -1.0)
			_surfacing = 1
		1:
			if global_position.y > top - 0.3:
				_surfacing = 2
				_breath = _rng.randf_range(2.0, 5.0) * (2.0 if giant else 1.0) * (3.0 if habit == "float" else 1.0)
		2:
			_breath -= delta
			if _breath <= 0.0:
				_surfacing = 3
				_breath = 1.6
				_air = _dive_time()
			var along := Vector3(heading.x, 0.0, heading.z).normalized()
			return Vector4(along.x, 0.15, along.z, 0.12 if habit == "float" else 0.35)
		3:
			_breath -= delta
			if _breath <= 0.0:
				_surfacing = 0
			var down := Vector3(heading.x, 0.0, heading.z).normalized() + Vector3.DOWN * 0.8
			return Vector4(down.x, down.y, down.z, 0.6)
	var up := Vector3(heading.x, 0.0, heading.z).normalized() * 1.2 + Vector3.UP
	if group and group.present > 1:
		up += _keep_apart() * 1.5
	return Vector4(up.x, up.y, up.z, 0.7)


## How long it stays down between breaths (s).
func _dive_time() -> float:
	return _rng.randf_range(18.0, 36.0) * clampf(pow(length, 0.4), 1.0, 3.0)


# An ambusher holds still at its lair, watching what comes near, and moves house now and then.
func _ambush(delta: float, to_player: Vector3, far: float) -> Vector4:
	_lair_time -= delta
	if _lair_time <= 0.0:
		_lair = somewhere()
		_lair_time = _rng.randf_range(40.0, 80.0)
	var to_lair := _lair - global_position
	if to_lair.length() > maxf(length * 0.8, 0.4):
		var t := to_lair.normalized()
		return Vector4(t.x, t.y, t.z, 0.35)
	# (a moray breathes with its mouth: open and shut)
	bite = 0.2 + 0.2 * sin(_clock * 2.2)
	if far < 6.0:
		return Vector4(to_player.x, 0.0, to_player.z, 0.03)
	return Vector4(heading.x, 0.0, heading.z, 0.03)


# A grazer: now and then nose down to the floor or a rock in front of it, nibbling, then on.
func _graze(delta: float) -> Vector4:
	_graze_t -= delta
	if _graze_at != Vector3.INF:
		var to := _graze_at - global_position
		if to.length() < maxf(length * 0.7, 0.25):
			bite = 0.5 + 0.5 * sin(_clock * 14.0)
			var down := Vector3(to.x, minf(to.y, 0.0) - 0.4, to.z)
			if _graze_t <= 0.0:
				_graze_at = Vector3.INF
				_graze_t = _rng.randf_range(4.0, 10.0)
			return Vector4(down.x, down.y, down.z, 0.06)
		if _graze_t <= -6.0:
			_graze_at = Vector3.INF
			_graze_t = _rng.randf_range(4.0, 10.0)
		var t := to.normalized()
		return Vector4(t.x, t.y, t.z, 0.4)
	if _graze_t <= 0.0:
		var ahead := global_position + Vector3(heading.x, 0.0, heading.z).normalized() * (1.0 + length * 2.0)
		ahead.y = Sea.ground(ahead.x, ahead.z) + length * 0.35
		# (on a rock, if there is one: pushed out to its face)
		_graze_at = Sea.clear_of_rocks(ahead, length * 0.35)
		_graze_t = _rng.randf_range(2.0, 4.0)
	return _roam(delta)


# A cleaner keeps to its station, bobbing to show it is open; with a fish there, round its head.
func _clean() -> Vector4:
	var at := station_at + Vector3(sin(_clock * 1.3) * 0.3, 0.25 + sin(_clock * 2.3) * 0.15, cos(_clock * 1.3) * 0.3)
	if client and is_instance_valid(client) and client.away <= 0.0 and client.visit_at != Vector3.INF:
		at = client.mouth() + Vector3(sin(_clock * 3.0), 0.4 + 0.3 * sin(_clock * 2.0), cos(_clock * 3.0)) * client.length * 0.35
	var to := at - global_position
	var d := to.length()
	return Vector4(to.x, to.y, to.z, clampf(d * 0.8, 0.05, 0.8))


# A client goes to a cleaning station and hangs there, mouth open, while it is cleaned.
func _visit(delta: float) -> Vector4:
	var at := visit_at + Vector3.UP * (length * 0.4 + 0.2)
	var to := at - global_position
	if to.length() < length + 0.3:
		_visit_t -= delta
		bite = 0.6
		if _visit_t <= -_rng.randf_range(5.0, 7.0):
			visit_at = Vector3.INF
			_visit_t = _rng.randf_range(30.0, 70.0)
		return Vector4(heading.x, 0.0, heading.z, 0.03)
	_visit_t = 0.0
	var t := to.normalized()
	return Vector4(t.x, t.y, t.z, 0.45)


# A pack hunter at a swarm: round it with the others, closing it into a ball, then now and then a
# dash through it, mouth open (each one's turn comes on its own clock, so they take turns).
func _pack(delta: float) -> Vector4:
	_pack_t -= delta
	if _pack_t <= 0.0:
		_dash = not _dash
		_pack_t = _rng.randf_range(1.0, 1.6) if _dash else _rng.randf_range(2.5, 5.5)
	var off := global_position - prey_at
	var d := maxf(off.length(), 0.01)
	if _dash:
		bite = 1.0
		feeding = d < prey_r + length
		var t := (-off / d) if d > prey_r * 0.25 else heading
		return Vector4(t.x, t.y, t.z, 1.6)
	var flat := Vector3(off.x, 0.0, off.z)
	var fl := maxf(flat.length(), 0.01)
	var round_way := Vector3(-flat.z, 0.0, flat.x) / fl * _turn_way
	var ring := prey_r + 1.2 + length * 0.6
	var w := round_way + flat / fl * clampf((ring - fl) * 0.6, -1.0, 1.0)
	w.y = clampf(-off.y * 0.4, -0.6, 0.6)
	return Vector4(w.x, w.y, w.z, 0.9)


# A filter feeder cruises through the cloud or swarm, mouth wide.
func _filter() -> Vector4:
	var to := prey_at - global_position
	var d := to.length()
	feeding = d < prey_r + length * 0.6
	if d < prey_r + length * 1.5:
		bite = 1.0
	var t := to / maxf(d, 0.01)
	if d < prey_r * 0.4:
		t = heading
	return Vector4(t.x, t.y, t.z, 0.5)


# A drifter goes where the water takes it, bobbing, hardly steering.
func _drift(delta: float) -> Vector4:
	var s := float(get_instance_id() % 1000) * 0.37
	var w := Vector3(sin(s + _clock * 0.05), sin(_clock * 0.4 + s) * 0.6, cos(s * 1.3 + _clock * 0.04))
	_goal_time -= delta
	if _goal_time <= 0.0:
		_goal = somewhere()
		_goal_time = 30.0
	w += (_goal - global_position).normalized() * 0.4
	return Vector4(w.x, w.y, w.z, 0.25 / maxf(Fish.pace(length) * slow, 0.05) * 0.6)


# A seahorse clings to its holdfast, and moves to another now and then; a clownfish or a
# garibaldi keeps to its own home.
func _stay(delta: float) -> Vector4:
	_lair_time -= delta
	if _lair_time <= 0.0:
		_lair = somewhere() if habit == "cling" else _lair
		_lair_time = _rng.randf_range(15.0, 30.0)
		_goal = _lair + Vector3(_rng.randf_range(-1.0, 1.0), _rng.randf_range(0.0, 0.6), _rng.randf_range(-1.0, 1.0)) * (length * 4.0)
	var at := _lair if habit == "cling" else _goal
	var to := at - global_position
	var d := to.length()
	if d < maxf(length * 0.6, 0.15):
		return Vector4(heading.x, 0.0, heading.z, 0.02)
	return Vector4(to.x, to.y, to.z, 0.4 if d > 1.0 else 0.2)


# A leap: out through the surface; a flying fish spreads its wings and glides.
func _leap_start() -> void:
	airborne = true
	var flat := Vector3(heading.x, 0.0, heading.z).normalized()
	var pace := maxf(_speed, Fish.pace(length))
	var lift := 3.0 if _has & (1 << L_WINGS) else 3.2 + length * 0.4
	_vel = flat * pace * 1.2 + Vector3.UP * lift
	_leap_cool = _rng.randf_range(4.0, 10.0)


func _fly(delta: float) -> void:
	var gliding := _has & (1 << L_WINGS) != 0 and _vel.y < 0.5 and _leap_cool > 1.0
	_vel.y -= (2.2 if gliding else 9.0) * delta
	var next := global_position + _vel * delta
	var held := Sea.keep_in(Vector3(next.x, Sea.SURFACE - 1.0, next.z), 0.3)
	global_position = Vector3(held.x, next.y, held.z)
	heading = _vel.normalized()
	if global_position.y < Sea.SURFACE - 0.1 and _vel.y < 0.0:
		airborne = false
		heading.y = clampf(heading.y, -0.5, 0.5)
		heading = heading.normalized()
		_speed = _vel.length() * 0.7
	_arch = lerpf(_arch, -0.6 if _vel.y > 0.0 else 0.4, 1.0 - exp(-4.0 * delta))
	pose(delta, 0.4, 0.0)
	if _has & (1 << L_WINGS):
		# (set straight: Fish.pose moves the wings too)
		_look.set(&"wings", 1.0 if gliding or _vel.y > 0.0 else 0.0)
	if _has & (1 << L_ARCH):
		_put(L_ARCH, _arch)


# What it shows of what it is doing, on its creature's own settings (only those it has, only
# when they change, only when it is in sight).
func _show(delta: float, to_player: Vector3, far: float, player: Player) -> void:
	if _has == 0 or not visible:
		return
	if _has & (1 << L_PUFF):
		_put(L_PUFF, move_toward(float(_look.get(&"puff")), 1.0 if _alarm > 0.4 else 0.0, delta * 1.2))
	if _has & (1 << L_OPEN) and _base_open >= 0.0:
		_put(L_OPEN, _base_open * (1.0 - _alarm))
	if _has & (1 << L_FURL):
		_put(L_FURL, _alarm)
	if _has & (1 << L_TUCK):
		_put(L_TUCK, _alarm)
	if _has & (1 << L_DIG):
		_put(L_DIG, _alarm)
	if _has & (1 << L_THREAT) and far < 6.0:
		_look.set(&"threat", global_basis.inverse() * (to_player / maxf(far, 0.01)) * _alarm)
	if _has & (1 << L_GRIP):
		_put(L_GRIP, move_toward(_sent[L_GRIP], 1.0 if _speed < 0.08 else 0.0, delta * 2.0))
	if _has & (1 << L_SIT):
		_put(L_SIT, move_toward(_sent[L_SIT], 1.0 if habit == "ambush" and _speed < 0.15 and mode == Mode.WANDER else 0.0, delta * 1.5))
	if _has & (1 << L_LURE):
		# (bright and steady while it waits; flickering as it is about to strike)
		_put(L_LURE, (0.4 + 0.6 * float(sin(_clock * 40.0) > 0.0)) if _warn > 0.0 else 0.85 + 0.15 * sin(_clock * 2.0))
	if _has & (1 << L_SCOOPS):
		_put(L_SCOOPS, move_toward(_sent[L_SCOOPS], 1.0 if bite > 0.5 else 0.0, delta * 1.5))
	if _has & (1 << L_FLARE):
		_put(L_FLARE, move_toward(_sent[L_FLARE], 1.0 if player.alive and far < 0.5 + player.length * 3.0 else 0.0, delta * 3.0))
	if _has & (1 << L_SPREAD):
		var open := (1.0 if far < 1.5 + length * 6.0 else 0.6) if habit == "sting" else _alarm
		_put(L_SPREAD, move_toward(_sent[L_SPREAD], open, delta * 2.0))
	if _has & (1 << L_STRIKE):
		_reflex(far)
		_put(L_STRIKE, _strike)
	if _has & (1 << L_SNAP):
		_reflex(far)
		if kind == "gar":
			# (a gar strikes sideways)
			_put(L_SNAP, _strike * signf(heading.cross(to_player).y + 0.001))
		else:
			_put(L_SNAP, _strike)
	if _has & (1 << L_ARCH):
		_put(L_ARCH, _arch)
	if _has & (1 << L_AFLOAT):
		_put(L_AFLOAT, move_toward(_sent[L_AFLOAT], 1.0 if _surfacing == 2 else 0.0, delta * 1.0))
	if _has & (1 << L_SWIM) and (habit == "hop" or habit == "shy"):
		# (a clam claps only when it swims off; a feather star stays put)
		# (set straight: Fish.pose sets `swim` too)
		_look.set(&"swim", 1.0 if _hop.length_squared() > 0.01 else 0.0)
	if _has & (1 << L_EYES) and far < 5.0:
		# (it watches what comes near)
		var t := to_player / maxf(far, 0.01)
		_look.set(&"eye_look", Vector2(clampf(t.dot(heading) * 0.8, -1.0, 1.0), clampf(t.y, -1.0, 1.0)))


# A small one's reflex: the player within reach and it strikes (a mantis shrimp's punch, a pistol
# shrimp's snap); a hunter's strike as it closes (Mode.HUNT sets `_strike`).
func _reflex(far: float) -> void:
	if habit == "strike" and far < 0.25 + length * 3.0 and _strike_cool <= 0.0:
		_strike = 1.0
		_strike_cool = 1.6


func _put(which: int, value: float) -> void:
	if absf(_sent[which] - value) > 0.004:
		_sent[which] = value
		_look.set(_LOOKS[which], value)


# The lowest it goes at a place: the floor, and room for itself over it.
func _floor_at(x: float, z: float) -> float:
	return Sea.ground(x, z) + (_stands() if on_floor else maxf(length * 0.3, 0.3))


# The middle of where it lives.
func _home() -> Vector3:
	if zones.is_empty():
		return Vector3(0.0, global_position.y, 0.0)
	var at: Vector2 = Sea.ZONES[zones[0]].at
	return Vector3(at.x, global_position.y, at.y)
