extends Node
## The smoke test's checks (`-- --check`, run by tests/smoke.sh): the sea is stocked, the
## player starts small, eats a krill put in its mouth, cannot eat what is its own size, grows
## into the next fish when fed, is fled from by a smaller fish, is hunted down and eaten by a
## bigger one, starts again small, and is stung by a jelly bigger than it. Prints a CHECK line
## each and GULP SMOKE PASSED or FAILED, then quits.

var main: Node
## The touch checks instead (`-- --check=touch`, in a window: tests/touch.sh): touches sent as
## a finger would send them work the stick, the burst button and the start-again button.
var touch := false

var _bad := 0


func _ready() -> void:
	_run.call_deferred()


func _run() -> void:
	if touch:
		await _touches()
		return
	var life: Life = main.life
	var player: Player = main.player
	life.hunting = false
	await _frames(30)
	_check("the sea is stocked", life.creatures.size() >= 30 and life.schools.size() >= 10 and life.jellies.size() == 9,
			"%d fish, %d schools, %d jellies, %d nettles" % [life.creatures.size(), life.schools.size(), life.jellies.size(), life.nettles.size()])
	_check("starts as the smallest fish", player.alive and player.stage == 0 and player.kind == "sardine", "%s %.2f m" % [player.kind, player.length])
	# A krill in its mouth is eaten.
	var krill: Dictionary = life.schools[0]
	var cloud: Flock = krill.flock
	cloud.global_position = player.global_position
	krill.goal = player.global_position
	var meals := player.meals
	var progress := player.progress
	for n in 30:
		cloud.move_boid(0, player.mouth())
		await _frames(1)
		if player.meals > meals:
			break
	_check("eats a krill", player.meals > meals and player.progress > progress, "meals %d, progress %.3f" % [player.meals, player.progress])
	_check("cannot eat a sardine yet", not Life.is_food(player.length, Life.SARDINE_LENGTH))
	# Fed, it becomes the next fish, bigger.
	var was := player.length
	for n in 40:
		if player.choosing:
			main._on_picked("smolt")
		if player.stage > 0:
			break
		player.feed(player.length)
	_check("grows into the next fish", player.stage == 1 and player.kind == "smolt" and player.length > was * 0.9, "%s %.2f m" % [player.kind, player.length])
	_check("can eat a sardine now", Life.is_food(player.length, Life.SARDINE_LENGTH))
	_check("a shark does not graze on krill", not Life.is_food(3.0, Life.KRILL_LENGTH) and Life.is_food(3.0, 1.0))
	# A smaller fish near it flees.
	player.progress = 0.9
	player.feed(0.05)
	var small: Creature = life.creatures[0]
	small.length = 0.3
	small.place(player.global_position + player.global_basis.x * 2.0)
	var apart := small.global_position.distance_to(player.global_position)
	await _frames(20)
	var fled := small.away <= 0.0 and small.mode == Creature.Mode.FLEE
	await _frames(40)
	_check("a smaller fish flees", fled and small.global_position.distance_to(player.global_position) > apart,
			"%.1f m then %.1f m" % [apart, small.global_position.distance_to(player.global_position)])
	# A bigger fish hunts it down and eats it.
	life.hunting = true
	player.safe = 0.0
	var big: Creature
	for each in life.creatures:
		if each.kind == "salmon":
			big = each
			break
	# (a small one: a bigger salmon takes no notice of so small a fish)
	big.length = 0.9
	big.place(player.global_position - player.heading * 1.6)
	big.heading = player.heading
	big._tired = 0.0
	var hunted := false
	for n in 900:
		await _frames(1)
		hunted = hunted or big.mode == Creature.Mode.HUNT
		if not player.alive:
			break
	_check("a bigger fish hunts it", hunted)
	_check("being eaten ends the run", not player.alive and main.over and main.hud.over, "%s %.2f m, hunter %.2f m %.1f m off, mode %d, choosing %s" % [player.kind, player.length, big.length, big.global_position.distance_to(player.global_position), big.mode, player.choosing])
	# Another run starts small.
	main.restart()
	await _frames(5)
	_check("starts again small", player.alive and player.stage == 0 and not main.over and player.length < 0.2, "%s %.2f m" % [player.kind, player.length])
	# A jelly wider than it can eat stings it.
	life.hunting = false
	await _frames(200)
	life.hunting = true
	var jelly: MoonJelly = life.jellies[life.jellies.size() - 1]
	for n in 60:
		jelly.global_position = player.global_position + player.heading * 0.1
		await _frames(1)
		if not player.alive:
			break
	_check("a big jelly stings it", not player.alive)
	await _fishing()
	print("GULP SMOKE PASSED" if _bad == 0 else "GULP SMOKE FAILED (%d)" % _bad)
	get_tree().quit()


## Hooks, nets and trawls (scripts/fishers.gd): a bait hooks it and the struggle frees it; left on
## the line it is hauled out; too big, it snaps the line; a net holds a fish of its size until it
## struggles free, lets a smaller one through and is torn by a bigger one; a trawl catches a fish
## that stays in it, not one that swims out of its mouth, and lets a big one through.
func _fishing() -> void:
	var life: Life = main.life
	var player: Player = main.player
	var fishers: Fishers = main.fishers
	var by := [""]
	player.died.connect(func(what: String) -> void: by[0] = what)
	life.hunting = false
	fishers.always = true
	# A hook.
	main.restart()
	await _frames(3)
	var rig: Fishers.Rig = fishers.rigs[0]
	await _to_bait(rig)
	_check("a bait hooks it", fishers.holding == "hook" and player.caught, "%s, %s %.2f m, bait %.2f m" % [fishers.holding, player.kind, player.length, rig.bait_long])
	player.boost_held = true
	_aim(player, Vector3.DOWN + Vector3.RIGHT * 0.3)
	var hooked_for := 0
	for n in 400:
		await _frames(1)
		hooked_for = n
		if fishers.holding == "":
			break
	player.boost_held = false
	_check("struggling frees it from the hook", fishers.holding == "" and player.alive and not player.caught and rig.away > 0.0, "%.1f s" % (hooked_for / 60.0))
	main.restart()
	await _frames(3)
	rig = fishers.rigs[1]
	await _to_bait(rig)
	by[0] = ""
	for n in 1200:
		await _frames(1)
		if not player.alive:
			break
	_check("left on the line it is hauled out", not player.alive and by[0] == "hook" and main.over, "hauled at %.2f m/s, caught by %s" % [fishers.rigs[1].haul, by[0]])
	main.restart()
	await _frames(3)
	rig = fishers.rigs[5]
	player.begin(player.global_position, "bluefin")
	await _to_bait(rig)
	_check("a fish too big for the hook snaps the line", fishers.holding == "" and rig.away > 0.0 and player.alive, "%s %.2f m, snaps over %.2f m" % [player.kind, player.length, rig.snap])
	main.restart()
	await _frames(3)
	rig = fishers.rigs[5]
	rig.away = 0.01
	await _frames(2)
	await _to_bait(rig, 20)
	_check("a fish too small for the bait leaves it", fishers.holding == "", "%s %.2f m, bait %.2f m" % [player.kind, player.length, rig.bait_long])
	# A net.
	var net: Fishers.Net = fishers.nets[0]
	main.restart()
	await _frames(3)
	player.begin(player.global_position, "smolt")
	await _into_net(net, 0.3)
	_check("a net holds a fish of its size", fishers.holding == "net" and player.caught, "%s %.2f m, holds %.2f to %.2f m" % [player.kind, player.length, net.lo, net.hi])
	player.boost_held = true
	var held_for := 0
	for n in 400:
		await _frames(1)
		held_for = n
		if fishers.holding == "":
			break
	player.boost_held = false
	_check("struggling frees it from the net, through a hole", fishers.holding == "" and player.alive and net.side(player.global_position) < 0.0 and net.holes.size() > 0,
			"%.1f s, %d holes" % [held_for / 60.0, net.holes.size()])
	main.restart()
	await _frames(3)
	await _into_net(net, 0.5)
	await _frames(30)
	_check("a fish too small swims through the net", fishers.holding == "" and net.side(player.global_position) < 0.0, "%s %.2f m" % [player.kind, player.length])
	main.restart()
	await _frames(3)
	player.begin(player.global_position, "white_shark")
	var holes := net.holes.size()
	await _into_net(net, 0.75)
	await _frames(40)
	_check("a fish too big tears through the net", fishers.holding == "" and net.holes.size() > holes and net.side(player.global_position) < 0.0, "%s %.2f m" % [player.kind, player.length])
	# A trawl.
	var trawler: Fishers.Trawler = fishers.trawlers[0]
	main.restart()
	await _frames(3)
	player.begin(player.global_position, "smolt")
	player.throttle = 0.0
	await _into_trawl(trawler)
	var got_in := fishers.holding == "trawl"
	by[0] = ""
	for n in 1200:
		await _frames(1)
		if not player.alive:
			break
	player.throttle = 1.0
	_check("a trawl catches a fish that stays in it", got_in and not player.alive and by[0] == "trawl", "in %s, %s" % [got_in, by[0]])
	main.restart()
	await _frames(3)
	player.begin(player.global_position, "smolt")
	await _into_trawl(trawler)
	got_in = fishers.holding == "trawl"
	_aim(player, -trawler.trawl.global_basis.z)
	player.boost_held = true
	await _frames(150)
	player.boost_held = false
	_check("a fish swims out of a trawl's mouth", got_in and fishers.holding == "" and player.alive and trawler.frame_of(player.global_position).z < 0.0,
			"in %s, %.1f m ahead of its mouth" % [got_in, -trawler.frame_of(player.global_position).z])
	main.restart()
	await _frames(3)
	player.begin(player.global_position, "white_shark")
	await _into_trawl(trawler)
	await _frames(30)
	_check("a fish too big goes through a trawl", fishers.holding == "" and player.alive, "%s %.2f m" % [player.kind, player.length])
	fishers.always = false


# Holds the player's mouth at a rig's bait until it bites (or `frames` go by).
func _to_bait(rig: Fishers.Rig, frames := 60) -> void:
	var player: Player = main.player
	_aim(player, Vector3(1.0, -0.2, 0.0))
	for n in frames:
		player.global_position = rig.bait_at() - player.heading * (player.length * 0.42 + 0.02)
		await _frames(1)
		if main.fishers.holding != "" or rig.away > 0.0:
			return


# Puts the player a little in front of a net (on its +normal side, a share of the way along it),
# swimming into it.
func _into_net(net: Fishers.Net, along: float) -> void:
	var player: Player = main.player
	var at := net.a.lerp(net.b, along)
	at.y = lerpf(net.top, net.bottom, 0.4)
	player.global_position = at + net.normal * (0.6 + player.length * 0.5)
	_aim(player, -net.normal)
	main.fishers.restart()
	for n in 90:
		await _frames(1)
		if main.fishers.holding != "" or net.side(player.global_position) < 0.0:
			return


# Puts the player just in front of a trawl's mouth, facing back into it, until it is in.
func _into_trawl(trawler: Fishers.Trawler) -> void:
	var player: Player = main.player
	player.global_position = trawler.trawl.global_transform * Vector3(0.0, 0.0, -0.4)
	_aim(player, trawler.trawl.global_basis.z)
	main.fishers.restart()
	for n in 30:
		await _frames(1)
		if main.fishers.holding != "" or trawler.frame_of(player.global_position).z > 1.0:
			return


func _aim(player: Player, way: Vector3) -> void:
	way = way.normalized()
	player.yaw = atan2(-way.x, -way.z)
	player.pitch = asin(clampf(way.y, -1.0, 1.0))
	player.heading = way


func _frames(count: int) -> void:
	for n in count:
		await get_tree().process_frame


func _check(what: String, good: bool, note := "") -> void:
	if not good:
		_bad += 1
	print("CHECK %s: %s%s" % [what, "ok" if good else "BAD", ("  (" + note + ")") if note != "" else ""])


func _touches() -> void:
	# (deaf to the real mouse, keys and gamepad as far as can be: the window never has focus)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_NO_FOCUS, true)
	var life: Life = main.life
	var player: Player = main.player
	var pad: TouchPad = main.pad
	life.hunting = false
	await _frames(30)
	var u := pad.unit()
	# The stick, pushed right: the fish turns right.
	var yaw := player.yaw
	_touch(0, pad.stick_home() + Vector2(70.0 * u, 0.0), true)
	await _frames(30)
	_check("the stick pushed right turns the fish right", pad.stick.x > 0.4 and player.yaw < yaw - 0.2, "stick %.2f, yaw %.2f to %.2f" % [pad.stick.x, yaw, player.yaw])
	# Dragged up: nose up.
	var pitch := player.pitch
	_drag(0, pad.stick_home() + Vector2(0.0, -90.0 * u))
	await _frames(30)
	_check("the stick pushed up lifts its nose", pad.stick.y > 0.5 and player.pitch > pitch + 0.2, "stick %.2f, pitch %.2f to %.2f" % [pad.stick.y, pitch, player.pitch])
	# The burst button, with another finger.
	_touch(1, pad.boost_home(), true)
	await _frames(30)
	_check("the round button is a burst", pad.boost and player.boosting and player.stamina < 0.95, "stamina %.2f" % player.stamina)
	_touch(0, pad.stick_home(), false)
	_touch(1, pad.boost_home(), false)
	await _frames(5)
	_check("letting go lets go", pad.stick == Vector2.ZERO and not pad.boost and not player.boosting)
	# The speed lever: pulled to dead slow the fish slows, pushed to full ahead it speeds up; it stays
	# where it is put, and a touch on it is not a burst.
	_touch(2, pad.lever_at(0.0), true)
	await _frames(120)
	var slow := player.velocity.length()
	var slow_set := pad.throttle
	var burst_meanwhile := pad.boost
	_drag(2, pad.lever_at(1.0))
	_touch(2, pad.lever_at(1.0), false)
	await _frames(60)
	_check("the lever sets the speed", slow_set < 0.1 and pad.throttle > 0.9 and player.velocity.length() > slow * 1.5 and not burst_meanwhile,
			"lever %.2f then %.2f, %.2f m/s then %.2f" % [slow_set, pad.throttle, slow, player.velocity.length()])
	# The run over: the round arrow starts another.
	player.safe = 0.0
	player.die("test")
	await _frames(50)
	var again: Control = main.hud.get_child(0)
	_check("the start-again button shows", main.over and again.visible)
	var middle := again.global_position + again.size * 0.5
	_touch(0, middle, true)
	await _frames(3)
	_touch(0, middle, false)
	await _frames(10)
	_check("a tap on it starts another run", not main.over and player.alive and pad.visible)
	print("GULP TOUCH PASSED" if _bad == 0 else "GULP TOUCH FAILED (%d)" % _bad)
	get_tree().quit()


# A finger down or up at a place on the screen (given in the game's own units, sent in window pixels).
func _touch(finger: int, at: Vector2, down: bool) -> void:
	var event := InputEventScreenTouch.new()
	event.index = finger
	event.position = get_viewport().get_final_transform() * at
	event.pressed = down
	Input.parse_input_event(event)


func _drag(finger: int, to: Vector2) -> void:
	var event := InputEventScreenDrag.new()
	event.index = finger
	event.position = get_viewport().get_final_transform() * to
	Input.parse_input_event(event)
