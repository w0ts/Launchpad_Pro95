"""Enum-like namespaces of the Live API (values match Live's integer values where known)."""


class _Enum(object):
	def __init__(self, **values):
		self.__dict__.update(values)
		self.values = dict((v, k) for k, v in values.items())


Quantization = _Enum(q_no_q=0, q_8_bars=1, q_4_bars=2, q_2_bars=3, q_bar=4, q_half=5, q_half_triplet=6,
	q_quarter=7, q_quarter_triplet=8, q_eight=9, q_eight_triplet=10, q_sixtenth=11,
	q_sixtenth_triplet=12, q_thirtytwoth=13)

RecordingQuantization = _Enum(rec_q_no_q=0, rec_q_quarter=1, rec_q_eight=2, rec_q_eight_triplet=3,
	rec_q_eight_eight_triplet=4, rec_q_sixtenth=5, rec_q_sixtenth_triplet=6,
	rec_q_sixtenth_sixtenth_triplet=7, rec_q_thirtysecond=8)

SessionRecordStatus = _Enum(off=0, on=1, transition=2)

CaptureMode = _Enum(all=0, all_except_selected=1)

MapMode = _Enum(absolute=0, absolute_14_bit=1, relative_signed_bit=2, relative_signed_bit2=3,
	relative_binary_offset=4, relative_two_compliment=5, relative_smooth_signed_bit=6,
	relative_smooth_signed_bit2=7, relative_smooth_binary_offset=8, relative_smooth_two_compliment=9)

NavDirection = _Enum(up=0, down=1, left=2, right=3)

# Used at import time by ableton.v2.control_surface (an installed Live's pushbase needs it).
AutomationState = _Enum(none=0, playing=1, overridden=2)

ParameterState = _Enum(enabled=0, irrelevant=1, disabled=2)

WarpMode = _Enum(beats=0, tones=1, texture=2, repitch=3, complex=4, rex=5, complex_pro=6)

PlaybackMode = _Enum(classic=0, one_shot=1, slicing=2)

GridQuantization = _Enum(no_grid=0, g_8_bars=1, g_4_bars=2, g_2_bars=3, g_bar=4, g_half=5, g_quarter=6,
	g_eighth=7, g_sixteenth=8, g_thirtysecond=9)
