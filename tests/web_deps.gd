extends SceneTree
## Checks the web export's exclude list (export_presets.cfg, written by tools/web_excludes.sh): no
## file the web build keeps depends on one it leaves out (a model whose pictures were left out
## would load without them, or not at all). Also lists what is largest among what is kept.
##   godot --headless --path . --audio-driver Dummy -s res://tests/web_deps.gd
## Prints `WEB DEPS PASS` or each broken dependency and `WEB DEPS FAIL`.

var _excludes: PackedStringArray = []


func _initialize() -> void:
	var cfg := ConfigFile.new()
	cfg.load("res://export_presets.cfg")
	_excludes = String(cfg.get_value("preset.0", "exclude_filter", "")).split(",", false)
	var files: PackedStringArray = []
	_walk("res://", files)
	var broken := 0
	var kept := 0
	for f in files:
		if _excluded(f):
			continue
		kept += 1
		for dep in ResourceLoader.get_dependencies(f):
			var path := dep.get_slice("::", 2) if "::" in dep else dep
			if path.begins_with("uid://"):
				var id := ResourceUID.text_to_id(path)
				path = ResourceUID.get_id_path(id) if ResourceUID.has_id(id) else path
			if _excluded(path):
				print("WEB DEPS kept %s needs left-out %s" % [f, path])
				broken += 1
	print("WEB DEPS %d files kept were checked; %d broken" % [kept, broken])
	print("WEB DEPS PASS" if broken == 0 else "WEB DEPS FAIL")
	quit()


func _walk(dir: String, out: PackedStringArray) -> void:
	for d in DirAccess.get_directories_at(dir):
		if d.begins_with(".") or d == "build" or d == "addons":
			continue
		if FileAccess.file_exists(dir.path_join(d).path_join(".gdignore")):
			continue
		_walk(dir.path_join(d), out)
	for f in DirAccess.get_files_at(dir):
		var ext := f.get_extension()
		if ext in ["glb", "tscn", "tres", "scn", "res", "material", "gltf"]:
			out.append(dir.path_join(f))


func _excluded(path: String) -> bool:
	var p := path.trim_prefix("res://")
	for pattern in _excludes:
		if p.match(pattern) or path.match(pattern) or ("res://" + pattern) == path:
			return true
	return false
