@tool
extends EditorNode3DGizmoPlugin
## Size handles for the bay editor's round areas (bay_circle.gd): a handle on the ring for its radius,
## and one on the dashed ring for its outer radius where it has one. Dragging is undoable.

const CIRCLE := preload("res://addons/bay_layout/bay_circle.gd")

var plugin: EditorPlugin


func _init() -> void:
	create_handle_material("handles")


func _get_gizmo_name() -> String:
	return "BayCircle"


func _has_gizmo(node: Node3D) -> bool:
	return node.get_script() == CIRCLE


func _redraw(gizmo: EditorNode3DGizmo) -> void:
	gizmo.clear()
	var node := gizmo.get_node_3d()
	var handles := PackedVector3Array([Vector3(float(node.get(&"radius")), 0.0, 0.0)])
	if float(node.get(&"outer")) > 0.0:
		handles.append(Vector3(float(node.get(&"outer")), 0.0, 0.0))
	gizmo.add_handles(handles, get_material("handles", gizmo), [])


func _get_handle_name(_gizmo: EditorNode3DGizmo, handle_id: int, _secondary: bool) -> String:
	return "Radius" if handle_id == 0 else "Outer radius"


func _get_handle_value(gizmo: EditorNode3DGizmo, handle_id: int, _secondary: bool) -> Variant:
	return gizmo.get_node_3d().get(&"radius" if handle_id == 0 else &"outer")


func _set_handle(gizmo: EditorNode3DGizmo, handle_id: int, _secondary: bool, camera: Camera3D, screen_pos: Vector2) -> void:
	var node := gizmo.get_node_3d()
	var plane := Plane(Vector3.UP, node.global_position.y)
	var hit: Variant = plane.intersects_ray(camera.project_ray_origin(screen_pos), camera.project_ray_normal(screen_pos))
	if hit == null:
		return
	var r := Vector2((hit as Vector3).x - node.global_position.x, (hit as Vector3).z - node.global_position.z).length()
	node.set(&"radius" if handle_id == 0 else &"outer", snappedf(r, 0.5))
	node.update_gizmos()


func _commit_handle(gizmo: EditorNode3DGizmo, handle_id: int, _secondary: bool, restore: Variant, cancel: bool) -> void:
	var node := gizmo.get_node_3d()
	var property := &"radius" if handle_id == 0 else &"outer"
	if cancel:
		node.set(property, restore)
		return
	var ur := plugin.get_undo_redo()
	ur.create_action("Bay: resize " + node.name)
	ur.add_do_property(node, property, node.get(property))
	ur.add_undo_property(node, property, restore)
	ur.add_do_method(node, &"update_gizmos")
	ur.add_undo_method(node, &"update_gizmos")
	ur.commit_action()
