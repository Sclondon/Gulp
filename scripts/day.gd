class_name Day
extends RefCounted
## The time of day (tools/WATER_FX.md). A whole day goes by in `LENGTH` seconds of play, starting
## mid-morning; Sea reads it to light the water, the sky, the light shafts and the caustics.
## The user (2026-11-18): "Ther should be a day and night cycle (dont make night too dark)".
##
## `--hour=<0..24>` (after --) holds the clock at that hour, for pictures and tests.
## Everything here is static: there is one day for the whole game. Sea moves it on (`advance`).

## Seconds of play in a whole day (nine minutes).
const LENGTH := 540.0
## The hour a game starts at.
const START := 9.5
## Sunrise and sunset (hours). The light comes up and goes down over `TWILIGHT` hours round each.
const RISE := 6.0
const SET := 19.0
const TWILIGHT := 1.2

static var _now := START / 24.0
static var _held := false
static var _read_args := false


## Moves the clock on (Sea calls this once a frame).
static func advance(delta: float) -> void:
	_args()
	if not _held:
		_now = fmod(_now + delta / LENGTH, 1.0)


## How far through the day it is: 0 midnight, 0.5 noon.
static func now() -> float:
	_args()
	return _now


## The hour, 0 to 24 (for the panel's clock, if it ever has one).
static func hour() -> float:
	return now() * 24.0


## Holds the clock at an hour (or lets it run again with a negative one).
static func hold(at_hour: float) -> void:
	_read_args = true
	if at_hour < 0.0:
		_held = false
		return
	_held = true
	_now = fmod(at_hour, 24.0) / 24.0


## How much daylight there is: 1 from mid-morning to mid-afternoon, 0 at night, easing
## through dawn and dusk.
static func light() -> float:
	var h := hour()
	var up := smoothstep(RISE - TWILIGHT * 0.5, RISE + TWILIGHT * 1.5, h)
	var down := 1.0 - smoothstep(SET - TWILIGHT * 1.5, SET + TWILIGHT * 0.5, h)
	return clampf(minf(up, down), 0.0, 1.0)


## How much of the low, warm light of dawn or dusk there is (0..1): most as the sun is on the
## horizon.
static func glow() -> float:
	var h := hour()
	var dawn := 1.0 - smoothstep(0.0, TWILIGHT * 1.3, absf(h - RISE - 0.2))
	var dusk := 1.0 - smoothstep(0.0, TWILIGHT * 1.3, absf(h - SET + 0.2))
	return maxf(dawn, dusk)


## How high the sun is (radians above the horizon; below it at night).
static func sun_height() -> float:
	var h := hour()
	if h >= RISE and h <= SET:
		# (an arch through the day, its top at noon, about 62 degrees up)
		return deg_to_rad(62.0) * sin(PI * (h - RISE) / (SET - RISE))
	return -deg_to_rad(40.0) * sin(PI * fmod(h - SET + 24.0, 24.0) / (24.0 - (SET - RISE)))


## The way to the light that is up (a unit vector from the sea up to it): the sun by day, the
## moon by night. It never drops lower than about 20 degrees, so the water is never lit side-on.
static func sun_direction() -> Vector3:
	var h := hour()
	var day := h >= RISE and h <= SET
	var height := sun_height()
	var across: float
	if day:
		# (from the east, over the south, to the west: east is +x, out to sea)
		across = remap(h, RISE, SET, 0.0, PI)
	else:
		# (the moon: across the other way through the night)
		var into := fmod(h - SET + 24.0, 24.0) / (24.0 - (SET - RISE))
		across = into * PI
		height = deg_to_rad(55.0) * sin(into * PI)
	height = maxf(absf(height), deg_to_rad(20.0))
	var flat := Vector3(cos(across), 0.0, sin(across) * 0.6 + 0.4).normalized()
	return (flat * cos(height) + Vector3.UP * sin(height)).normalized()


## The colour of the light from above (the sun's, or the moon's at night): white-blue at midday,
## warm at dawn and dusk, pale blue by moonlight.
static func light_colour() -> Color:
	var noon := Color(0.62, 0.82, 1.0)
	var low := Color(1.0, 0.66, 0.42)
	var moon := Color(0.5, 0.62, 0.95)
	var c := moon.lerp(noon, light())
	return c.lerp(low, glow() * 0.75)


## The colour of the sky over the water.
static func sky_colour() -> Color:
	var noon := Color(0.55, 0.75, 0.95)
	var low := Color(1.0, 0.56, 0.32)
	var night := Color(0.1, 0.15, 0.3)
	return night.lerp(noon, light()).lerp(low, glow() * 0.6)


static func _args() -> void:
	if _read_args:
		return
	_read_args = true
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--hour="):
			hold(float(arg.get_slice("=", 1)))
