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
## the boy steers.
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
		# (its plank lines and grime are vertex colours)
		for mesh: MeshInstance3D in hull.find_children("*", "MeshInstance3D", true, false):
			for surface in mesh.mesh.get_surface_count():
				var paint := mesh.mesh.surface_get_material(surface) as StandardMaterial3D
				if paint:
					paint.vertex_color_use_as_albedo = true
		for named: String in SPOTS:
			var marker := hull.find_child(named) as Node3D
			if marker:
				_spots[named] = _place_in(marker, boat)
		_wheel = hull.find_child("Wheel") as Node3D
		_pump = hull.find_child("PumpWheel") as Node3D
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
	logo = TitleLogo.new()
	add_child(logo)
	_foam("BowWave", 40, 0.4, 1.6, 1.4)
	_foam("Wake", 50, 0.55, 2.4, 0.7)


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
	_steam(delta)
	# The boat on the swell (seen broadside: it rolls towards and away, and pitches a little).
	boat.rotation.z = sin(_clock * 0.8) * 0.03
	boat.rotation.x = sin(_clock * 0.6 + 1.0) * 0.018
	boat.position.y = sin(_clock * 0.7) * 0.06
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
