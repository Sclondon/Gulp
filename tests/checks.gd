extends Node
## The smoke test's checks (`-- --check`, run by tests/smoke.sh): the sea is stocked, the
## player starts small, eats a krill put in its mouth, cannot eat what is its own size, grows
## into the next fish when fed, is fled from by a smaller fish, is hunted down and eaten by a
## bigger one, starts again small, and is stung by a jelly bigger than it. Prints a CHECK line
## each and GULP SMOKE PASSED or FAILED, then quits.

var main: Node

var _bad := 0


func _ready() -> void:
	_run.call_deferred()


func _run() -> void:
	var life: Life = main.life
	var player: Player = main.player
	life.hunting = false
	await _frames(30)
	_check("the sea is stocked", life.creatures.size() == 32 and life.schools.size() == 10 and life.jellies.size() == 9,
			"%d fish, %d schools, %d jellies" % [life.creatures.size(), life.schools.size(), life.jellies.size()])
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
	_check("cannot eat a sardine yet", not Life.can_eat(player.length, Life.SARDINE_LENGTH))
	# Fed, it becomes the next fish, bigger.
	var was := player.length
	for n in 40:
		if player.stage > 0:
			break
		player.feed(player.length)
	_check("grows into the next fish", player.stage == 1 and player.kind == "smolt" and player.length > was, "%s %.2f m" % [player.kind, player.length])
	_check("can eat a sardine now", Life.can_eat(player.length, Life.SARDINE_LENGTH))
	# A smaller fish near it flees.
	player.progress = 0.9
	player.feed(0.01)
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
	big.place(player.global_position - player.heading * 3.0)
	big.heading = player.heading
	var hunted := false
	for n in 900:
		await _frames(1)
		hunted = hunted or big.mode == Creature.Mode.HUNT
		if not player.alive:
			break
	_check("a bigger fish hunts it", hunted)
	_check("being eaten ends the run", not player.alive and main.over and main.hud.over)
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
	print("GULP SMOKE PASSED" if _bad == 0 else "GULP SMOKE FAILED (%d)" % _bad)
	get_tree().quit()


func _frames(count: int) -> void:
	for n in count:
		await get_tree().process_frame


func _check(what: String, good: bool, note := "") -> void:
	if not good:
		_bad += 1
	print("CHECK %s: %s%s" % [what, "ok" if good else "BAD", ("  (" + note + ")") if note != "" else ""])
