class_name Fishers
extends Node3D
## People fishing from the surface, a danger in the sea in three forms. The user (2026-11-18): "We
## need to add fisherman- hooks nets and trawlers". tools/FISHERS.md has the design, the numbers and
## whose calls they were. The gear is models/fishing_gear.glb (tools/build_fishing_gear.py); the
## trawlers are the title's shrimp boat (models/shrimp_boat.glb, used as it is).
##
## - Hooks (`rigs`): a baited hook on a line hanging from a float, or from the rod of an angler's
##   skiff. The bait is food by the usual rule. A fish that takes it is hooked and hauled up to the
##   surface, unless it is too long for the hook (the line snaps and it keeps the bait). Hauled out,
##   the run ends ("hook").
## - Nets (`nets`): curtains of net hung from floats at the surface, or standing off the bottom on
##   weights. A fish of the right size that swims into one is caught in its mesh and, held too long,
##   hauled ("net"); a smaller one swims through the mesh, a bigger one tears through and leaves a hole.
## - Trawlers (`trawlers`): boats going round and round a loop over the shelf's edge and the open
##   sea, each towing a trawl. What is in a trawl's mouth is swept back to the cod end and, still
##   there after a few seconds, caught ("trawl"). A fish gets out by swimming out of the mouth faster
##   than the tow, or through the mesh if it is small. The giants are never caught.
##
## Hooked or caught in a net, the player struggles: holding the burst, and turning away from what
## holds it, work it loose (`grip` runs from 1 to 0; `doom` is how near it is to being hauled).
## The Meter shows both over the sea. Fish of the sea are caught too: some take a bait and are
## hauled up, some swim into a net and hang there, some are swept into a trawl; each comes back
## later somewhere else, as anything eaten does.
##
## Main makes it once, steps it after Life (so not while the player chooses), restarts it with each
## run, and adds its `meter` over the sea. Arguments read here (for pictures and tests): --catch arms
## it even with --calm or --near; --look=<side|below|close|hull> puts the eye beside whatever
## --near (hook, skiff, net, trawl) chose; --no-fishers leaves it all out (to compare a frame's cost).

const GEAR := "res://models/fishing_gear.glb"
const BOAT := "res://models/shrimp_boat.glb"
const NET_SHADER := preload("res://shaders/net.gdshader")

## Where each run starts (Main.restart): nothing of this is put within SPARE metres of it.
static var START: Vector3 = Vector3(Sea.START.x, Sea.SURFACE - 7.0, Sea.START.y)
const SPARE := 30.0

## The two kinds of rig: how much bigger than life its gear is drawn, how long its bait counts as
## for the eating rule (m), and the longest fish its hook holds (a longer one snaps the line).
const RIGS := {
	"worm": {"scale": 2.0, "bait": 0.07, "snap": 0.9},
	"fish": {"scale": 3.0, "bait": 0.2, "snap": 2.0},
}
## The hook's bend, where the bait sits and what catches in a mouth (the model's own metres).
const BEND := Vector3(0.009, -0.036, 0.0)
## How far above the hook its sinker is (m).
const SINKER_UP := 0.4
## Rigs under floats, by zone, and the zones of the two anglers' skiffs (two rods each).
const FLOATS := ["river", "grass", "grass", "sand", "sand", "open", "beach", "beach", "docks", "docks"]
const SKIFFS := ["kelp", "reef"]
## The skiff's rod tips (Godot, its own space: tools/build_fishing_gear.py ROD_TIPS).
const ROD_TIPS := [Vector3(-1.55, 1.62, 0.55), Vector3(1.55, 1.62, 0.55)]
## Hauling: how long it takes to bring a hooked fish up from where it bit (s), slowest (m/s).
const HAUL_TIME := 7.0
const HAUL_SLOWEST := 0.4
## How much slower the haul goes while the fish bursts against it.
const HAUL_FIGHT := 0.3
## Seconds before a lost or taken bait is replaced.
const REBAIT := Vector2(18.0, 30.0)

## The struggle: how much grip goes a second while bursting, more while bursting pointed away from
## what holds it, and while wriggling (the stick hard over).
const STRUGGLE_BURST := 0.42
const STRUGGLE_AWAY := 0.18
const STRUGGLE_WRIGGLE := 0.1
## After getting free, nothing catches it for this long (s).
const SHAKEN := 2.0

## The nets: from (x, z), to (x, z), how they hang ("drift": from floats at the surface; "bottom":
## off the floor), how tall (m), and the lengths of fish they hold (smaller swim through, bigger
## tear through).
const NETS := [
	[Vector2(-100.0, -40.0), Vector2(-96.0, -16.0), "drift", 5.0, 0.3, 1.6],
	[Vector2(-112.0, 60.0), Vector2(-106.0, 84.0), "drift", 5.0, 0.3, 1.6],
	[Vector2(-22.0, -108.0), Vector2(-6.0, -101.0), "bottom", 3.5, 0.25, 1.2],
]
## Seconds a fish can hang in a net before it is hauled.
const NET_HOLD := 10.0
## Floats and weights along a net, one each this many metres.
const NET_SPACING := 1.5
## Sea life held in one net at once.
const NET_CATCH := 4

## The trawlers' loops (a racetrack: its middle, the radius of its turns, half its straight) and
## how deep each trawl's mouth goes (m under the surface; never nearer the floor than 2.2 m).
const LOOPS := [
	{"at": Vector2(-95.0, -10.0), "radius": 12.0, "half": 48.0, "depth": 8.0},
	{"at": Vector2(10.0, -30.0), "radius": 10.0, "half": 18.0, "depth": 13.0},
]
## The tow (m/s); how far behind the boat, along its way, the trawl's mouth is (m); where on the boat
## the warps leave it (its stern, its own space); how far apart the otter doors are (m).
const TOW := 1.3
const LAG := 32.0
const STERN := Vector3(1.0, 0.9, 6.3)
const DOORS := 5.5
## The cod end: from this far behind the mouth (m); a fish still there after CODEND_TIME s is caught.
const CODEND := 7.0
const CODEND_TIME := 5.0
## A fish longer than this tears through a trawl; one shorter than this (at the mouth, at the cod
## end) slips through its mesh.
const TRAWL_BIG := 2.6
const TRAWL_PASS := Vector2(0.3, 0.1)
## Sea life in one trawl at once.
const TRAWL_CATCH := 6
## Beyond these the boats, and the trawls and nets, are not drawn (m).
const BOAT_SEEN := 75.0
const GEAR_SEEN := 70.0


## One baited hook on its line.
class Rig:
	var kind := "worm"
	var bait_long := 0.07
	var snap := 0.9
	var big := 2.0
	## Where its line comes down from: a float at the surface (`bob`) or a skiff's rod (`skiff`, `rod`).
	var bob: MeshInstance3D
	var skiff: Node3D
	var rod := 0
	## Where the hook hangs when nothing has it, and a sway of its own.
	var home := Vector3.ZERO
	var phase := 0.0
	## The hook (with its bait) and sinker, and the line in two pieces.
	var hook: Node3D
	var bait: MeshInstance3D
	var sinker: MeshInstance3D
	var line: MeshInstance3D
	var leader: MeshInstance3D
	## Seconds until it is baited again (0: it is).
	var away := 0.0
	## What is on it (the player or a Creature), how much line is out (m), the haul (m/s), where it is.
	var on: Node3D
	var out := 0.0
	var out_from := 1.0
	var haul := 0.0
	var tip := Vector3.ZERO
	var lift := 0.0

	func anchor() -> Vector3:
		if skiff:
			var at: Vector3 = skiff.global_transform * Fishers.ROD_TIPS[rod]
			return Vector3(at.x, Sea.SURFACE, at.z)
		return Vector3(bob.global_position.x, Sea.SURFACE, bob.global_position.z)

	func top() -> Vector3:
		if skiff:
			var at: Vector3 = skiff.global_transform * Fishers.ROD_TIPS[rod]
			return at
		return bob.global_position + Vector3.DOWN * 0.05 * bob.scale.y

	func bait_at() -> Vector3:
		return hook.global_transform * Fishers.BEND


## One net.
class Net:
	var a := Vector3.ZERO
	var b := Vector3.ZERO
	var how := "drift"
	var top := 0.0
	var bottom := 0.0
	var lo := 0.3
	var hi := 1.6
	var along := Vector3.RIGHT
	var normal := Vector3.FORWARD
	var long := 1.0
	var panel: MeshInstance3D
	var material: ShaderMaterial
	## Torn places: each (along, down, radius, seconds until it is mended).
	var holes: Array[Vector4] = []
	## Creatures hanging in it: each [creature, where, seconds left].
	var catch: Array = []

	func side(p: Vector3) -> float:
		return (p - a).dot(normal)

	## Where a point is on it: (metres along from its first end, metres down from its top).
	func on_it(p: Vector3) -> Vector2:
		return Vector2((p - a).dot(along), top - p.y)

	func covers(p: Vector3, room := 0.0) -> bool:
		var where := on_it(p)
		if where.x < -room or where.x > long + room or p.y > top + room or p.y < bottom - room:
			return false
		for hole in holes:
			if Vector2(hole.x, hole.y).distance_to(where) < hole.z:
				return false
		return true

	func nearest(p: Vector3) -> Vector3:
		var t := clampf((p - a).dot(along), 0.0, long)
		return Vector3(a.x, clampf(p.y, bottom, top), a.z) + along * t

	func shade() -> void:
		var list: Array[Vector4] = []
		for hole in holes:
			list.append(Vector4(hole.x, hole.y, hole.z, 0.0))
		while list.size() < 6:
			list.append(Vector4.ZERO)
		material.set_shader_parameter(&"holes", list)


## One trawler and its trawl.
class Trawler:
	var loop: Dictionary
	var s := 0.0
	var boat: Node3D
	var trawl: MeshInstance3D
	var doors: Array[MeshInstance3D] = []
	var warps: Array[MeshInstance3D] = []
	var bridles: Array[MeshInstance3D] = []
	var mouth_y := 0.0
	## The player: in the trawl, how long in the cod end; the last place in its frame.
	var holds := false
	var codend := 0.0
	var was := Vector3.ZERO
	## Creatures swept in: each [creature, where in the trawl's frame, seconds in the cod end].
	var catch: Array = []

	## The half width and half height of the trawl at a distance behind its mouth (as built).
	static func section(z: float) -> Vector2:
		if z <= 8.0:
			var s := pow(clampf(z, 0.0, 8.0) / 8.0, 0.8)
			return Vector2(lerpf(3.0, 0.45, s), lerpf(1.5, 0.45, s))
		var bulge := 0.45 + 0.15 * sin(minf((z - 8.0) / 1.8, 1.0) * PI * 0.8)
		return Vector2(bulge, bulge)

	## Where a point is in the trawl's frame (x across, y up, z back from the mouth), and how far
	## out from its middle as a share of the net's own width there (under 1: inside).
	func frame_of(p: Vector3) -> Vector3:
		return trawl.global_transform.affine_inverse() * p

	static func spread(local: Vector3) -> float:
		var wide := section(local.z)
		return pow(local.x / wide.x, 2.0) + pow(local.y / wide.y, 2.0)


var player: Player
var life: Life
## Catching is on while Life hunts (or always: --catch, and the checks).
var always := false
var rigs: Array[Rig] = []
var nets: Array[Net] = []
var trawlers: Array[Trawler] = []
var skiffs: Array[Node3D] = []
## What holds the player just now ("hook", "net", "trawl" or ""), how much of its hold is left
## (1..0), and how near it is to being caught (0..1).
var holding := ""
var grip := 1.0
var doom := 0.0
## The struggle bar, the line's pull, the net's place and the way out, shown over the sea.
var meter: Meter
## What it has cost (microseconds) over how many steps, for a timed run's print.
var cost_usec := 0
var steps := 0
## How often the player was held by each, got free, was caught; and sea life caught.
var tally := {}

var _rng := RandomNumberGenerator.new()
var _meshes := {}
var _line_material: StandardMaterial3D
var _warp_material: StandardMaterial3D
var _clock := 0.0
var _shaken := 0.0
var _rig: Rig
var _net: Net
var _net_at := Vector3.ZERO
var _net_from := 0.0
var _trawler: Trawler
var _held := {}
var _scan := 0.0
var _look := ""
var _near := ""
var _buoys: Array[MeshInstance3D] = []
# (--no-fishers: none of it, to compare what a frame costs)
var _off := false


func _ready() -> void:
	_rng.seed = 23
	# (after Main, which places the eye each frame: --look puts it somewhere else afterwards)
	process_priority = 100
	for arg in OS.get_cmdline_user_args():
		if arg == "--catch":
			always = true
		elif arg.begins_with("--look="):
			_look = arg.get_slice("=", 1)
		elif arg.begins_with("--near="):
			_near = arg.get_slice("=", 1)
		elif arg == "--no-fishers":
			_off = true
	var gear: Node = (load(GEAR) as PackedScene).instantiate()
	for mesh: MeshInstance3D in gear.find_children("*", "MeshInstance3D", true, false):
		_meshes[String(mesh.name)] = mesh.mesh
	gear.free()
	_line_material = StandardMaterial3D.new()
	_line_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_line_material.albedo_color = Color(0.78, 0.88, 0.92)
	_warp_material = StandardMaterial3D.new()
	_warp_material.albedo_color = Color(0.18, 0.17, 0.15)
	_warp_material.roughness = 0.8
	meter = Meter.new()
	_make_rigs()
	_make_nets()
	_make_trawlers()
	if _off:
		visible = false


func _exit_tree() -> void:
	if steps > 600:
		print("GULP FISHERS a frame %.3f ms (%d steps); %s" % [cost_usec / 1000.0 / steps, steps, tally])


## A new run: whatever held the player lets go.
func restart() -> void:
	_let_go(false)
	_shaken = 0.0
	for each in trawlers:
		each.holds = false
		each.codend = 0.0
		each.was = Vector3(0.0, 0.0, -100.0)
	for net in nets:
		_net_side_reset(net)


func step(delta: float) -> void:
	if _off:
		return
	var t0 := Time.get_ticks_usec()
	_clock += delta
	_shaken = maxf(_shaken - delta, 0.0)
	if holding != "" and not player.alive:
		_let_go(false)
	var armed := (always or life.hunting) and player.alive and not player.in_air and _shaken <= 0.0
	_scan -= delta
	var scanning := _scan <= 0.0
	if scanning:
		_scan = 0.25
	for trawler in trawlers:
		_step_trawler(trawler, delta, armed, scanning)
	for rig in rigs:
		_step_rig(rig, delta, armed, scanning)
	for net in nets:
		_step_net(net, delta, armed, scanning)
	for skiff in skiffs:
		var rock: float = skiff.get_meta(&"phase")
		skiff.position.y = Sea.SURFACE + 0.04 * sin(_clock * 1.1 + rock)
		skiff.rotation.z = 0.03 * sin(_clock * 0.9 + rock * 2.0)
	if holding != "":
		meter.what = holding
		meter.grip = grip
		meter.doom = doom
	else:
		meter.what = ""
	cost_usec += Time.get_ticks_usec() - t0
	steps += 1


## The way out of whatever holds the player (for the bot): away from the line, back out of the net,
## forward out of the trawl's mouth.
func way_out() -> Vector3:
	match holding:
		"hook":
			var pull := (_rig.anchor() - player.global_position).normalized()
			return (-pull + Vector3.DOWN * 0.3).normalized()
		"net":
			return (_net.normal * (1.0 if _net_from > 0.0 else -1.0) * -1.0).normalized()
		"trawl":
			return -_trawler.trawl.global_basis.z.normalized()
	return player.heading


## Everything here that could end the player's run, near it: each [where, how big]. For the bot.
func threats() -> Array:
	var found := []
	if not player.alive:
		return found
	var at := player.global_position
	for rig in rigs:
		if rig.away <= 0.0 and rig.on == null and Life.is_food(player.length, rig.bait_long) and player.length <= rig.snap:
			var bait := rig.bait_at()
			if bait.distance_to(at) < 12.0:
				found.append([bait, 0.4])
	for net in nets:
		if player.length >= net.lo and player.length <= net.hi:
			var near := net.nearest(at)
			if near.distance_to(at) < 10.0:
				found.append([near, 0.8])
	for trawler in trawlers:
		if player.length <= TRAWL_BIG:
			var mouth := trawler.trawl.global_position
			if mouth.distance_to(at) < 25.0:
				found.append([mouth, 3.0])
				found.append([trawler.trawl.global_transform * Vector3(0.0, 0.0, 4.0), 2.0])
	return found


## Where one of them is, for --near: a bait, the middle of a net, a trawl's mouth.
func near(what: String) -> Vector3:
	match what:
		"hook":
			return rigs[3].bait_at()
		"net":
			var net := nets[0]
			return (net.a + net.b) * 0.5 + Vector3.DOWN * 2.0
		"trawl":
			return trawlers[0].trawl.global_position
		"skiff":
			return rigs[FLOATS.size()].bait_at()
	return Vector3.ZERO


# ---------------------------------------------------------------------------------------------- hooks
func _make_rigs() -> void:
	for zone: String in FLOATS:
		var at := Sea.place(_rng, zone, 1.0, START, SPARE)
		var rig := Rig.new()
		rig.kind = "fish" if zone == "open" else "worm"
		_fill_rig(rig)
		rig.bob = _mesh("Bobber", rig.big * 1.5)
		rig.bob.position = Vector3(at.x, Sea.SURFACE, at.z)
		var deep := Sea.SURFACE - Sea.ground(at.x, at.z)
		rig.home = Vector3(at.x, Sea.SURFACE - clampf(_rng.randf_range(2.5, 7.0), 1.5, maxf(deep - 1.5, 1.5)), at.z)
		_lay_rig(rig)
	for zone: String in SKIFFS:
		var at := Sea.place(_rng, zone, 3.0, START, SPARE)
		var skiff := MeshInstance3D.new()
		skiff.mesh = _meshes["Skiff"]
		skiff.position = Vector3(at.x, Sea.SURFACE, at.z)
		skiff.rotation.y = _rng.randf() * TAU
		skiff.set_meta(&"phase", _rng.randf() * TAU)
		add_child(skiff)
		skiffs.append(skiff)
		for k in 2:
			var rig := Rig.new()
			rig.kind = "fish" if k == 0 else "worm"
			_fill_rig(rig)
			rig.skiff = skiff
			rig.rod = k
			# (bottom fishing: the hook a metre and a bit over the floor, off to the rod's side)
			var tip := skiff.transform * (ROD_TIPS[k] as Vector3) + skiff.transform.basis.x * (0.8 if k == 1 else -0.8)
			rig.home = Vector3(tip.x, Sea.ground(tip.x, tip.z) + 1.3, tip.z)
			_lay_rig(rig)


func _fill_rig(rig: Rig) -> void:
	var kind: Dictionary = RIGS[rig.kind]
	rig.bait_long = kind.bait
	rig.snap = kind.snap
	rig.big = kind.scale
	rig.phase = _rng.randf() * TAU


func _lay_rig(rig: Rig) -> void:
	rig.hook = Node3D.new()
	rig.hook.scale = Vector3.ONE * rig.big
	add_child(rig.hook)
	var hook := MeshInstance3D.new()
	hook.mesh = _meshes["Hook"]
	rig.hook.add_child(hook)
	rig.bait = MeshInstance3D.new()
	rig.bait.mesh = _meshes["Worm" if rig.kind == "worm" else "BaitFish"]
	rig.hook.add_child(rig.bait)
	rig.sinker = _mesh("Sinker", rig.big)
	rig.line = _line(_line_material)
	rig.leader = _line(_line_material)
	if rig.bob:
		add_child(rig.bob)
	rig.hook.rotation.y = rig.phase
	# (where it hangs from the start, so that --near finds it before the first step)
	rig.tip = rig.home
	rig.hook.position = rig.tip - Vector3(rig.hook.global_basis * BEND)
	rigs.append(rig)


func _step_rig(rig: Rig, delta: float, armed: bool, scanning: bool) -> void:
	var anchor := rig.anchor()
	var seen := anchor.distance_to(player.global_position) < GEAR_SEEN
	if rig.bob:
		# (it bobs on the swell; it is dragged under while something is on the line)
		var under := -0.12 * rig.big - 0.05 * sin(_clock * 17.0) if rig.on else 0.0
		rig.bob.position.y = Sea.SURFACE + 0.025 * rig.big * sin(_clock * 1.3 + rig.phase) + under
	if rig.away > 0.0:
		rig.away -= delta
		if rig.away <= 0.0:
			_show_rig(rig, true)
		return
	if rig.on:
		_haul(rig, delta)
	else:
		var sway := Vector3(sin(_clock * 0.4 + rig.phase), 0.0, cos(_clock * 0.31 + rig.phase * 1.7)) * 0.25
		rig.tip = rig.home + sway
		rig.hook.position = rig.tip - Vector3(rig.hook.global_basis * BEND)
		rig.hook.rotation.y = rig.phase + 0.3 * sin(_clock * 0.5 + rig.phase)
		if seen and armed and holding == "":
			_try_bite(rig)
		if scanning and seen:
			_tempt(rig)
	_draw_rig(rig, seen)


func _draw_rig(rig: Rig, seen: bool) -> void:
	rig.hook.visible = seen
	rig.sinker.visible = seen
	rig.line.visible = seen
	rig.leader.visible = seen
	if not seen:
		return
	var eye := rig.hook.global_position
	var sink := eye + Vector3.UP * SINKER_UP
	var top := rig.top()
	if rig.on:
		# (taut: the sinker slides down the line to the hook's eye)
		sink = eye.lerp(top, 0.06)
	rig.sinker.position = sink
	_stretch(rig.line, top, sink, 0.006 * rig.big)
	_stretch(rig.leader, sink, eye, 0.004 * rig.big)


## The player's mouth has come to the bait: it bites, and is hooked (or snaps the line).
func _try_bite(rig: Rig) -> void:
	if not Life.is_food(player.length, rig.bait_long):
		return
	var bait := rig.bait_at()
	# (the same reach as eating: Life.TAKES, tools/QUALITY.md)
	if player.mouth().distance_to(bait) > player.length * Life.TAKES + Life.TAKES_LEAST + rig.bait_long * 0.5:
		return
	if player.length > rig.snap:
		# (too big for the hook: it takes the bait and the line parts)
		player.feed(rig.bait_long)
		_lose_rig(rig)
		_count("snapped")
		return
	rig.on = player
	_start_haul(rig)
	holding = "hook"
	_count("hooked")
	grip = 1.0
	doom = 0.0
	_rig = rig
	player.caught = true
	player.ate.emit(bait)


func _start_haul(rig: Rig) -> void:
	rig.out = rig.anchor().distance_to(rig.tip)
	rig.out_from = maxf(rig.out, 0.5)
	rig.haul = maxf(rig.out / HAUL_TIME, HAUL_SLOWEST)
	rig.lift = 0.0
	rig.bait.visible = false


## Something is on the line: it comes up, a little slower while it fights.
func _haul(rig: Rig, delta: float) -> void:
	var anchor := rig.anchor()
	var fish: Fish = rig.on
	if fish == player:
		_struggle(delta, (anchor - player.global_position).normalized())
		if holding != "hook":
			return
		var fight := player.boosting
		rig.out = maxf(rig.out - rig.haul * (HAUL_FIGHT if fight else 1.0) * delta, 0.0)
		doom = clampf(1.0 - rig.out / rig.out_from, 0.0, 1.0)
	else:
		var creature := fish as Creature
		if creature == null or creature.away > 0.0:
			_free_creature(fish)
			rig.on = null
			_lose_rig(rig)
			return
		rig.out = maxf(rig.out - rig.haul * delta, 0.0)
	# The fish hangs from the line, swung a little the way it pulls.
	var flat := Vector3(fish.heading.x, 0.0, fish.heading.z)
	var way := (Vector3.DOWN + flat * (0.7 if fish == player and player.boosting else 0.35)).normalized()
	rig.tip = anchor + way * rig.out
	if rig.out <= 0.05:
		# At the surface: out it comes.
		if rig.lift == 0.0 and fish == player:
			player.leapt.emit(anchor)
		rig.lift += delta
		rig.tip = anchor + Vector3.UP * minf(rig.lift * 3.0, 1.2)
	fish.global_position = rig.tip - fish.heading * fish.length * 0.42
	rig.hook.position = rig.tip - Vector3(rig.hook.global_basis * BEND)
	if rig.lift > 0.45:
		if fish == player:
			_let_go(false)
			player.safe = 0.0
			player.die("hook")
			_count("caught")
		else:
			_count("sea life hooked")
			fish.visible = false
			(fish as Creature).away = _rng.randf_range(8.0, 16.0)
			_free_creature(fish)
		rig.on = null
		_lose_rig(rig)


## Now and then a fish of the sea that is near a bait goes for it, and may be hooked.
func _tempt(rig: Rig) -> void:
	var bait := rig.bait_at()
	for each in life.awake:
		if each.away > 0.0 or each.giant or not each.visible or _held.has(each.get_instance_id()):
			continue
		if each.length > rig.snap or not Life.is_food(each.length, rig.bait_long):
			continue
		var far := each.global_position.distance_to(bait)
		if far > 6.0:
			continue
		if each.mouth().distance_to(bait) < each.length * Life.TAKES + Life.TAKES_LEAST + rig.bait_long * 0.5:
			rig.on = each
			_held[each.get_instance_id()] = true
			_start_haul(rig)
			return
		if each.mode == Creature.Mode.WANDER and _rng.randf() < 0.08:
			each._goal = bait
			each._goal_time = 6.0


func _lose_rig(rig: Rig) -> void:
	rig.away = _rng.randf_range(REBAIT.x, REBAIT.y)
	_show_rig(rig, false)


func _show_rig(rig: Rig, shown: bool) -> void:
	rig.hook.visible = shown
	rig.bait.visible = shown
	rig.sinker.visible = shown
	rig.line.visible = shown
	rig.leader.visible = shown


# ---------------------------------------------------------------------------------------------- nets
func _make_nets() -> void:
	for spec: Array in NETS:
		var net := Net.new()
		var from: Vector2 = spec[0]
		var to: Vector2 = spec[1]
		net.how = spec[2]
		net.lo = spec[4]
		net.hi = spec[5]
		var tall: float = spec[3]
		if net.how == "drift":
			net.top = Sea.SURFACE - 0.12
		else:
			var floor_y := -INF
			for k in 9:
				var p := from.lerp(to, k / 8.0)
				floor_y = maxf(floor_y, Sea.ground(p.x, p.y))
			net.top = floor_y + 0.3 + tall
		net.bottom = net.top - tall
		net.a = Vector3(from.x, net.top, from.y)
		net.b = Vector3(to.x, net.top, to.y)
		net.long = net.a.distance_to(net.b)
		net.along = (net.b - net.a) / net.long
		net.normal = net.along.cross(Vector3.UP).normalized()
		net.material = ShaderMaterial.new()
		net.material.shader = NET_SHADER
		net.material.set_shader_parameter(&"sway", 0.25)
		net.shade()
		net.panel = MeshInstance3D.new()
		net.panel.mesh = _meshes["NetPanel"]
		net.panel.material_override = net.material
		net.panel.lod_bias = 64.0
		net.panel.transform = Transform3D(Basis(net.along * net.long, Vector3.UP * tall, net.normal), (net.a + net.b) * 0.5)
		net.panel.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(net.panel)
		# Floats along its head, weights along its foot, a marker buoy over each end.
		var count := int(net.long / NET_SPACING) + 1
		_row(net, "NetFloat", net.top + 0.05, count, 2.0)
		_row(net, "NetWeight", net.bottom, count, 2.0)
		for end: Vector3 in [net.a, net.b]:
			var buoy := _mesh("MarkerBuoy", 1.6)
			buoy.position = Vector3(end.x, Sea.SURFACE, end.z)
			buoy.set_meta(&"phase", _rng.randf() * TAU)
			add_child(buoy)
			_buoys.append(buoy)
			if net.how == "bottom":
				var rope := _line(_warp_material)
				_stretch(rope, Vector3(end.x, Sea.SURFACE, end.z), end, 0.02)
		nets.append(net)
		_net_side_reset(net)


func _row(net: Net, mesh_name: String, y: float, count: int, big: float) -> void:
	var many := MultiMesh.new()
	many.transform_format = MultiMesh.TRANSFORM_3D
	many.mesh = _meshes[mesh_name]
	many.instance_count = count
	var basis := Basis(net.along, Vector3.UP, net.normal).scaled(Vector3.ONE * big)
	for k in count:
		var at := net.a.lerp(net.b, k / maxf(count - 1.0, 1.0))
		many.set_instance_transform(k, Transform3D(basis, Vector3(at.x, y, at.z)))
	var draw := MultiMeshInstance3D.new()
	draw.multimesh = many
	draw.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(draw)


func _net_side_reset(net: Net) -> void:
	net.set_meta(&"side", net.side(player.global_position) if player else 0.0)


func _step_net(net: Net, delta: float, armed: bool, scanning: bool) -> void:
	var at := player.global_position
	var far := net.nearest(at).distance_to(at)
	net.panel.visible = far < GEAR_SEEN
	# Torn places are mended after a while.
	var mended := false
	for k in range(net.holes.size() - 1, -1, -1):
		var hole := net.holes[k]
		hole.w -= delta
		net.holes[k] = hole
		if hole.w <= 0.0:
			net.holes.remove_at(k)
			mended = true
	if mended:
		net.shade()
	# Sea life hanging in it.
	for k in range(net.catch.size() - 1, -1, -1):
		var held: Array = net.catch[k]
		var fish: Creature = held[0]
		held[2] = float(held[2]) - delta
		if fish.away > 0.0 or float(held[2]) <= 0.0:
			if fish.away <= 0.0:
				fish.visible = false
				fish.away = _rng.randf_range(8.0, 16.0)
			_free_creature(fish)
			net.catch.remove_at(k)
			continue
		fish.global_position = held[1]
	if scanning and far < 45.0:
		_net_scan(net)
	var was: float = net.get_meta(&"side")
	var now := net.side(at)
	net.set_meta(&"side", now)
	if holding == "net" and _net == net:
		# Held: it stays where it went in, struggling.
		player.global_position = _net_at
		_struggle(delta, net.normal * signf(_net_from))
		if holding != "net":
			return
		doom = minf(doom + delta / NET_HOLD, 1.0)
		if doom >= 1.0:
			_let_go(false)
			player.safe = 0.0
			player.die("net")
			_count("caught")
		return
	if not armed or holding != "" or far > player.length + 1.0:
		return
	if signf(was) == signf(now) or was == 0.0:
		return
	# It has gone through the net's plane this frame: where?
	var cross := at.lerp(at - player.velocity * delta, absf(now) / maxf(absf(now) + absf(was), 0.0001))
	if not net.covers(cross):
		return
	if player.length < net.lo:
		return
	if player.length > net.hi:
		# (too big: it tears through, and leaves a hole)
		_tear(net, cross, player.length * 0.45)
		_count("tore")
		return
	holding = "net"
	_count("netted")
	_net = net
	_net_from = was
	_net_at = cross + net.normal * signf(was) * player.length * 0.1
	grip = 1.0
	doom = 0.0
	player.caught = true
	player.global_position = _net_at


func _tear(net: Net, at: Vector3, radius: float) -> void:
	var where := net.on_it(at)
	if net.holes.size() >= 6:
		net.holes.remove_at(0)
	net.holes.append(Vector4(where.x, where.y, radius, 60.0))
	net.shade()


func _net_scan(net: Net) -> void:
	# (schooling, 2026-11-18: a swarm or school swimming into the net loses a few to it, and scatters)
	for t: float in [0.2, 0.5, 0.8]:
		var at := net.a.lerp(net.b, t)
		at.y = lerpf(net.top, net.bottom, 0.5)
		if life.catch_schools(at, 1.5, 1) > 0:
			_count("school fish netted")
	if net.catch.size() >= NET_CATCH:
		return
	for each in life.awake:
		if each.away > 0.0 or each.giant or not each.visible or _held.has(each.get_instance_id()):
			continue
		if each.length < net.lo or each.length > net.hi:
			continue
		if absf(net.side(each.global_position)) > 0.25 or not net.covers(each.global_position):
			continue
		_held[each.get_instance_id()] = true
		net.catch.append([each, each.global_position, _rng.randf_range(25.0, 40.0)])
		_count("sea life netted")
		if net.catch.size() >= NET_CATCH:
			return


# ---------------------------------------------------------------------------------------------- trawlers
func _make_trawlers() -> void:
	var boat_scene: PackedScene = load(BOAT) if ResourceLoader.exists(BOAT) else null
	for k in LOOPS.size():
		var trawler := Trawler.new()
		trawler.loop = LOOPS[k]
		trawler.s = _rng.randf() * _loop_length(trawler.loop)
		if boat_scene:
			trawler.boat = boat_scene.instantiate()
			# (one mesh a material, not about 45 pieces: scripts/still_batch.gd)
			StillBatch.merge(trawler.boat)
		else:
			trawler.boat = Node3D.new()
		add_child(trawler.boat)
		_wake(trawler.boat)
		trawler.trawl = MeshInstance3D.new()
		trawler.trawl.mesh = _meshes["Trawl"]
		trawler.trawl.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		var net_material := ShaderMaterial.new()
		net_material.shader = NET_SHADER
		net_material.set_shader_parameter(&"panel", false)
		net_material.set_shader_parameter(&"mesh", 0.22)
		net_material.set_shader_parameter(&"strand", 0.018)
		for surface in trawler.trawl.mesh.get_surface_count():
			var made := trawler.trawl.mesh.surface_get_material(surface)
			if made and made.resource_name == "net":
				trawler.trawl.set_surface_override_material(surface, net_material)
		add_child(trawler.trawl)
		for side in 2:
			var door := _mesh("OtterDoor", 1.0)
			trawler.doors.append(door)
			trawler.warps.append(_line(_warp_material))
			trawler.bridles.append(_line(_warp_material))
		trawler.mouth_y = Sea.SURFACE - float(trawler.loop.depth)
		trawler.was = Vector3(0.0, 0.0, -100.0)
		trawlers.append(trawler)
		_place_trawler(trawler, 0.0)


## The boat's wake: bubbles streaming from under its stern.
func _wake(boat: Node3D) -> void:
	var wake := CPUParticles3D.new()
	wake.amount = 60
	wake.lifetime = 5.0
	wake.local_coords = false
	wake.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	wake.emission_box_extents = Vector3(1.4, 0.25, 0.4)
	wake.direction = Vector3(0.0, 0.15, 1.0)
	wake.spread = 25.0
	wake.initial_velocity_min = 0.2
	wake.initial_velocity_max = 0.7
	wake.gravity = Vector3(0.0, 0.08, 0.0)
	wake.scale_amount_min = 0.5
	wake.scale_amount_max = 1.6
	var drop := SphereMesh.new()
	drop.radius = 0.07
	drop.height = 0.14
	drop.radial_segments = 6
	drop.rings = 3
	var white := StandardMaterial3D.new()
	white.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	white.albedo_color = Color(0.85, 0.95, 1.0)
	drop.material = white
	wake.mesh = drop
	wake.position = Vector3(0.0, -0.5, 6.6)
	wake.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	boat.add_child(wake)


static func _loop_length(loop: Dictionary) -> float:
	return 4.0 * float(loop.half) + TAU * float(loop.radius)


## Where along its loop a point `s` metres round is (at the surface), and which way it goes there.
static func loop_at(loop: Dictionary, s: float) -> Array:
	var c: Vector2 = loop.at
	var r: float = loop.radius
	var h: float = loop.half
	var straight := 2.0 * h
	var arc := PI * r
	s = fposmod(s, 2.0 * straight + 2.0 * arc)
	var p := Vector2.ZERO
	var t := Vector2.ZERO
	if s < straight:
		p = Vector2(c.x + r, c.y - h + s)
		t = Vector2(0.0, 1.0)
	elif s < straight + arc:
		var a := (s - straight) / r
		p = Vector2(c.x + r * cos(a), c.y + h + r * sin(a))
		t = Vector2(-sin(a), cos(a))
	elif s < 2.0 * straight + arc:
		p = Vector2(c.x - r, c.y + h - (s - straight - arc))
		t = Vector2(0.0, -1.0)
	else:
		var a := PI + (s - 2.0 * straight - arc) / r
		p = Vector2(c.x + r * cos(a), c.y - h + r * sin(a))
		t = Vector2(-sin(a), cos(a))
	return [Vector3(p.x, Sea.SURFACE, p.y), Vector3(t.x, 0.0, t.y)]


func _place_trawler(trawler: Trawler, delta: float) -> void:
	trawler.s += TOW * delta
	var here := loop_at(trawler.loop, trawler.s)
	var at: Vector3 = here[0]
	var bob := 0.06 * sin(_clock * 0.8 + trawler.s)
	trawler.boat.global_transform = Transform3D(Basis.looking_at(here[1], Vector3.UP).rotated(here[1], 0.02 * sin(_clock * 0.7)), at + Vector3.UP * bob)
	var behind := loop_at(trawler.loop, trawler.s - LAG)
	var mouth: Vector3 = behind[0]
	var want := maxf(Sea.SURFACE - float(trawler.loop.depth), Sea.ground(mouth.x, mouth.z) + 2.2)
	trawler.mouth_y = want if delta == 0.0 else lerpf(trawler.mouth_y, want, 1.0 - exp(-0.5 * delta))
	mouth.y = trawler.mouth_y
	trawler.trawl.global_transform = Transform3D(Basis.looking_at(behind[1], Vector3.UP), mouth)
	var doors := loop_at(trawler.loop, trawler.s - LAG + 5.0)
	var across := (doors[1] as Vector3).cross(Vector3.UP).normalized()
	for side in 2:
		var hand := -1.0 if side == 0 else 1.0
		var door := trawler.doors[side]
		var door_at: Vector3 = doors[0] + across * DOORS * hand
		door_at.y = trawler.mouth_y + 0.4
		door.global_transform = Transform3D(Basis.looking_at(doors[1], Vector3.UP).scaled(Vector3.ONE), door_at)
		_stretch(trawler.warps[side], trawler.boat.global_transform * Vector3(STERN.x * hand, STERN.y, STERN.z), door_at, 0.035)
		_stretch(trawler.bridles[side], door_at, trawler.trawl.global_transform * Vector3(3.0 * hand, 0.0, 0.0), 0.03)


func _step_trawler(trawler: Trawler, delta: float, armed: bool, scanning: bool) -> void:
	_place_trawler(trawler, delta)
	var eye := player.global_position
	trawler.boat.visible = trawler.boat.global_position.distance_to(eye) < BOAT_SEEN
	var near := trawler.trawl.global_position.distance_to(eye) < GEAR_SEEN
	trawler.trawl.visible = near
	for k in 2:
		trawler.doors[k].visible = near
		trawler.warps[k].visible = near
		trawler.bridles[k].visible = near
	_trawl_catch(trawler, delta, scanning)
	# The player.
	var local := trawler.frame_of(eye)
	var was := trawler.was
	trawler.was = local
	if not trawler.holds:
		if not armed or holding != "" or player.length > TRAWL_BIG:
			return
		# (in through the mouth: the net has come over it, or it has swum in)
		if was.z < 0.0 and local.z >= 0.0 and local.z < 3.0 and Trawler.spread(local) < 1.0:
			trawler.holds = true
			trawler.codend = 0.0
			_trawler = trawler
			holding = "trawl"
			_count("trawled")
			grip = 1.0
			doom = 0.0
		return
	if not player.alive:
		trawler.holds = false
		return
	if local.z < 0.0 or player.length > TRAWL_BIG:
		# Out of the mouth.
		_trawl_out(trawler)
		return
	var squeeze := Trawler.spread(local)
	if squeeze >= 1.0:
		var pass_through := lerpf(TRAWL_PASS.x, TRAWL_PASS.y, clampf(local.z / CODEND, 0.0, 1.0))
		if player.length < pass_through:
			# (small enough to go through the mesh)
			_trawl_out(trawler)
			return
		# (the net holds it in)
		var inside := Vector3(local.x, local.y, 0.0) / sqrt(squeeze) * 0.96
		local = Vector3(inside.x, inside.y, local.z)
	local.z = minf(local.z, 9.4)
	player.global_position = trawler.trawl.global_transform * local
	trawler.was = local
	if local.z > CODEND:
		trawler.codend += delta
	else:
		trawler.codend = maxf(trawler.codend - delta * 0.5, 0.0)
	# (for the trawl, the bar is how far in it is: swum out, it is empty)
	grip = clampf(local.z / CODEND, 0.05, 1.0)
	doom = clampf(trawler.codend / CODEND_TIME, 0.0, 1.0)
	if trawler.codend >= CODEND_TIME:
		_trawl_out(trawler)
		player.safe = 0.0
		player.die("trawl")
		_count("caught")


func _trawl_out(trawler: Trawler) -> void:
	trawler.holds = false
	trawler.codend = 0.0
	if _trawler == trawler:
		_trawler = null
		holding = ""
		_shaken = SHAKEN * 0.5
		if player.alive:
			_count("out of a trawl")


## Sea life swept into a trawl goes back to its cod end, and is hauled.
func _trawl_catch(trawler: Trawler, delta: float, scanning: bool) -> void:
	for k in range(trawler.catch.size() - 1, -1, -1):
		var held: Array = trawler.catch[k]
		var fish: Creature = held[0]
		if fish.away > 0.0:
			_free_creature(fish)
			trawler.catch.remove_at(k)
			continue
		var local: Vector3 = held[1]
		local.z = minf(local.z + 1.6 * delta, 9.0)
		var wide := Trawler.section(local.z) * 0.8
		local.x = clampf(local.x, -wide.x, wide.x)
		local.y = clampf(local.y, -wide.y, wide.y)
		held[1] = local
		if local.z >= 8.5:
			held[2] = float(held[2]) + delta
		fish.global_position = trawler.trawl.global_transform * local
		if float(held[2]) > 4.0:
			fish.visible = false
			fish.away = _rng.randf_range(10.0, 20.0)
			_free_creature(fish)
			trawler.catch.remove_at(k)
	if not scanning or trawler.catch.size() >= TRAWL_CATCH:
		return
	var mouth := trawler.trawl.global_position
	if mouth.distance_to(player.global_position) > 50.0:
		return
	# (schooling, 2026-11-18: the trawl takes from a swarm or school its mouth passes through, and
	# the rest of it scatters)
	if life.catch_schools(mouth, 2.0, 3) > 0:
		_count("school fish trawled")
	for each in life.awake:
		if each.away > 0.0 or each.giant or not each.visible or each.length > TRAWL_BIG or _held.has(each.get_instance_id()):
			continue
		if each.global_position.distance_to(mouth) > 6.0:
			continue
		var local := trawler.frame_of(each.global_position)
		if local.z >= 0.0 and local.z < 2.0 and Trawler.spread(local) < 1.0:
			_held[each.get_instance_id()] = true
			trawler.catch.append([each, local, 0.0])
			_count("sea life trawled")
			if trawler.catch.size() >= TRAWL_CATCH:
				return


# ---------------------------------------------------------------------------------------------- the struggle
## The player fights what holds it: the burst, turning away from `pull`, wriggling.
func _struggle(delta: float, pull: Vector3) -> void:
	var loose := 0.0
	# (pulling away counts only while it bursts against what holds it)
	if player.boosting:
		loose += STRUGGLE_BURST
		if player.heading.dot(pull) < -0.3:
			loose += STRUGGLE_AWAY
	if absf(player.stick.x) > 0.5 or absf(player.stick.y) > 0.5:
		loose += STRUGGLE_WRIGGLE
	grip = maxf(grip - loose * delta, 0.0)
	if grip <= 0.0:
		_let_go(true)


## Whatever holds the player lets go of it (`won`: it struggled free).
func _let_go(won: bool) -> void:
	if holding == "hook" and _rig:
		# (the line parts, or the fish is gone: the hook and its line are gone a while)
		_rig.on = null
		_lose_rig(_rig)
	elif holding == "net" and _net and won:
		# (it tears its way through, to the far side)
		_tear(_net, _net_at, player.length * 0.5)
		player.global_position = _net_at - _net.normal * signf(_net_from) * player.length * 0.7
		_net_side_reset(_net)
	elif holding == "trawl" and _trawler:
		_trawler.holds = false
		_trawler.codend = 0.0
	if won:
		_count("freed")
		_shaken = SHAKEN
		player.ate.emit(player.mouth())
	holding = ""
	_rig = null
	_net = null
	_trawler = null
	grip = 1.0
	doom = 0.0
	if player:
		player.caught = false


func _count(what: String) -> void:
	tally[what] = int(tally.get(what, 0)) + 1


func _free_creature(fish: Node3D) -> void:
	if is_instance_valid(fish):
		_held.erase(fish.get_instance_id())


# ---------------------------------------------------------------------------------------------- pieces
func _mesh(mesh_name: String, big: float) -> MeshInstance3D:
	var made := MeshInstance3D.new()
	made.mesh = _meshes[mesh_name]
	made.scale = Vector3.ONE * big
	made.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	if mesh_name != "Bobber" and mesh_name != "MarkerBuoy":
		add_child(made)
	return made


func _line(material: Material) -> MeshInstance3D:
	var made := MeshInstance3D.new()
	made.mesh = _meshes["Line"]
	made.material_override = material
	made.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(made)
	return made


## A line (a unit rod along y) stretched from a to b, so thick.
static func _stretch(line: MeshInstance3D, a: Vector3, b: Vector3, thick: float) -> void:
	var d := b - a
	var long := d.length()
	if long < 0.001:
		line.visible = false
		return
	var y := d / long
	var x := y.cross(Vector3.FORWARD if absf(y.z) < 0.9 else Vector3.RIGHT).normalized()
	var z := x.cross(y)
	line.transform = Transform3D(Basis(x * thick, y * long, z * thick), a)


# ---------------------------------------------------------------------------------------------- pictures
func _process(_delta: float) -> void:
	for buoy in _buoys:
		buoy.position.y = Sea.SURFACE + 0.05 * sin(_clock * 1.2 + float(buoy.get_meta(&"phase")))
	if _look == "" or _near == "":
		return
	var eye := get_viewport().get_camera_3d()
	if eye == null:
		return
	var at := near(_near)
	var from := at
	match [_near, _look]:
		["hook", "side"], ["skiff", "side"]:
			from = at + Vector3(1.0, 0.15, 0.25)
		["hook", "below"], ["skiff", "below"]:
			from = at + Vector3(0.6, -1.6, 0.8)
			at = at.lerp(Vector3(at.x, Sea.SURFACE, at.z), 0.5)
		["hook", "close"], ["skiff", "close"]:
			from = at + Vector3(0.2, 0.03, 0.14)
		["net", "side"]:
			from = at + nets[0].normal * 13.0 + Vector3.UP * 0.5
		["net", "below"]:
			from = at + nets[0].normal * 4.0 + Vector3.DOWN * 5.0
			at += Vector3.UP * 2.0
		["net", "close"]:
			from = at + nets[0].normal * 1.8 + nets[0].along * 0.6
		["trawl", "side"]:
			var trawl := trawlers[0].trawl
			at = trawl.global_transform * Vector3(0.0, 0.0, 3.0)
			from = at + trawl.global_basis.x.normalized() * 16.0 + Vector3.UP * 2.0
		["trawl", "below"]:
			var trawl := trawlers[0].trawl
			at = trawl.global_position.lerp(trawlers[0].boat.global_position, 0.5)
			from = trawl.global_transform * Vector3(0.0, -9.0, -6.0)
		["trawl", "hull"]:
			at = trawlers[0].boat.global_position
			from = at + Vector3(4.0, -9.0, 5.0)
		["trawl", "close"]:
			var trawl := trawlers[0].trawl
			from = trawl.global_transform * Vector3(1.2, 0.5, -4.5)
			at = trawl.global_transform * Vector3(0.0, 0.0, 4.0)
	eye.global_position = from
	if from.distance_to(at) > 0.01:
		eye.look_at(at, Vector3.UP)


## The struggle shown over the sea: what holds the fish, how much of its hold is left (the bar that
## runs down as it struggles), how near it is to being hauled (the red bar), and the burst (the bolt;
## the burst button itself is ringed).
class Meter:
	extends Control

	const BRASS := Color(0.85, 0.66, 0.3)
	const IRON := Color(0.07, 0.08, 0.1)

	var what := "":
		set(to):
			if to != what:
				what = to
				queue_redraw()
	var grip := 1.0
	var doom := 0.0
	var _clock := 0.0

	func _ready() -> void:
		set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		mouse_filter = Control.MOUSE_FILTER_IGNORE
		# (over the controls, which Main adds after it, so that the ring round the burst button shows)
		_on_top.call_deferred()

	func _on_top() -> void:
		if get_parent():
			get_parent().move_child(self, -1)

	func _process(delta: float) -> void:
		_clock += delta
		if what != "":
			queue_redraw()

	func _draw() -> void:
		if what == "":
			return
		var u := minf(size.x, size.y) / 720.0
		var tall := 92.0 * u
		var wide := minf(420.0 * u, size.x - 40.0 * u)
		var middle := Vector2(size.x * 0.5, maxf(size.y * 0.36, 260.0 * u))
		var box := Rect2(middle - Vector2(wide, tall) * 0.5, Vector2(wide, tall))
		draw_rect(box, Color(IRON, 0.85))
		draw_rect(box, BRASS, false, 3.0 * u)
		var flash := 0.5 + 0.5 * sin(_clock * 10.0)
		# What holds it.
		var icon := box.position + Vector2(tall * 0.5, tall * 0.5)
		draw_circle(icon, tall * 0.4, Color(0.13, 0.15, 0.18))
		draw_arc(icon, tall * 0.4, 0.0, TAU, 32, BRASS, 2.0 * u, true)
		_icon(icon, tall * 0.28, u)
		# Its hold: the bar that runs down as it struggles (for the trawl, how far in it is).
		var left := box.position.x + tall
		var bar := Rect2(Vector2(left, box.position.y + tall * 0.2), Vector2(box.end.x - left - tall * 0.75, tall * 0.28))
		draw_rect(bar, Color(0.2, 0.2, 0.22))
		draw_rect(Rect2(bar.position, Vector2(bar.size.x * clampf(grip, 0.0, 1.0), bar.size.y)), Color(0.98, 0.62, 0.18))
		draw_rect(bar, BRASS, false, 2.0 * u)
		# How near it is to being hauled.
		var red := Rect2(Vector2(left, box.position.y + tall * 0.6), Vector2(bar.size.x, tall * 0.18))
		draw_rect(red, Color(0.2, 0.08, 0.08))
		draw_rect(Rect2(red.position, Vector2(red.size.x * clampf(doom, 0.0, 1.0), red.size.y)), Color(1.0, 0.2, 0.15, 0.7 + 0.3 * flash))
		draw_rect(red, BRASS, false, 2.0 * u)
		# The burst: a bolt, flashing.
		_bolt(Vector2(box.end.x - tall * 0.38, middle.y), tall * 0.3, Color(1.0, 0.85, 0.3, 0.5 + 0.5 * flash))
		# And a ring round the burst button.
		var pad: Variant = get_parent().get(&"pad")
		if pad is Control and (pad as Control).visible and (pad as Control).has_method(&"boost_home"):
			var at: Vector2 = (pad as Control).call(&"boost_home")
			draw_arc(at, (95.0 + 12.0 * flash) * u, 0.0, TAU, 48, Color(1.0, 0.8, 0.25, 0.35 + 0.5 * flash), 6.0 * u, true)

	func _icon(at: Vector2, r: float, u: float) -> void:
		var ink := Color(0.9, 0.95, 1.0)
		match what:
			"hook":
				draw_line(at + Vector2(-r * 0.2, -r), at + Vector2(-r * 0.2, r * 0.3), ink, 3.0 * u, true)
				draw_arc(at + Vector2(r * 0.25, r * 0.3), r * 0.45, 0.0, PI, 16, ink, 3.0 * u, true)
				draw_line(at + Vector2(r * 0.7, r * 0.3), at + Vector2(r * 0.7, -r * 0.2), ink, 3.0 * u, true)
				draw_line(at + Vector2(r * 0.7, -r * 0.2), at + Vector2(r * 0.45, r * 0.05), ink, 3.0 * u, true)
				draw_arc(at + Vector2(-r * 0.2, -r * 1.05), r * 0.15, 0.0, TAU, 12, ink, 2.0 * u, true)
			"net":
				for k in 5:
					var t := -1.0 + k * 0.5
					draw_line(at + Vector2(t * r - r * 0.5, -r), at + Vector2(t * r + r * 0.5, r), ink, 2.0 * u, true)
					draw_line(at + Vector2(t * r + r * 0.5, -r), at + Vector2(t * r - r * 0.5, r), ink, 2.0 * u, true)
			"trawl":
				var mouth_top := at + Vector2(-r, -r * 0.8)
				var mouth_low := at + Vector2(-r, r * 0.8)
				var end := at + Vector2(r, 0.0)
				draw_polyline(PackedVector2Array([mouth_top, end, mouth_low]), ink, 3.0 * u, true)
				draw_line(mouth_top, mouth_low, ink, 3.0 * u, true)
				draw_line(at + Vector2(-r * 0.2, -r * 0.5), at + Vector2(-r * 0.2, r * 0.5), ink, 2.0 * u, true)
				draw_line(at + Vector2(r * 0.4, -r * 0.25), at + Vector2(r * 0.4, r * 0.25), ink, 2.0 * u, true)

	func _bolt(at: Vector2, r: float, colour: Color) -> void:
		draw_colored_polygon(PackedVector2Array([at + Vector2(r * 0.15, -r), at + Vector2(-r * 0.55, r * 0.15), at + Vector2(-r * 0.05, r * 0.15),
				at + Vector2(-r * 0.2, r), at + Vector2(r * 0.55, -r * 0.2), at + Vector2(r * 0.05, -r * 0.2)]), colour)
