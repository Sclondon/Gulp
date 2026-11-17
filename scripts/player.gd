class_name Player
extends Fish
## The player's fish. It always swims the way it points; `stick` turns it (x: round to the
## right, y: nose up) and `boost_held` is a burst of speed that uses up `stamina`. Main sets
## those two each frame, from the touch pad, the keys, a gamepad, or the bot.
##
## Eating (`feed`, called by Life) fills `progress`; when it is full the fish becomes the next
## in `STAGES`, bigger. The last stage only grows to its full length. `die` ends the run.

signal ate(at: Vector3)
signal grew(stage: int)
signal died(by: String)

## What it is at each stage, and how long from when it becomes that until it becomes the next.
const STAGES := [
	{"kind": "sardine", "from": 0.18, "to": 0.34},
	{"kind": "smolt", "from": 0.36, "to": 0.68},
	{"kind": "salmon", "from": 0.72, "to": 1.35},
	{"kind": "tuna", "from": 1.45, "to": 2.7},
	{"kind": "shark", "from": 2.9, "to": 6.0},
]
## How much of a stage a meal its own length would fill (a meal of a fifth its length fills a
## good deal less: see `feed`).
const MEAL := 0.5
## A burst: how much faster, how long a full `stamina` lasts (s), how long it takes to fill (s).
const BOOST := 1.8
const BOOST_LASTS := 2.2
const BOOST_FILLS := 5.0

var stage := 0
## How far through its stage it has eaten its way (0..1).
var progress := 0.0
var alive := false
var stamina := 1.0
var boosting := false
## Seconds for which nothing can eat it (at the start of a run, and just after it grows).
var safe := 0.0
var meals := 0

var stick := Vector2.ZERO
var boost_held := false

var yaw := 0.0
var pitch := 0.0
var _speed := 0.0


## Starts a run: at a place, as the fish of a stage.
func begin(at: Vector3, from_stage := 0) -> void:
	stage = clampi(from_stage, 0, STAGES.size() - 1)
	progress = 0.0
	meals = 0
	stamina = 1.0
	safe = 3.0
	alive = true
	visible = true
	global_position = at
	# (looking in towards the middle of the sea)
	yaw = atan2(at.x, at.z) if Vector2(at.x, at.z).length() > 1.0 else 0.0
	pitch = 0.0
	heading = _way()
	set_kind(STAGES[stage].kind)
	_grow()
	_speed = Fish.pace(length)


## Whether it is at its last stage and its full length.
func is_biggest() -> bool:
	return stage == STAGES.size() - 1 and progress >= 1.0


## It has eaten something `prey_length` metres long (`rich`: how much food it is for its size).
func feed(prey_length: float, rich := 1.0) -> void:
	meals += 1
	progress += MEAL * rich * pow(prey_length / length, 1.5)
	ate.emit(mouth())
	if progress >= 1.0 and stage < STAGES.size() - 1:
		stage += 1
		progress = 0.0
		set_kind(STAGES[stage].kind)
		flash()
		safe = maxf(safe, 2.0)
		grew.emit(stage)
	progress = minf(progress, 1.0)
	_grow()


## Something has eaten it (or stung it).
func die(by: String) -> void:
	if not alive or safe > 0.0:
		return
	alive = false
	visible = false
	died.emit(by)


func step(delta: float) -> void:
	if not alive:
		return
	safe = maxf(safe - delta, 0.0)
	# Small fish turn quicker than big ones.
	var nimble := clampf(pow(length, -0.2), 0.6, 1.4)
	yaw -= stick.x * 2.3 * nimble * delta
	pitch = clampf(pitch + stick.y * 1.7 * nimble * delta, -1.15, 1.15)
	heading = _way()
	boosting = boost_held and stamina > 0.0
	if boosting:
		stamina = maxf(stamina - delta / BOOST_LASTS, 0.0)
	elif not boost_held:
		stamina = minf(stamina + delta / BOOST_FILLS, 1.0)
	var want := Fish.pace(length) * 1.15 * (BOOST if boosting else 1.0)
	_speed = lerpf(_speed, want, 1.0 - exp(-4.0 * delta))
	velocity = heading * _speed
	var room := maxf(length * 0.3, 0.12)
	global_position = Sea.clear_of_rocks(Sea.keep_in(global_position + velocity * delta, room), room)
	pose(delta, 2.0 if boosting else 1.0, stick.x)
	# (it blinks while nothing can eat it)
	_body.visible = safe <= 0.0 or fmod(safe, 0.3) > 0.1


func _way() -> Vector3:
	return Vector3(-sin(yaw) * cos(pitch), sin(pitch), -cos(yaw) * cos(pitch))


func _grow() -> void:
	length = lerpf(STAGES[stage].from, STAGES[stage].to, progress)
