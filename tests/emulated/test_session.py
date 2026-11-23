"""Session mode: the 8x8 grid launches clips, the scene buttons launch scenes, the arrows
move the session box, and the left buttons modify a pad press (delete, duplicate,
double, quantize, shift = select)."""

import Live
from harness.rig import BOTTOM, LEFT, TOP, make_song


def slot(rig, track, scene):
    return rig.song.tracks[track].clip_slots[scene]


def test_pad_fires_its_clip(make_rig):
    rig = make_rig(song=make_song(clips=[(2, 1)]))
    rig.tap(2, 1)
    assert slot(rig, 2, 1).fire_count == 1
    rig.song.advance(1.0)
    rig.tick()
    assert slot(rig, 2, 1).is_playing


def test_clip_pad_shows_the_clip_colour(make_rig):
    from Launchpad_Pro95.Colors import CLIP_COLOR_TABLE

    rig = make_rig(song=make_song(clips=[(0, 0)]))
    rig.tick()
    assert rig.device.led(0, 0) == CLIP_COLOR_TABLE[Live.Clip.Clip().color]
    assert rig.device.led(1, 0) != rig.device.led(0, 0)


def test_playing_clip_pulses_or_flashes(make_rig):
    rig = make_rig(song=make_song(clips=[(0, 0)]))
    rig.tap(0, 0)
    rig.song.advance(1.0)
    rig.tick()
    led = rig.device.grid_led(0, 0)
    assert led.flash is not None or led.pulse is not None or led.static != 60


def test_scene_button_fires_the_scene(make_rig):
    rig = make_rig(song=make_song(clips=[(0, 2), (3, 2)]))
    rig.tap_side(2)
    assert rig.song.scenes[2].fire_count == 1
    assert slot(rig, 0, 2).fire_count == 1 and slot(rig, 3, 2).fire_count == 1


def test_arrows_move_the_session_box(make_rig):
    rig = make_rig(song=make_song(num_tracks=16, num_scenes=16))
    session = rig.surface._session
    rig.tap_top(TOP["right"])
    rig.tap_top(TOP["down"])
    assert (session.track_offset(), session.scene_offset()) == (1, 1)
    rig.tap_top(TOP["left"])
    rig.tap_top(TOP["up"])
    assert (session.track_offset(), session.scene_offset()) == (0, 0)


def test_session_box_is_highlighted_in_live(rig):
    assert rig.c_instance.session_highlight[:4] == (0, 0, 8, 8)


def test_delete_and_pad_deletes_the_clip(make_rig):
    rig = make_rig(song=make_song(clips=[(1, 1)]))
    rig.press_left(LEFT["delete"])
    rig.tap(1, 1)
    rig.release_left(LEFT["delete"])
    assert not slot(rig, 1, 1).has_clip
    assert slot(rig, 1, 1).fire_count == 0


def test_shift_and_pad_selects_the_clip_without_firing(make_rig):
    rig = make_rig(song=make_song(clips=[(1, 1)]))
    rig.press_left(LEFT["shift"])
    rig.tap(1, 1)
    rig.release_left(LEFT["shift"])
    assert rig.song.view.highlighted_clip_slot is slot(rig, 1, 1)
    assert slot(rig, 1, 1).fire_count == 0


def test_double_and_pad_doubles_the_loop(make_rig):
    song = make_song(clips=[(0, 0)])
    song.tracks[0].clip_slots[0].clip.add_new_notes(
        (Live.Clip.MidiNoteSpecification(pitch=60, start_time=1.0, duration=0.5, velocity=100),)
    )
    rig = make_rig(song=song)
    rig.press_left(LEFT["double"])
    rig.tap(0, 0)
    rig.release_left(LEFT["double"])
    clip = slot(rig, 0, 0).clip
    assert clip.length == 8.0
    assert [n[1] for n in clip.note_tuples()] == [1.0, 5.0]


def test_duplicate_copies_then_pastes_a_clip(make_rig):
    rig = make_rig(song=make_song(clips=[(0, 0)]))
    rig.press_left(LEFT["duplicate"])
    rig.tap(0, 0)
    rig.tap(2, 3)
    rig.release_left(LEFT["duplicate"])
    assert "clip copied" in rig.messages and "clip pasted" in rig.messages
    assert slot(rig, 2, 3).has_clip


def test_duplicate_and_scene_button_duplicates_the_scene(make_rig):
    rig = make_rig(song=make_song(clips=[(0, 0)]))
    rig.press_left(LEFT["duplicate"])
    rig.tap_side(0)
    rig.release_left(LEFT["duplicate"])
    assert len(rig.song.scenes) == 9
    assert slot(rig, 0, 1).has_clip


def test_delete_and_scene_button_deletes_the_scene(rig):
    rig.press_left(LEFT["delete"])
    rig.tap_side(3)
    rig.release_left(LEFT["delete"])
    assert len(rig.song.scenes) == 7


def test_quantize_and_pad_quantizes_the_clip(make_rig):
    rig = make_rig(song=make_song(clips=[(0, 0)]))
    rig.press_left(LEFT["quantize"])
    rig.tap(0, 0)
    rig.release_left(LEFT["quantize"])
    assert hasattr(slot(rig, 0, 0).clip, "quantized_with")


def test_record_button_toggles_session_record(rig):
    rig.tap_left(LEFT["record"])
    assert rig.song.session_record


def test_undo_and_click_buttons(rig):
    rig.song.can_undo = True
    rig.tap_left(LEFT["undo"])
    assert rig.song.undo_steps == ["undo"]
    rig.tap_left(LEFT["click"])
    assert rig.song.metronome


def test_stop_clip_mode_row_stops_a_track(make_rig):
    rig = make_rig(song=make_song(clips=[(4, 0)]))
    rig.tap(4, 0)
    rig.song.advance(1.0)
    rig.tap_bottom(BOTTOM["stop_clip"])
    rig.tick()
    rig.tap(4, 7)  # bottom row = stop buttons
    assert rig.song.tracks[4].fired_slot_index == -2


def test_stop_clip_mode_row_shows_stopped_and_playing_tracks(make_rig):
    rig = make_rig(song=make_song(clips=[(4, 0)]))
    rig.tap(4, 0)
    rig.song.advance(1.0)
    rig.tap_bottom(BOTTOM["stop_clip"])
    rig.tick()
    skin = rig.surface._skin
    assert rig.device.grid_led(4, 7).static == int(skin["Session.StopClip"])
    assert rig.device.grid_led(3, 7).static == int(skin["Session.StoppedClip"])


def test_stop_clip_mode_scene_button_stops_the_scene(make_rig):
    rig = make_rig(song=make_song(clips=[(1, 0), (2, 0)]))
    rig.tap_side(0)
    rig.song.advance(1.0)
    rig.tap_bottom(BOTTOM["stop_clip"])
    rig.tap_side(0)
    assert [rig.song.tracks[i].fired_slot_index for i in (1, 2)] == [-2, -2]


def test_stop_clip_mode_last_scene_button_stops_all(make_rig):
    rig = make_rig(song=make_song(clips=[(1, 0), (2, 3)]))
    rig.tap(1, 0)
    rig.tap(2, 3)
    rig.song.advance(1.0)
    rig.tap_bottom(BOTTOM["stop_clip"])
    rig.tap_side(7)
    assert [rig.song.tracks[i].fired_slot_index for i in (1, 2)] == [-2, -2]


def test_session_zoom_overview_pad_moves_the_box(make_rig):
    rig = make_rig(song=make_song(num_tracks=24, num_scenes=24))
    rig.press_top(TOP["session"])
    rig.tick()
    rig.tap(1, 1)  # second block of 8 tracks, second block of 8 scenes
    rig.release_top(TOP["session"])
    session = rig.surface._session
    assert (session.track_offset(), session.scene_offset()) == (8, 8)
