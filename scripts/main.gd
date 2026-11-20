extends Control
## Gulp (a placeholder name): you start as a small fish in a 3D sea, eat what is smaller than
## you, keep clear of what is bigger, and grow, through bigger and bigger fish. Being eaten
## ends the run, and you start again small.
##
## The sea is drawn in a SubViewport at half size and shown through Salmon Run 2's post shader
## (its underwater picture: swaying, tinted, banded and dithered), as Salmon Run 2 and Moon
## Jellies do it. Over it: the Hud and the TouchPad.
##
## Controls: the stick (or A/D and W/S, the arrow keys, a gamepad's left stick) turns the fish,
## which always swims the way it points; the round button (or Space, Shift, a gamepad's A) is
## a burst of speed. The lever round that button (or Q and E, a gamepad's shoulders) sets how fast
## it swims. When a run is over, the round arrow (or Enter, Space, a gamepad's A)
## starts another.
##
## Arguments (after --): --bot plays by itself and starts again when eaten; --seconds=<n> quits
## after n seconds (with --bot, printing how it did); --check runs the smoke test's checks
## (tests/checks.gd) and quits, --check=touch its touch checks (in a window); --as=<kind> starts runs as that animal (a name in Player.GROWTH; --stage=<n> is the old five by number); --calm:
## nothing hunts; --over ends the run at once (for a picture of that screen); --shot=<seconds>
## saves a picture at that time and quits (--out=<file>); --near=<jelly|shark|salmon|sardines|krill>
## starts the run beside one of those, with nothing hunting (to look at it); --sell sells the fish
## a second in (a picture of the sale screen), --shop then opens the shop.
##
## The loop (DESIGN.md): swimming into the net hung beside the boat ends a run as a sale (Purse,
## Sale), then the shop (Shop) buys the amplifier's steps, then the eye goes down from the boat
## to a new fish. Below the amplifier's depth the picture fills with static and the fish is
## turned back up.

const SAVE := "user://gulp.cfg"
## The shared sea of players lives on the site's server (--server=<url> for another; a web build
## joins it by itself, anything else only when told a server; --offline never does).
const ARENA_SERVER := "https://scareathon-v3-production.up.railway.app"

var sea: Sea
var life: Life
var player: Player
var camera: Camera3D
var hud: Hud
var pad: TouchPad
## The boat: the game starts on it (steaming round), and once under way it lies hove-to with its
## net out, where the fish is sold (DESIGN.md's loop); never null after _ready. Its card (null once
## the game has started), whether the eye is with the boat or on its way down from it to the fish
## (`_on_deck`), and how far down it has gone (-1: not yet started).
var title: Title
var _card: Title.Card
var _on_deck := false
var _dive := -1.0
## Money, gear and what has been sold, kept between runs (memory only when a test, the bot or a
## picture drives); the sale and shop screens; whether they are up (the run ended in the net).
var purse: Purse
var sale: Sale
var shop: Shop
var selling := false
## What the last sale fetched (Purse.sell's receipt).
var receipt := {}
## The machine's depth limit holds (the smoke test turns it off but for its own check).
var limited := true
## How close the fish's mouth must come to the middle of the net's hoop to be hauled in (m; more
## for a big fish: a share of its length). (tools/QUALITY.md: the hoop is 0.8 m across; it was 0.9 m
## and 0.4 of a length, so a fish was sold with its mouth half a metre outside the hoop, an orca's
## three metres off. Now inside the hoop's rim, or a big head against it.)
const NET_REACH := 0.55
const NET_REACH_PER_LENGTH := 0.15
## A run must have gone on this long before the net takes it (s): it starts by the boat.
const NET_AFTER := 4.0
var _selling_for := 0.0
var _run_for := 0.0
var _dive_from := Transform3D()
var _titled := false
# Shows every animal kind and material once on the loading screen (scripts/warmer.gd); null when a
# test or picture drives without the title.
var warmer: Warmer
# The loading screen (scripts/loading_swarm.gd), while it is up.
var _loading: LoadingSwarm
# Where the screens' warm-up has got to (Main._warm_screens; -1 done), and frames into its step.
var _screens_step := 0
var _screens_frames := 0
var _scenery: Scenery
## Paused from the panel's button (or P, Escape): the sea stands still.
var paused := false
var bot: Bot
var arena: Arena

## The run is over (the player was eaten).
var over := false
var deaths := 0
var best_stage := 0
var total_meals := 0

var _viewport: SubViewport
var effects: Effects
## Hooks, nets and trawlers (tools/FISHERS.md).
var fishers: Fishers
var _clock := 0.0
var _over_for := 0.0
var _start_kind := "sardine"
var _post: ShaderMaterial
var _frames := 0
# For a picture: "--feed" fills its stage after a moment (the choice of what to become),
# "--leap" sends it up through the surface.
var _trick := ""
var _server := ""
var _offline := false
var _name := "FISH"
# For the two-copy test of the arena: "a" (a tuna that swims into the other) or "b" (a sardine
# that stays put).
var _role := ""
var _role_done := false
var _quit_at := -1.0
var _shot_at := -1.0
var _shot_out := ""
var _checking := false
var _touching := false
var _end_now := false
var _saves := true
var _accept_was := false
var _p_was := false
var _grazed := 0.0
# Where a run starts (x and z): by the kelp, or (from the title) under the boat.
var _start := Sea.START
var _near := ""
# For tests/perf.gd: the places to measure (--perf=), and the animal to swim as (--perf-as=).
var _perf := ""
var _perf_as := ""
var _perf_shots := ""
# Frames over 50 ms logged with what happened in them (--hitches; scripts/hitches.gd), and the swim
# round the bay that looks for them (--tour; tests/tour.gd).
var _hitches := false
var _tour := ""


func _ready() -> void:
	var botted := false
	var calm := false
	for arg in OS.get_cmdline_user_args():
		if arg == "--bot":
			botted = true
		elif arg == "--check":
			_checking = true
		elif arg == "--check=touch":
			_touching = true
		elif arg == "--title":
			_titled = true
		elif arg == "--dive":
			_titled = true
			_trick = "--dive"
		elif arg == "--calm":
			calm = true
		elif arg == "--over":
			_end_now = true
		elif arg.begins_with("--seconds="):
			_quit_at = float(arg.get_slice("=", 1))
		elif arg.begins_with("--stage="):
			# (the old five stages, by number)
			_start_kind = ["sardine", "smolt", "salmon", "tuna", "shark"][clampi(int(arg.get_slice("=", 1)), 0, 4)]
		elif arg == "--feed" or arg == "--leap" or arg == "--sell" or arg == "--shop" or arg == "--rogue":
			_trick = arg
		elif arg.begins_with("--server="):
			_server = arg.get_slice("=", 1)
		elif arg == "--offline":
			_offline = true
		elif arg.begins_with("--name="):
			_name = arg.get_slice("=", 1)
		elif arg.begins_with("--role="):
			_role = arg.get_slice("=", 1)
			calm = true
		elif arg.begins_with("--as="):
			_start_kind = arg.get_slice("=", 1)
		elif arg.begins_with("--shot="):
			_shot_at = float(arg.get_slice("=", 1))
		elif arg.begins_with("--near="):
			_near = arg.get_slice("=", 1)
			calm = true
		elif arg.begins_with("--out="):
			_shot_out = arg.get_slice("=", 1)
		elif arg.begins_with("--perf="):
			_perf = arg.get_slice("=", 1)
			calm = true
			# (the sand as fine as a web build or a phone draws it, not a desktop's)
			Sand.quality = 1
			_titled = _perf.split(",").has("title")
		elif arg.begins_with("--perf-shots="):
			_perf_shots = arg.get_slice("=", 1)
		elif arg.begins_with("--perf-as="):
			_perf_as = arg.get_slice("=", 1)
		elif arg == "--hitches":
			_hitches = true
		elif arg == "--tour" or arg.begins_with("--tour="):
			# (a swim round the bay logging freezes: tests/tour.gd)
			_tour = arg.get_slice("=", 1) if "=" in arg else "all"
			_hitches = true
			calm = true
	# (a phone draws the sand as coarse as it goes, as GameCommon's sand would drop to itself after
	# some slow seconds: CLAUDE.md, "Decision: a phone tier")
	if Tier.phone():
		Sand.quality = 0
	# (a test's runs are not kept as the player's best)
	_saves = not (botted or _checking or _touching or _shot_at >= 0.0 or _quit_at >= 0.0 or _role != "" or _perf != "" or _tour != "")
	var container := SubViewportContainer.new()
	container.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	container.stretch = true
	container.stretch_shrink = 2
	container.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	container.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var post := ShaderMaterial.new()
	post.shader = preload("res://shaders/post.gdshader")
	post.set_shader_parameter(&"underwater", 1.0)
	post.set_shader_parameter(&"water_tint", Color(0.06, 0.2, 0.5))
	post.set_shader_parameter(&"tint", 0.35)
	post.set_shader_parameter(&"sway", 0.002)
	post.set_shader_parameter(&"shafts", 0.12)
	post.set_shader_parameter(&"levels", 28.0)
	post.set_shader_parameter(&"dither", 0.5)
	post.set_shader_parameter(&"vignette", 0.3)
	container.material = post
	_post = post
	add_child(container)
	_viewport = SubViewport.new()
	container.add_child(_viewport)
	var logger: Hitches = null
	if _hitches:
		logger = Hitches.new()
		logger.view = _viewport
		logger.main = self
		add_child(logger)
	sea = Sea.new()
	_viewport.add_child(sea)
	player = Player.new()
	_viewport.add_child(player)
	var scenery := Scenery.new()
	_scenery = scenery
	scenery.player = player
	_viewport.add_child(scenery)
	life = Life.new()
	scenery.life = life
	life.player = player
	life.hunting = not calm
	_viewport.add_child(life)
	# (the reef-back walking the deep floor is solid as the giants are: its trunk, 4 to 13 m up, nose
	# to tail-root; CLAUDE.md "Decision: solid giants")
	var walker: Variant = scenery.get(&"_reef_back")
	if walker is Node3D:
		life.solids.append([walker, Vector3(0.0, 8.5, 0.0), 12.0, 4.5])
	camera = Camera3D.new()
	camera.near = 0.05
	camera.far = 150.0
	_viewport.add_child(camera)
	camera.current = true
	sea.eye = camera
	sea.sand.focus = camera
	effects = Effects.new()
	effects.player = player
	# (water fx, tools/WATER_FX.md: the trail's shimmer and the burst's streaks are drawn by the post shader)
	effects.camera = camera
	effects.post = _post
	_viewport.add_child(effects)
	# (fishers: hooks, nets, trawlers; its meter shows the struggle over the sea)
	fishers = Fishers.new()
	fishers.player = player
	fishers.life = life
	_viewport.add_child(fishers)
	add_child(fishers.meter)
	hud = Hud.new()
	hud.player = player
	hud.restart.connect(restart)
	hud.picked.connect(_on_picked)
	add_child(hud)
	pad = TouchPad.new()
	add_child(pad)
	pad.pause_pressed.connect(_toggle_pause)
	player.ate.connect(_on_ate)
	player.grew.connect(_on_grew)
	player.died.connect(_on_died)
	player.choice.connect(_on_choice)
	player.leapt.connect(_on_splash)
	player.splashed.connect(_on_splash)
	if _server == "" and OS.has_feature("web") and not (_checking or _touching):
		_server = ARENA_SERVER
	if _server != "" and not _offline:
		arena = Arena.new()
		arena.player = player
		_viewport.add_child(arena)
		arena.board_changed.connect(func() -> void: hud.scores = arena.top)
		arena.open(_server, _name)
	if botted:
		bot = Bot.new()
		bot.player = player
		bot.life = life
		bot.fishers = fishers
	purse = Purse.new(SAVE if _saves else "")
	if _saves:
		hud.best = purse.best
	sale = Sale.new()
	add_child(sale)
	sale.done.connect(_open_shop)
	shop = Shop.new()
	add_child(shop)
	shop.bought.connect(func() -> void: player.deepest = _deepest())
	shop.dive.connect(_dive_again)
	# (a black light over everything, so that each lit program has one version: Warmer.add_null_lamp)
	Warmer.add_null_lamp(_viewport)
	# The game opens on the boat, unless something is driving it (a test, a bot, a picture): then
	# the boat lies hove-to by where the fish starts.
	var opening := _titled or not (botted or _checking or _touching or _shot_at >= 0.0 or _quit_at >= 0.0 or _role != "" or _near != "" or _end_now or _perf != "")
	if not opening:
		title = Title.new()
		title.hove = true
		title.eye_node = camera
		title.position = Vector3(_start.x, Sea.SURFACE, _start.y + 4.0)
		_viewport.add_child(title)
	restart()
	if opening:
		_open_title()
	# (the models' own materials lit per vertex: five times cheaper for a browser to compile)
	Warmer.light_per_vertex(_viewport)
	if _perf != "":
		var perf: Node = (load("res://tests/perf.gd") as GDScript).new()
		perf.set(&"main", self)
		perf.set(&"places", _perf.split(","))
		perf.set(&"as_kind", _perf_as)
		perf.set(&"shots", _perf_shots)
		add_child(perf)
	if _tour != "":
		var tour: Node = (load("res://tests/tour.gd") as GDScript).new()
		tour.set(&"main", self)
		tour.set(&"hitches", logger)
		if _tour != "all":
			tour.set(&"legs", _tour.split(","))
		add_child(tour)
	if _checking or _touching:
		var checks: Node = (load("res://tests/checks.gd") as GDScript).new()
		checks.set(&"main", self)
		checks.set(&"touch", _touching)
		add_child(checks)


## Starts a run.
func restart() -> void:
	var at := Sea.clear_of_rocks(Vector3(_start.x, maxf(Sea.SURFACE - 7.0, Sea.ground(_start.x, _start.y) + 1.5), _start.y), 0.5)
	player.begin(at, _start_kind)
	player.deepest = _deepest()
	_run_for = 0.0
	if arena:
		arena.spawn()
	hud.offer([])
	life.make_way(at)
	over = false
	_over_for = 0.0
	hud.over = false
	hud.reached = player.length
	hud.danger = 0.0
	pad.visible = true
	pad.release()
	if _near != "":
		_go_near()
	fishers.restart()
	camera.global_position = _camera_place()
	_aim_camera()


## Puts the player beside something, looking at it (--near).
func _go_near() -> void:
	var what := Vector3.ZERO
	var big := 1.0
	match _near:
		"kelp", "grass", "reef", "sand", "river", "open", "trench", "docks", "ruins", "pirate", "beach", "crags":
			var zone: Vector2 = Sea.ZONES[_near].at
			what = Vector3(zone.x, Sea.ground(zone.x, zone.y) + 3.0, zone.y)
			big = 4.0
		"barrel":
			# (just under the surf at Santa Cruz's point break, where the barrels peel: scripts/breakers.gd)
			var site: Dictionary = Breakers.SITES[0]
			var mid: Vector2 = (site.from + site.to) * 0.5
			what = Vector3(mid.x, Sea.SURFACE - 1.5, mid.y)
			big = 2.0
		"jelly":
			what = life.jellies[life.jellies.size() - 1].global_position
		"sardines":
			what = (life.schools[Life.KRILL_CLOUDS].flock as Flock).global_position
			big = 3.0
		"krill":
			what = (life.schools[0].flock as Flock).global_position
		"boat":
			# (the boat's own net, where the fish is sold)
			what = title.hoop() if title else Vector3(_start.x, Sea.SURFACE - 3.0, _start.y)
			big = 2.0
		"hook", "skiff", "net", "trawl":
			what = fishers.near(_near)
			big = 0.6 if _near == "hook" or _near == "skiff" else 4.0
		_:
			for each in life.creatures:
				if each.kind == _near:
					what = each.global_position
					big = each.length
	var from := what + Vector3(0.0, 0.2, 1.0).normalized() * (1.2 + big * 1.2)
	player.global_position = from
	player.yaw = 0.0
	player.pitch = -0.15
	player.heading = (what - from).normalized()


func _process(delta: float) -> void:
	_clock += delta
	delta = minf(delta, 0.05)
	if _on_deck:
		_title_step(delta)
		# (while the warm-up runs, the sea's light is the one it is showing things under: Warmer.above)
		if warmer and not warmer.done():
			sea.set_above(warmer.above)
		else:
			sea.set_above(camera.global_position.y > Sea.surface_height(camera.global_position.x, camera.global_position.z, camera.global_position.y))
		_post.set_shader_parameter(&"underwater", 0.0 if sea.above else 1.0)
		camera.fov = 72.0 if size.y > size.x else 60.0
		_finish_frame()
		return
	_steer()
	_frames += 1
	if _trick == "--feed" and _clock > 0.8:
		_trick = ""
		player.feed(player.length * 3.0)
	elif _trick == "--leap" and _clock > 0.3:
		_trick = ""
		player.global_position.y = Sea.SURFACE - 1.5
		player.pitch = 0.9
		player.boost_held = true
	elif _trick == "--rogue" and _clock > 0.5:
		# (a rogue wave across the fish, at its highest in 15 s: tools/WATER_FX.md)
		_trick = ""
		Sea.rogue_wave(Vector2(player.global_position.x, player.global_position.z), Vector2(player.heading.x, player.heading.z), true)
	elif (_trick == "--sell" or _trick == "--shop") and _clock > 1.0:
		# (for a picture of the sale, or of the shop after it)
		var then := _trick
		_trick = ""
		_sell()
		if then == "--shop":
			sale.visible = false
			_open_shop()
	# (while it is choosing what to become, or paused, the sea stands still)
	if Input.is_action_just_pressed(&"ui_cancel") or (Input.is_physical_key_pressed(KEY_P) and not _p_was):
		_toggle_pause()
	_p_was = Input.is_physical_key_pressed(KEY_P)
	if not player.choosing and not paused:
		player.step(delta)
		# (a rogue wave pushes what swims near the top: Surf.surge)
		if player.alive and not player.in_air and not player.caught:
			player.global_position += Sea.surge(player.global_position) * delta
		# (the plankton that drifts everywhere feeds the smallest fish a little as it swims through
		# it: the user, "that you can eat maybe??"; the plankton clouds are the rich feeding)
		if player.alive and not player.in_air and player.length < Life.PLANKTON_EATER:
			_grazed += player.velocity.length() * delta
			if _grazed > 3.0:
				_grazed = 0.0
				player.feed(Life.PLANKTON_LENGTH)
		life.step(delta)
		fishers.step(delta)
		# The boat's net: swum into, the fish is hauled up and sold (DESIGN.md's loop).
		if player.alive:
			_run_for += delta
			if _run_for > NET_AFTER and not player.in_air and not player.caught and player.mouth().distance_to(title.hoop()) < maxf(NET_REACH, player.length * NET_REACH_PER_LENGTH):
				_sell()
	if selling:
		_selling_for += delta
		if bot and _selling_for > 1.0:
			# (the bot does not shop: it swims again)
			sale.visible = false
			shop.visible = false
			selling = false
			hud.visible = true
			restart()
	if arena:
		arena.step(delta)
		if _role != "":
			_play_role()
		if _frames % 4 == 0 and player.alive:
			var food := life.nearest_food()
			player.near_food = food != Vector3.INF and food.distance_to(player.mouth()) < 0.4 + player.length * 1.2
	elif bot:
		var ways := player.options()
		if ways.is_empty():
			player.choosing = false
		else:
			_on_picked(ways[randi() % ways.size()])
	# Above the surface the air is clear; under it the water is blue and thick.
	sea.set_above(camera.global_position.y > Sea.surface_height(camera.global_position.x, camera.global_position.z, camera.global_position.y))
	_post.set_shader_parameter(&"underwater", 0.0 if sea.above else 1.0)
	# (the picture's water tint: green-teal in the kelp forest, Sea.post_tint)
	_post.set_shader_parameter(&"water_tint", sea.post_tint)
	if player.alive:
		# (water fx: quicker in a leap, and back under the water after one; tools/WATER_FX.md)
		camera.global_position = camera.global_position.lerp(_camera_place(), 1.0 - exp(-(8.0 if player.in_air or camera.global_position.y > Sea.SURFACE - 0.4 else 5.0) * delta))
		_aim_camera()
		hud.reached = maxf(hud.reached, player.length)
	# (wider in an upright window, where the picture is narrow; wider still in a burst: water fx)
	camera.fov = (72.0 if size.y > size.x else 60.0) + effects.fov_kick
	hud.danger = lerpf(hud.danger, 1.0 if (life.hunters > 0 or (arena and arena.hunters() > 0)) and player.alive else 0.0, 1.0 - exp(-6.0 * delta))
	pad.stamina = player.stamina
	pad.speed = lerpf(pad.speed, player.velocity.length() / (Fish.pace(player.length) * 1.15 * Player.BOOST), 1.0 - exp(-8.0 * delta)) if player.alive else 0.0
	pad.level = player.stage
	pad.progress = player.progress
	pad.length = player.length
	pad.heading = atan2(player.heading.x, -player.heading.z)
	# (the depth dial's full scale is as deep as the signal reaches: the needle at its stop is the
	# limit; past that the picture fills with static)
	var down := Sea.SURFACE - player.global_position.y
	pad.depth = clampf(down / (purse.depth() if limited else 100.0), 0.0, 1.0)
	_post.set_shader_parameter(&"signal_loss", clampf((down - purse.depth() + 3.0) / 5.0, 0.0, 1.0) if limited and player.alive else 0.0)
	if _frames % 6 == 0:
		_sound_out()
	if over:
		_over_for += delta
		if bot and _over_for > 1.0:
			restart()
	elif _end_now and _clock > 0.5:
		_end_now = false
		player.safe = 0.0
		player.die("test")
	_finish_frame()


## Opens on the boat, over where the fish starts.
func _open_title() -> void:
	title = Title.new()
	title.position = Vector3(player.global_position.x, Sea.SURFACE, player.global_position.z + 4.0)
	_viewport.add_child(title)
	_card = Title.Card.new()
	add_child(_card)
	title.eye_node = camera
	_on_deck = true
	_card.go.connect(func() -> void:
		if _dive < 0.0 and _card.primed >= 1.0:
			# (the fish is put in the water under the boat, wherever that has got to, and the boat
			# heaves to there, its net out, for the rest of the game)
			title.heave_to()
			_start = Vector2(title.global_position.x, title.global_position.z)
			restart()
			pad.visible = false
			_dive = 0.0
			_dive_from = camera.global_transform
			title.logo.visible = false
			_card.visible = false)
	hud.visible = false
	pad.visible = false
	_dive = -1.0
	_begin_warm()
	# (the loading screen, over everything, until everything is loaded and compiled: not for
	# pictures and tests, which want the title itself)
	if _trick == "" and _shot_at < 0.0:
		_loading = LoadingSwarm.new()
		add_child(_loading)
		# (the sea's own picture is not drawn behind it until everything is compiled: drawn, it would
		# compile all it shows in its first frame, twenty seconds with the loading screen not yet up;
		# the warm-up's little view compiles each thing one a frame instead)
		_viewport.render_target_update_mode = SubViewport.UPDATE_DISABLED


# A browser compiles each shader program the first time it is drawn, and stops the game for it.
# So everything is loaded and compiled on the loading screen, before the title shows, and nothing
# after (the user, 2026-11-19: "All loading should just happen at the start you shouldnt have to
# wait for buttons or anything"; scripts/warmer.gd; CLAUDE.md, "Decision: everything compiled on
# the loading screen").
func _begin_warm() -> void:
	warmer = Warmer.new()
	warmer.viewport = _viewport
	warmer.life = life
	add_child(warmer)
	warmer.begin(_warm_extras())


# The screens drawn over the sea in play, shown under the loading screen once each so that what they
# draw is compiled there too: the panel, the HUD, a card of every fish the player may become (each
# card draws its animal in a little world of its own), the sale and the shop. A step every three
# frames; true when done.
func _warm_screens() -> bool:
	if _screens_step < 0:
		return true
	_screens_frames += 1
	if _screens_frames < 3:
		return false
	_screens_frames = 0
	var kinds: Array = Player.GROWTH.keys()
	var batches := ceili(kinds.size() / 4.0)
	var at := _screens_step
	_screens_step += 1
	if at == 0:
		hud.visible = true
		pad.visible = true
	if at < batches:
		hud.offer(kinds.slice(at * 4, at * 4 + 4))
		return false
	if at == batches:
		hud.offer([])
		var sample := purse.price_of("salmon", 1.0, false)
		sample["money"] = purse.money
		sale.show_receipt(sample)
		return false
	if at == batches + 1:
		sale.visible = false
		shop.open(purse)
		return false
	shop.visible = false
	hud.visible = false
	pad.visible = false
	_screens_step = -1
	return true


# What is made only as the eye nears it, so is not yet in the sea to be found: the eelgrass
# fields' squares (one program for all of them, by its shader and MultiMesh format).
func _warm_extras() -> Array:
	var out := []
	var fields: Array = _scenery.get(&"_grass") if _scenery else []
	for field: Node3D in fields:
		var like := MultiMesh.new()
		like.transform_format = MultiMesh.TRANSFORM_3D
		like.use_custom_data = true
		out.append({"name": "grass field", "thing": [field.get_script().call(&"mesh_of", 0), field.call(&"material"), like]})
	return out


# A frame of the title: the eye astern of the boat, or on its way down through the surface to
# the fish. The fish waits; the sea goes on only once the eye is on its way.
func _title_step(delta: float) -> void:
	if _dive < 0.0:
		camera.global_transform = title.eye(size.y > size.x)
		if warmer:
			warmer.step()
		if warmer and warmer.done() and _viewport.render_target_update_mode != SubViewport.UPDATE_ALWAYS:
			_viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
		var screens := warmer == null or not warmer.done() or _warm_screens()
		_card.primed = 1.0 if warmer == null or (warmer.done() and screens) else minf(warmer.progress(), 0.99)
		if is_instance_valid(_loading):
			# (it is up for at least three seconds, so the logo is seen made)
			_loading.progress = minf(_card.primed, _clock / 3.0)
			_loading.share = _card.primed
			if _card.primed >= 1.0 and _clock > 4.2:
				_loading.finish()
				_loading = null
		if _trick == "--dive" and _clock > 0.6 and _card.primed >= 1.0:
			_trick = ""
			_card.go.emit()
		return
	_dive += delta / 1.8
	life.step(delta)
	var behind := Transform3D(Basis.IDENTITY, _camera_place()).looking_at(player.global_position + player.heading * player.length, Vector3.UP)
	camera.global_transform = _dive_from.interpolate_with(behind, smoothstep(0.0, 1.0, _dive))
	if _dive >= 1.0:
		# (the boat stays, hove-to with its net out: DESIGN.md's loop)
		_on_deck = false
		_dive = -1.0
		if _card:
			_card.queue_free()
			_card = null
		hud.visible = true
		pad.visible = true
		pad.release()


## The fish was swum into the boat's net: it is hauled up and sold, and the sale shows, then the
## shop (DESIGN.md's loop, 3 and 4).
func _sell() -> void:
	receipt = purse.sell(player.kind, player.length, player.is_biggest())
	player.haul()
	effects.splash(Vector3(player.global_position.x, Sea.SURFACE, player.global_position.z))
	hud.best = maxf(hud.best, hud.reached)
	hud.offer([])
	hud.visible = false
	pad.visible = false
	pad.release()
	paused = false
	pad.paused = false
	selling = true
	_selling_for = 0.0
	sale.show_receipt(receipt)


func _open_shop() -> void:
	shop.open(purse)


## From the shop back into the sea: a new run, the eye starting on the boat and going down
## through the surface to the fish under it, as from the title.
func _dive_again() -> void:
	selling = false
	restart()
	pad.visible = false
	camera.global_transform = title.eye(size.y > size.x)
	_dive_from = camera.global_transform
	_dive = 0.0
	_on_deck = true


## How deep the fish may go just now (m).
func _deepest() -> float:
	return purse.depth() if limited else INF


## Pauses the game, or goes on (the panel's pause button; P or Escape).
func _toggle_pause() -> void:
	if over or _on_deck or selling:
		return
	paused = not paused
	pad.paused = paused
	pad.release()


## A picture or the end of a timed run, when its time has come.
func _finish_frame() -> void:
	if _shot_at >= 0.0 and _clock >= _shot_at:
		_shot_at = -1.0
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(_shot_out)
		print("GULP SHOT ", _shot_out, " eye y %.1f, fish y %.1f, in air %s, above %s" % [camera.global_position.y, player.global_position.y, player.in_air, sea.above])
		get_tree().quit()
	elif _quit_at >= 0.0 and _clock >= _quit_at:
		_quit_at = -1.0
		if bot:
			best_stage = maxi(best_stage, player.stage)
			print("GULP BOT best_stage=%d deaths=%d meals=%d longest=%.2f" % [best_stage, deaths, total_meals + player.meals, maxf(hud.best, hud.reached)])
			print("GULP BOT PASSED" if best_stage >= 1 else "GULP BOT FAILED (never grew a stage)")
		var cost := life.cost_usec / maxf(life.steps, 1.0) / 1000.0
		print("GULP COST a frame: schools %.2f ms, fish %.2f ms, jellies %.2f ms, flocks themselves %.2f ms" % [cost.x, cost.y, cost.z, life.flock_ms / maxf(life.steps, 1.0)])
		var drawn := Engine.get_frames_drawn()
		print("GULP RAN %.0f s" % _clock + (", %d frames drawn, %.1f ms a frame" % [drawn, 1000.0 * _clock / drawn] if drawn > 0 else ""))
		get_tree().quit()


## The two-copy test of the arena (tests/arena.sh): "b" is a sardine held where it started; "a" is
## a tuna held back until it can see the other and both may be eaten, then let go to swim into it.
func _play_role() -> void:
	var start := Vector3(-24.0, Sea.SURFACE - 7.0, 6.0)
	if _role == "b":
		if player.alive:
			player.global_position = start + Vector3(9.0, 0.0, 0.0)
		for line in arena.log_lines:
			if line.begins_with("eaten by") and not _role_done:
				_role_done = true
				print("ARENA PASS b was eaten by the other player; top ", arena.top)
	else:
		var seen := false
		for rival: Arena.Rival in arena.rivals.values():
			seen = seen or (rival.visible and rival.alive)
		if not seen or _clock < 5.0:
			player.global_position = start
		for line in arena.log_lines:
			if line.begins_with("ate") and not _role_done:
				_role_done = true
				print("ARENA PASS a ate the other player and is %.2f m" % player.length)
	if _clock > 16.0:
		if not _role_done:
			print("ARENA FAIL %s: online %s, rivals %d, log %s" % [_role, arena.online, arena.rivals.size(), arena.log_lines])
		get_tree().quit()


## What the sonar on the panel sees: whatever is after the fish, and what it could eat, within
## the scope's range, each as where it is from the fish (to its right, ahead of it).
func _sound_out() -> void:
	var seen: Array[Vector3] = []
	if player.alive:
		var ahead := Vector3(player.heading.x, 0.0, player.heading.z)
		ahead = ahead.normalized() if ahead.length() > 0.01 else Vector3.FORWARD
		var right := ahead.cross(Vector3.UP)
		for threat: Array in life.threats():
			var off: Vector3 = threat[0] - player.global_position
			if off.length() < TouchPad.SONAR_RANGE:
				seen.append(Vector3(off.dot(right), off.dot(ahead), 1.0 + Sonar.high(off.y)))
		for each in life.awake:
			if seen.size() > 40:
				break
			if each.visible and each.away <= 0.0 and not each.giant:
				var off := each.global_position - player.global_position
				if off.length() < TouchPad.SONAR_RANGE:
					if Life.is_food(player.length, each.length):
						seen.append(Vector3(off.dot(right), off.dot(ahead), Sonar.high(off.y)))
					elif each.hunts and Life.can_eat(each.length, player.length) and player.length >= each.length * Life.TOO_SMALL:
						seen.append(Vector3(off.dot(right), off.dot(ahead), 1.0 + Sonar.high(off.y)))
	pad.blips = seen
	# (the alarm: how near the nearest thing after the fish is, from 12 lengths of the fish, and
	# no less than 5 m, down to upon it)
	var near := INF
	if player.alive:
		for threat: Array in life.threats():
			near = minf(near, (threat[0] as Vector3).distance_to(player.global_position))
	var from := maxf(5.0, player.length * 12.0)
	pad.alarm = clampf(1.0 - near / from, 0.0, 1.0) if near < from else 0.0
	# (and the parts of the sea, as landmarks)
	var marks := []
	if player.alive:
		var forward := Vector3(player.heading.x, 0.0, player.heading.z)
		forward = forward.normalized() if forward.length() > 0.01 else Vector3.FORWARD
		var aside := forward.cross(Vector3.UP)
		for zone: String in Sea.ZONES:
			var middle: Vector2 = Sea.ZONES[zone].at
			var to := Vector3(middle.x - player.global_position.x, 0.0, middle.y - player.global_position.z)
			marks.append([zone, Vector2(to.dot(aside), to.dot(forward))])
		# (the boat, where its net hangs: the way to end a run as a sale)
		var hoop := title.hoop()
		var to_boat := Vector3(hoop.x - player.global_position.x, 0.0, hoop.z - player.global_position.z)
		marks.append(["boat", Vector2(to_boat.dot(aside), to_boat.dot(forward))])
	pad.landmarks = marks


## Reads the controls into the player's stick and burst: the bot's if it is playing, or the
## touch pad's, the keys' and a gamepad's together. (The smoke test's checks steer it themselves.)
func _steer() -> void:
	if _checking:
		return
	if bot:
		if player.alive:
			bot.drive()
		return
	var pushed := pad.stick
	pushed.x += _key(KEY_D, KEY_RIGHT) - _key(KEY_A, KEY_LEFT)
	pushed.y += _key(KEY_W, KEY_UP) - _key(KEY_S, KEY_DOWN)
	var joy := Vector2(Input.get_joy_axis(0, JOY_AXIS_LEFT_X), -Input.get_joy_axis(0, JOY_AXIS_LEFT_Y))
	if joy.length() > 0.25:
		pushed += joy
	var accept := Input.is_physical_key_pressed(KEY_SPACE) or Input.is_joy_button_pressed(0, JOY_BUTTON_A)
	player.stick = pushed.limit_length(1.0)
	# The speed lever: Q and E (or a gamepad's shoulders) ease it down and up.
	var ease := _key(KEY_E, KEY_E) - _key(KEY_Q, KEY_Q)
	ease += (1.0 if Input.is_joy_button_pressed(0, JOY_BUTTON_RIGHT_SHOULDER) else 0.0) - (1.0 if Input.is_joy_button_pressed(0, JOY_BUTTON_LEFT_SHOULDER) else 0.0)
	pad.throttle = clampf(pad.throttle + ease * get_process_delta_time() * 0.9, 0.0, 1.0)
	player.throttle = pad.throttle
	player.boost_held = pad.boost or accept or Input.is_physical_key_pressed(KEY_SHIFT)
	# (when the run is over, the same keys start another: on a fresh press, a moment after)
	accept = accept or Input.is_physical_key_pressed(KEY_ENTER)
	if over and _over_for > 0.6 and accept and not _accept_was:
		restart()
	_accept_was = accept


func _key(one: Key, other: Key) -> float:
	return 1.0 if Input.is_physical_key_pressed(one) or Input.is_physical_key_pressed(other) else 0.0


## Where the camera wants to be: behind the fish and a little above, further back the bigger
## the fish is, and inside the sea.
func _camera_place() -> Vector3:
	var long := player.length
	# (above as well as behind: from straight behind a fish is only as big as it is thick)
	var behind := player.global_position - player.heading * (0.25 + long * 1.9) + Vector3.UP * (0.2 + long * 1.1)
	if player.in_air:
		# (water fx, tools/WATER_FX.md: out of the water with it, behind it along its way (not
		# along its nose, which swings from up to down), a little above the water and rising
		# with it, so that the leap is seen against the sky)
		var flat := Vector3(player.velocity.x, 0.0, player.velocity.z)
		if flat.length() < 0.01:
			flat = Vector3(player.heading.x, 0.0, player.heading.z) + Vector3.FORWARD * 0.001
		# (and a little to one side, so that its arc is seen and not only its tail)
		flat = flat.normalized().rotated(Vector3.UP, 0.45)
		var after := player.global_position - flat * (0.6 + long * 1.9)
		# (over the water as it is there: the waves and a rogue wave lift it)
		var under_fish := Sea.surface_height(player.global_position.x, player.global_position.z)
		after.y = Sea.surface_height(after.x, after.z) + 0.35 + long * 0.5 + maxf(player.global_position.y - under_fish, 0.0) * 0.55
		return after
	# (water fx: in the water the eye stays under it, below the waves; it used to rise out of it
	# whenever the fish swam near the top, and looked down through the surface at nothing)
	behind = Sea.keep_in(behind, 0.3)
	behind.y = minf(behind.y, Sea.surface_height(behind.x, behind.z) - 0.5)
	# (QUALITY.md: kept out of rocks and the floor; when that brings it in close, it looks down from
	# higher over the fish instead, if that sees further)
	var pivot := player.global_position + Vector3.UP * long * 0.3
	var eye := _camera_clear(pivot, behind, long * 0.7 + 0.2)
	if eye.distance_squared_to(behind) > 0.0025:
		var over := Sea.keep_in(pivot + Vector3.UP * (0.4 + long * 1.8) - player.heading * long * 0.7, 0.3)
		over.y = minf(over.y, Sea.surface_height(over.x, over.z) - 0.5)
		var high := _camera_clear(pivot, over, long * 0.7 + 0.2)
		if high.distance_to(pivot) > eye.distance_to(pivot) + 0.1:
			eye = high
	return eye


## The camera's way from the fish out to where it wants to be, tried at EYE_STEPS points: it stops
## short of the first that is in a rock (Sea.clear_of_rocks) or under the floor, but never nearer
## the fish than `least` (outside its body), and is then pushed clear of the rock it is in.
## (tools/QUALITY.md: it went through the rocks, the hulls and the floor.)
const EYE_STEPS := 8
const EYE_ROOM := 0.3


func _camera_clear(from: Vector3, to: Vector3, least: float) -> Vector3:
	var way := to - from
	var span := way.length()
	if span < 0.001:
		return to
	var free := 1.0
	for k in range(1, EYE_STEPS + 1):
		var t := float(k) / EYE_STEPS
		var q := from + way * t
		if q.y < Sea.ground(q.x, q.z) + EYE_ROOM or Sea.clear_of_rocks(q, EYE_ROOM).distance_squared_to(q) > 0.0001:
			free = float(k - 1) / EYE_STEPS
			break
	var at := from + way * maxf(free, minf(least / span, 1.0))
	at = Sea.clear_of_rocks(at, EYE_ROOM)
	at.y = maxf(at.y, Sea.ground(at.x, at.z) + EYE_ROOM)
	return at


func _aim_camera() -> void:
	var at := player.global_position + player.heading * player.length * 0.6
	if player.in_air:
		# (water fx: a little under it, so that it flies in the top half of the picture, clear of the panel)
		at = player.global_position + Vector3.DOWN * (0.15 + player.length * 0.35)
	if at.distance_to(camera.global_position) > 0.05:
		camera.look_at(at, Vector3.UP)


func _on_ate(at: Vector3) -> void:
	effects.eat(at)


func _on_grew(stage: int) -> void:
	best_stage = maxi(best_stage, stage)
	hud.grew()


func _on_choice(options: Array) -> void:
	hud.offer(options)
	pad.visible = false
	pad.release()


func _on_picked(kind: String) -> void:
	if not player.choosing:
		return
	hud.offer([])
	pad.visible = true
	player.choose(kind)


## A splash where it leaves the water and where it comes back in.
func _on_splash(at: Vector3) -> void:
	effects.splash(at)


func _on_died(by: String) -> void:
	if arena and by != "player":
		arena.died(by)
	hud.offer([])
	if bot:
		print("GULP BOT eaten by %s at %.0f s, stage %d, %.2f m, %d meals" % [by, _clock, player.stage, player.length, player.meals])
	over = true
	deaths += 1
	total_meals += player.meals
	best_stage = maxi(best_stage, player.stage)
	hud.best = maxf(hud.best, hud.reached)
	hud.over = true
	pad.visible = false
	pad.release()
	# (kept with the purse: Purse.save writes the money and gear as well as the longest)
	purse.best = maxf(purse.best, hud.best)
	purse.save()

