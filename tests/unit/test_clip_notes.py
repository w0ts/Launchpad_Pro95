"""Tests for ClipNotes with fake clips (run outside Live: python3 -m pytest tests)."""

import importlib.util
import os
from collections import namedtuple

import pytest

_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "ClipNotes.py")
_spec = importlib.util.spec_from_file_location("ClipNotes", _PATH)
ClipNotes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ClipNotes)

MidiNote = namedtuple(
    "MidiNote", "pitch start_time duration velocity mute probability velocity_deviation release_velocity"
)


def spec_factory(**kwargs):
    defaults = dict(probability=1.0, velocity_deviation=0.0, release_velocity=64.0)
    defaults.update(kwargs)
    return MidiNote(**defaults)


class OldClip:
    """Live 9/10 clip: only the selection-based note calls."""

    def __init__(self, notes):
        self.notes = tuple(notes)
        self.selected = False

    def select_all_notes(self):
        self.selected = True

    def deselect_all_notes(self):
        self.selected = False

    def get_selected_notes(self):
        assert self.selected
        return self.notes

    def replace_selected_notes(self, notes):
        assert self.selected
        self.notes = tuple(notes)


class NewClip:
    """Live 11+ clip: extended note calls."""

    def __init__(self, notes):
        self.notes = list(notes)

    def get_all_notes_extended(self):
        return tuple(self.notes)

    def get_notes_extended(self, from_pitch, pitch_span, from_time, time_span):
        return tuple(self.notes)

    def remove_notes_extended(self, from_pitch, pitch_span, from_time, time_span):
        assert (from_pitch, pitch_span) == (0, 128)
        self.notes = [n for n in self.notes if not from_time <= n.start_time < from_time + time_span]

    def add_new_notes(self, specs):
        self.notes.extend(specs)

    def get_selected_notes(self):
        raise AssertionError("deprecated call used on Live 11+")

    replace_selected_notes = get_selected_notes


def test_old_api_read_and_write():
    clip = OldClip([(60, 0.0, 0.25, 100, False)])
    assert ClipNotes.read_all_notes(clip) == ((60, 0.0, 0.25, 100, False),)
    ClipNotes.write_all_notes(clip, [[62, 1.0, 0.5, 90, True]])
    assert clip.notes == ((62, 1.0, 0.5, 90, True),)
    assert not clip.selected


def test_new_api_read_returns_old_tuple_format():
    clip = NewClip([spec_factory(pitch=60, start_time=0.0, duration=0.25, velocity=100.0, mute=False)])
    assert ClipNotes.read_all_notes(clip) == ((60, 0.0, 0.25, 100.0, False),)


def test_new_api_write_replaces_notes():
    clip = NewClip([spec_factory(pitch=60, start_time=0.0, duration=0.25, velocity=100.0, mute=False)])
    ClipNotes.write_all_notes(clip, [(64, 2.0, 0.5, 80, True)], spec_factory=spec_factory)
    assert ClipNotes.read_all_notes(clip) == ((64, 2.0, 0.5, 80.0, True),)


def test_new_api_write_keeps_probability_of_existing_notes():
    clip = NewClip(
        [
            spec_factory(
                pitch=60,
                start_time=1.0,
                duration=0.25,
                velocity=100.0,
                mute=False,
                probability=0.5,
                velocity_deviation=10.0,
                release_velocity=30.0,
            )
        ]
    )
    # The step sequencer mutes the note: same pitch and time, so its extras stay.
    ClipNotes.write_all_notes(clip, [(60, 1.0, 0.25, 100.0, True)], spec_factory=spec_factory)
    note = clip.notes[0]
    assert (note.mute, note.probability, note.velocity_deviation, note.release_velocity) == (True, 0.5, 10.0, 30.0)


def test_new_api_write_empty_clears_clip():
    clip = NewClip([spec_factory(pitch=60, start_time=0.0, duration=0.25, velocity=100.0, mute=False)])
    ClipNotes.write_all_notes(clip, (), spec_factory=spec_factory)
    assert clip.notes == []


class Live110Clip:
    """Live 11.0 clip: extended calls, but no get_all_notes_extended yet."""

    def __init__(self, notes):
        self.notes = list(notes)

    def get_notes_extended(self, from_pitch, pitch_span, from_time, time_span):
        return tuple(self.notes)

    def add_new_notes(self, specs):
        self.notes.extend(specs)


IdNote = namedtuple("IdNote", MidiNote._fields + ("note_id",))


class IdClip(NewClip):
    """Live 11+ clip whose notes carry note_id and that can remove notes by id."""

    def __init__(self, notes):
        super().__init__(())
        self.next_id = 1
        self.add_new_notes(notes)

    def add_new_notes(self, specs):
        for spec in specs:
            self.notes.append(IdNote(*spec, note_id=self.next_id))
            self.next_id += 1

    def remove_notes_by_id(self, ids):
        ids = set(ids)
        self.notes = [n for n in self.notes if n.note_id not in ids]


@pytest.mark.parametrize("clip_class", [NewClip, IdClip], ids=["range", "by_id"])
def test_new_api_write_does_not_duplicate_notes_before_time_zero(clip_class):
    # A clip whose loop starts before 0 can hold notes at negative times.
    clip = clip_class(
        [
            spec_factory(pitch=60, start_time=-1.0, duration=0.25, velocity=100.0, mute=False),
            spec_factory(pitch=62, start_time=1.0, duration=0.25, velocity=100.0, mute=False),
        ]
    )
    notes = ClipNotes.read_all_notes(clip)
    ClipNotes.write_all_notes(clip, notes, spec_factory=spec_factory)
    ClipNotes.write_all_notes(clip, notes, spec_factory=spec_factory)
    assert sorted(ClipNotes.read_all_notes(clip)) == sorted(notes)


def test_new_api_write_removes_by_id_when_available():
    clip = IdClip([spec_factory(pitch=60, start_time=0.0, duration=0.25, velocity=100.0, mute=False)])
    clip.remove_notes_extended = None  # must not be needed
    ClipNotes.write_all_notes(clip, [(64, 2.0, 0.5, 80, False)], spec_factory=spec_factory)
    assert ClipNotes.read_all_notes(clip) == ((64, 2.0, 0.5, 80.0, False),)


def test_new_api_without_get_all_notes_extended():
    clip = Live110Clip([spec_factory(pitch=48, start_time=0.5, duration=1.0, velocity=70.0, mute=False)])
    assert ClipNotes.read_all_notes(clip) == ((48, 0.5, 1.0, 70.0, False),)
