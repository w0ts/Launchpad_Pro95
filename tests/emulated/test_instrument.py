"""Note button: instrument mode. On a MIDI track the grid plays the notes of a scale layout
(note mode), on a track with a drum rack it plays the drum pads (drum mode), on an audio
track it is dark (audio mode). Scene buttons, top first: scale (hold), octave up, octave
down, -, mute (drum), solo (drum), play clip, stop clip."""

import Live
from harness.rig import TOP, make_song

SCALE, UP, DOWN, MUTE, SOLO, PLAY, STOP = 0, 1, 2, 4, 5, 6, 7


def instrument(rig):
    return rig.surface._instrument_component


def drum_song():
    song = make_song(clips=[(0, 0)])
    rack = Live.RackDevice.RackDevice(name="Drums", drum=True)
    rack.canonical_parent = song.tracks[0]
    song.tracks[0].devices = (rack,)
    return song


def enter(rig):
    rig.tap_top(TOP["note"])
    rig.tick(2)
    return rig


def test_note_mode_pads_play_notes_on_the_track(rig):
    enter(rig)
    assert instrument(rig).get_mode() == "note_mode"
    assert rig.press(0, 7) == "track"
    status, note, velocity = rig.track_input[-1]
    assert status & 0xF0 == 0x90 and velocity == 127
    rig.release(0, 7)


def test_note_mode_pads_rise_to_the_right_and_up(rig):
    enter(rig)
    rig.press(0, 7)
    rig.press(1, 7)
    rig.press(0, 6)
    low, right, up = [m[1] for m in rig.track_input[-3:]]
    assert low < right and low < up


def test_note_mode_arms_the_selected_track_implicitly(rig):
    enter(rig)
    assert rig.song.tracks[0].implicit_arm
    assert rig.c_instance.controlled_track is rig.song.tracks[0]


def test_leaving_note_mode_releases_the_implicit_arm(rig):
    enter(rig)
    rig.tap_top(TOP["session"])
    rig.tick()
    assert not rig.song.tracks[0].implicit_arm


def test_octave_up_raises_the_pads(rig):
    enter(rig)
    rig.press(0, 7)
    before = rig.track_input[-1][1]
    rig.release(0, 7)
    rig.tap_side(UP)
    rig.tick()
    rig.press(0, 7)
    assert rig.track_input[-1][1] == before + 12


def test_holding_scale_shows_the_scale_editor(rig):
    enter(rig)
    rig.press_side(SCALE)
    rig.tick()
    assert instrument(rig).get_mode() == "scale_mode"
    rig.release_side(SCALE)
    rig.tick()
    assert instrument(rig).get_mode() == "note_mode"


def test_root_pads_are_lit(rig):
    enter(rig)
    rig.tick()
    values = [value for row in rig.device.grid_values() for value in row]
    assert len(set(values)) > 1


def test_arrows_select_tracks(rig):
    enter(rig)
    rig.tap_top(TOP["right"])
    rig.tick()
    assert rig.song.view.selected_track is rig.song.tracks[1]
    assert rig.song.tracks[1].implicit_arm


def test_play_and_stop_buttons(make_rig):
    rig = enter(make_rig(song=make_song(clips=[(0, 0)])))
    rig.tap_side(PLAY)
    assert rig.song.tracks[0].clip_slots[0].fire_count == 1
    rig.tap_side(STOP)
    assert rig.song.tracks[0].fired_slot_index == -2


def test_drum_rack_track_is_drum_mode(make_rig):
    rig = enter(make_rig(song=drum_song()))
    assert instrument(rig).get_mode() == "drum_mode"
    assert rig.surface._drum_group._drum_group_device is rig.song.tracks[0].devices[0]


def test_drum_pads_play_the_rack_notes(make_rig):
    rig = enter(make_rig(song=drum_song()))
    assert rig.press(0, 7) == "track"
    assert rig.track_input[-1][1] == 36
    rig.release(0, 7)


def test_drum_mode_mute_button_and_pad_mutes_the_drum_pad(make_rig):
    rig = enter(make_rig(song=drum_song()))
    rig.press_side(MUTE)
    rig.tap(0, 7)
    rig.release_side(MUTE)
    assert rig.song.tracks[0].devices[0].drum_pads[36].mute


def test_audio_track_is_audio_mode_and_dark(make_rig):
    rig = enter(make_rig(song=make_song(midi_tracks=(1,))))
    assert instrument(rig).get_mode() == "audio_mode"
    rig.tick()
    assert all(value in (None, 0) for row in rig.device.grid_values() for value in row)
