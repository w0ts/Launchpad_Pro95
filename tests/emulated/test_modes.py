"""Every mode of Launchpad_Pro95: the buttons that select it, the layout it asks the
Launchpad Pro for, and how pressing its button again behaves."""

import pytest
from harness.devices import LIVE_LAYOUT_COMMAND, STANDALONE_LAYOUT_COMMAND
from harness.rig import BOTTOM, TOP, make_song

SESSION_LAYOUT, DRUM_LAYOUT, NOTE_LAYOUT, USER_LAYOUT, FADER_LAYOUT = 0, 1, 2, 3, 5

BOTTOM_MODES = [
    ("record_arm", "record_arm_mode", SESSION_LAYOUT),
    ("track_select", "track_select_mode", SESSION_LAYOUT),
    ("mute", "mute_mode", SESSION_LAYOUT),
    ("solo", "solo_mode", SESSION_LAYOUT),
    ("volume", "volume_mode", FADER_LAYOUT),
    ("pan", "pan_mode", FADER_LAYOUT),
    ("sends", "sends_mode", FADER_LAYOUT),
    ("stop_clip", "stop_clip_mode", SESSION_LAYOUT),
]


def layouts_sent(rig):
    return [
        (body[0], body[1])
        for body in rig.device.sysex_commands
        if body[0] in (LIVE_LAYOUT_COMMAND, STANDALONE_LAYOUT_COMMAND)
    ]


@pytest.mark.parametrize("button, mode, layout", BOTTOM_MODES, ids=[m[1] for m in BOTTOM_MODES])
def test_bottom_buttons_select_their_mode_and_layout(rig, button, mode, layout):
    rig.tap_bottom(BOTTOM[button])
    rig.tick()
    assert rig.mode == mode
    assert rig.device.live_layout == layout


@pytest.mark.parametrize("button, mode, layout", BOTTOM_MODES, ids=[m[1] for m in BOTTOM_MODES])
def test_bottom_mode_button_again_returns_to_session(rig, button, mode, layout):
    rig.tap_bottom(BOTTOM[button])
    rig.tap_bottom(BOTTOM[button])
    rig.tick()
    assert rig.mode == "session_mode"


@pytest.mark.parametrize("button, mode, layout", BOTTOM_MODES, ids=[m[1] for m in BOTTOM_MODES])
def test_bottom_mode_button_is_lit_in_its_mode(rig, button, mode, layout):
    rig.tap_bottom(BOTTOM[button])
    rig.tick()
    assert rig.device.bottom_led(BOTTOM[button]).value not in (None, 0)


def test_holding_session_again_shows_the_overview_until_released(rig):
    rig.press_top(TOP["session"])
    rig.tick()
    assert rig.mode == "session_zooming_mode"
    rig.release_top(TOP["session"])
    rig.tick()
    assert rig.mode == "session_mode"


def test_holding_session_in_a_mixer_mode_shows_the_overview(rig):
    rig.tap_bottom(BOTTOM["mute"])
    rig.press_top(TOP["session"])
    rig.tick()
    assert rig.surface._session_zooming_manager.is_enabled()
    rig.release_top(TOP["session"])


def test_note_button_selects_the_instrument(rig):
    rig.tap_top(TOP["note"])
    rig.tick()
    assert rig.mode == "note_mode"
    assert rig.surface._instrument_component.is_enabled()
    assert rig.device.standalone_layout == USER_LAYOUT


def test_note_button_on_a_midi_track_is_note_mode(rig):
    rig.tap_top(TOP["note"])
    rig.tick()
    assert rig.surface._instrument_component.get_mode() == "note_mode"


def test_note_button_on_an_audio_track_is_audio_mode(make_rig):
    song = make_song(midi_tracks=(1,))
    rig = make_rig(song=song)
    rig.tap_top(TOP["note"])
    rig.tick()
    assert rig.surface._instrument_component.get_mode() == "audio_mode"


def test_note_button_again_toggles_the_detail_view(rig):
    view = rig.application.view
    rig.tap_top(TOP["note"])
    before = view.is_view_visible("Detail/Clip")
    rig.tap_top(TOP["note"])
    assert view.is_view_visible("Detail/Clip") != before


def test_device_button_selects_the_device_mode(rig):
    rig.tap_top(TOP["device"])
    rig.tick()
    assert rig.mode == "device_mode"
    assert rig.surface._device.is_enabled()
    assert rig.device.standalone_layout == DRUM_LAYOUT


def test_user_button_starts_with_the_drum_step_sequencer(rig):
    rig.tap_top(TOP["user"])
    rig.tick()
    assert rig.mode == "user_mode"
    assert rig.surface._user_button_modes.selected_mode == "stepsequencer_mode"
    assert rig.surface._step_sequencer.is_enabled()
    assert not rig.surface._step_sequencer2.is_enabled()


def test_user_button_cycles_the_sequencers_and_user_mode(rig):
    rig.tap_top(TOP["user"])
    rig.tap_top(TOP["user"])
    rig.tick()
    assert rig.surface._user_button_modes.selected_mode == "stepsequencer2_mode"
    assert rig.surface._step_sequencer2.is_enabled()
    assert not rig.surface._step_sequencer.is_enabled()
    assert "melodic step sequencer" in rig.messages
    rig.tap_top(TOP["user"])
    rig.tick()
    assert rig.surface._user_button_modes.selected_mode == "user_mode"
    assert not rig.surface._step_sequencer.is_enabled()
    assert not rig.surface._step_sequencer2.is_enabled()
    assert layouts_sent(rig)[-1] == (LIVE_LAYOUT_COMMAND, USER_LAYOUT)
    rig.tap_top(TOP["user"])
    assert rig.surface._user_button_modes.selected_mode == "stepsequencer_mode"


def test_user_mode_disables_session_recording(rig):
    rig.tap_top(TOP["user"])
    assert not rig.surface._session_record.is_enabled()
    rig.tap_top(TOP["session"])
    assert rig.surface._session_record.is_enabled()


@pytest.mark.parametrize("top", ["note", "device", "user"])
def test_leaving_a_mode_for_session_sends_the_session_layout(rig, top):
    rig.tap_top(TOP[top])
    rig.tick()
    rig.tap_top(TOP["session"])
    rig.tick()
    assert rig.mode == "session_mode"
    assert layouts_sent(rig)[-1] == (LIVE_LAYOUT_COMMAND, SESSION_LAYOUT)


def test_every_mode_and_back_logs_no_errors(rig):
    for button in ("note", "device", "user", "user", "user", "session"):
        rig.tap_top(TOP[button])
        rig.tick()
    for button, _mode, _layout in BOTTOM_MODES:
        rig.tap_bottom(BOTTOM[button])
        rig.tick()
    problems = [line for line in rig.log if "Traceback" in line or "rror" in line or "xception" in line]
    assert problems == []
