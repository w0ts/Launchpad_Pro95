"""Mixer modes (bottom buttons). Arm, track select, mute, solo and stop: the bottom grid row
acts on the 8 tracks of the session box while the rest stays the session. Volume, pan and
sends: the Launchpad Pro shows 8 faders (CC 21..28) mapped to the tracks."""
import pytest

from harness.devices import FADER_SETUP_COMMAND
from harness.rig import BOTTOM, make_song

ROW = 7  # the bottom grid row


def tracks(rig):
	return rig.song.tracks


@pytest.mark.parametrize("mode, attribute", [("mute", "mute"), ("solo", "solo"), ("record_arm", "arm")])
def test_bottom_row_toggles_the_track(rig, mode, attribute):
	rig.tap_bottom(BOTTOM[mode])
	rig.tick()
	before = getattr(tracks(rig)[3], attribute)
	rig.tap(3, ROW)
	assert getattr(tracks(rig)[3], attribute) != before


def test_mute_row_lights_follow_live(rig):
	rig.tap_bottom(BOTTOM["mute"])
	rig.tick()
	before = rig.device.led(2, ROW)
	tracks(rig)[2].mute = True
	rig.tick()
	assert rig.device.led(2, ROW) != before


def test_track_select_row_selects_the_track(rig):
	rig.tap_bottom(BOTTOM["track_select"])
	rig.tap(5, ROW)
	assert rig.song.view.selected_track is tracks(rig)[5]


def test_other_rows_still_launch_clips_in_a_mixer_mode(make_rig):
	rig = make_rig(song=make_song(clips=[(1, 0)]))
	rig.tap_bottom(BOTTOM["mute"])
	rig.tap(1, 0)
	assert tracks(rig)[1].clip_slots[0].fire_count == 1


def test_record_arm_mode_pad_arms_and_launches(make_rig):
	rig = make_rig(song=make_song(clips=[(2, 0)]))
	rig.tap_bottom(BOTTOM["record_arm"])
	rig.tap(2, 0)
	assert tracks(rig)[2].arm
	assert rig.song.session_record


@pytest.mark.parametrize("mode", ["volume", "pan", "sends"])
def test_fader_modes_set_up_the_eight_faders(rig, mode):
	rig.tap_bottom(BOTTOM[mode])
	rig.tick()
	assert sorted(rig.device.fader_setups) == list(range(8))
	assert rig.device.commands(FADER_SETUP_COMMAND)


def test_volume_fader_moves_the_track_volume(rig):
	rig.tap_bottom(BOTTOM["volume"])
	rig.tick()
	assert rig.send(rig.device.fader_message(4, 0)) == "parameter"
	assert tracks(rig)[4].mixer_device.volume.value == 0.0
	rig.send(rig.device.fader_message(4, 127))
	assert tracks(rig)[4].mixer_device.volume.value == pytest.approx(1.0)


def test_pan_fader_moves_the_track_pan(rig):
	rig.tap_bottom(BOTTOM["pan"])
	rig.tick()
	rig.send(rig.device.fader_message(0, 0))
	assert tracks(rig)[0].mixer_device.panning.value == pytest.approx(-1.0)


def test_volume_fader_shows_the_track_volume(rig):
	tracks(rig)[1].mixer_device.volume.value = 1.0
	rig.tap_bottom(BOTTOM["volume"])
	rig.tick()
	kind, colour, value = rig.device.fader_setups[1]
	assert value == 127


def test_sends_mode_scene_buttons_select_the_send(rig):
	rig.tap_bottom(BOTTOM["sends"])
	rig.tick()
	rig.tap_side(1)  # send B
	rig.tick()
	rig.send(rig.device.fader_message(0, 127))
	assert tracks(rig)[0].mixer_device.sends[1].value == pytest.approx(1.0)
	assert tracks(rig)[0].mixer_device.sends[0].value == 0.0
