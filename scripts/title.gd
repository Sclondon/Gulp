class_name Title
extends Node3D
## The start of the game: a shrimp boat under way on the sea. The user (2026-11-18): "the main
## menu / start of the game should be the boy from warren, a sea captain, and and oldtimy diver on
## a shrimping boat (look up reference pics). In the open back cabin of the shrimping boat should
## be a old timey franketstein computer hooked up to a helmet on the boys head- the controls for
## the pc are the controls for the game"; "The boat should be perpendicular in the start scene,
## and the pc against the portside wall", "And hooked up to a monitor"; "The captain needs to be
## driving the boat(which should be moving), the boy sitting on a stool plugged into the vr head
## set, and the diver operating machinery in the back". The concept picture is
## tools/art_src/concept_boat.jpg.
##
## So: the boat (models/shrimp_boat.glb) steams round a wide circle, rocking on the swell, a bow
## wave and a wake behind it; the eye rides off its starboard beam looking across the deck. The
## captain stands at the wheel and turns it; against the port wall of the open cabin stands the
## computer, which is the game's own control panel (models/control_panel.glb, the same model the
## TouchPad shows, on a bench), with a monitor on the wall over it; the boy sits at it on a stool
## in a helmet (models/brain_helmet.glb) cabled to it, his hands on its stick and its button; the
## diver winds the crank of his air pump on the aft deck. When the game is started, Main puts
## the fish in the water under the boat and sends the eye down through the surface to it: what
## the boy steers. Then the boat heaves to there (`heave_to`) and stays for the whole game, its net
## (models/boat_net.glb) hung in the water off the starboard outrigger: a fish swum into its hoop
## (`hoop`) is hauled up and sold (DESIGN.md's loop; Main). While hove-to the people and the
## computer are drawn only when the eye is above the water and near.
##
## This node is where the boat is and how it is headed (its origin on the waterline, the bow
## towards its -Z); `boat` under it rocks. The boat's markers say where things go and which way
## they face (tools/SHRIMP_BOAT.md: a marker's -Z is its facing); the figures are TitleFigures
## (tools/TITLE_FIGURES.md), whose constants say where their hands are. Any part that is not
## there yet (a model not built) is left out.

const BOAT := "res://models/shrimp_boat.glb"
const PANEL := "res://models/control_panel.glb"
const HELMET := "res://models/brain_helmet.glb"
const HELMET_PAINT := "res://textures/panel/helmet_atlas.png"
const FIGURES := "res://scripts/title_figures.gd"
## The net the fish is sold into (tools/build_boat_net.py): its origin is the middle of its hoop, its
## line runs NET_LINE metres straight up from there; it hangs from the starboard outrigger's end
## (NET_TIP, measured off models/shrimp_boat.glb), so the hoop is about 3.6 m under the water.
const NET := "res://models/boat_net.glb"
const NET_TIP := Vector3(3.41, 8.39, 1.78)
const NET_LINE := 12.0
## How far off the eye may be for the figures and the computer to be drawn (m), during a run.
const DETAIL_SEEN := 45.0
## How big the computer is beside the model it shares with the TouchPad, and how high its bench is (m).
const COMPUTER := 0.25
const BENCH := 0.5
## The boy's head, as a radius over his hair (m): what the helmet is sized to.
const HEAD := 0.128
## How far out from the wall the boy sits (m): his hands (TitleFigures.BOY_LEFT_HAND and
## BOY_RIGHT_HAND, 0.32 ahead of him) then rest on the stick's ball and the button.
const SEAT_OUT := 0.84
## The boat's course: a circle of this radius (m), at this speed (m/s), turning to port.
const COURSE := 45.0
const SPEED := 2.4
## Where things go on the boat if its model does not say (metres from its middle at the waterline;
## the bow is towards -Z, starboard +X).
const SPOTS := {
	"ConsoleSpot": Vector3(-1.37, 0.92, -0.2),
	"CaptainSpot": Vector3(0.0, 0.97, -2.75),
	"DiverSpot": Vector3(-0.2, 0.88, 3.0),
	"HelmetCable": Vector3(-1.37, 2.22, -0.2),
	"MonitorSpot": Vector3(-1.37, 2.67, -0.2),
	"BowWave": Vector3(0.0, 0.0, -5.1),
	"Wake": Vector3(0.0, 0.0, 6.5),
}

var boat: Node3D
var boy: Node3D
## The game's name, spelt in fish, held in front of the eye (scripts/title_logo.gd).
var logo: TitleLogo
var _spots := {}
var _figures: GDScript
var _captain: Node3D
var _diver: Node3D
var _wheel: Node3D
var _pump: Node3D
var _helmet: Node3D
var _cables: Array[Node3D] = []
var _sockets: Array[Node3D] = []
var _clock := 0.0
var _middle := Vector3.ZERO
var _round := PI
## Hove-to (the game is under way, DESIGN.md's loop): it no longer steams round but lies where it
## is, its net out. Set by `heave_to`, or before it is added to start so.
var hove := false
## The game's camera: during a run the figures and the computer are drawn only while it is above
## the water and near.
var eye_node: Node3D
## The net (null if its model is not built).
var net: Node3D
var _detail: Array[Node3D] = []
var _foams: Array[CPUParticles3D] = []

## At the helm (the user, 2026-11-20: "we need to work on controlling the boat", then "Drive the shrimp
## boat"): after the start button and before the dive the player drives the boat with the panel (the
## stick steers, the lever is the throttle, the plunger a short burst); Main calls `drive` each frame
## and places its camera by `chase`. CLAUDE.md, "Decision: driving the shrimp boat" (the numbers are
## Claude's picks). Set by `take_helm`, cleared by `heave_to`.
var helm := false
## Its way through the water (m/s, level), how fast it is turning (rad/s, + to port), and how much of
## the burst is left (0..1).
var velocity := Vector3.ZERO
var burst_left := 1.0
var _turn := 0.0
var _bursting := false
var _heel := 0.0
var _chase_yaw := 0.0
var _chase_at := Vector3.INF
## Its speed at the lever's top (m/s), what the burst adds and for how long it lasts in one go (s) and
## how long it takes to fill again (s); how quickly it gathers way and loses it (1/s); how quickly the
## keel kills sideways drift (1/s).
const TOP_SPEED := 6.0
const BURST_SPEED := 4.0
const BURST_LASTS := 2.0
const BURST_FILL := 5.0
const GATHER := 0.45
const COAST := 0.3
const BURST_GATHER := 1.3
const KEEL := 2.2
## Its turning circle at speed (m, a radius), the least it turns at a standstill (rad/s, steerage way),
## and how quickly the rudder takes hold (1/s); how far it heels outward in a turn at most (rad), and
## how much its bow lifts at full speed (rad).
const TURN_RADIUS := 12.0
const TURN_STILL := 0.12
const TURN_EASE := 2.2
const HEEL := 0.09
const SQUAT := 0.03
## The water it needs (m): from SHOAL deep it is pushed back towards deeper water, harder the shallower,
## and any way it has into the shallows is taken off, all of it by AGROUND (a soft push, not a wall).
## How much room it keeps from rocks (m) and the bay's edges (m), and how hard the push is (m/s^2).
const SHOAL := 4.0
const AGROUND := 1.5
const ROCK_ROOM := 4.0
const EDGE_ROOM := 8.0
const PUSH_BACK := 7.0
## How much a wave's slope carries it (a share of g): it runs down the face of the swell and the surf.
const WAVE_CARRY := 0.22
## The chase camera (behind and above, its height fixed over the sea's middle so it never bobs, the
## horizon level, the way it looks lagging the boat's heading): how far back and up in a wide window and
## in an upright one (m), how far ahead of the boat it looks (m: negative is short of it, so the boat
## stands higher in the picture, over the panel), and how quickly it swings round after the boat (1/s)
## and follows it (1/s).
const CHASE_BACK := Vector2(17.0, 24.0)
const CHASE_UP := Vector2(6.0, 9.5)
const CHASE_AHEAD := Vector2(4.0, -3.0)
const CHASE_SWING := 1.8
const CHASE_FOLLOW := 5.0


func _ready() -> void:
	# (it starts where it was put, on the west of its circle, heading north)
	_middle = position + Vector3(COURSE, 0.0, 0.0)
	_steam(0.0)
	boat = Node3D.new()
	add_child(boat)
	for named: String in SPOTS:
		# (facing starboard, unless the model says)
		_spots[named] = Transform3D(Basis(Vector3.UP, -PI * 0.5), SPOTS[named])
	if ResourceLoader.exists(BOAT):
		var hull: Node3D = (load(BOAT) as PackedScene).instantiate()
		boat.add_child(hull)
		# (its paint, plank lines and grime are one baked picture in the model: tools/build_shrimp_boat.py)
		for named: String in SPOTS:
			var marker := hull.find_child(named) as Node3D
			if marker:
				_spots[named] = _place_in(marker, boat)
		_wheel = hull.find_child("Wheel") as Node3D
		_pump = hull.find_child("PumpWheel") as Node3D
		# (its still parts as one mesh a material: it lies hove-to in sight for the whole game, and was
		# about 45 draws; scripts/still_batch.gd)
		StillBatch.merge(hull, [_wheel, _pump])
	# The computer: the control panel's housings on a bench against the wall, leaning back a
	# little: the instruments (the two small boxes under them) to the left, then the helm and the
	# engine close together, where the boy's hands are; and its monitor on the wall over it.
	# (The models face +Z; a marker faces its -Z: so they are turned round on the spot.)
	var about := Basis(Vector3.UP, PI)
	var console: Transform3D = _spots["ConsoleSpot"]
	var parts: Node3D = (load(HELMET) as PackedScene).instantiate()
	PanelModel.paint(parts, true, HELMET_PAINT)
	var bench := _take(parts, "Bench")
	bench.transform = console * Transform3D(about, Vector3(0.0, 0.0, -0.36))
	boat.add_child(bench)
	var computer: Node3D = (load(PANEL) as PackedScene).instantiate()
	PanelModel.paint(computer, true)
	computer.transform = console * Transform3D((about * Basis(Vector3.RIGHT, -0.12)).scaled(Vector3.ONE * COMPUTER), Vector3(0.0, BENCH, -0.22))
	var helm_at := 0.57
	var engine_at := 2.82
	(computer.find_child("Helm") as Node3D).position.x = helm_at
	(computer.find_child("Engine") as Node3D).position.x = engine_at
	(computer.find_child("Gauges") as Node3D).position = Vector3(-2.73, PanelModel.SMALL_TALL + 0.03, 0.0)
	(computer.find_child("Switches") as Node3D).position = Vector3(-2.73 - PanelModel.SMALL_WIDE * 0.5 - 0.05, 0.0, 0.0)
	(computer.find_child("Aux") as Node3D).position = Vector3(-2.73 + PanelModel.SMALL_WIDE * 0.5 + 0.05, 0.0, 0.0)
	boat.add_child(computer)
	# (the boy sits in front of where the helm and the engine meet: the computer's x there, in
	# the console's frame, which is turned round)
	var seat := console * Vector3(-(helm_at + engine_at) * 0.5 * COMPUTER, 0.0, -SEAT_OUT)
	var monitor := _take(parts, "Monitor")
	if monitor:
		monitor.transform = (_spots["MonitorSpot"] as Transform3D) * Transform3D(about, Vector3.ZERO)
		boat.add_child(monitor)
		# (its screen glows green)
		var screen := monitor.find_child("MonitorScreen") as MeshInstance3D
		if screen:
			var lit: ShaderMaterial = (screen.get_surface_override_material(0) as ShaderMaterial).duplicate()
			lit.set_shader_parameter(&"tint", Color(2.5, 3.0, 2.5))
			lit.set_shader_parameter(&"glow", Color(0.03, 0.22, 0.07))
			screen.set_surface_override_material(0, lit)
	var stool := _take(parts, "Stool")
	if stool:
		stool.position = seat
		boat.add_child(stool)
	# The three of them, each at its work.
	if ResourceLoader.exists(FIGURES):
		_figures = load(FIGURES)
		boy = _figures.call(&"boy")
		# (facing the console: the way its marker faces, turned round)
		boy.transform = Transform3D(console.basis * about, seat)
		boat.add_child(boy)
		_captain = _figures.call(&"captain")
		_captain.transform = _spots["CaptainSpot"]
		boat.add_child(_captain)
		_diver = _figures.call(&"diver")
		# (the pump's crank is 0.5 m from his spot; his hands reach 0.34)
		_diver.transform = (_spots["DiverSpot"] as Transform3D) * Transform3D(Basis.IDENTITY, Vector3(0.0, 0.0, -0.16))
		boat.add_child(_diver)
		# The helmet on the boy's head, and its two cables to the computer.
		var head: Node3D = _figures.call(&"head_node", boy)
		if head:
			_helmet = _take(parts, "Helmet")
			head.add_child(_helmet)
			# (built round a head of radius 1 with its face to +Z, as the mount is: sized to his, and sat
			# on the middle of his skull)
			_helmet.transform = Transform3D(Basis.IDENTITY.scaled(Vector3.ONE * HEAD), Vector3(0.0, 0.1, 0.005))
			var cable := _take(parts, "Cable")
			for named: String in ["CableA", "CableB"]:
				_sockets.append(_helmet.find_child(named))
				var one: Node3D = cable.duplicate()
				boat.add_child(one)
				_cables.append(one)
			cable.free()
	parts.free()
	for each: Node3D in [bench, computer, monitor, stool, boy, _captain, _diver]:
		if each:
			_detail.append(each)
	_detail.append_array(_cables)
	logo = TitleLogo.new()
	add_child(logo)
	_foam("BowWave", 40, 0.4, 1.6, 1.4)
	_foam("Wake", 50, 0.55, 2.4, 0.7)
	# The net, hung from the starboard outrigger's end (two-sided, drawn as the fishers' nets are).
	if ResourceLoader.exists(NET):
		net = (load(NET) as PackedScene).instantiate()
		var mesh_paint := ShaderMaterial.new()
		mesh_paint.shader = load("res://shaders/net.gdshader")
		mesh_paint.set_shader_parameter(&"panel", false)
		mesh_paint.set_shader_parameter(&"mesh", 0.12)
		mesh_paint.set_shader_parameter(&"strand", 0.014)
		for mesh: MeshInstance3D in net.find_children("*", "MeshInstance3D", true, false):
			for surface in mesh.mesh.get_surface_count():
				var made := mesh.mesh.surface_get_material(surface)
				if made and made.resource_name == "net":
					mesh.set_surface_override_material(surface, mesh_paint)
		net.position = NET_TIP - Vector3(0.0, NET_LINE, 0.0)
		boat.add_child(net)
	if hove:
		heave_to()
	elif net:
		net.visible = false


## Stops it where it is, its net out: the game is under way. The name over it goes.
func heave_to() -> void:
	hove = true
	helm = false
	velocity = Vector3.ZERO
	_turn = 0.0
	_heel = 0.0
	if logo:
		logo.visible = false
	for foam in _foams:
		foam.emitting = false
	if net:
		net.visible = true


## The player takes the helm: it stops steaming round its circle and goes as it is driven, under way at
## its circling speed. The name over it goes.
func take_helm() -> void:
	helm = true
	if logo:
		logo.visible = false
	velocity = -global_basis.z * SPEED
	_chase_yaw = global_rotation.y
	_chase_at = Vector3.INF


## Puts it somewhere, heading somewhere (radians round from north, the sea's -Z, towards west): for tests.
func place(at: Vector2, heading: float) -> void:
	position = Vector3(at.x, Sea.SURFACE, at.y)
	basis = Basis(Vector3.UP, heading)
	velocity = -basis.z * velocity.length()
	_chase_yaw = heading
	_chase_at = Vector3.INF


## Its speed through the water as a share of the most it goes, bursting (for the panel's speed dial).
func speed_share() -> float:
	return clampf(velocity.length() / (TOP_SPEED + BURST_SPEED), 0.0, 1.0)


## One frame at the helm: `stick` (x right, -1..1) puts the rudder over, `throttle` (0..1) sets the way
## it gathers to, `burst` held adds a short burst. An arcade boat, not a simulation (as most games
## drive boats: a velocity kept along the keel, its sideways part damped hard, a turn rate that needs
## way on, the hull's tilt only drawn): it gathers way and loses it slowly, turns in a circle, runs down
## the faces of waves, and is pushed back from shallows, rocks and the bay's edges.
func drive(stick: Vector2, throttle: float, burst: bool, delta: float) -> void:
	if not helm or delta <= 0.0:
		return
	var ahead := -global_basis.z
	ahead.y = 0.0
	ahead = ahead.normalized()
	# The burst: held, it lasts BURST_LASTS in one go; let go, it fills again.
	_bursting = burst and burst_left > 0.0
	if _bursting:
		burst_left = maxf(burst_left - delta / BURST_LASTS, 0.0)
	elif not burst:
		burst_left = minf(burst_left + delta / BURST_FILL, 1.0)
	# Way along the keel, gathered or lost towards what the lever asks; drift across it killed by the keel.
	var along := velocity.dot(ahead)
	var want := clampf(throttle, 0.0, 1.0) * TOP_SPEED + (BURST_SPEED if _bursting else 0.0)
	var rate := BURST_GATHER if _bursting else (GATHER if want > along else COAST)
	along = lerpf(along, want, 1.0 - exp(-rate * delta))
	var across := (velocity - ahead * velocity.dot(ahead)) * exp(-KEEL * delta)
	velocity = ahead * along + across
	# The rudder: a turn rate that grows with the way on (a turning circle of TURN_RADIUS), a little at
	# a standstill, eased in.
	var want_turn := -clampf(stick.x, -1.0, 1.0) * maxf(absf(along) / TURN_RADIUS, TURN_STILL)
	_turn = lerpf(_turn, want_turn, 1.0 - exp(-TURN_EASE * delta))
	rotate_y(_turn * delta)
	# (it heels outward in a turn, more the faster: drawn on the rocking boat)
	_heel = clampf(-_turn * along * 0.06, -HEEL, HEEL)
	# The water's slope carries it a little (down the face of the swell and the surf), and a rogue wave
	# shoves it.
	var at := global_position
	var slope := Vector2(Sea.surface_height(at.x + 1.5, at.z) - Sea.surface_height(at.x - 1.5, at.z), Sea.surface_height(at.x, at.z + 1.5) - Sea.surface_height(at.x, at.z - 1.5)) / 3.0
	velocity -= Vector3(slope.x, 0.0, slope.y) * 9.8 * WAVE_CARRY * delta
	velocity += Sea.surge(Vector3(at.x, Sea.SURFACE - 0.5, at.z)) * delta
	_keep_off(delta)
	velocity.y = 0.0
	position += velocity * delta
	position.y = Sea.SURFACE


# The soft push back from what it cannot go into: shallows (Bay's depth, at the hull's middle and at
# its bow), rocks standing near the surface, the bay's edges.
func _keep_off(delta: float) -> void:
	var at := global_position
	var ahead := -global_basis.z
	var away := Vector3.ZERO
	var most := 0.0
	for probe: Vector3 in [at, at + ahead * 5.0]:
		var deep := Sea.SURFACE - Sea.ground(probe.x, probe.z)
		var shallow := clampf((SHOAL - deep) / (SHOAL - AGROUND), 0.0, 1.5)
		if shallow <= 0.0:
			continue
		# (downhill: the way the floor falls)
		var fall := Vector3(Sea.ground(probe.x - 1.0, probe.z) - Sea.ground(probe.x + 1.0, probe.z), 0.0, Sea.ground(probe.x, probe.z - 1.0) - Sea.ground(probe.x, probe.z + 1.0))
		if fall.length() < 0.0001:
			fall = (at - probe) if probe != at else -ahead
		away += fall.normalized() * shallow
		most = maxf(most, shallow)
	var rock := Sea.clear_of_rocks(Vector3(at.x, Sea.SURFACE - 1.0, at.z), ROCK_ROOM)
	var off := Vector3(rock.x - at.x, 0.0, rock.z - at.z)
	if off.length() > 0.001:
		var into := clampf(off.length() / 1.5, 0.0, 1.5)
		away += off.normalized() * into
		most = maxf(most, into)
	var inside := Vector3(clampf(at.x, Sea.WEST + EDGE_ROOM, Sea.EAST - EDGE_ROOM) - at.x, 0.0, clampf(at.z, Sea.NORTH + EDGE_ROOM, Sea.SOUTH - EDGE_ROOM) - at.z)
	if inside.length() > 0.001:
		away += inside.normalized() * clampf(inside.length() / 3.0, 0.0, 1.5)
		most = maxf(most, clampf(inside.length() / 3.0, 0.0, 1.5))
	if most <= 0.0:
		return
	away = away.normalized()
	# (the way it has towards what it must keep off is taken off, all of it by the hard edge; then it is
	# pushed back out)
	var toward := -velocity.dot(away)
	if toward > 0.0:
		velocity += away * toward * (1.0 - exp(-4.0 * most * delta))
	velocity += away * PUSH_BACK * most * delta
	if most > 1.0:
		# (past the hard edge: never on the beach)
		position += away * (most - 1.0) * 2.0 * delta


## Where the camera stands at the helm (in the world): behind the boat and above it, at a fixed height
## over the sea's middle (no bob with the swell; higher over a rogue wave), the horizon level, swinging
## round after the boat's heading a little late so a turn is seen. `upright`: a narrow window.
func chase(delta: float, upright: bool) -> Transform3D:
	var k := 1 if upright else 0
	var yaw := global_rotation.y
	_chase_yaw = yaw if _chase_at == Vector3.INF else lerp_angle(_chase_yaw, yaw, 1.0 - exp(-CHASE_SWING * delta))
	var flat := Vector3(global_position.x, Sea.SURFACE, global_position.z)
	var back := Vector3(sin(_chase_yaw), 0.0, cos(_chase_yaw))
	var want := flat + back * CHASE_BACK[k] + Vector3.UP * CHASE_UP[k]
	# (over a rogue wave it rises, slowly: still never riding the swell)
	want.y = maxf(want.y, Sea.surface_height(want.x, want.z) + CHASE_UP[k] * 0.5)
	_chase_at = want if _chase_at == Vector3.INF else _chase_at.lerp(want, 1.0 - exp(-CHASE_FOLLOW * delta))
	var look := flat - back * CHASE_AHEAD[k] + Vector3.UP * 1.5
	return Transform3D(Basis.IDENTITY, _chase_at).looking_at(look, Vector3.UP)


## The middle of the net's hoop (in the world), where a fish swims in to be sold.
func hoop() -> Vector3:
	return net.global_position if net else global_transform * (NET_TIP - Vector3(0.0, NET_LINE, 0.0))


# Foam left on the water where the boat cuts it (at a marker on the waterline): white puffs that
# stay behind in the sea, spread and fade.
func _foam(at: String, amount: int, big: float, lasts: float, apart: float) -> void:
	var puff := StandardMaterial3D.new()
	puff.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	puff.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	puff.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	puff.vertex_color_use_as_albedo = true
	puff.albedo_color = Color(0.93, 0.97, 1.0, 0.5)
	var quad := QuadMesh.new()
	quad.size = Vector2(big, big * 0.5)
	quad.material = puff
	var foam := CPUParticles3D.new()
	foam.amount = amount
	foam.lifetime = lasts
	foam.local_coords = false
	foam.mesh = quad
	foam.direction = Vector3(0.0, 0.2, 1.0)
	foam.spread = 70.0
	foam.flatness = 0.9
	foam.initial_velocity_min = 0.2
	foam.initial_velocity_max = apart
	foam.gravity = Vector3.ZERO
	foam.damping_min = 0.6
	foam.damping_max = 1.2
	foam.scale_amount_min = 0.5
	foam.scale_amount_max = 1.4
	var fade := Gradient.new()
	fade.set_color(0, Color(1.0, 1.0, 1.0, 0.9))
	fade.set_color(1, Color(1.0, 1.0, 1.0, 0.0))
	foam.color_ramp = fade
	foam.position = (_spots[at] as Transform3D).origin + Vector3(0.0, 0.06, 0.0)
	# (on this node, not the rocking boat: the foam lies on the water)
	add_child(foam)
	_foams.append(foam)


# Takes a part out of a model, to put it somewhere else.
func _take(model: Node3D, named: String) -> Node3D:
	var part := model.find_child(named) as Node3D
	if part:
		part.get_parent().remove_child(part)
	return part


# Where a node of a model is, and how it is turned, in the space of something it is under.
func _place_in(node: Node3D, under: Node3D) -> Transform3D:
	var at := Transform3D.IDENTITY
	var each: Node = node
	while each != under and each is Node3D:
		at = (each as Node3D).transform * at
		each = each.get_parent()
	return at.orthonormalized()


# Carries the boat on round its circle.
func _steam(delta: float) -> void:
	_round -= SPEED / COURSE * delta
	var out := Vector3(cos(_round), 0.0, sin(_round))
	position = _middle + out * COURSE
	# (heading along the circle, the way it is going round: its -Z)
	var ahead := Vector3(sin(_round), 0.0, -cos(_round))
	basis = Basis.looking_at(ahead, Vector3.UP)


func _process(delta: float) -> void:
	_clock += delta
	if helm:
		# (its foam only while it makes way)
		var making := velocity.length() > 0.8
		for foam in _foams:
			if foam.emitting != making:
				foam.emitting = making
	elif not hove:
		_steam(delta)
	elif eye_node:
		# (hove-to, under way: the people and the computer only while they could be seen)
		var near := eye_node.global_position.y > Sea.SURFACE and eye_node.global_position.distance_to(global_position) < DETAIL_SEEN
		if _detail.size() > 0 and _detail[0].visible != near:
			for each in _detail:
				each.visible = near
	# The boat on the swell: it rides the water as it is drawn (Sea.surface_height: the swell, and a rogue
	# wave if one comes by), pitching to the water under its bow and stern and rolling to its sides,
	# eased as a heavy hull would, with a little roll of its own on top.
	var at := global_position
	var ahead := -global_basis.z
	var abeam := global_basis.x
	var middle := Sea.surface_height(at.x, at.z)
	var bow := Sea.surface_height(at.x + ahead.x * 3.0, at.z + ahead.z * 3.0)
	var stern := Sea.surface_height(at.x - ahead.x * 3.0, at.z - ahead.z * 3.0)
	var starboard := Sea.surface_height(at.x + abeam.x * 1.6, at.z + abeam.z * 1.6)
	var port := Sea.surface_height(at.x - abeam.x * 1.6, at.z - abeam.z * 1.6)
	var ease := 1.0 - exp(-2.5 * delta)
	var float_at := (middle + bow + stern) / 3.0 - at.y + sin(_clock * 0.7) * 0.03
	# (lifted quickly by water rising under it, settling slowly: a breaker's face passed up through the
	# hull at the slow rate)
	boat.position.y = lerpf(boat.position.y, float_at, (1.0 - exp(-7.0 * delta)) if float_at > boat.position.y else ease)
	# (at the helm: its bow lifts a little with speed, and it heels outward in a turn)
	var squat := SQUAT * clampf(velocity.length() / TOP_SPEED, 0.0, 1.5) if helm else 0.0
	boat.rotation.x = lerpf(boat.rotation.x, atan2(bow - stern, 6.0) + sin(_clock * 0.6 + 1.0) * 0.008 + squat, ease)
	boat.rotation.z = lerpf(boat.rotation.z, atan2(starboard - port, 3.2) + sin(_clock * 0.8) * 0.015 + _heel, ease)
	# The wheel goes with the captain's hands, the pump's crank with the diver's.
	if _figures:
		if _wheel and _captain:
			_wheel.rotation.z = -float(_figures.call(&"wheel_turn", _captain))
		if _pump and _diver:
			_pump.rotation.x = -float(_figures.call(&"crank_angle", _diver))
	# The cables, from the helmet's sockets to the top of the computer, hanging slack.
	var top: Transform3D = _spots["HelmetCable"]
	for k in _cables.size():
		var from := boat.to_local(_sockets[k].global_position)
		var to := top * Vector3((k - 0.5) * 0.5, -0.2, -0.25)
		var along := to - from
		var long := along.length()
		var side := along.cross(Vector3.UP).normalized() * long
		_cables[k].transform = Transform3D(Basis(along, Vector3.UP * long * 0.8, side * 0.7), from)


## Where the eye stands (in the world): riding off the boat's starboard beam and a little above,
## looking across the deck into the open cabin; further off in an upright window, where the
## picture is narrow.
func eye(upright: bool) -> Transform3D:
	var console: Vector3 = (_spots["ConsoleSpot"] as Transform3D).origin
	var from := global_transform * Vector3(19.0 if upright else 10.5, 4.6 if upright else 3.0, console.z + (0.0 if upright else 0.6))
	var at := global_transform * Vector3(0.0, 2.6 if upright else 1.9, console.z + (0.0 if upright else 0.3))
	var seen := Transform3D(Basis.IDENTITY, from).looking_at(at, Vector3.UP)
	if logo and logo.visible:
		logo.hold(seen, upright)
	return seen


## The card over the title: the game's name, and the button that starts it (or Enter, Space, a
## gamepad's A).
class Card:
	extends Control
	signal go
	## How much of what must be made ready before the game can start has been (0..1): the button
	## is dim, with a ring filling round it, until it is 1.
	var primed := 1.0
	# (kept here: a picture loaded inside _draw is let go before it is drawn, and draws white)
	var _logo: Texture2D = load("res://textures/title/logo.png")
	var _start: Texture2D = load("res://textures/title/start.png")

	func _ready() -> void:
		set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		mouse_filter = Control.MOUSE_FILTER_IGNORE

	func _process(_delta: float) -> void:
		queue_redraw()

	func _unit() -> float:
		return minf(size.x, size.y) / 720.0

	func _button() -> Vector2:
		return Vector2(size.x * 0.5, size.y - 110.0 * _unit())

	func _input(event: InputEvent) -> void:
		if not visible:
			return
		var touch := event as InputEventScreenTouch
		if touch and touch.pressed and touch.position.distance_to(_button()) < 95.0 * _unit():
			go.emit()
		elif event.is_action_pressed(&"ui_accept"):
			go.emit()

	func _draw() -> void:
		var u := _unit()
		# The name and the button are pictures (textures/title: made with an image generator after the
		# user asked, "the logo and start button needa concept art pass"; the originals are in
		# tools/art_src/concept_logo.jpg).
		# (the name itself is spelt in fish in the world: scripts/title_logo.gd; the picture logo,
		# textures/title/logo.png, is retired)
		# the start button: its lens is 0.355 of the picture's width from its left, half way down;
		# breathing; dim, with a ring filling round it, until the game is ready to start
		var start := _start
		var middle := _button()
		var r := (78.0 + 4.0 * sin(Time.get_ticks_msec() * 0.004)) * u
		var across := r * 2.0 / 0.7
		var tall := across * start.get_height() / start.get_width()
		var shade := Color.WHITE if primed >= 1.0 else Color(0.45, 0.45, 0.5)
		draw_texture_rect(start, Rect2(middle - Vector2(across * 0.355, tall * 0.5), Vector2(across, tall)), false, shade)
		if primed < 1.0:
			draw_arc(middle, r + 12.0 * u, -PI * 0.5, -PI * 0.5 + TAU * primed, 48, Color(0.95, 0.75, 0.3), 7.0 * u, true)
