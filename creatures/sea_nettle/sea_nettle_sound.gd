class_name SeaNettleSound
## The sea nettle's sounds, made in code (nothing to load), each made once:
##
## - `pulse()`: one beat of its bell, soft and wet: a low hollow push of air
##   and a faint squelch as the jelly draws in and lets go.
## - `sting()`: its tentacles firing, a dry crackle like static, with a sharp
##   snap at the front.

const RATE := 22050

static var _made := {}


static func pulse() -> AudioStreamWAV:
	return _make("pulse", 0.9, func(t: float, rng: RandomNumberGenerator, s: Dictionary) -> float:
		var push := smoothstep(0.0, 0.12, t) * exp(-t * 5.0)
		var hollow := sin(t * TAU * (70.0 + 30.0 * exp(-t * 6.0))) * push
		var wet := (_low(s, "a", rng.randf_range(-1.0, 1.0), 0.25) - _low(s, "b", rng.randf_range(-1.0, 1.0), 0.03)) * push
		return hollow * 1.2 + wet * 0.8)


static func sting() -> AudioStreamWAV:
	return _make("sting", 0.7, func(t: float, rng: RandomNumberGenerator, s: Dictionary) -> float:
		var snap := exp(-t * 60.0) * rng.randf_range(-1.0, 1.0)
		var crackle := 0.0
		if rng.randf() < 0.03 * exp(-t * 4.0):
			s["click"] = 1.0
		s["click"] = maxf(float(s.get("click", 0.0)) - 1.0 / (0.002 * RATE), 0.0)
		crackle = rng.randf_range(-1.0, 1.0) * float(s["click"])
		var fizz := (rng.randf_range(-1.0, 1.0) - _low(s, "a", rng.randf_range(-1.0, 1.0), 0.5)) * exp(-t * 7.0) * 0.3
		return snap * 1.5 + crackle * 1.2 + fizz)


## A one-pole low-pass filter kept in `state` under `key`.
static func _low(state: Dictionary, key: String, value: float, amount: float) -> float:
	var was: float = state.get(key, 0.0)
	var now := lerpf(was, value, amount)
	state[key] = now
	return now


static func _make(key: String, length: float, sample: Callable) -> AudioStreamWAV:
	if _made.has(key):
		return _made[key]
	var count := int(RATE * length)
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(key)
	var state := {}
	var values := PackedFloat32Array()
	values.resize(count)
	var loudest := 0.0
	for i in count:
		var v := tanh(float(sample.call(float(i) / RATE, rng, state)) * 1.5)
		values[i] = v
		loudest = maxf(loudest, absf(v))
	var data := PackedByteArray()
	data.resize(count * 2)
	for i in count:
		var v := values[i] / maxf(loudest, 0.001) * smoothstep(0.0, 0.02, float(count - i) / RATE)
		data.encode_s16(i * 2, int(clampf(v, -1.0, 1.0) * 26000.0))
	var made := AudioStreamWAV.new()
	made.format = AudioStreamWAV.FORMAT_16_BITS
	made.mix_rate = RATE
	made.data = data
	_made[key] = made
	return made
