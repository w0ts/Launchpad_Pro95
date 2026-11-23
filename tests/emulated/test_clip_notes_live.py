"""ClipNotes against the fake Live clip (note ids, deprecated-call recording), and the step
sequencer editing a clip that holds notes before time 0."""

import Live
from harness.rig import TOP, make_song


def notes_before_zero_song():
    song = make_song()
    clip = Live.Clip.Clip(length=4.0, notes=[(36, -1.0, 0.25, 100, False), (38, 1.0, 0.25, 90, False)])
    clip.loop_start = -2.0  # a loop that starts before 0 can hold notes at negative times
    song.tracks[0].clip_slots[0].set_clip(clip)
    return song


def test_write_all_notes_keeps_notes_before_zero_once(framework):
    from Launchpad_Pro95.ClipNotes import read_all_notes, write_all_notes

    clip = notes_before_zero_song().tracks[0].clip_slots[0].clip
    notes = read_all_notes(clip)
    write_all_notes(clip, notes)
    write_all_notes(clip, notes)
    assert sorted(read_all_notes(clip)) == sorted(notes)
    assert clip.deprecated_calls == []


def test_step_sequencer_edit_keeps_the_note_before_zero(make_rig):
    rig = make_rig(song=notes_before_zero_song())
    rig.tap_top(TOP["user"])
    rig.tick(2)
    clip = rig.song.tracks[0].clip_slots[0].clip
    rig.tap(0, 0)
    rig.tap(1, 0)
    early = [n for n in clip.note_tuples() if n[1] < 0]
    assert early == [(36, -1.0, 0.25, 100.0, False)]
    assert clip.deprecated_calls == []


def test_clip_actions_delete_pitch_removes_only_that_pitch_in_the_loop(make_rig):
    song = make_song()
    clip = Live.Clip.Clip(
        length=4.0, notes=[(36, 0.0, 0.25, 100, False), (36, 5.0, 0.25, 100, False), (38, 1.0, 0.25, 100, False)]
    )
    song.tracks[0].clip_slots[0].set_clip(clip)
    rig = make_rig(song=song)
    rig.tap(0, 0)
    rig.song.advance(1.0)  # the clip plays: it is the clip the actions work on
    actions = rig.surface._clip_actions_component
    actions.use_selected_track(True)
    actions.delete_pitch(36)
    assert clip.note_tuples() == ((38, 1.0, 0.25, 100.0, False), (36, 5.0, 0.25, 100.0, False))
    assert clip.deprecated_calls == []


def test_melodic_sequencer_never_uses_the_deprecated_calls(make_rig):
    rig = make_rig(song=notes_before_zero_song())
    rig.tap_top(TOP["user"])
    rig.tap_top(TOP["user"])
    rig.tick(2)
    rig.tap(0, 6)
    assert rig.song.tracks[0].clip_slots[0].clip.deprecated_calls == []
