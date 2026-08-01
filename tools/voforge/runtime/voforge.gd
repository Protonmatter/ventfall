# voforge runtime — Godot 4 consumer (reference implementation).
#
#   var vo := VoForge.new()
#   add_child(vo)
#   vo.say("res://vo", "voss", "Four drones and a rig older than I am.")
#
# The hash must match voforge's Python djb2 exactly; it is computed over the
# UTF-8 bytes of "who|text".
class_name VoForge
extends AudioStreamPlayer

signal line_missing(who: String, text: String)

static func vo_hash(who: String, text: String) -> String:
	var bytes := (who + "|" + text).to_utf8_buffer()
	var h := 5381
	for b in bytes:
		h = ((h * 33) ^ b) & 0xFFFFFFFF
	return "%08x" % h

static func line_path(base_dir: String, who: String, text: String) -> String:
	return "%s/%s.mp3" % [base_dir, vo_hash(who, text)]

func say(base_dir: String, who: String, text: String) -> void:
	var path := line_path(base_dir, who, text)
	if not ResourceLoader.exists(path):
		line_missing.emit(who, text)
		return
	stop()
	stream = load(path)
	play()
