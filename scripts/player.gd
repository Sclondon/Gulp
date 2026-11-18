class_name Player
extends Fish
## The player's fish. It always swims the way it points; `stick` turns it (x: round to the
## right, y: nose up) and `boost_held` is a burst of speed that uses up `stamina`. Main sets
## those two each frame, from the touch pad, the keys, a gamepad, or the bot.
##
## Eating (`feed`, called by Life) fills `progress`; when it is full the fish becomes something
## bigger. What it can become branches (`GROWTH`): where there is more than one way on it waits
## (`choosing`) until one is picked (`choose`: the Hud shows them). The last of a line only
## grows to its full length. `die` ends the run.
##
## Swum up fast through the surface it leaps clear of the water (`in_air`) and falls back in.

signal ate(at: Vector3)
signal grew(stage: int)
signal died(by: String)
## There is more than one thing it can become now: these.
signal choice(options: Array)
## It has left the water, or come back into it.
signal leapt(at: Vector3)
signal splashed(at: Vector3)

## What each kind is as the player: how long from when it becomes that until it grows out of
## it, and what it can become then (those whose creatures are installed are offered).
const GROWTH := {
	"sardine": {"from": 0.18, "to": 0.34, "next": ["mackerel", "smolt", "surfperch", "flying"]},
	"flying": {"from": 0.36, "to": 0.55, "next": ["bonito", "mahi", "salmon"]},
	"mackerel": {"from": 0.36, "to": 0.6, "next": ["bonito", "barracuda"]},
	"smolt": {"from": 0.36, "to": 0.68, "next": ["salmon"]},
	"surfperch": {"from": 0.36, "to": 0.5, "next": ["kelp_bass", "rockfish"]},
	"bonito": {"from": 0.62, "to": 1.0, "next": ["tuna", "mahi"]},
	"barracuda": {"from": 0.62, "to": 1.3, "next": ["wahoo", "leopard_shark"]},
	"salmon": {"from": 0.72, "to": 1.35, "next": ["tuna", "leopard_shark"]},
	"kelp_bass": {"from": 0.52, "to": 0.95, "next": ["grouper", "leopard_shark"]},
	"rockfish": {"from": 0.52, "to": 0.9, "next": ["grouper", "snapper"]},
	"snapper": {"from": 0.92, "to": 1.3, "next": ["leopard_shark", "sea_bass"]},
	"tuna": {"from": 1.45, "to": 2.1, "next": ["bluefin", "sailfish"]},
	"mahi": {"from": 1.05, "to": 1.7, "next": ["sailfish", "blue_shark"]},
	"wahoo": {"from": 1.4, "to": 2.1, "next": ["swordfish", "blue_shark"]},
	"leopard_shark": {"from": 1.05, "to": 1.8, "next": ["blue_shark", "sea_bass"]},
	"grouper": {"from": 0.98, "to": 1.6, "next": ["sea_bass", "blue_shark"]},
	"sea_bass": {"from": 1.7, "to": 2.6, "next": ["white_shark"]},
	"bluefin": {"from": 2.2, "to": 3.0, "next": ["white_shark", "marlin"]},
	"sailfish": {"from": 2.2, "to": 3.0, "next": ["marlin", "swordfish"]},
	"blue_shark": {"from": 1.9, "to": 3.2, "next": ["white_shark"]},
	"swordfish": {"from": 3.1, "to": 4.4, "next": ["orca"]},
	"marlin": {"from": 3.1, "to": 4.4, "next": ["orca"]},
	"white_shark": {"from": 3.3, "to": 5.6, "next": ["orca"]},
	"orca": {"from": 5.8, "to": 8.0, "next": []},
	# (the code-built shark, where no better one is installed)
	"shark": {"from": 2.9, "to": 6.0, "next": []},
}
## What a kind becomes when none of its own are installed.
const ELSE := {"sardine": "smolt", "smolt": "salmon", "salmon": "tuna", "tuna": "shark", "bluefin": "shark", "sailfish": "shark"}
## How much of a stage a meal its own length would fill (a meal of a fifth its length fills a
## good deal less: see `feed`).
const MEAL := 0.5
## A burst: how much faster, how long a full `stamina` lasts (s), how long it takes to fill (s).
const BOOST := 1.8
const BOOST_LASTS := 2.2
const BOOST_FILLS := 5.0
## How fast dead slow is, as a share of its cruising pace (full ahead is 1.15 of it).
const SLOWEST := 0.3
## A leap: how fast it must be going up through the surface (as a share of its cruising pace),
## how much the water lets go of it, and how it falls.
## (0.9 was more than its cruising speed at the speed lever's starting place (0.3 + 0.85 x 0.7 =
## 0.895 of its pace): without the burst it only ever stuck under the surface. tools/WATER_FX.md)
const LEAP_PACE := 0.75
const LEAP_KICK := 1.35
const GRAVITY := 9.0
## How high a leap takes it at least (metres above where it left the water): `LEAP_LEAST` and
## `LEAP_PER_LENGTH` of its length, on a burst; three quarters of that without. (Thrown out only
## by its own speed, big fish, being slow for their size, never got clear of the water: an orca
## rose 1.6 m, under a third of its length.)
const LEAP_LEAST := 0.25
const LEAP_PER_LENGTH := 0.9

## How deep it may go (m under the surface: the amplifier's reach, set by Main; INF: anywhere).
## Below it, it is turned back upwards, and it is never let more than LIMIT_GIVE metres deeper.
var deepest := INF
const LIMIT_GIVE := 3.0

## How many times it has become something bigger this run.
var stage := 0
## How far through its stage it has eaten its way (0..1).
var progress := 0.0
var alive := false
var stamina := 1.0
var boosting := false
## Seconds for which nothing can eat it (at the start of a run, and just after it grows).
var safe := 0.0
var meals := 0
## Waiting for a choice of what to become (the sea stands still meanwhile).
var choosing := false
## Out of the water, in the middle of a leap.
var in_air := false
## On a hook or in a net (Fishers holds it where it is; it can only struggle).
var caught := false

var stick := Vector2.ZERO
var boost_held := false
## How fast it is asked to swim: 0 dead slow to 1 full ahead (the speed lever).
var throttle := 1.0

var yaw := 0.0
var pitch := 0.0
var _speed := 0.0


## Starts a run: at a place, as a kind (the smallest unless told).
func begin(at: Vector3, as_kind := "sardine") -> void:
	if not GROWTH.has(as_kind):
		as_kind = "sardine"
	stage = 0
	progress = 0.0
	meals = 0
	stamina = 1.0
	safe = 3.0
	alive = true
	choosing = false
	in_air = false
	caught = false
	visible = true
	global_position = at
	# (looking out to sea)
	yaw = -PI * 0.5
	pitch = 0.0
	heading = _way()
	set_kind(as_kind)
	_grow()
	_speed = Fish.pace(length)


## What it can become when this stage is full (none: it is the last of its line).
func options() -> Array:
	var found := []
	for each: String in GROWTH[kind].next:
		if Species.has(each):
			found.append(each)
	if found.is_empty() and ELSE.has(kind):
		found.append(ELSE[kind])
	return found


## Whether it is at the end of its line and its full length.
func is_biggest() -> bool:
	return options().is_empty() and progress >= 1.0


## It has eaten something `prey_length` metres long (`rich`: how much food it is for its size).
func feed(prey_length: float, rich := 1.0) -> void:
	meals += 1
	progress += MEAL * rich * pow(prey_length / length, 1.5)
	ate.emit(mouth())
	_snap = 0.25
	progress = minf(progress, 1.0)
	_grow()
	if progress >= 1.0 and not choosing:
		var ways := options()
		if ways.size() == 1:
			choose(ways[0])
		elif ways.size() > 1:
			choosing = true
			safe = maxf(safe, 1.0)
			choice.emit(ways)


## Becomes one of the things it can become.
func choose(what: String) -> void:
	choosing = false
	stage += 1
	progress = 0.0
	set_kind(what)
	flash()
	safe = maxf(safe, 2.5)
	_grow()
	grew.emit(stage)


## Hauled up in the boat's net: the run ends as a sale (not a death: `died` is not sent).
func haul() -> void:
	alive = false
	visible = false
	choosing = false


## Something has eaten it (or stung it).
func die(by: String) -> void:
	if not alive or safe > 0.0:
		return
	alive = false
	visible = false
	choosing = false
	died.emit(by)


func step(delta: float) -> void:
	if not alive:
		return
	safe = maxf(safe - delta, 0.0)
	_snap = maxf(_snap - delta, 0.0)
	# Small fish turn quicker than big ones.
	var nimble := clampf(pow(length, -0.2), 0.6, 1.4)
	var room := maxf(length * 0.3, 0.12)
	if in_air:
		# A leap: it falls as anything does, turning nose down as it goes; the stick only
		# swings it a little.
		yaw -= stick.x * 0.8 * delta
		velocity = velocity.rotated(Vector3.UP, -stick.x * 0.8 * delta)
		velocity.y -= GRAVITY * delta
		heading = velocity.normalized()
		var next := global_position + velocity * delta
		var held := Sea.keep_in(Vector3(next.x, Sea.SURFACE - 1.0, next.z), room)
		global_position = Vector3(held.x, next.y, held.z)
		if global_position.y < Sea.SURFACE - room * 0.5 and velocity.y < 0.0:
			in_air = false
			pitch = asin(clampf(heading.y, -1.0, 1.0))
			yaw = atan2(-heading.x, -heading.z)
			_speed = velocity.length() * 0.75
			_landed = 0.9
			splashed.emit(Vector3(global_position.x, Sea.SURFACE, global_position.z))
		pose(delta, 0.4, stick.x)
		# (still blinking if it is: it was left hidden for the whole leap when it went up hidden)
		_body.visible = safe <= 0.0 or fmod(safe, 0.3) > 0.1
		return
	yaw -= stick.x * 2.3 * nimble * delta
	pitch = clampf(pitch + stick.y * 1.7 * nimble * delta, -1.15, 1.15)
	if _landed > 0.0:
		# (back in from a leap it comes out of its dive by itself, unless steered: it went
		# straight on down to the floor)
		_landed -= delta
		if absf(stick.y) < 0.3 and pitch < -0.3:
			pitch = move_toward(pitch, -0.3, 1.6 * delta)
	if Sea.SURFACE - global_position.y > deepest:
		# Below where the machine's signal reaches (DESIGN.md: the amplifier): it is turned back
		# up, whatever the stick says (and held no more than LIMIT_GIVE under that depth).
		pitch = move_toward(pitch, 0.7, 2.6 * delta)
	heading = _way()
	boosting = boost_held and stamina > 0.0
	if boosting:
		stamina = maxf(stamina - delta / BOOST_LASTS, 0.0)
	elif not boost_held:
		stamina = minf(stamina + delta / BOOST_FILLS, 1.0)
	var want := Fish.pace(length) * lerpf(SLOWEST, 1.15, throttle) * (BOOST if boosting else 1.0)
	_speed = lerpf(_speed, want, 1.0 - exp(-4.0 * delta))
	velocity = heading * _speed
	if caught:
		# (Fishers: on a hook or in a net it stays where it is held, and only struggles)
		pose(delta, 2.0 if boosting else 1.0, stick.x)
		return
	var next := global_position + velocity * delta
	if next.y > Sea.SURFACE - room and heading.y > 0.2 and _speed > Fish.pace(length) * LEAP_PACE:
		# Up through the surface, fast enough: out it comes.
		in_air = true
		velocity *= LEAP_KICK
		# (at least high enough to be seen clear of the water, in proportion to its length)
		var least := sqrt(2.0 * GRAVITY * (LEAP_LEAST + length * LEAP_PER_LENGTH)) * (1.0 if boosting else 0.75)
		velocity.y = maxf(velocity.y, least)
		global_position = next
		leapt.emit(Vector3(next.x, Sea.SURFACE, next.z))
	else:
		global_position = Sea.clear_of_rocks(Sea.keep_in(next, room), room)
		global_position.y = maxf(global_position.y, Sea.SURFACE - deepest - LIMIT_GIVE)
		# (held under the surface, it levels off along it)
		if next.y > Sea.SURFACE - room and pitch > 0.0:
			pitch = maxf(pitch - 2.0 * delta, 0.0)
	bite = 1.0 if _snap > 0.0 or near_food else 0.0
	pose(delta, 2.0 if boosting else lerpf(0.3, 1.0, throttle), stick.x)
	# (it blinks while nothing can eat it)
	_body.visible = safe <= 0.0 or fmod(safe, 0.3) > 0.1


## Something it can eat is right ahead of its mouth (Life says): it opens wide.
var near_food := false
var _snap := 0.0
# Seconds since it came back in from a leap (counting down from 0.9).
var _landed := 0.0


func _way() -> Vector3:
	return Vector3(-sin(yaw) * cos(pitch), sin(pitch), -cos(yaw) * cos(pitch))


func _grow() -> void:
	length = lerpf(GROWTH[kind].from, GROWTH[kind].to, progress)
