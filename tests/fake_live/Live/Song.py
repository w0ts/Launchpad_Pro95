"""Live.Song: the Song class, its enums and the scale list (Live 12 API)."""

from ._enums import CaptureMode, Quantization, RecordingQuantization, SessionRecordStatus
from ._model import Song, SongView

__all__ = [
    "CaptureMode",
    "Quantization",
    "RecordingQuantization",
    "SessionRecordStatus",
    "Song",
    "SongView",
    "SCALES",
    "get_all_scales_ordered",
    "BeatTime",
    "TimeFormat",
]

# Live 12's scale list, in its order. Written from memory of Live 12's scale menu: the
# names and order are NOT verified against a real Live (the list lives in the Live binary).
SCALES = (
    ("Major", (0, 2, 4, 5, 7, 9, 11)),
    ("Minor", (0, 2, 3, 5, 7, 8, 10)),
    ("Dorian", (0, 2, 3, 5, 7, 9, 10)),
    ("Mixolydian", (0, 2, 4, 5, 7, 9, 10)),
    ("Lydian", (0, 2, 4, 6, 7, 9, 11)),
    ("Phrygian", (0, 1, 3, 5, 7, 8, 10)),
    ("Locrian", (0, 1, 3, 5, 6, 8, 10)),
    ("Whole Tone", (0, 2, 4, 6, 8, 10)),
    ("Half-whole Dim.", (0, 1, 3, 4, 6, 7, 9, 10)),
    ("Whole-half Dim.", (0, 2, 3, 5, 6, 8, 9, 11)),
    ("Minor Blues", (0, 3, 5, 6, 7, 10)),
    ("Minor Pentatonic", (0, 3, 5, 7, 10)),
    ("Major Pentatonic", (0, 2, 4, 7, 9)),
    ("Harmonic Minor", (0, 2, 3, 5, 7, 8, 11)),
    ("Harmonic Major", (0, 2, 4, 5, 7, 8, 11)),
    ("Dorian #4", (0, 2, 3, 6, 7, 9, 10)),
    ("Phrygian Dominant", (0, 1, 4, 5, 7, 8, 10)),
    ("Melodic Minor", (0, 2, 3, 5, 7, 9, 11)),
    ("Lydian Augmented", (0, 2, 4, 6, 8, 9, 11)),
    ("Lydian Dominant", (0, 2, 4, 6, 7, 9, 10)),
    ("Super Locrian", (0, 1, 3, 4, 6, 8, 10)),
    ("8-Tone Spanish", (0, 1, 3, 4, 5, 6, 8, 10)),
    ("Bhairav", (0, 1, 4, 5, 7, 8, 11)),
    ("Hungarian Minor", (0, 2, 3, 6, 7, 8, 11)),
    ("Hirajoshi", (0, 2, 3, 7, 8)),
    ("In-Sen", (0, 1, 5, 7, 10)),
    ("Iwato", (0, 1, 5, 6, 10)),
    ("Kumoi", (0, 2, 3, 7, 9)),
    ("Pelog Selisir", (0, 1, 3, 7, 8)),
    ("Pelog Tembung", (0, 1, 5, 7, 8)),
    ("Messiaen 3", (0, 2, 3, 4, 6, 7, 8, 10, 11)),
    ("Messiaen 4", (0, 1, 2, 5, 6, 7, 8, 11)),
    ("Messiaen 5", (0, 1, 5, 6, 7, 11)),
    ("Messiaen 6", (0, 2, 4, 5, 6, 8, 10, 11)),
    ("Messiaen 7", (0, 1, 2, 3, 5, 6, 7, 8, 9, 11)),
)


def get_all_scales_ordered():
    return SCALES


class BeatTime:
    def __init__(self, bars=1, beats=1, sub_division=1, ticks=0):
        self.bars, self.beats, self.sub_division, self.ticks = bars, beats, sub_division, ticks


class TimeFormat:
    ms_time = 0
    smpte_24 = 1
    smpte_25 = 2
    smpte_29 = 3
    smpte_30 = 4
    smpte_30_drop = 5
