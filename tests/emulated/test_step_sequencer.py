"""Drum step sequencer (user button, first sub mode). In its normal mode the top 4 rows of
the grid are 32 steps of the selected note, the bottom-left 4x4 pads select the note and
the bottom-right 4x4 pads are the loop selector. Scene buttons, top first: scale, octave
up, octave down, quantization, velocity, mode, mute shift, lock."""
import Live
import pytest

from harness.rig import TOP, make_song

VELOCITY, MODE, MUTE_SHIFT = 4, 5, 6


@pytest.fixture
def seq_rig(make_rig):
	rig = make_rig(song=make_song(clips=[(0, 0)]))
	rig.tap_top(TOP["user"])
	rig.tick(2)
	assert rig.surface._user_button_modes.selected_mode == "stepsequencer_mode"
	return rig


def clip(rig, track=0, scene=0):
	return rig.song.tracks[track].clip_slots[scene].clip


def stepseq(rig):
	return rig.surface._step_sequencer


def editor(rig):
	return stepseq(rig)._note_editor


def add_note(rig, start, pitch=None, **k):
	pitch = editor(rig)._key_indexes[0] if pitch is None else pitch
	clip(rig).add_new_notes((Live.Clip.MidiNoteSpecification(pitch=pitch, start_time=start,
		duration=editor(rig).quantization, velocity=100, mute=False, **k),))
	rig.tick()


def test_step_sequencer_follows_the_selected_clip(seq_rig):
	assert stepseq(seq_rig)._clip is clip(seq_rig)


def test_pad_adds_a_note_through_the_live11_api(seq_rig):
	"""A note added from a pad ends up in the clip, and no deprecated note call is made."""
	rig = seq_rig
	rig.tap(0, 0)
	notes = clip(rig).note_tuples()
	assert len(notes) == 1
	pitch, start, duration, velocity, mute = notes[0]
	assert (pitch, start, duration, mute) == (editor(rig)._key_indexes[0], 0.0, editor(rig).quantization, False)
	assert clip(rig).deprecated_calls == []


def test_second_press_removes_the_note(seq_rig):
	rig = seq_rig
	rig.tap(0, 0)
	rig.tap(0, 0)
	assert clip(rig).note_tuples() == ()
	assert clip(rig).deprecated_calls == []


def test_pads_map_to_steps_left_to_right_then_down(seq_rig):
	rig = seq_rig
	step = editor(rig).quantization
	rig.tap(3, 0)
	rig.tap(0, 1)
	assert sorted(note[1] for note in clip(rig).note_tuples()) == [3 * step, 8 * step]


def test_note_lights_its_pad(seq_rig):
	rig = seq_rig
	before = rig.device.led(2, 0)
	rig.tap(2, 0)
	rig.tick()
	assert rig.device.led(2, 0) != before


def test_notes_added_in_live_show_on_the_pads(seq_rig):
	rig = seq_rig
	empty = rig.device.led(1, 0)
	add_note(rig, editor(rig).quantization)
	assert rig.device.led(1, 0) != empty


def test_editing_keeps_probability_of_other_notes(seq_rig):
	rig = seq_rig
	add_note(rig, 0.0, probability=0.5, velocity_deviation=12.0)
	rig.tap(1, 0)
	kept = [n for n in clip(rig).get_all_notes_extended() if n.start_time == 0.0]
	assert len(kept) == 1
	assert (kept[0].probability, kept[0].velocity_deviation) == (0.5, 12.0)
	assert clip(rig).deprecated_calls == []


def test_reading_notes_uses_only_the_live11_api(seq_rig):
	rig = seq_rig
	add_note(rig, 0.0)
	rig.tap_top(TOP["session"])
	rig.tap_top(TOP["user"])
	rig.tick(2)
	assert clip(rig).deprecated_calls == []


def test_note_selector_pad_changes_the_edited_note(seq_rig):
	rig = seq_rig
	first = editor(rig)._key_indexes[0]
	rig.tap(1, 7)  # bottom-left 4x4 block, second pad of the bottom row
	rig.tick()
	assert editor(rig)._key_indexes[0] != first
	rig.tap(0, 0)
	assert clip(rig).note_tuples()[0][0] == editor(rig)._key_indexes[0]


def test_pad_on_empty_slot_creates_a_clip(make_rig):
	rig = make_rig()
	rig.tap_top(TOP["user"])
	rig.tick(2)
	rig.tap(0, 0)
	rig.tick(2)
	slot = rig.song.tracks[0].clip_slots[0]
	assert slot.has_clip and slot.clip.length > 0


def test_selecting_another_scene_follows_its_clip(seq_rig):
	rig = seq_rig
	rig.song.tracks[0].clip_slots[1].create_clip(4.0)
	rig.song.view.selected_scene = rig.song.scenes[1]
	rig.tick()
	assert stepseq(rig)._clip is clip(rig, 0, 1)
	rig.tap(0, 0)
	assert clip(rig, 0, 1).note_tuples() != ()
	assert clip(rig, 0, 0).note_tuples() == ()


def test_quantization_button_changes_the_step_length(seq_rig):
	rig = seq_rig
	before = editor(rig).quantization
	rig.tap_side(3)
	rig.tick()
	assert editor(rig).quantization != before


def test_loop_selector_double_tap_sets_a_one_block_loop(seq_rig):
	rig = seq_rig
	q = stepseq(rig)._quantization
	rig.tap(5, 4)  # second loop block (8 steps each)
	rig.tap(5, 4)
	assert (clip(rig).loop_start, clip(rig).loop_end) == (8 * q, 16 * q)


def test_mute_shift_and_loop_block_deletes_its_notes(seq_rig):
	rig = seq_rig
	q = stepseq(rig)._quantization
	add_note(rig, 0.0)
	add_note(rig, 8 * q)
	rig.press_side(MUTE_SHIFT)
	rig.press(4, 4)
	rig.press(4, 4)  # both loop points on block 0
	rig.release(4, 4)
	rig.release_side(MUTE_SHIFT)
	assert [n[1] for n in clip(rig).note_tuples()] == [8 * q]
	assert clip(rig).deprecated_calls == []


def test_mute_shift_and_pad_mutes_a_note(seq_rig):
	rig = seq_rig
	add_note(rig, 0.0)
	rig.press_side(MUTE_SHIFT)
	rig.tap(0, 0)
	rig.release_side(MUTE_SHIFT)
	assert any(n[4] for n in clip(rig).note_tuples())
	assert clip(rig).deprecated_calls == []


def test_mode_button_switches_to_multinote(seq_rig):
	rig = seq_rig
	rig.tap_side(MODE)
	rig.tick()
	assert stepseq(rig)._mode != 1


def test_multinote_mode_edits_several_pitches(seq_rig):
	rig = seq_rig
	rig.tap_side(MODE)
	rig.tick()
	rig.tap(0, 0)
	rig.tap(0, 6)
	pitches = sorted(set(n[0] for n in clip(rig).note_tuples()))
	assert len(pitches) == 2
	assert clip(rig).deprecated_calls == []


def test_scale_button_enters_scale_edit_and_leaves(seq_rig):
	rig = seq_rig
	rig.press_side(0)
	rig.tick()
	assert stepseq(rig)._mode == 10  # STEPSEQ_MODE_SCALE_EDIT
	rig.release_side(0)
	rig.tick()


def test_arrows_select_tracks_and_scenes(make_rig):
	rig = make_rig(song=make_song(clips=[(0, 0), (1, 0)]))
	rig.tap_top(TOP["user"])
	rig.tap_top(TOP["right"])
	rig.tick()
	assert rig.song.view.selected_track is rig.song.tracks[1]
	assert stepseq(rig)._clip is clip(rig, 1, 0)
	rig.tap_top(TOP["down"])
	assert rig.song.view.selected_scene is rig.song.scenes[1]


def test_lock_button_keeps_the_clip(make_rig):
	rig = make_rig(song=make_song(clips=[(0, 0), (1, 0)]))
	rig.tap_top(TOP["user"])
	rig.tick()
	rig.tap_side(7)
	rig.tick()
	rig.song.view.selected_track = rig.song.tracks[1]
	rig.tick()
	assert stepseq(rig)._clip is clip(rig, 0, 0)


def test_playhead_moves_with_the_clip(seq_rig):
	rig = seq_rig
	rig.tap_top(TOP["session"])
	rig.tap(0, 0)
	rig.tap_top(TOP["user"])
	rig.song.advance(1.0)
	rig.tick()
	assert editor(rig)._playhead is not None
