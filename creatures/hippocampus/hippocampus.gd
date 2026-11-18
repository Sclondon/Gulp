class_name Hippocampus
extends SeaMyth
## The sea-horse of old maps, 3.52 m from the tip of its muzzle to the back of its coiled tail: a
## horse's head, neck, chest and forelegs, the legs ending in hooves with webbed fins behind them, a
## finned crest along the neck and a mane of kelp, the body running back into a long scaled fish tail
## that curls down and under in a coil at its end, a spiny fin along its back all the way.
##
## Its forelegs paddle in a slow gallop (each swinging from the shoulder and folding at the knee, the
## left a little behind the right); its tail sculls from side to side; its mane streams and sways.
## `gape` opens its mouth (the lower jaw drops). `kelpie` gives it the kelpie's look: darker, with
## weed draped over its neck, back and tail (the same model: the weed is folded away otherwise).
##
## Its nose points along its own -Z, its back up; its origin is half way along its length, at the
## height of its body's middle line behind the chest. How it looks and swims only; no sound.
##
## The models are creatures/hippocampus/models/hippocampus.glb (and _lo, _game), built by
## tools/build_hippocampus.py; it wears the shared creatures/sea_myth/sea_myth.gdshader.

const MODEL := "res://creatures/hippocampus/models/hippocampus%s.glb"
## As built: from the tip of its muzzle to the back of its coil; from its hooves to the top of its
## mane, and the width of its chest (metres, at scale 1). Its ears and mane stand 1.13 m above its
## origin, its hooves and coil reach 1.07 below it.
const LENGTH := 3.52
const DEPTH := 2.2
const WIDTH := 0.41
const SETTINGS := {
	&"nose_z": -1.737, &"body_len": 3.52,
	&"wave_axis": 0.0, &"wave_from": 0.4, &"wave_amp": 0.18, &"wave_len": 1.0, &"recoil": 0.02,
	&"curl_from": 0.35,
	&"jaw_hinge": Vector2(0.7319, -1.4808), &"gape_max": 0.42,
	&"shoulder": Vector3(0.14, 0.1, -0.79), &"elbow": Vector3(0.17, -0.35, -0.89), &"elbow_w": 0.55,
	&"limb_beats": 1.0, &"limb_swing": 0.32, &"limb_bend": 0.7, &"limb_lag": 0.2, &"limb_off": 0.3,
	&"limb_rest": 0.0,
	&"strand_beats": 1.0, &"strand_amp": 0.09,
	&"fin_beats": 2.0, &"fin_amp": 0.025,
	&"scales": 1.0, &"scale_size": 0.07, &"scale_round": 16.0,
	&"spots": 0.0, &"rim": 0.08, &"rim_col": Color(0.6, 0.8, 0.75), &"mottle": 0.14, &"rough": 0.55,
	&"fin_rays": 3.0,
	&"kelpie": 0.0, &"kelpie_tint": Color(0.5, 0.56, 0.45),
}

## The kelpie's look: darker, with weed draped over it (for a river mouth).
@export var kelpie := false:
	set(value):
		kelpie = value
		_send(&"kelpie", 1.0 if value else 0.0)


## Its full model's mesh, or the low one's (one surface each, to wear `new_material()`).
static func mesh_of(low_wanted := false) -> Mesh:
	return SeaMyth.load_mesh(MODEL % ("_lo" if low_wanted else ""))


## Its game model's mesh (one surface, without the importer's automatic LODs).
static func game_mesh() -> Mesh:
	return SeaMyth.load_mesh(MODEL % "_game", true)


## A new material for its meshes (the shared shader with its settings); set `kelpie` 1.0 on it for
## the kelpie's look.
static func new_material() -> ShaderMaterial:
	return SeaMyth.material_with(SETTINGS)


func _init() -> void:
	super()
	beat = 2.0
	tail_beats = 1


func _ready() -> void:
	super()
	_send(&"kelpie", 1.0 if kelpie else 0.0)


func _model() -> String:
	return MODEL


func _settings() -> Dictionary:
	return SETTINGS


func _margin() -> float:
	return 0.3 * LENGTH
