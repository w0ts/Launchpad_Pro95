"""A fake clock for the script's time.time() calls (long presses, double taps...).

The script reads wall-clock time in several modules. The rig replaces their ``time``
module by a FakeTime whose time() only moves when the test ticks (100 ms per tick, like
Live's update_display timer), so press timings are deterministic.
"""

import time as _real_time

TICK_SECONDS = 0.1
START = 1000.0

# Script modules that call time.time().
TIMED_MODULES = ("DeviceComponent", "NoteEditorComponent", "StepSequencerComponent", "StepSequencerComponent2")


class FakeTime:
    def __init__(self, start=START):
        self.now = start

    def time(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds

    def __getattr__(self, name):
        return getattr(_real_time, name)
