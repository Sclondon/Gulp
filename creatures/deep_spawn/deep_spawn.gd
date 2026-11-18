class_name DeepSpawn
extends SeaMyth
## The old one's fish-spawn, 1.59 m from the tips of its tentacles to the tips of its tail fin: a
## pale bloated fish, lumpy, with a cluster of six small dark eyes over a round mouth ringed with
## pink tentacles, the mouth a dark funnel; long ragged fins and trailing torn membranes; rows of
## blue-white lights along its flanks. Of our own design (no creature of any story copied).
##
## It swims as a fish does, its tail beating from side to side; its tentacles writhe and its fins
## ripple. `gape` spreads its tentacles wide from its mouth (as it bites). `glow` sets how bright its
## lights are (0 dark, 1 as built, 2 bright). Many can share one material: they are made to hunt in
## groups.
##
## Its nose points along its own -Z, its back up; its origin is half way along its length, on its
## middle line. How it looks and swims only; no sound.
##
## The models are creatures/deep_spawn/models/deep_spawn.glb (and _lo, _game), built by
## tools/build_deep_spawn.py; it wears the shared creatures/sea_myth/sea_myth.gdshader.

const MODEL := "res://creatures/deep_spawn/models/deep_spawn%s.glb"
## As built: from the tips of its tentacles to its tail fin; its body's depth and width at the
## deepest (metres, at scale 1). Its lips are 0.18 m behind the front; its fins reach 0.36 m to each
## side and 0.43 below its middle line.
const LENGTH := 1.59
const DEPTH := 0.53
const WIDTH := 0.45
const SETTINGS := {
	&"nose_z": -0.794, &"body_len": 1.587,
	&"wave_axis": 0.0, &"wave_from": 0.3, &"wave_amp": 0.1, &"wave_len": 1.0, &"recoil": 0.015,
	&"curl_from": 0.3,
	&"mouth_xy": Vector2(0.0, -0.015), &"tent_amp": 0.04, &"tent_spread": 0.1,
	&"strand_beats": 1.0, &"strand_amp": 0.05,
	&"fin_beats": 2.0, &"fin_amp": 0.03,
	&"scales": 0.0, &"spots": 1.6, &"spot_size": 0.06, &"spot_round": 11.0,
	&"glow_col": Color(0.55, 0.88, 1.0),
	&"rim": 0.22, &"rim_col": Color(0.75, 0.85, 0.95), &"mottle": 0.1, &"rough": 0.45, &"fin_rays": 7.0,
}

## How bright its lights are: 0 dark, 1 as built, 2 bright.
@export_range(0.0, 2.0) var glow := 1.0:
	set(value):
		glow = clampf(value, 0.0, 2.0)
		_send(&"spots", 1.6 * glow)


## Its full model's mesh, or the low one's (one surface each, to wear `new_material()`).
static func mesh_of(low_wanted := false) -> Mesh:
	return SeaMyth.load_mesh(MODEL % ("_lo" if low_wanted else ""))


## Its game model's mesh (one surface, without the importer's automatic LODs).
static func game_mesh() -> Mesh:
	return SeaMyth.load_mesh(MODEL % "_game", true)


## A new material for its meshes (the shared shader with its settings).
static func new_material() -> ShaderMaterial:
	return SeaMyth.material_with(SETTINGS)


func _init() -> void:
	super()
	beat = 1.8


func _model() -> String:
	return MODEL


func _settings() -> Dictionary:
	return SETTINGS


func _margin() -> float:
	return 0.3 * LENGTH
