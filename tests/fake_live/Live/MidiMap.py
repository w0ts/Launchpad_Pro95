"""Live.MidiMap: what build_midi_map registers. The fake keeps it in a MidiMapHandle.

Live routes an incoming message to the script (receive_midi) only when it was forwarded
in the current MIDI map; a mapped message moves a parameter directly; anything else goes
to the tracks as instrument input (after the note/CC translations of the c_instance).
"""
from ._enums import MapMode

__all__ = ["MapMode", "MidiMapHandle", "CCFeedbackRule", "NoteFeedbackRule", "PitchBendFeedbackRule", "forward_midi_note", "forward_midi_cc", "forward_midi_pitchbend", "map_midi_cc_with_feedback_map", "map_midi_note_with_feedback_map", "map_midi_pitchbend_with_feedback_map", "map_midi_cc", "map_midi_note", "send_feedback_for_parameter", "NOTE", "CC", "PITCHBEND"]

NOTE, CC, PITCHBEND = "note", "cc", "pitchbend"


class MidiMapHandle:
	def __init__(self):
		self.forwarded = set()
		self.mappings = {}
		self.feedback = []

	def is_forwarded(self, kind, channel, identifier):
		return (kind, channel, identifier) in self.forwarded


class _FeedbackRule:
	def __init__(self):
		self.channel = 0
		self.delay_in_ms = 0.0


class CCFeedbackRule(_FeedbackRule):
	def __init__(self):
		super().__init__()
		self.cc_no = 0
		self.cc_value_map = ()
		self.enabled = True


class NoteFeedbackRule(_FeedbackRule):
	def __init__(self):
		super().__init__()
		self.note_no = 0
		self.vel_map = ()


class PitchBendFeedbackRule(_FeedbackRule):
	def __init__(self):
		super().__init__()
		self.value_pair_map = ()


def forward_midi_note(script_handle, midi_map_handle, channel, identifier):
	midi_map_handle.forwarded.add((NOTE, channel, identifier))
	return True


def forward_midi_cc(script_handle, midi_map_handle, channel, identifier):
	midi_map_handle.forwarded.add((CC, channel, identifier))
	return True


def forward_midi_pitchbend(script_handle, midi_map_handle, channel):
	midi_map_handle.forwarded.add((PITCHBEND, channel, None))
	return True


def map_midi_cc_with_feedback_map(midi_map_handle, parameter, channel, cc, map_mode, feedback_rule,
		needs_takeover=True, sensitivity=1.0):
	midi_map_handle.mappings[(CC, channel, cc)] = parameter
	midi_map_handle.feedback.append(feedback_rule)
	return True


def map_midi_note_with_feedback_map(midi_map_handle, parameter, channel, note, feedback_rule):
	midi_map_handle.mappings[(NOTE, channel, note)] = parameter
	midi_map_handle.feedback.append(feedback_rule)
	return True


def map_midi_pitchbend_with_feedback_map(midi_map_handle, parameter, channel, feedback_rule, needs_takeover=True):
	midi_map_handle.mappings[(PITCHBEND, channel, None)] = parameter
	return True


def map_midi_cc(midi_map_handle, parameter, channel, cc, map_mode, avoid_takeover=False):
	midi_map_handle.mappings[(CC, channel, cc)] = parameter
	return True


def map_midi_note(midi_map_handle, parameter, channel, note):
	midi_map_handle.mappings[(NOTE, channel, note)] = parameter
	return True


def send_feedback_for_parameter(midi_map_handle, parameter):
	pass
