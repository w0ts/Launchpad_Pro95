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
        devices = (
            Live.Device.Device(name=f"Synth{index}", class_name="TestSynth", num_parameters=16),
            Live.Device.Device(name=f"Fx{index}", class_name="TestFx", num_parameters=8),
        )
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


def _song_with_enum(values):
    song = device_song()
    device = song.tracks[0].devices[0]
    params = list(device.parameters)
    params[1] = Live.DeviceParameter.DeviceParameter(
        name="Enum", value=float(values - 1), min=0.0, max=float(values - 1), is_quantized=True
    )
    device.parameters = tuple(params)
    return song


def test_nine_value_enum_is_a_big_enum(make_rig):
    """9 values do not fit the 8 pads of a column: it must not be drawn as a small enum."""
    rig = make_rig(song=_song_with_enum(9))
    rig.tap_top(TOP["device"])
    rig.tick(2)
    parameter = rig.song.tracks[0].devices[0].parameters[1]
    rig.tap(0, 4)  # big enum: pad 3 from the bottom steps down by one
    assert parameter.value == 7.0


def test_eight_value_enum_has_one_pad_per_value(make_rig):
    rig = make_rig(song=_song_with_enum(8))
    rig.tap_top(TOP["device"])
    rig.tick(2)
    parameter = rig.song.tracks[0].devices[0].parameters[1]
    rig.tap(0, 5)  # third pad from the bottom
    assert parameter.value == 2.0


def test_strip_without_parameter_is_not_quantized(framework):
    from Launchpad_Pro95.DeviceControllerStrip import DeviceControllerStrip

    class NoParameter:
        _parameter_to_map_to = None

    assert DeviceControllerStrip._is_quantized.fget(NoParameter()) is False


def test_device_inside_a_rack_does_not_break_the_device_buttons(make_rig):
    """A device in a rack chain is not in track.devices: selected_device_idx is None."""
    song = make_song()
    inner = Live.Device.Device(name="Inner", class_name="TestSynth", num_parameters=8)
    rack = Live.RackDevice.RackDevice(name="Rack", chains=(Live.Chain.Chain(devices=(inner,)),))
    rack.canonical_parent = song.tracks[0]
    song.tracks[0].devices = (rack,)
    song.tracks[0].view.selected_device = inner
    song.appointed_device = inner
    rig = make_rig(song=song)
    rig.tap_top(TOP["device"])
    rig.tick(2)
    assert component(rig)._device is inner
    rig.tap_top(TOP["up"])
    rig.tap_top(TOP["down"])
    rig.tick()


@pytest.mark.parametrize("which", ["return", "master"])
def test_device_mode_with_a_return_or_master_track_selected(make_rig, which):
    rig = make_rig(song=device_song())
    song = rig.song
    song.view.selected_track = song.return_tracks[0] if which == "return" else song.master_track
    rig.tick()
    rig.tap_top(TOP["device"])
    rig.tick(2)
    rig.tap_top(TOP["left"])
    rig.tap_top(TOP["right"])
    rig.tick()


def long_press(rig, index):
    rig.press_side(index)
    rig.wait(1.0)
    rig.release_side(index)
    rig.tick()


def test_lock_buttons_store_lock_unlock_and_remove(device_rig):
    rig = device_rig
    synth = rig.song.tracks[0].devices[0]
    long_press(rig, LOCK1)
    assert component(rig)._locked_devices[0] is synth
    assert " '1-MIDI - Synth0' stored into lock button 1" in rig.messages
    long_press(rig, LOCK1 + 1)  # the same device in a second slot
    assert component(rig)._locked_devices[1] is None
    assert any("is already stored in lock button 1 ! aborting." in m for m in rig.messages)
    rig.tap_side(LOCK1)  # locked: a tap unlocks
    assert component(rig)._locked_device_index is None
    assert any(m.startswith("unlocked from ' ") for m in rig.messages)
    rig.song.view.selected_track = rig.song.tracks[1]
    rig.tick()
    rig.tap_side(LOCK1)  # a tap locks to the stored device again
    assert component(rig)._locked_device_index == 0 and component(rig)._device is synth
    assert any(m.startswith("locked to '1-MIDI - Synth0") for m in rig.messages)
    long_press(rig, LOCK1)  # removes the stored device
    assert component(rig)._locked_devices[0] is None
    assert any(m.startswith("removing '1-MIDI - Synth0' from block button 1") for m in rig.messages)


def test_lock_button_without_a_stored_device_does_nothing(device_rig):
    rig = device_rig
    rig.tap_side(LOCK1 + 3)
    assert component(rig)._locked_device_index is None
    assert component(rig)._locked_devices == [None] * 4
