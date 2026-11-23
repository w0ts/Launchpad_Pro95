"""Known bugs of the script, not fixed yet (strict xfail: a fix makes the test pass, which
fails the run until the mark is removed). Each reason says where the bug is."""
import Live
import pytest

from harness.rig import TOP, make_song

VELOCITY, MUTE_SHIFT = 4, 6


def _drum_seq(make_rig, song=None):
	rig = make_rig(song=song or make_song(clips=[(0, 0)]))
	rig.tap_top(TOP["user"])
	rig.tick(2)
	return rig


def _melodic_seq(make_rig, song=None):
	rig = make_rig(song=song or make_song(clips=[(0, 0)]))
	rig.tap_top(TOP["user"])
	rig.tap_top(TOP["user"])
	rig.tick(2)
	return rig


def _clip(rig, track=0, scene=0):
	return rig.song.tracks[track].clip_slots[scene].clip


def _add(clip, pitch, start, duration=0.25, velocity=100):
	clip.add_new_notes((Live.Clip.MidiNoteSpecification(pitch=pitch, start_time=start, duration=duration,
		velocity=velocity, mute=False),))


def test_velocity_shift_edit_does_not_duplicate_the_note(make_rig):
	rig = _drum_seq(make_rig)
	rig.tap(0, 0)
	rig.press_side(VELOCITY)
	rig.tap(0, 0)
	rig.release_side(VELOCITY)
	notes = _clip(rig).note_tuples()
	assert len(notes) == 1 and notes[0][3] != 80  # the velocity changed (80: the default)


def test_mute_shift_edit_does_not_duplicate_the_note(make_rig):
	rig = _drum_seq(make_rig)
	rig.tap(0, 0)
	rig.press_side(MUTE_SHIFT)
	rig.tap(0, 0)
	rig.release_side(MUTE_SHIFT)
	notes = _clip(rig).note_tuples()
	assert len(notes) == 1 and notes[0][4] is True


def test_switching_slots_releases_the_old_slot_listener(make_rig):
	rig = _drum_seq(make_rig)
	old_slot = rig.song.tracks[0].clip_slots[0]
	seq = rig.surface._step_sequencer
	rig.song.view.selected_scene = rig.song.scenes[1]
	rig.tick()
	assert not old_slot.has_clip_has_listener(seq.on_clip_slot_has_clip_changed)


def test_loop_selector_sets_a_loop_after_the_current_one(make_rig):
	rig = _drum_seq(make_rig)
	q = rig.surface._step_sequencer._quantization
	rig.tap(6, 4)  # third loop block, past the 4-beat loop at 1/16
	rig.tap(6, 4)
	assert (_clip(rig).loop_start, _clip(rig).loop_end) == (16 * q, 24 * q)


def test_entering_the_melodic_sequencer_keeps_the_clip_loop(make_rig):
	rig = _melodic_seq(make_rig)
	assert (_clip(rig).loop_start, _clip(rig).loop_end) == (0.0, 4.0)


def test_reentering_the_melodic_sequencer_keeps_its_quantization(make_rig):
	rig = _melodic_seq(make_rig)
	rig.tap_side(3)  # quantization: 1/32
	before = (rig.surface._step_sequencer2._quantization, _clip(rig).loop_end)
	rig.tap_top(TOP["session"])
	rig.tap_top(TOP["user"])
	rig.tap_top(TOP["user"])
	rig.tick(2)
	assert (rig.surface._step_sequencer2._quantization, _clip(rig).loop_end) == before


def test_melodic_notes_have_a_length(make_rig):
	rig = _melodic_seq(make_rig)
	rig.tap(0, 6)
	assert _clip(rig).note_tuples()[0][2] > 0


def test_melodic_degrees_follow_the_major_scale(make_rig):
	rig = _melodic_seq(make_rig)
	rig.press_side(0)  # scale editor (C major), released: the sequencer takes the scale
	rig.tick()
	rig.release_side(0)
	rig.tick()
	keys = rig.surface._step_sequencer2._note_editor._key_indexes[:7]
	root = keys[0]
	assert [k - root for k in keys] == [0, 2, 4, 5, 7, 9, 11]


def test_melodic_sequencer_reads_long_clips(make_rig):
	rig = _melodic_seq(make_rig)
	clip = _clip(rig)
	clip.loop_end = clip.end_marker = 64.0
	_add(clip, 36, 40.0)  # step 160 at 1/16: the notes listener parses it
	assert rig.surface._step_sequencer2._note_editor._clip is clip


def test_entering_the_melodic_sequencer_keeps_the_clip_notes(make_rig):
	song = make_song(clips=[(0, 0)])
	clip = song.tracks[0].clip_slots[0].clip
	_add(clip, 36, 1.0)
	_add(clip, 40, 2.0, duration=0.5, velocity=90)
	before = clip.note_tuples()
	_melodic_seq(make_rig, song)
	assert clip.note_tuples() == before



def test_entering_and_leaving_the_sequencers_never_changes_the_clip(make_rig):
	song = make_song(clips=[(0, 0)])
	clip = song.tracks[0].clip_slots[0].clip
	_add(clip, 36, 0.5, duration=0.3, velocity=77)
	_add(clip, 37, 1.0)  # off the C major lanes
	clip.add_new_notes((Live.Clip.MidiNoteSpecification(pitch=40, start_time=2.0, duration=0.25,
		velocity=100, mute=True),))
	before = (clip.note_tuples(), clip.loop_start, clip.loop_end)
	rig = _drum_seq(make_rig, song)
	rig.tap_top(TOP["user"])  # melodic
	rig.tick(2)
	rig.tap_top(TOP["session"])
	rig.tap_top(TOP["user"])
	rig.tap_top(TOP["user"])
	rig.tick(2)
	rig.tap_top(TOP["session"])
	rig.tick()
	assert (clip.note_tuples(), clip.loop_start, clip.loop_end) == before

def test_melodic_edit_keeps_notes_before_zero(make_rig):
	song = make_song(clips=[(0, 0)])
	clip = song.tracks[0].clip_slots[0].clip
	clip.loop_start = -1.0
	_add(clip, 36, -1.0)
	rig = _melodic_seq(make_rig, song)
	rig.tap(2, 6)
	assert [n for n in clip.note_tuples() if n[1] < 0] != []


def test_melodic_pattern_octave_of_negative_index(framework):
	from Launchpad_Pro95.ScaleComponent import MelodicPattern

	pattern = MelodicPattern(steps=[1, 7], scale=[0, 2, 4, 5, 7, 9, 11], base_note=36, origin=[-1, 0])
	assert pattern.note(0, 0).index == 36 - 1  # one degree below C is B of the octave below


def test_target_track_starts_on_a_track_armed_before_boot(make_rig):
	song = make_song()
	song.tracks[2].arm = True
	rig = make_rig(song=song)
	target = rig.surface._target_track_component
	assert song.tracks[2] in target._armed_track_stack
	assert target.target_track is song.tracks[2]


def test_target_track_stack_is_per_instance(make_rig):
	first = make_rig()
	second = make_rig()
	assert first.surface._target_track_component._armed_track_stack is not \
		second.surface._target_track_component._armed_track_stack


def test_target_track_stack_drops_removed_tracks(rig):
	target = rig.surface._target_track_component
	target._armed_track_stack[:] = list(rig.song.tracks[:2])
	target._refresh_armed_track_stack([])
	assert target._armed_track_stack == []


def test_melodic_pattern_has_no_note_outside_the_midi_range(framework):
	from Launchpad_Pro95.ScaleComponent import MelodicPattern

	low = MelodicPattern(steps=[1, 3], scale=[0, 2, 4, 5, 7, 9, 11], base_note=-24, origin=[0, 0])
	assert low.note(0, 0).index is None and not low.note(0, 0).valid
	high = MelodicPattern(steps=[1, 3], scale=[0, 2, 4, 5, 7, 9, 11], base_note=120, origin=[0, 0])
	assert high.note(7, 0).index is None


@pytest.mark.parametrize("note", [0, 3, 4, 11, 12, 40, 127])
def test_note_selector_selects_low_notes(make_rig, note):
	selector = _drum_seq(make_rig).surface._step_sequencer._note_selector
	selector.set_key(5)
	selector.set_selected_note(note)
	assert selector._root_note + selector._offset == note


def test_extending_the_loop_copies_the_loop_not_the_clip_start(make_rig):
	rig = _drum_seq(make_rig)
	c = _clip(rig)
	c.loop_start = 2.0
	c.add_new_notes((Live.Clip.MidiNoteSpecification(pitch=36, start_time=2.0, duration=0.25, velocity=100, mute=False),
		Live.Clip.MidiNoteSpecification(pitch=40, start_time=0.5, duration=0.25, velocity=100, mute=False)))
	rig.tick()
	rig.press_side(VELOCITY)  # held: the new blocks get a copy of the loop
	rig.press(5, 4)  # block 1 (beats 2-4): the loop
	rig.press(6, 4)  # block 2 (beats 4-6)
	rig.release(6, 4)
	rig.release(5, 4)
	rig.release_side(VELOCITY)
	assert (c.loop_start, c.loop_end) == (2.0, 6.0)
	assert (36, 4.0) in [(n[0], n[1]) for n in c.note_tuples()]
	assert all(n[1] < 4.0 for n in c.note_tuples() if n[0] == 40)


@pytest.mark.parametrize("which", ["return", "master"])
def test_sequencer_arrows_with_a_return_or_master_track_selected(make_rig, which):
	rig = make_rig(song=make_song(clips=[(0, 0)]))
	song = rig.song
	song.view.selected_track = song.return_tracks[0] if which == "return" else song.master_track
	rig.tick()
	rig.tap_top(TOP["user"])
	rig.tick(2)
	for arrow in ("left", "right", "up", "down"):
		rig.tap_top(TOP[arrow])
	rig.tick()


def test_disabling_a_disabled_track_controller_keeps_the_implicit_arm(make_rig):
	rig = make_rig(song=make_song(clips=[(0, 0)]))
	controller = rig.surface._step_sequencer._track_controller
	controller.set_enabled(False)
	controller._implicit_arm = True
	track = rig.song.view.selected_track
	track.implicit_arm = True  # e.g. set by note mode
	controller.set_enabled(False)
	assert track.implicit_arm
