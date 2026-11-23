"""Live.Track."""
from ._model import Track, TrackView

__all__ = ["Track", "TrackView"]

# Live's Boost.Python classes print as <class 'Track.Track'>; scripts compare that string.
Track.__module__ = "Track"
