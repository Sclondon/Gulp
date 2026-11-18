extends SceneTree
## Shows the loading screen by itself and saves pictures of it filling:
##   godot --path . --audio-driver Dummy --resolution 1280x720 -s tests/loading_view.gd -- --out=<folder>
## It loads over 4 s, holds a second, scatters, and quits.

var _swarm: LoadingSwarm
var _clock := 0.0
var _out := ""
var _taken := {}


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):
			_out = arg.get_slice("=", 1)
	_swarm = LoadingSwarm.new()
	root.add_child(_swarm)


func _process(delta: float) -> bool:
	_clock += delta
	if is_instance_valid(_swarm):
		_swarm.progress = clampf(_clock / 4.0, 0.0, 1.0)
	for at: float in [0.3, 2.0, 5.2, 5.7]:
		if _clock >= at and not _taken.has(at) and _out != "":
			_taken[at] = true
			root.get_texture().get_image().save_png("%s/loading_%.1f.png" % [_out, at])
	if _clock > 5.3 and is_instance_valid(_swarm):
		_swarm.finish()
	return _clock > 6.5
