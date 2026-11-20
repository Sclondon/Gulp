@tool
extends EditorPlugin
## The bay editor (README, "Editing the bay"; CLAUDE.md, "Decision: the bay's layout in one file,
## edited in the Godot editor"). Open editor/bay_layout.tscn: a bar over the 3D view has Save, Rebake,
## Play here and the floor's brushes; round areas get size handles. Everything else is Godot's own:
## drag places with the move gizmo, edit outlines with the path tools, numbers in the Inspector, and
## ctrl+Z undoes all of it, brush strokes too.

const EDITOR := preload("res://addons/bay_layout/bay_editor.gd")
const FLOOR := preload("res://addons/bay_layout/bay_floor.gd")
const CIRCLE := preload("res://addons/bay_layout/bay_circle.gd")
const SURFACE := 40.0
const BRUSHES := ["Off", "Raise", "Lower", "Smooth"]

var _bar: HBoxContainer
var _brush: OptionButton
var _size: SpinBox
var _strength: SpinBox
var _status: Label
var _gizmos: EditorNode3DGizmoPlugin
var _stroke_before := PackedFloat32Array()
var _stroking := false
var _last_dab := Vector2.INF
var _play_args := ""
var _restore_args := -1
## Engine arguments put before the game's own on Play here (tests/bay_layout_editor.gd: headless, silent).
var play_engine_args := ""


func _enter_tree() -> void:
	_bar = HBoxContainer.new()
	_bar.add_child(VSeparator.new())
	var title := Label.new()
	title.text = "Bay:"
	_bar.add_child(title)
	_button("Save", "Save the layout (data/layout.json) and redraw the floor (ctrl+S does the same)", _save)
	_button("Rebake floor", "Bake the floor again from the layout and the brushes, then redraw it (a few seconds)", _rebake)
	_button("Play here", "Save, then play the game starting where the 3D view's camera is (or where it looks, from above the water)", _play_here)
	_bar.add_child(VSeparator.new())
	var brush_label := Label.new()
	brush_label.text = "Floor brush:"
	_bar.add_child(brush_label)
	_brush = OptionButton.new()
	for b in BRUSHES:
		_brush.add_item(b)
	_brush.tooltip_text = "Paint the floor: Raise, Lower or Smooth (select any node of the bay first). Off to move things again."
	_brush.item_selected.connect(_on_brush)
	_bar.add_child(_brush)
	_size = _spin("Size", 1.0, 60.0, 8.0, "Brush radius (m)")
	_strength = _spin("Strength", 0.05, 5.0, 0.5, "How much each dab raises or lowers the middle (m); for Smooth, how far it smooths (0 to 1)")
	_status = Label.new()
	_status.modulate = Color(0.8, 0.9, 1.0)
	_bar.add_child(_status)
	add_control_to_container(CONTAINER_SPATIAL_EDITOR_MENU, _bar)
	_gizmos = preload("res://addons/bay_layout/circle_gizmo.gd").new()
	_gizmos.set(&"plugin", self)
	add_node_3d_gizmo_plugin(_gizmos)
	scene_changed.connect(_on_scene_changed)
	_on_scene_changed(EditorInterface.get_edited_scene_root())
	set_process(true)
	# (the headless check of the editor: tests/bay_layout_editor.gd)
	if "--bay-layout-test" in OS.get_cmdline_user_args():
		var test: Node = (load("res://tests/bay_layout_editor.gd") as GDScript).new()
		test.set(&"plugin", self)
		add_child(test)


func _exit_tree() -> void:
	remove_node_3d_gizmo_plugin(_gizmos)
	remove_control_from_container(CONTAINER_SPATIAL_EDITOR_MENU, _bar)
	_bar.queue_free()


func _process(_delta: float) -> void:
	var root := _root()
	_bar.visible = root != null
	if root:
		var s: String = root.get(&"status")
		var floor_node: Node = root.get(&"floor_node")
		if floor_node and floor_node.call(&"needs_bake"):
			s += "  (brush edits not baked yet)"
		_status.text = s
	if _restore_args >= 0:
		_restore_args -= 1
		if _restore_args < 0:
			ProjectSettings.set_setting("editor/run/main_run_args", _play_args)


func _on_scene_changed(_root_node: Node) -> void:
	if _bar:
		_bar.visible = _root() != null


func _handles(object: Object) -> bool:
	var root := _root()
	return root != null and object is Node and (object == root or root.is_ancestor_of(object))


func _forward_3d_gui_input(camera: Camera3D, event: InputEvent) -> int:
	var root := _root()
	if root == null or _brush.selected == 0:
		return AFTER_GUI_INPUT_PASS
	var floor_node: Node = root.get(&"floor_node")
	if event is InputEventMouse:
		var at: Vector3 = floor_node.call(&"hit", camera.project_ray_origin(event.position), camera.project_ray_normal(event.position))
		var spot := Vector2(at.x, at.z)
		floor_node.call(&"show_ring", spot, _size.value if at != Vector3.INF else 0.0)
		if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed and at != Vector3.INF:
				_stroking = true
				_stroke_before = (floor_node.get(&"adjust") as PackedFloat32Array).duplicate()
				_dab(floor_node, spot)
			elif not event.pressed and _stroking:
				_stroking = false
				var after := (floor_node.get(&"adjust") as PackedFloat32Array).duplicate()
				var ur := get_undo_redo()
				ur.create_action("Bay floor: " + BRUSHES[_brush.selected], UndoRedo.MERGE_DISABLE, floor_node)
				ur.add_do_method(floor_node, &"set_adjust", after)
				ur.add_undo_method(floor_node, &"set_adjust", _stroke_before)
				ur.commit_action(false)
			return AFTER_GUI_INPUT_STOP
		if event is InputEventMouseMotion and _stroking and at != Vector3.INF:
			# (a dab each quarter of the brush's radius)
			if spot.distance_to(_last_dab) > _size.value * 0.25:
				_dab(floor_node, spot)
			return AFTER_GUI_INPUT_STOP
	return AFTER_GUI_INPUT_PASS


func _dab(floor_node: Node, spot: Vector2) -> void:
	_last_dab = spot
	var mode: String = BRUSHES[_brush.selected].to_lower()
	floor_node.call(&"dab", mode, spot, _size.value, _strength.value if mode != "smooth" else clampf(_strength.value, 0.0, 1.0))


func _on_brush(index: int) -> void:
	var root := _root()
	if root == null:
		return
	if index == 0:
		(root.get(&"floor_node") as Node).call(&"show_ring", Vector2.ZERO, 0.0)
	else:
		# (the brushes act on whatever of the bay is selected: the floor, so the move gizmo is out of the way)
		EditorInterface.get_selection().clear()
		EditorInterface.get_selection().add_node(root.get(&"floor_node"))


func _save() -> void:
	var root := _root()
	if root:
		var bake: bool = root.call(&"save_layout")
		root.call(&"refresh_floor", bake)


func _rebake() -> void:
	var root := _root()
	if root:
		root.call(&"save_layout")
		root.call(&"refresh_floor", true)


## Saves, bakes if it must, and plays the game from the 3D view's camera (main.gd's --at=).
func _play_here() -> void:
	play_here()


## (public for the test)
func play_here() -> void:
	var root := _root()
	if root == null:
		return
	var bake: bool = root.call(&"save_layout")
	if bake:
		root.call(&"refresh_floor_now", true)
	var camera := EditorInterface.get_editor_viewport_3d(0).get_camera_3d()
	var floor_node: Node = root.get(&"floor_node")
	var at := camera.global_position
	if at.y > SURFACE - 1.0:
		# (from above the water: where the camera looks, a few metres over the floor)
		var hit: Vector3 = floor_node.call(&"hit", at, -camera.global_basis.z)
		if hit != Vector3.INF:
			at = hit + Vector3(0.0, 3.0, 0.0)
	var low: float = floor_node.call(&"height_at", at.x, at.z) + 1.5
	at.y = clampf(at.y, low, maxf(low, SURFACE - 1.5))
	_play_args = String(ProjectSettings.get_setting("editor/run/main_run_args", ""))
	ProjectSettings.set_setting("editor/run/main_run_args", (play_engine_args + " -- --at=%.1f,%.1f,%.1f --unlimited" % [at.x, at.y, at.z]).strip_edges())
	EditorInterface.play_main_scene()
	# (put back a few frames on, so that the setting is not kept)
	_restore_args = 3


func _root() -> Node:
	var root := EditorInterface.get_edited_scene_root()
	return root if root != null and root.get_script() == EDITOR else null


func _button(text: String, tip: String, pressed: Callable) -> void:
	var b := Button.new()
	b.text = text
	b.tooltip_text = tip
	b.flat = false
	b.pressed.connect(pressed)
	_bar.add_child(b)


func _spin(label: String, low: float, high: float, value: float, tip: String) -> SpinBox:
	var l := Label.new()
	l.text = label
	_bar.add_child(l)
	var s := SpinBox.new()
	s.min_value = low
	s.max_value = high
	s.step = 0.05
	s.value = value
	s.tooltip_text = tip
	s.custom_minimum_size.x = 70
	_bar.add_child(s)
	return s
