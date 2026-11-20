extends SceneTree
## Writes the phone tier's smaller copies of the set pieces' big atlases into textures/phone/ (the same
## name, at most PHONE_SIZE a side), which `Tier.texture()` hands a phone in place of the full ones
## (tools/PERF.md, "Memory on phones"). Run it again after rebuilding any of them, then `--import`:
##   godot --headless --path . --audio-driver Dummy -s res://tools/phone_textures.gd
## New copies are imported lossy with mipmaps, as their full ones are (their .import files are kept
## in the repo; a copy made for the first time needs its .import set so, by hand or as the others).

const SOURCES := [
	"res://textures/wreck_atlas_bow.png",
	"res://textures/wreck_atlas_stern.png",
	"res://textures/pirate_atlas.png",
	"res://textures/ruins_canyon_atlas.png",
]
const PHONE_SIZE := 1024


func _initialize() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://textures/phone"))
	for path: String in SOURCES:
		var image := Image.load_from_file(ProjectSettings.globalize_path(path))
		if image == null or image.is_empty():
			printerr("PHONE could not read ", path)
			continue
		var was := image.get_size()
		var scale := float(PHONE_SIZE) / float(maxi(was.x, was.y))
		if scale < 1.0:
			image.resize(maxi(1, roundi(was.x * scale)), maxi(1, roundi(was.y * scale)), Image.INTERPOLATE_LANCZOS)
		var out := "res://textures/phone/" + path.get_file()
		image.save_png(ProjectSettings.globalize_path(out))
		print("PHONE %s %s -> %s" % [out, was, image.get_size()])
	quit()
