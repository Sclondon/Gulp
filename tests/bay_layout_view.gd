extends SceneTree
## A picture of the bay editor's scene (editor/bay_layout.tscn) as it draws, without the editor: from
## high over the bay looking down at a slant, and straight down. Needs the floor's picture made once by
## the editor (or by addons/bay_layout/floor_dump.gd -- --out=<project>/.godot/editor/bay_layout_floor.bin).
##   godot --path . --audio-driver Dummy --resolution 1280x900 -s res://tests/bay_layout_view.gd -- --out=<folder>
## Prints BAY VIEW DONE.

var _out := ""
var _n := 0
var _camera: Camera3D


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):
			_out = arg.get_slice("=", 1)
	DirAccess.make_dir_recursive_absolute(_out)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_NO_FOCUS, true)
	var bay: Node3D = (load("res://editor/bay_layout.tscn") as PackedScene).instantiate()
	root.add_child(bay)
	var sun := DirectionalLight3D.new()
	sun.rotation = Vector3(-1.0, 0.6, 0.0)
	root.add_child(sun)
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.18, 0.2, 0.24)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.6, 0.6, 0.65)
	root.add_child(env)
	_camera = Camera3D.new()
	_camera.far = 2000.0
	root.add_child(_camera)
	_camera.current = true
	_camera.look_at_from_position(Vector3(20.0, 330.0, 250.0), Vector3(20.0, 30.0, 10.0))


func _process(_delta: float) -> bool:
	_n += 1
	if _n == 20:
		_save("bay_editor_slant.png")
		_camera.projection = Camera3D.PROJECTION_ORTHOGONAL
		_camera.size = 330.0
		_camera.look_at_from_position(Vector3(20.0, 300.0, 0.0), Vector3(20.0, 0.0, 0.0), Vector3(0.0, 0.0, -1.0))
	elif _n == 30:
		_save("bay_editor_top.png")
		print("BAY VIEW DONE")
		quit()
	return false


func _save(name: String) -> void:
	root.get_viewport().get_texture().get_image().save_png(_out.path_join(name))
