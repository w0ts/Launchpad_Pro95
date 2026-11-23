"""Test double for Live's pushbase.special_session_component (only what the script uses).

Launchpad_Pro95's SpecialSessionComponent.copyclip() uses ClipSlotCopyHandler to copy a
clip between slots. The fetched framework tree has no usable pushbase (the decompiled one
of the pinned commit holds merge-conflict markers and needs ableton.v2.control_surface),
so conftest puts this stub on the path when ABLETON_FRAMEWORK_DIR has no pushbase. With an
installed Live's "MIDI Remote Scripts" folder, the real module is used.

Written from the Live 11 behaviour: copy only from a slot with a clip that is not
recording, and only MIDI to MIDI tracks / audio to audio tracks; notifications are dropped.
"""


class ClipSlotCopyHandler(object):

	def __init__(self, *a, **k):
		self._is_copying = False
		self._source_clip_slot = None

	@property
	def is_copying(self):
		return self._is_copying

	def duplicate(self, clip_slot):
		if self._is_copying:
			self._finish_copying(clip_slot)
		else:
			self._start_copying(clip_slot)

	def stop_copying(self):
		self._reset_copying_state()

	def _start_copying(self, source_clip_slot):
		if getattr(source_clip_slot, "is_group_slot", False):
			return
		clip = source_clip_slot.clip
		if clip is not None and not clip.is_recording:
			self._is_copying = True
			self._source_clip_slot = source_clip_slot

	def _finish_copying(self, target_clip_slot):
		if getattr(target_clip_slot, "is_group_slot", False):
			return
		source_is_audio = self._source_clip_slot.clip.is_audio_clip
		if source_is_audio == target_clip_slot.canonical_parent.has_audio_input:
			self._source_clip_slot.duplicate_clip_to(target_clip_slot)
		self._reset_copying_state()

	def _reset_copying_state(self):
		self._source_clip_slot = None
		self._is_copying = False
