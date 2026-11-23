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


def spec(pitch, start, duration=0.25, velocity=100, mute=False):
	return Live.Clip.MidiNoteSpecification(pitch=pitch, start_time=start, duration=duration,
		velocity=velocity, mute=mute)


def rig_with_notes(make_rig, specs, length=4.0):
	song = make_song(clips=[(0, 0)])
	slot_clip = song.tracks[0].clip_slots[0].clip
	slot_clip.loop_end = length
	slot_clip.end_marker = length
	slot_clip.add_new_notes(tuple(specs))
	rig = make_rig(song=song)
	rig.tap_top(TOP["user"])
	rig.tap_top(TOP["user"])
	rig.tick(2)
	return rig


def test_steps_after_128_are_written_back(make_rig):
	rig = rig_with_notes(make_rig, [spec(36, 40.0)], length=64.0)
	ed = editor(rig)
	ed.set_page(20)  # steps 160-167
	rig.tap(1, 6)  # step 161, lowest degree
	starts = sorted(n[1] for n in clip(rig).note_tuples())
	assert starts == [40.0, 161 * ed.quantization]


def test_notes_before_time_zero_are_kept_and_not_shown(make_rig):
	rig = rig_with_notes(make_rig, [spec(36, -1.0)])
	ed = editor(rig)
	assert ed._notes_pitches[-7:] == [0] * 7  # never shown at the last step
	rig.tap(0, 6)
	assert sorted(n[1] for n in clip(rig).note_tuples()) == [-1.0, 0.0]


def test_new_clip_with_the_same_notes_is_parsed(make_rig):
	"""A duplicated clip (same notes, new clip) must show its notes, and editing it keeps them."""
	rig = rig_with_notes(make_rig, [spec(36, 0.0), spec(38, 0.25)])
	rig.song.tracks[0].duplicate_clip_slot(0)
	rig.song.view.selected_scene = rig.song.scenes[1]
	rig.tick()
	copy = rig.song.tracks[0].clip_slots[1].clip
	assert editor(rig)._clip is copy
	rig.tap(3, 6)
	assert len(copy.note_tuples()) == 3


def test_muted_notes_stay_muted(make_rig):
	rig = rig_with_notes(make_rig, [spec(36, 0.0, mute=True)])
	assert editor(rig)._notes_pitches[0:7] == [0] * 7  # the grid has no muted colour: not shown
	rig.tap(3, 6)
	notes = dict((n[1], n) for n in clip(rig).note_tuples())
	assert notes[0.0][4] is True


def test_notes_off_the_scale_or_octaves_are_kept(make_rig):
	off_scale = spec(37, 0.0)  # C# is not in C major
	too_high = spec(120, 0.5)  # above the 7 octaves of the lanes
	rig = rig_with_notes(make_rig, [off_scale, too_high])
	rig.tap(3, 6)
	pitches = sorted(n[0] for n in clip(rig).note_tuples())
	assert 37 in pitches and 120 in pitches


def test_chord_notes_on_one_step_are_all_kept(make_rig):
	rig = rig_with_notes(make_rig, [spec(36, 0.0), spec(40, 0.0)])
	ed = editor(rig)
	assert ed._notes_pitches[0:7].count(1) == 2
	rig.tap(3, 6)
	assert sorted(n[0] for n in clip(rig).note_tuples() if n[1] == 0.0) == [36, 40]


def test_untouched_steps_keep_their_notes_exactly(make_rig):
	original = (36, 0.0, 0.3, 90.0, False)
	rig = rig_with_notes(make_rig, [spec(*original)])
	rig.tap(3, 6)
	assert original in clip(rig).note_tuples()


def test_song_key_and_scale_changes_do_not_crash(melodic_rig):
	rig = melodic_rig
	rig.song.root_note = 2
	rig.song.scale_name = "Minor"
	rig.tick()


QUANTIZE = 3


def test_finer_quantization_never_makes_an_empty_loop(make_rig):
	rig = rig_with_notes(make_rig, [], length=1.0)
	before = editor(rig).quantization
	rig.tap_side(QUANTIZE)
	ratio = editor(rig).quantization / before
	assert clip(rig).loop_end == pytest.approx(1.0 * ratio)
	assert clip(rig).loop_end > clip(rig).loop_start
