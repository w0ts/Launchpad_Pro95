"""Live.Application: version, document, application view and the Launchpad challenge helpers."""
from ._enums import NavDirection

# Version reported by the fake application (Live 11+ is the supported range).
VERSION = (12, 1, 0)

# The Launchpad Pro challenge: Launchpad_Pro95 sends a random number, the device answers
# encrypt_challenge2(number). The real algorithm is inside Live; any deterministic function
# works here as long as the emulated device uses the same one (it calls this module too).
FIXED_RANDOM_INT = 123456789

_state = {"song": None, "combine": True}


def set_document(song):
	"""Test helper: the Song returned by get_document() and used by the application."""
	_state["song"] = song


def set_combine_apcs(value):
	_state["combine"] = bool(value)


def combine_apcs():
	return _state["combine"]


def get_random_int(low, high):
	return low + FIXED_RANDOM_INT % max(1, high - low)


def encrypt_challenge2(challenge):
	value = (challenge * 2654435761 + 12345) & 0xFFFFFFFF
	return (value >> 7) & 0x7F7F


class ApplicationView:
	NavDirection = NavDirection

	def __init__(self):
		self._visible = {"Session": True, "Arranger": False, "Detail": True, "Detail/Clip": False,
			"Detail/DeviceChain": True, "Browser": False}
		self._listeners = {}
		self.focused_document_view = "Session"
		self.browse_mode = False

	def is_view_visible(self, name, main_window_only=True):
		return self._visible.get(name, False)

	def _set_visible(self, name, visible):
		if self._visible.get(name, False) != visible:
			self._visible[name] = visible
			for listener in tuple(self._listeners.get(name, ())):
				listener()

	def show_view(self, name):
		self._set_visible(name, True)
		if name == "Detail/Clip":
			self._set_visible("Detail/DeviceChain", False)
		elif name == "Detail/DeviceChain":
			self._set_visible("Detail/Clip", False)

	def hide_view(self, name):
		self._set_visible(name, False)

	def focus_view(self, name):
		self.show_view(name)

	def is_view_focused(self, name):
		return self._visible.get(name, False)

	def scroll_view(self, direction, name, modifier_pressed):
		pass

	def zoom_view(self, direction, name, modifier_pressed):
		pass

	def toggle_browse(self):
		self.browse_mode = not self.browse_mode

	def add_is_view_visible_listener(self, name, listener):
		listeners = self._listeners.setdefault(name, [])
		if listener in listeners:
			raise RuntimeError("Listener already connected")
		listeners.append(listener)

	def remove_is_view_visible_listener(self, name, listener):
		listeners = self._listeners.setdefault(name, [])
		if listener not in listeners:
			raise RuntimeError("Listener not connected")
		listeners.remove(listener)

	def is_view_visible_has_listener(self, name, listener):
		return listener in self._listeners.get(name, ())

	def listener_count(self, name):
		return len(self._listeners.get(name, ()))


class Application:
	View = ApplicationView

	def __init__(self):
		self.view = ApplicationView()

	def get_major_version(self):
		return VERSION[0]

	def get_minor_version(self):
		return VERSION[1]

	def get_bugfix_version(self):
		return VERSION[2]

	def get_document(self):
		return _state["song"]

	def has_option(self, name):
		return False


_application = Application()


def get_application():
	return _application


def reset_application():
	"""Test helper: a fresh application view (listeners dropped)."""
	global _application
	_application = Application()
	return _application
