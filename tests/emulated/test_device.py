"""Device mode: each grid column is a slider for one parameter of the selected device
(bottom pad = minimum, top pad = maximum). Arrows: left/right = track, up/down = device.
Scene buttons, top first: on/off, bank down, bank up, precision, lock 1-4."""
import Live
import pytest

from harness.rig import TOP, make_song

ON_OFF, PREV_BANK, NEXT_BANK, PRECISION, LOCK1 = 0, 1, 2, 3, 4


def device_song():
	song = make_song()
	for index in (0, 1):
		track = song.tracks[index]
		devices = (Live.Device.Device(name="Synth%d" % index, class_name="TestSynth", num_parameters=16),
			Live.Device.Device(name="Fx%d" % index, class_name="TestFx", num_parameters=8))
		track.devices = devices
		for device in devices:
			device.canonical_parent = track
		track.view.selected_device = devices[0]
	song.appointed_device = song.tracks[0].devices[0]
	return song


@pytest.fixture
def device_rig(make_rig):
	rig = make_rig(song=device_song())
	rig.tap_top(TOP["device"])
	rig.tick(2)
	return rig


def component(rig):
	return rig.surface._device


def test_device_mode_controls_the_selected_device(device_rig):
	assert component(device_rig)._device is device_rig.song.tracks[0].devices[0]


def test_top_pad_of_a_column_sets_the_parameter_to_maximum(device_rig):
	rig = device_rig
	parameter = rig.song.tracks[0].devices[0].parameters[1]
	rig.tap(0, 0)
	rig.tick()
	assert parameter.value == pytest.approx(parameter.max)
	rig.tap(0, 7)
	rig.tick()
	assert parameter.value == pytest.approx(parameter.min)


def test_parameter_value_lights_the_column(device_rig):
	rig = device_rig
	parameter = rig.song.tracks[0].devices[0].parameters[2]
	parameter.value = parameter.max
	rig.tick(2)
	column = [rig.device.led(1, y) for y in range(8)]
	assert len(set(column)) == 1 and column[0] not in (None, 0)


def test_right_arrow_selects_the_next_track_and_its_device(device_rig):
	rig = device_rig
	rig.tap_top(TOP["right"])
	rig.tick()
	assert rig.song.view.selected_track is rig.song.tracks[1]
	assert component(rig)._device is rig.song.tracks[1].devices[0]


def test_down_arrow_selects_the_next_device(device_rig):
	rig = device_rig
	rig.tap_top(TOP["down"])
	rig.tick()
	assert rig.song.appointed_device is rig.song.tracks[0].devices[1]


def test_next_bank_button_moves_to_the_next_parameters(device_rig):
	rig = device_rig
	rig.tap_side(NEXT_BANK)
	rig.tick()
	assert component(rig)._bank_index == 1


def test_on_off_button_toggles_the_device(device_rig):
	rig = device_rig
	on_off = rig.song.tracks[0].devices[0].parameters[0]
	rig.tap_side(ON_OFF)
	assert on_off.value == 0.0


def test_lock_button_keeps_the_device_when_the_track_changes(device_rig):
	rig = device_rig
	rig.press_side(LOCK1)
	rig.wait(1.0)  # a long press stores the device in the lock slot
	rig.release_side(LOCK1)
	rig.tick()
	rig.song.view.selected_track = rig.song.tracks[1]
	rig.tick()
	assert component(rig)._device is rig.song.tracks[0].devices[0]


def test_no_device_leaves_the_grid_dark(make_rig):
	rig = make_rig()
	rig.tap_top(TOP["device"])
	rig.tick(2)
	assert component(rig)._device is None
	assert all(value in (None, 0) for row in rig.device.grid_values() for value in row)
