"""Live.SimplerDevice (only what an installed Live's ableton.v2.control_surface reads)."""
from ._enums import PlaybackMode

__all__ = ["PlaybackMode", "get_available_voice_numbers"]


def get_available_voice_numbers():
	return (1, 2, 4, 6, 8, 12, 16, 24, 32)
