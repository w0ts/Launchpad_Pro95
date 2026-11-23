"""FakeCInstance: the object Live hands to create_instance(), recording what the script does."""
import threading


class FakeNoteRepeat:
	"""Live's c_instance.note_repeat."""

	def __init__(self):
		self.enabled = False
		self.repeat_rate = 1.0


class FakeCInstance:
	def __init__(self, song, on_midi=None):
		self._song = song
		self._on_midi = on_midi
		self._lock = threading.Lock()
		self.sent = []
		self.log = []
		self.messages = []
		self.rebuild_requested = False
		self.note_translations = {}
		self.cc_translations = {}
		self.pad_translation = None
		self.feedback_channels = None
		self.feedback_velocity = None
		self.session_highlight = None
		self.controlled_track = None
		self.lock_toggles = 0
		self.note_repeat = FakeNoteRepeat()
		self._handle = object()

	# -- Live API
	def song(self):
		return self._song

	def handle(self):
		return self._handle

	def instance_identifier(self):
		return 0

	def send_midi(self, midi_bytes):
		midi_bytes = tuple(midi_bytes)
		for byte in midi_bytes:
			if not 0 <= byte <= 255:
				raise ValueError(f"Invalid MIDI byte in {midi_bytes!r}")
		with self._lock:
			self.sent.append(midi_bytes)
		if self._on_midi is not None:
			self._on_midi(midi_bytes)
		return True

	def log_message(self, message):
		self.log.append(str(message))

	def show_message(self, message):
		self.messages.append(str(message))

	def request_rebuild_midi_map(self):
		self.rebuild_requested = True

	def set_pad_translation(self, translation):
		self.pad_translation = translation

	def set_note_translation(self, from_identifier, from_channel, to_identifier, to_channel):
		self.note_translations[(from_identifier, from_channel)] = (to_identifier, to_channel)

	def set_cc_translation(self, from_identifier, from_channel, to_identifier, to_channel):
		self.cc_translations[(from_identifier, from_channel)] = (to_identifier, to_channel)

	def set_feedback_channels(self, channels):
		self.feedback_channels = tuple(channels)

	def set_feedback_velocity(self, velocity):
		self.feedback_velocity = velocity

	def set_session_highlight(self, track_offset, scene_offset, width, height, include_return_tracks):
		self.session_highlight = (track_offset, scene_offset, width, height, include_return_tracks)

	def set_controlled_track(self, track):
		self.controlled_track = track

	def release_controlled_track(self):
		self.controlled_track = None

	def toggle_lock(self):
		self.lock_toggles += 1

	def update_locks(self):
		pass

	# -- helpers for tests
	def clear_translations(self):
		self.note_translations = {}
		self.cc_translations = {}

	def take_sent(self):
		with self._lock:
			sent, self.sent = self.sent, []
		return sent
