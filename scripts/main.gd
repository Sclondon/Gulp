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
## starts the run beside one of those, with nothing hunting (to look at it).

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
## The boat the game starts on (null once the game is under way), its card, and how far the eye
## has gone on its way down to the fish (-1: not yet started).
var title: Title
var _card: Title.Card
var _dive := -1.0
var _dive_from := Transform3D()
var _titled := false
# The kinds whose models are still to be shown once behind the title (see _warm), how many there
# were, how many of those must be done before the game may start, and the little view they are
# shown in.
var _warming: Array[String] = []
var _warm_all := 0
var _warm_first := 0
var _warm_view: SubViewport
var _warm_now: Node3D
var _warm_wait := 0
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
		elif arg == "--feed" or arg == "--leap":
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
	# (a test's runs are not kept as the player's best)
	_saves = not (botted or _checking or _touching or _shot_at >= 0.0 or _quit_at >= 0.0 or _role != "")
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
	sea = Sea.new()
	_viewport.add_child(sea)
	player = Player.new()
	_viewport.add_child(player)
	var scenery := Scenery.new()
	scenery.player = player
	_viewport.add_child(scenery)
	life = Life.new()
	life.player = player
	life.hunting = not calm
	_viewport.add_child(life)
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
	if _saves:
		var kept := ConfigFile.new()
		if kept.load(SAVE) == OK:
			hud.best = float(kept.get_value("best", "length", 0.0))
	restart()
	# The game opens on the boat, unless something is driving it (a test, a bot, a picture).
	if _titled or not (botted or _checking or _touching or _shot_at >= 0.0 or _quit_at >= 0.0 or _role != "" or _near != "" or _end_now):
		_open_title()
	if _checking or _touching:
		var checks: Node = (load("res://tests/checks.gd") as GDScript).new()
		checks.set(&"main", self)
		checks.set(&"touch", _touching)
		add_child(checks)


## Starts a run.
func restart() -> void:
	var at := Sea.clear_of_rocks(Vector3(_start.x, maxf(Sea.SURFACE - 7.0, Sea.ground(_start.x, _start.y) + 1.5), _start.y), 0.5)
	player.begin(at, _start_kind)
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
		"kelp", "grass", "reef", "sand", "river", "open", "trench", "docks", "ruins", "pirate", "beach":
			var zone: Vector2 = Sea.ZONES[_near].at
			what = Vector3(zone.x, Sea.ground(zone.x, zone.y) + 3.0, zone.y)
			big = 4.0
		"jelly":
			what = life.jellies[life.jellies.size() - 1].global_position
		"sardines":
			what = (life.schools[Life.KRILL_CLOUDS].flock as Flock).global_position
			big = 3.0
		"krill":
			what = (life.schools[0].flock as Flock).global_position
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
	if title:
		_title_step(delta)
		sea.set_above(camera.global_position.y > Sea.SURFACE)
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
	# (while it is choosing what to become, or paused, the sea stands still)
	if Input.is_action_just_pressed(&"ui_cancel") or (Input.is_physical_key_pressed(KEY_P) and not _p_was):
		_toggle_pause()
	_p_was = Input.is_physical_key_pressed(KEY_P)
	if not player.choosing and not paused:
		player.step(delta)
		# (the plankton that drifts everywhere feeds the smallest fish a little as it swims through
		# it: the user, "that you can eat maybe??"; the plankton clouds are the rich feeding)
		if player.alive and not player.in_air and player.length < Life.PLANKTON_EATER:
			_grazed += player.velocity.length() * delta
			if _grazed > 3.0:
				_grazed = 0.0
				player.feed(Life.PLANKTON_LENGTH)
		life.step(delta)
		fishers.step(delta)
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
	sea.set_above(camera.global_position.y > Sea.SURFACE)
	_post.set_shader_parameter(&"underwater", 0.0 if sea.above else 1.0)
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
	pad.depth = clampf((Sea.SURFACE - player.global_position.y) / 100.0, 0.0, 1.0)
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
	_card.go.connect(func() -> void:
		if _dive < 0.0 and _card.primed >= 1.0:
			# (the fish is put in the water under the boat, wherever that has got to)
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


# A browser compiles each animal's shader the first time the animal is drawn, and on Windows that
# takes a second or two each: the game froze again and again as new kinds swam into view (the
# user, 2026-11-18: "its either really choppy on my pc with long freezes"). So behind the title
# each kind is shown once, a kind every few frames, to a tiny view of the same world far under
# the sea: first the kinds of the waters the fish starts in (the game may start when those are
# done), then the rest for as long as the title is up.
func _begin_warm() -> void:
	# (the waters it starts in: the part of the sea nearest the start)
	var near: Array[String] = []
	var nearest := INF
	for zone: String in Sea.ZONES:
		var far := (Sea.ZONES[zone].at as Vector2).distance_to(_start) - float(Sea.ZONES[zone].radius)
		if far < nearest:
			nearest = far
			near = [zone]
	var first: Array[String] = []
	var rest: Array[String] = []
	for kind: String in Species.ALL:
		if not Species.has(kind):
			continue
		var by_start := Player.GROWTH.has(kind) and float(Player.GROWTH[kind].from) < 0.5
		for zone: String in Species.of(kind).get("zones", []):
			by_start = by_start or zone in near
		(first if by_start else rest).append(kind)
	_warming = first + rest
	_warm_all = _warming.size()
	_warm_first = first.size()
	_warm_view = SubViewport.new()
	_warm_view.size = Vector2i(32, 32)
	_warm_view.world_3d = _viewport.find_world_3d()
	_warm_view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(_warm_view)
	var eye := Camera3D.new()
	eye.position = Vector3(0.0, -800.0, 3.0)
	eye.far = 12.0
	_warm_view.add_child(eye)


func _warm() -> void:
	_warm_wait -= 1
	if _warm_wait > 0:
		return
	if _warm_now:
		_warm_now.queue_free()
		_warm_now = null
	if _warming.is_empty():
		return
	var kind: String = _warming.pop_front()
	if _warming.size() == _warm_all - _warm_first:
		print("GULP WARM the near kinds are ready at %.1f s" % _clock)
	elif _warming.is_empty():
		print("GULP WARM every kind is ready at %.1f s" % _clock)
	var look := Species.make(kind)
	if look == null:
		return
	if &"game" in look:
		look.set(&"game", true)
	if &"cartoon_eyes" in look:
		look.set(&"cartoon_eyes", 1.0)
	_warm_now = Node3D.new()
	_warm_now.add_child(look)
	_warm_now.scale = Vector3.ONE / maxf(Species.long_of(kind, look), 0.05)
	_viewport.add_child(_warm_now)
	_warm_now.global_position = Vector3(0.0, -800.0, 0.0)
	_warm_wait = 2
	life.mark_dressed(kind)


# A frame of the title: the eye astern of the boat, or on its way down through the surface to
# the fish. The fish waits; the sea goes on only once the eye is on its way.
func _title_step(delta: float) -> void:
	if _dive < 0.0:
		camera.global_transform = title.eye(size.y > size.x)
		_warm()
		_card.primed = 1.0 if _warm_all == 0 else clampf(float(_warm_all - _warming.size()) / maxf(_warm_first, 1.0), 0.0, 1.0)
		if _trick == "--dive" and _clock > 0.6:
			_trick = ""
			_card.go.emit()
		return
	_dive += delta / 1.8
	life.step(delta)
	var behind := Transform3D(Basis.IDENTITY, _camera_place()).looking_at(player.global_position + player.heading * player.length, Vector3.UP)
	camera.global_transform = _dive_from.interpolate_with(behind, smoothstep(0.0, 1.0, _dive))
	if _dive >= 1.0:
		if _warm_now:
			_warm_now.queue_free()
			_warm_now = null
		_warm_view.queue_free()
		title.queue_free()
		title = null
		_card.queue_free()
		_card = null
		hud.visible = true
		pad.visible = true
		pad.release()


## Pauses the game, or goes on (the panel's pause button; P or Escape).
func _toggle_pause() -> void:
	if over or title:
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
		for each in life.creatures:
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
		after.y = Sea.SURFACE + 0.35 + long * 0.5 + maxf(player.global_position.y - Sea.SURFACE, 0.0) * 0.55
		return after
	# (water fx: in the water the eye stays under it, below the waves; it used to rise out of it
	# whenever the fish swam near the top, and looked down through the surface at nothing)
	behind = Sea.keep_in(behind, 0.3)
	behind.y = minf(behind.y, Sea.SURFACE - 0.5)
	return behind


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
	if _saves:
		var kept := ConfigFile.new()
		kept.set_value("best", "length", hud.best)
		kept.save(SAVE)

