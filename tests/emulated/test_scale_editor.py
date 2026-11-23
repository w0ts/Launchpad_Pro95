"""The scale editor (scale button held in the drum step sequencer). Top row: absolute root,
(unused), the layout modes and drum rack; second and third rows: the keys as on a piano, with
relative scale, circle of fifths and quick scale on the free pads; fourth row: the octave;
the four bottom rows: the scales."""

import pytest
from harness.rig import TOP, make_song

SCALE = 0


@pytest.fixture
def scale_rig(make_rig):
    rig = make_rig(song=make_song(clips=[(0, 0)]))
    rig.tap_top(TOP["user"])
    rig.tick(2)
    rig.press_side(SCALE)
    rig.tick()
    return rig


def scale(rig):
    return rig.surface._step_sequencer._scale_component


def led(rig, x, y):
    return rig.device.grid_led(x, y).static


def color(rig, key):
    return int(rig.surface._skin[key])


@pytest.mark.parametrize(
    "x, y, key, name",
    [(0, 2, 0, "C"), (1, 2, 2, "D"), (6, 2, 11, "B"), (0, 1, 1, "C#"), (5, 1, 10, "A#")],
)
def test_key_pads_select_the_root(scale_rig, x, y, key, name):
    rig = scale_rig
    rig.tap(x, y)
    rig.tick()
    assert scale(rig)._key == key
    assert f"root {name}" in rig.messages
    assert led(rig, x, y) == color(rig, "Scale.Key.On")


def test_circle_of_fifths_pads(scale_rig):
    rig = scale_rig
    rig.tap(7, 2)
    assert scale(rig)._key == 7  # C -> G
    assert "circle of 5ths -> C Major => G Major" in rig.messages
    rig.tap(6, 1)
    rig.tap(6, 1)
    assert scale(rig)._key == 5  # G -> C -> F


def test_relative_scale_pad_switches_major_and_minor(scale_rig):
    rig = scale_rig
    rig.tap(2, 1)
    assert (scale(rig)._key, scale(rig)._modus) == (9, 1)  # A minor
    assert "Relative scale : A Minor" in rig.messages
    rig.tap(2, 1)
    assert (scale(rig)._key, scale(rig)._modus) == (0, 0)


def test_scale_pads_select_the_scale(scale_rig):
    rig = scale_rig
    rig.tap(3, 5)  # (5 - 4) * 8 + 3
    rig.tick()
    assert scale(rig)._modus == 11
    assert "mode : Minor Pentatonic" in rig.messages
    assert led(rig, 3, 5) == color(rig, "Scale.Modus.On")
    assert led(rig, 0, 4) == color(rig, "Scale.Modus.Off")


def test_octave_pads(scale_rig):
    rig = scale_rig
    rig.tap(5, 3)
    rig.tick()
    assert scale(rig)._octave == 5
    assert led(rig, 5, 3) == color(rig, "Scale.Octave.On")


@pytest.mark.parametrize(
    "x, mode, message",
    [
        (2, "chromatic_gtr", "mode: chromatic gtr"),
        (3, "diatonic_ns", "mode: diatonic not staggered"),
        (4, "diatonic_chords", "mode: diatonic vertical (chords)"),
        (5, "diatonic", "mode: diatonic"),
        (6, "chromatic", "mode: chromatic"),
    ],
)
def test_layout_pads(scale_rig, x, mode, message):
    rig = scale_rig
    rig.tap(x, 0)
    rig.tick()
    assert scale(rig)._mode == mode and not scale(rig).is_drumrack
    assert message in rig.messages
    if x == 2:
        # this pad is turned on after its colour is set: it shows the pad's own on colour
        assert led(rig, x, 0) not in (color(rig, "Scale.Mode.On"), color(rig, "Scale.Mode.Off"))
    else:
        assert led(rig, x, 0) == color(rig, "Scale.Mode.On")


def test_absolute_root_pad_toggles(scale_rig):
    rig = scale_rig
    rig.tap(0, 0)
    rig.tick()
    assert scale(rig)._is_absolute and "absolute root" in rig.messages
    assert led(rig, 0, 0) == color(rig, "Scale.AbsoluteRoot.On")
    rig.tap(0, 0)
    assert not scale(rig)._is_absolute and "relative root" in rig.messages


def test_drum_rack_pad_disables_the_key_and_scale_pads(scale_rig):
    rig = scale_rig
    rig.tap(7, 0)
    rig.tick()
    assert scale(rig).is_drumrack and "mode: drumrack" in rig.messages
    for x, y in ((0, 1), (0, 2), (0, 4), (7, 7)):
        assert led(rig, x, y) == color(rig, "DefaultButton.Disabled")
    key, modus = scale(rig)._key, scale(rig)._modus
    rig.tap(1, 2)
    rig.tap(1, 4)
    rig.tap(0, 0)
    assert (scale(rig)._key, scale(rig)._modus, scale(rig)._is_absolute) == (key, modus, False)


def test_quick_scale_pads_toggle_the_keys(scale_rig):
    rig = scale_rig
    rig.tap(7, 1)
    rig.tick()
    assert scale(rig)._custom_scale and "Quick scale : ON" in rig.messages
    rig.tap(1, 2)  # D off
    rig.tap(0, 1)  # C# off
    rig.tick()
    assert scale(rig)._custom_keys[2] is False and scale(rig)._custom_keys[1] is False
    assert led(rig, 1, 2) == color(rig, "Scale.Key.Off")
    assert led(rig, 2, 2) == color(rig, "Scale.Key.On")
    assert led(rig, 7, 1) == color(rig, "Scale.QuickScale.On")
    assert led(rig, 0, 4) == color(rig, "DefaultButton.Disabled")
    assert 2 not in scale(rig).get_pattern().scale
    rig.tap(7, 1)
    assert not scale(rig)._custom_scale and "Quick scale : OFF" in rig.messages


def test_last_scale_row_is_dark_past_the_last_scale(scale_rig):
    rig = scale_rig
    rig.tick()
    count = len(scale(rig)._modus_list)
    for x in range(8):
        wanted = "DefaultButton.Disabled" if x + 24 > count else "Scale.Modus.Off"
        assert led(rig, x, 7) == color(rig, wanted), x
