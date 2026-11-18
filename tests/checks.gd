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
	# (the depth limit is off but for its own check: other checks put the fish deep)
	main.limited = false
	player.deepest = INF
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
		if cloud.rider_count() > 0:
			# (a swarm: its first rider's guide put so that the rider is at the mouth)
			cloud.move_boid(cloud.rider_lead(0), player.mouth() - cloud.rider_place(0))
		else:
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
	life.wake(small)
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
	life.wake(big)
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
	await _schooling()
	await _fishing()
	await _loop()
	print("GULP SMOKE PASSED" if _bad == 0 else "GULP SMOKE FAILED (%d)" % _bad)
	get_tree().quit()


## Schooling (tools/SCHOOLING.md): a swarm loses the one fish at the mouth and has it back later,
## scatters round the player and gathers again; a group keeps together; an ambusher warns before it
## lunges; a pufferfish blows up and cannot be eaten; a seal goes up for air; a lionfish stings
## without killing; pack hunters at a swarm take from it and ball it up.
func _schooling() -> void:
	var life: Life = main.life
	var player: Player = main.player
	life.hunting = false
	main.restart()
	await _frames(3)
	player.begin(player.global_position, "smolt")
	# A swarm: the fish at the mouth is taken, and the swarm parts round the player.
	var ball: Dictionary = life.schools[Life.KRILL_CLOUDS]
	var flock: Flock = ball.flock
	var at := flock.global_position
	player.global_position = at + Vector3(12.0, 0.0, 0.0)
	await _frames(5)
	var spread_before := _spread(flock)
	var meals := player.meals
	var gone := flock.riders_gone()
	var taken := -1
	for n in 20:
		var i := flock.nearest_rider(flock.boid_position(0), 1.0)
		if i < 0:
			await _frames(1)
			continue
		_aim(player, Vector3.FORWARD)
		player.global_position = flock.rider_position(i) - player.heading * player.length * 0.42
		await _frames(1)
		if player.meals > meals:
			taken = i
			break
	_check("the fish of a swarm at its mouth is eaten, and not drawn", player.meals > meals and taken >= 0 and flock.rider_gone(taken) and flock.riders_gone() > gone,
			"%d riders, %d gone, meals %d to %d" % [flock.rider_count(), flock.riders_gone(), meals, player.meals])
	var frightened := 0
	for n in 60:
		player.global_position = flock.middle()
		await _frames(1)
	for g in flock.boid_count():
		if flock.fear_of(g) > 0.05:
			frightened += 1
	var spread_during := _spread(flock)
	_check("a swarm scatters from the player in it", frightened > 0 and spread_during > spread_before * 1.05,
			"%d guides frightened, spread %.2f m to %.2f m" % [frightened, spread_before, spread_during])
	for n in 900:
		player.global_position = at + Vector3(30.0, 0.0, 0.0)
		await _frames(1)
	player.global_position = flock.middle() + Vector3(10.0, 0.0, 0.0)
	await _frames(2)
	var spread_after := _spread(flock)
	_check("it gathers again, and the eaten one comes back", spread_after < spread_during and not flock.rider_gone(taken),
			"spread %.2f m, gone %d" % [spread_after, flock.riders_gone()])
	# A group keeps together (and lines up, a school).
	var group: Creature.Group
	for g: Creature.Group in life.groups:
		if g.social == "school" and g.members.size() >= 3 and g.members[0].length > 0.3:
			group = g
			break
	var lead: Creature = group.members[0]
	player.global_position = lead.global_position + Vector3(0.0, 0.0, 14.0)
	for n in 600:
		player.global_position = group.mid + Vector3(0.0, 0.0, 14.0)
		await _frames(1)
	var far_out := 0.0
	var lined := 0.0
	for m in group.members:
		far_out = maxf(far_out, m.global_position.distance_to(group.mid) / m.length)
		lined += m.heading.dot(group.way)
	lined /= group.members.size()
	_check("a school keeps together, lined up", far_out < group.space * 4.0 and lined > 0.6,
			"%s ×%d: furthest %.1f lengths from the middle, lined up %.2f" % [lead.kind, group.members.size(), far_out, lined])
	# An ambusher warns (mouth wide open) before it lunges.
	life.hunting = true
	player.begin(player.global_position, "smolt")
	player.safe = 0.0
	var lurker := _one_of(["grouper"])
	# (one small enough to take notice of a smolt: Life.TOO_SMALL)
	lurker.length = 1.0
	lurker._tired = 0.0
	var warned_at := -1
	var lunged_at := -1
	var gaped := false
	for n in 120:
		_aim(player, lurker.heading)
		player.global_position = lurker.global_position + lurker.heading * (Creature.LUNGE_REACH + lurker.length * 0.9)
		player.safe = 0.0
		await _frames(1)
		if warned_at < 0 and lurker._warn > 0.0:
			warned_at = n
		if warned_at >= 0 and lurker.bite > 0.5:
			gaped = true
		if lurker._lunge > 0.0:
			lunged_at = n
			break
		if not player.alive:
			break
	_check("an ambusher opens wide before it lunges", warned_at >= 0 and gaped and lunged_at > warned_at + 20,
			"%s: warned at frame %d, lunged at %d" % [lurker.kind, warned_at, lunged_at])
	life.hunting = false
	main.restart()
	await _frames(3)
	# A pufferfish near a fish that could eat it blows up, and cannot be eaten.
	player.begin(player.global_position, "salmon")
	var puffer := _one_of(["pufferfish"])
	if puffer:
		for n in 90:
			_aim(player, puffer.global_position - player.global_position)
			player.global_position = puffer.global_position - player.heading * 1.0
			await _frames(1)
		for n in 30:
			player.global_position = puffer.global_position - player.heading * player.length * 0.42
			await _frames(1)
		_check("a pufferfish blows up and cannot be eaten", puffer.guarded() and puffer.away <= 0.0, "puffed %s" % puffer.guarded())
	# A seal out of breath goes up for air.
	var seal := _one_of(["seal", "sea_lion", "dolphin"])
	if seal:
		# (in open water 8 m down by the start: one wandering in the real bay's shallows is already as
		# high as it can go)
		seal.place(Vector3(Sea.START.x, Sea.SURFACE - 8.0, Sea.START.y))
		player.global_position = seal.global_position + Vector3(0.0, 0.0, 6.0)
		seal._air = 0.0
		var top := -INF
		# (up to 30 s)
		for n in 1800:
			player.global_position = seal.global_position + Vector3(0.0, 0.0, 6.0)
			await _frames(1)
			top = maxf(top, seal.global_position.y)
			if top > Sea.SURFACE - 0.5 - seal.length * 0.4:
				break
		_check("a %s goes up for air" % seal.kind, top > Sea.SURFACE - 0.5 - seal.length * 0.4, "reached %.1f m, the surface at %.1f; %s %.1f m long at %s, floor %.1f" % [top, Sea.SURFACE, seal.kind, seal.length, seal.global_position, Sea.ground(seal.global_position.x, seal.global_position.z)])
	# A lionfish's spines hurt a fish too small to eat it, and do not kill it.
	main.restart()
	await _frames(3)
	life.hunting = true
	var lion := _one_of(["lionfish"])
	if lion:
		lion.back_off()
		lion._tired = 99.0
		var stings := life.stings
		for n in 20:
			player.safe = 0.0
			player.global_position = lion.global_position + lion.global_basis.x * (lion.length * 0.3)
			await _frames(1)
			if life.stings > stings:
				break
		_check("a lionfish stings: a hurt, not a death", life.stings > stings and player.alive and player.stamina < 0.2,
				"stings %d, alive %s, burst %.2f" % [life.stings - stings, player.alive, player.stamina])
		lion._tired = 0.0
	life.hunting = false
	# Pack hunters at a swarm take from it and ball it up.
	var pack: Array[Creature] = []
	for each in life.creatures:
		if each.kind == "barracuda" and pack.size() < 3:
			pack.append(each)
			life.wake(each)
	var swarm: Dictionary = life.schools[Life.KRILL_CLOUDS + 1]
	var prey: Flock = swarm.flock
	var gone_before := prey.riders_gone()
	var most_gone := 0
	var balled := false
	# (Two parts, so that it does not hang on chance. A dash takes a fish only when a fish is at the
	# hunter's mouth at one of its few tries a second, and the swarm flees the hunters, so left to
	# itself the first fish went after 3 to 47 s or more of game time (it failed about one run in
	# three in 10 s, and sometimes in 60): first the pack is left to find the swarm and ball it up;
	# then one of them, dashing, has its open mouth put on one of the swarm's fish each frame, and
	# Life's own feeding must take it.)
	var took_at := -1
	var biter: Creature = null
	for n in 600:
		player.global_position = prey.middle() + Vector3(0.0, 4.0, 9.0)
		for k in pack.size():
			if n == 0:
				pack[k].place(prey.middle() + Vector3(4.0 + k, 0.0, 0.0))
		await _frames(1)
		balled = balled or prey.rules.orbit > 0.0
		for each in pack:
			if biter == null and each.prey is Dictionary and each.prey.flock == prey:
				biter = each
		if balled and biter:
			break
	if biter:
		for n in 300:
			player.global_position = prey.middle() + Vector3(0.0, 4.0, 9.0)
			biter._dash = true
			biter._pack_t = 1.0
			var fish := -1
			for i in prey.rider_count():
				# (one in open water: the swarm may hang among a biome's rocks, which push the hunter off it)
				if not prey.rider_gone(i) and Sea.clear_of_rocks(prey.rider_position(i), biter.length) == prey.rider_position(i):
					fish = i
					break
			if fish >= 0:
				biter.global_position = prey.rider_position(fish) - biter.heading * biter.length * 0.42
			# (a take is one more gone this frame than the last: eaten ones come back meanwhile, so the
			# count from before the pack arrived can fall below where it started)
			var was := prey.riders_gone()
			await _frames(1)
			most_gone = maxi(most_gone, prey.riders_gone())
			if prey.riders_gone() > was:
				took_at = n
				break
	_check("pack hunters at a swarm take from it and ball it up", took_at >= 0 and balled,
			"%d barracuda, %s at it, balled %s, a fish taken %s (%.1f s with its mouth among them)" % [pack.size(), biter != null, balled, took_at >= 0, took_at / 60.0])
	main.restart()
	await _frames(3)


# How far a flock's guides are from its middle, on average.
func _spread(flock: Flock) -> float:
	var mid := flock.centre()
	var sum := 0.0
	for g in flock.boid_count():
		sum += flock.boid_position(g).distance_to(mid)
	return sum / maxf(flock.boid_count(), 1.0)


# The first creature of one of some kinds, dressed and about.
func _one_of(kinds: Array) -> Creature:
	for kind: String in kinds:
		for each: Creature in main.life.creatures:
			if each.kind == kind and each.away <= 0.0:
				main.life.wake(each)
				if not each.dressed:
					each.dress()
				each.visible = true
				return each
	return null


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


## The treasure game's loop (DESIGN.md): swum into the boat's net the run ends as a sale, which pays
## the right sum and is saved; buying an amplifier step spends money and lets the fish deeper; below
## the amplifier's depth the picture fills with static and the fish is turned back up. (Into a test
## file, never the player's own save.)
func _loop() -> void:
	var life: Life = main.life
	var player: Player = main.player
	var purse: Purse = main.purse
	var path := "user://gulp_check.cfg"
	life.hunting = false
	purse.path = path
	purse.reset()
	main.restart()
	await _frames(3)
	player.begin(player.global_position, "salmon")
	main.set(&"_run_for", 99.0)
	var hoop: Vector3 = main.title.hoop()
	player.global_position = hoop + Vector3(2.0, 0.0, 0.3)
	_aim(player, hoop - player.mouth())
	for n in 240:
		await _frames(1)
		if main.selling or not player.alive:
			break
		_aim(player, hoop - player.mouth())
	_check("swimming into the boat's net ends the run as a sale", main.selling and not player.alive and not main.over and main.sale.visible,
			"selling %s, alive %s, %.2f m from the hoop" % [main.selling, player.alive, player.mouth().distance_to(hoop)])
	var got: Dictionary = main.receipt
	var worth: int = Purse.WORTH["salmon"]
	var expected := roundi(worth * float(got.get("length", 0.0))) + roundi(worth * Purse.FIRST_METRES)
	var kept := Purse.new(path)
	_check("a sale pays the right sum and saves it", got.get("kind", "") == "salmon" and int(got.total) == expected and purse.money == expected and kept.money == expected and "salmon" in kept.sold,
			"%s %.2f m: %d (expected %d), purse %d, saved %d" % [got.get("kind", ""), float(got.get("length", 0.0)), int(got.get("total", -1)), expected, purse.money, kept.money])
	_check("the first-sale bonus is paid once; the last of a line at full size is doubled",
			purse.price_of("salmon", 1.0, false).bonus == 0 and purse.price_of("orca", 8.0, true).total == Purse.WORTH["orca"] * 8 * 2 + roundi(Purse.WORTH["orca"] * Purse.FIRST_METRES))
	# The sale's button goes on to the shop; there a step of the amplifier is bought.
	main.limited = true
	main.sale.set(&"_for", 1.0)
	main.sale.call(&"_finish")
	await _frames(2)
	purse.money = Purse.AMP_PRICE[1] + 10
	var bought: bool = main.shop.visible and main.shop.buy_next()
	var again: bool = main.shop.buy_next()
	_check("buying a step spends money and raises the limit", bought and not again and purse.money == 10 and purse.amp == 1 and purse.depth() == Purse.AMP_DEPTH[1] and Purse.new(path).amp == 1,
			"shop %s, bought %s, money %d, depth %.0f m" % [main.shop.visible, bought, purse.money, purse.depth()])
	# The shop's button sends a new fish down from the boat, as deep as the amplifier now reaches.
	main.shop.set(&"_for", 1.0)
	main.shop.call(&"_finish")
	for n in 300:
		await _frames(1)
		if not main.get(&"_on_deck"):
			break
	_check("from the shop a new run starts by the boat, with the new limit", player.alive and not main.selling and not main.get(&"_on_deck") and player.deepest == Purse.AMP_DEPTH[1]
			and Vector2(player.global_position.x, player.global_position.z).distance_to(Vector2(main.title.global_position.x, main.title.global_position.z)) < 12.0,
			"alive %s, limit %.0f m" % [player.alive, player.deepest])
	# Below the amplifier's depth: static, and the fish is turned back up.
	purse.amp = 0
	player.deepest = purse.depth()
	var zone: Vector2 = Sea.ZONES["trench"].at
	player.global_position = Vector3(zone.x, Sea.SURFACE - purse.depth() - 1.0, zone.y)
	_aim(player, Vector3(0.3, -0.8, 0.0))
	var deepest_seen := 0.0
	var snow := 0.0
	for n in 180:
		await _frames(1)
		deepest_seen = maxf(deepest_seen, Sea.SURFACE - player.global_position.y)
		snow = maxf(snow, float(main.get(&"_post").get_shader_parameter(&"signal_loss")))
	var now := Sea.SURFACE - player.global_position.y
	_check("below the limit the picture fills with static and the fish is turned back", player.alive and now < purse.depth() and deepest_seen <= purse.depth() + Player.LIMIT_GIVE + 0.01 and snow > 0.5,
			"limit %.0f m: down to %.1f m, now %.1f m, static %.2f" % [purse.depth(), deepest_seen, now, snow])
	main.limited = false
	player.deepest = INF
	purse.reset()


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
	# The sale's round button goes on to the shop; a tap on the amplifier's next step buys it; the
	# shop's round button sends a new fish down from the boat.
	main.call(&"_sell")
	main.purse.money = 100
	# (each screen takes no touch for its first 0.4 s, so that a touch meant for the sea does not go through)
	await get_tree().create_timer(0.6).timeout
	await _tap(main.sale.get_child(0))
	_check("a tap on the sale's button opens the shop", not main.sale.visible and main.shop.visible)
	await get_tree().create_timer(0.6).timeout
	await _tap(main.shop.get_child(1))
	_check("a tap on the amplifier's next step buys it", main.purse.amp == 1 and main.purse.money == 100 - Purse.AMP_PRICE[1], "step %d, money %d" % [main.purse.amp, main.purse.money])
	await _tap(main.shop.get_child(main.shop.get_child_count() - 1))
	await _frames(5)
	_check("a tap on the shop's button dives again", not main.shop.visible and main.get(&"_on_deck") and player.alive)
	print("GULP TOUCH PASSED" if _bad == 0 else "GULP TOUCH FAILED (%d)" % _bad)
	get_tree().quit()


# A finger down or up at a place on the screen (given in the game's own units, sent in window pixels).
func _touch(finger: int, at: Vector2, down: bool) -> void:
	var event := InputEventScreenTouch.new()
	event.index = finger
	event.position = get_viewport().get_final_transform() * at
	event.pressed = down
	Input.parse_input_event(event)


# A finger down and up again on the middle of a control.
func _tap(control: Control) -> void:
	var middle := control.global_position + control.size * 0.5
	_touch(0, middle, true)
	await _frames(3)
	_touch(0, middle, false)
	await _frames(5)


func _drag(finger: int, to: Vector2) -> void:
	var event := InputEventScreenDrag.new()
	event.index = finger
	event.position = get_viewport().get_final_transform() * to
	Input.parse_input_event(event)
