"""Melodic step sequencer (user button pressed twice): one column per step, rows 0-6 are the
7 scale degrees (top row = highest), row 7 is the loop selector. Scene buttons, top first:
scale, octave, pitch, quantization, velocity, length, random, lock."""
import Live
import pytest

from harness.rig import TOP, make_song

OCTAVE, PITCH, VELOCITY, LENGTH, RANDOM = 1, 2, 4, 5, 6


@pytest.fixture
def melodic_rig(make_rig):
	rig = make_rig(song=make_song(clips=[(0, 0)]))
	rig.tap_top(TOP["user"])
	rig.tap_top(TOP["user"])
	rig.tick(2)
	assert rig.surface._user_button_modes.selected_mode == "stepsequencer2_mode"
	return rig


def clip(rig):
	return rig.song.tracks[0].clip_slots[0].clip


def editor(rig):
	return rig.surface._step_sequencer2._note_editor


def test_pad_enters_a_note_through_the_live11_api(melodic_rig):
	rig = melodic_rig
	ed = editor(rig)
	rig.tap(2, 6)  # third step, lowest degree
	notes = clip(rig).note_tuples()
	assert len(notes) == 1
	pitch, start, duration, velocity, mute = notes[0]
	assert start == pytest.approx(2 * ed.quantization)
	assert pitch == ed._key_indexes[0] + 12 * (ed._notes_octaves[2] - 2)
	assert not mute
	assert clip(rig).deprecated_calls == []


def test_higher_row_gives_a_higher_degree(melodic_rig):
	rig = melodic_rig
	rig.tap(0, 6)
	rig.tap(1, 0)
	by_start = dict((n[1], n[0]) for n in clip(rig).note_tuples())
	assert by_start[editor(rig).quantization] > by_start[0.0]


def test_second_press_clears_the_note(melodic_rig):
	rig = melodic_rig
	rig.tap(4, 3)
	assert len(clip(rig).note_tuples()) == 1
	rig.tap(4, 3)
	assert clip(rig).note_tuples() == ()
	assert clip(rig).deprecated_calls == []


def test_note_lights_its_pad(melodic_rig):
	rig = melodic_rig
	before = rig.device.led(5, 2)
	rig.tap(5, 2)
	rig.tick()
	assert rig.device.led(5, 2) != before


def test_existing_notes_are_parsed_into_steps(make_rig):
	song = make_song(clips=[(0, 0)])
	song.tracks[0].clip_slots[0].clip.add_new_notes((Live.Clip.MidiNoteSpecification(
		pitch=36, start_time=0.0, duration=0.25, velocity=100, mute=False),))
	rig = make_rig(song=song)
	rig.tap_top(TOP["user"])
	rig.tap_top(TOP["user"])
	rig.tick(2)
	assert editor(rig)._notes_pitches[0] == 1
	assert clip(rig).deprecated_calls == []


def test_velocity_page_changes_the_note_velocity(melodic_rig):
	rig = melodic_rig
	rig.tap(0, 6)
	before = clip(rig).note_tuples()[0][3]
	rig.tap_side(VELOCITY)
	rig.tick()
	rig.tap(0, 0)  # top row = highest velocity
	assert clip(rig).note_tuples()[0][3] != before


def test_octave_page_moves_the_note(melodic_rig):
	rig = melodic_rig
	rig.tap(0, 6)
	before = clip(rig).note_tuples()[0][0]
	rig.tap_side(OCTAVE)
	rig.tick()
	rig.tap(0, 0)  # highest octave
	assert clip(rig).note_tuples()[0][0] > before


def test_random_button_writes_notes(melodic_rig):
	rig = melodic_rig
	rig.tap_side(RANDOM)
	assert "randomise" in rig.messages
	assert clip(rig).deprecated_calls == []


def test_pad_on_empty_slot_creates_a_clip(make_rig):
	rig = make_rig()
	rig.tap_top(TOP["user"])
	rig.tap_top(TOP["user"])
	rig.tick(2)
	rig.tap(0, 0)
	rig.tick(2)
	assert rig.song.tracks[0].clip_slots[0].has_clip
