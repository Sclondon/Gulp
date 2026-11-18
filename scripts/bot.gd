class_name Bot
extends RefCounted
## Plays the game by itself (`-- --bot`): it swims at the nearest thing it can eat, and away
## from anything that could end its run when that gets close, with a burst. It works the same
## stick and burst button a player does. For the tests, not for show.

var player: Player
var life: Life
## Hooks, nets and trawls: it keeps clear of them, and struggles free when one has it.
var fishers: Fishers

# When it last ate, and how many meals it had had then: a while with nothing eaten and it gives up
# on what it is after (something that keeps running, or that it cannot reach) for a school.
var _meals := -1
var _hungry := 0.0


## Sets the player's stick and burst for this frame.
func drive() -> void:
	if fishers and fishers.holding != "":
		_struggle()
		return
	var at := player.global_position
	var away := Vector3.ZERO
	var close := false
	var threats := life.threats()
	if fishers:
		threats.append_array(fishers.threats())
	for threat: Array in threats:
		var from: Vector3 = at - threat[0]
		var far := from.length()
		var alarm: float = 3.5 + float(threat[1]) * 2.5
		if far < alarm and far > 0.001:
			away += from / far * (alarm - far)
			close = close or far < alarm * 0.6
	var way := Vector3.ZERO
	var burst := false
	if away.length() > 0.001:
		# (away, and never into the sand or the edge of the sea)
		way = (away.normalized() - (at - Vector3(20.0, 0.0, 0.0)) * Vector3(1.0, 0.0, 1.0) / 120.0).normalized()
		burst = close
	else:
		# (a while with nothing eaten: it gives up on what it was after, for a cloud of krill, then tries
		# again; each drive is a sixtieth of a second)
		if player.meals != _meals:
			_meals = player.meals
			_hungry = 0.0
		_hungry += 1.0 / 60.0
		if _hungry > 16.0:
			_hungry = 0.0
		var food := life.nearest_food(_hungry > 6.0)
		if food != Vector3.INF:
			way = (food - player.mouth()).normalized()
			burst = at.distance_to(food) < 3.0 and player.stamina > 0.5
		else:
			# nothing to eat that it knows of: back towards the middle
			way = (Vector3(-20.0, Sea.SURFACE - 8.0, 0.0) - at).normalized()
	if way.length() < 0.001:
		way = player.heading
	var want_yaw := atan2(-way.x, -way.z)
	var want_pitch := asin(clampf(way.y, -1.0, 1.0))
	player.stick = Vector2(clampf(-wrapf(want_yaw - player.yaw, -PI, PI) * 3.0, -1.0, 1.0), clampf((want_pitch - player.pitch) * 3.0, -1.0, 1.0))
	player.boost_held = burst


## On a hook, in a net or in a trawl: it bursts, pointed the way out, and wriggles.
func _struggle() -> void:
	var way := fishers.way_out()
	var want_yaw := atan2(-way.x, -way.z)
	var want_pitch := asin(clampf(way.y, -1.0, 1.0))
	var wriggle := 0.6 * sin(Time.get_ticks_msec() * 0.012)
	player.stick = Vector2(clampf(-wrapf(want_yaw - player.yaw, -PI, PI) * 3.0 + wriggle, -1.0, 1.0), clampf((want_pitch - player.pitch) * 3.0, -1.0, 1.0))
	player.boost_held = true
