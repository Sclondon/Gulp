class_name Tier
## Whether the game runs on a phone (or tablet), which draws and thinks far slower than a desktop:
## then Tier.phone() is true and the sea is drawn lighter (CLAUDE.md, "Decision: a phone tier";
## tools/PERF.md lists what it turns down). A desktop, in a browser or not, is left as it was.
##
## A phone is told by Godot's web feature tags (web_android, web_ios), a native mobile build, or
## the browser's user agent (an iPad's Safari says it is a Mac, but has a touch screen).
## `-- --phone` forces it on (to measure it on a desktop), `-- --desktop` off.

static var _phone := -1


static func phone() -> bool:
	if _phone < 0:
		_phone = 1 if _detect() else 0
	return _phone == 1


## The picture to load for `path`: on a phone its smaller copy in textures/phone/ when there is one
## (the set pieces' big atlases, written by tools/phone_textures.gd), else `path` itself. A phone's
## browser tab is killed when the page holds too much memory (tools/PERF.md, "Memory on phones").
static func texture(path: String) -> String:
	if phone():
		var small := "res://textures/phone/" + path.get_file()
		if ResourceLoader.exists(small):
			return small
	return path


static func _detect() -> bool:
	var args := OS.get_cmdline_user_args()
	if args.has("--phone"):
		return true
	if args.has("--desktop"):
		return false
	if OS.has_feature("web_android") or OS.has_feature("web_ios") or OS.has_feature("mobile"):
		return true
	if OS.has_feature("web"):
		var agent := str(JavaScriptBridge.eval("navigator.userAgent", true))
		var touches := int(JavaScriptBridge.eval("navigator.maxTouchPoints || 0", true))
		if agent.contains("Mobi") or agent.contains("Android") or agent.contains("iPhone") or agent.contains("iPad"):
			return true
		if agent.contains("Macintosh") and touches > 1:
			return true
	return false
