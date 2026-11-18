class_name Mermaid
extends SeaMyth
## A mermaid of sailors' tales, 1.89 m from the front of her head to the tips of her fluke: a wild
## sea-woman, not a pretty one. A long scaled tail with a broad flat fluke; pale grey-green skin;
## webbed hands of four long fingers, fins along the backs of her forearms and at her hips; fin
## ears; long hair of weed-tangled locks; a necklace of shells and a wrap of weed and shells across
## her chest. Her face is a smooth blank mask (brow, nose, chin, shallow sockets; no eyes, no mouth).
##
## She swims flat out as a dolphin does, her tail beating UP AND DOWN, her arms sweeping back along
## her sides once a beat and her hair streaming and swaying behind her. Her nose (the front of her
## head) points along her own -Z, her back up; her origin is on her middle line half way along.
## `gape` does nothing on her (she has no mouth). How she looks and swims only; no sound.
##
## The models are creatures/mermaid/models/mermaid.glb (and _lo, _game), built by
## tools/build_mermaid.py; she wears the shared creatures/sea_myth/sea_myth.gdshader.

const MODEL := "res://creatures/mermaid/models/mermaid%s.glb"
## As built: from the front of her head to her fluke tips, her body's depth at the chest and her
## width at the shoulders (metres, at scale 1). Her arms reach 0.36 m out to each side, her fluke
## 0.32; her hair 0.35.
const LENGTH := 1.89
const DEPTH := 0.2
const WIDTH := 0.39
## The shader numbers that make her herself (sea_myth.gdshader lists what each is).
const SETTINGS := {
	&"nose_z": -0.947, &"body_len": 1.887,
	&"wave_axis": 1.0, &"wave_from": 0.4, &"wave_amp": 0.09, &"wave_len": 1.0, &"recoil": 0.0,
	&"curl_from": 0.35,
	&"shoulder": Vector3(0.18, 0.0, -0.63), &"elbow": Vector3(0.27, -0.085, -0.43), &"elbow_w": 0.5,
	&"limb_beats": 1.0, &"limb_swing": 0.22, &"limb_bend": -0.3, &"limb_lag": 0.15, &"limb_off": 0.0,
	&"limb_rest": -0.1,
	&"strand_beats": 1.0, &"strand_amp": 0.07,
	&"fin_beats": 2.0, &"fin_amp": 0.012,
	&"scales": 1.0, &"scale_size": 0.055, &"scale_round": 14.0,
	&"spots": 0.0, &"rim": 0.12, &"rim_col": Color(0.7, 0.85, 0.82), &"mottle": 0.12, &"rough": 0.6,
	&"fin_rays": 10.0,
}


## Her full model's mesh, or the low one's (one surface each, to wear `new_material()`).
static func mesh_of(low_wanted := false) -> Mesh:
	return SeaMyth.load_mesh(MODEL % ("_lo" if low_wanted else ""))


## Her game model's mesh (one surface, without the importer's automatic LODs).
static func game_mesh() -> Mesh:
	return SeaMyth.load_mesh(MODEL % "_game", true)


## A new material for her meshes (the shared shader with her settings); `phase`, `sway`, `curl`,
## `arch` and the rest are the game's to set.
static func new_material() -> ShaderMaterial:
	return SeaMyth.material_with(SETTINGS)


func _model() -> String:
	return MODEL


func _settings() -> Dictionary:
	return SETTINGS


func _margin() -> float:
	return 0.35 * LENGTH
