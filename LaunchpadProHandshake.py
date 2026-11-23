"""Identity and challenge handshake, layout sysex and sysex from the Launchpad Pro."""

import Live

from .consts import (
    CHALLENGE_PREFIX,
    FEEDBACK_CHANNELS,
    LIVE_MODE_SWITCH_REQUEST,
    NOTE_LAYOUT_SYSEX_BYTE,
    SYSEX_CHALLENGE_RESPONSE_BYTE,
    SYSEX_PARAM_BYTE_LAYOUT,
    SYSEX_STANDARD_PREFIX,
    SYSEX_STANDARD_SUFFIX,
    SYSEX_STATUS_BYTE_LAYOUT,
    SYSEX_STATUS_BYTE_MODE,
)


class LaunchpadProHandshakeMixin:
    """Layout switching and the sysex side of Launchpad_Pro95."""

    def _clear_send_cache(self):
        with self.component_guard():
            for control in self.controls:
                control.clear_send_cache()

    def _update_hardware(self):
        self._clear_send_cache()
        self.update()

    def _update_global_components(self):
        self._actions_component.update()
        self._session_record.update()
        self._modifier_background_component.update()

    def _layout_setup(self, mode, mode_type=SYSEX_PARAM_BYTE_LAYOUT):
        self._layout_switch(mode, mode_type)

        self._clear_send_cache()
        self._update_global_components()

    def _layout_switch(self, mode, mode_type=SYSEX_PARAM_BYTE_LAYOUT):
        prefix = SYSEX_STANDARD_PREFIX + mode_type
        suffix = SYSEX_STANDARD_SUFFIX
        self._send_midi(prefix + mode + suffix)
        self._last_sent_mode_byte = mode

    def port_settings_changed(self):
        self.set_highlighting_session_component(None)
        super().port_settings_changed()

    def on_identified(self):
        self._send_challenge()

    def _send_challenge(self):
        challenge_bytes = []
        for index in range(4):
            challenge_bytes.append(self._challenge >> 8 * index & 127)

        challenge = CHALLENGE_PREFIX + tuple(challenge_bytes) + (247,)
        self._send_midi(challenge)

    def _on_handshake_successful(self):
        self._do_send_midi(LIVE_MODE_SWITCH_REQUEST)
        with self.component_guard():
            self._modes.set_enabled(True)
            self._actions_component.set_enabled(True)
            self._session_record.set_enabled(True)
            self._modifier_background_component.set_enabled(True)
            self._shifted_background.set_enabled(True)
            self.release_controlled_track()
            self.set_feedback_channels(FEEDBACK_CHANNELS)
        if self._last_sent_mode_byte is not None:
            self._layout_setup(self._last_sent_mode_byte)
        self.set_highlighting_session_component(self._session)
        self.update()

    def _is_challenge_response(self, midi_bytes):
        return len(midi_bytes) == 10 and midi_bytes[:7] == SYSEX_STANDARD_PREFIX + SYSEX_CHALLENGE_RESPONSE_BYTE

    def _is_response_valid(self, midi_bytes):
        response = int(midi_bytes[7])
        response += int(midi_bytes[8] << 8)
        return response == Live.Application.encrypt_challenge2(self._challenge)

    def handle_sysex(self, midi_bytes):
        if len(midi_bytes) < 7:
            pass
        elif self._is_challenge_response(midi_bytes) and self._is_response_valid(midi_bytes):
            self._on_handshake_successful()
        elif midi_bytes[6] == SYSEX_STATUS_BYTE_LAYOUT and midi_bytes[7] == NOTE_LAYOUT_SYSEX_BYTE[0]:
            self._update_hardware()
        elif midi_bytes[6] in (SYSEX_STATUS_BYTE_MODE, SYSEX_STATUS_BYTE_LAYOUT):
            pass
        elif tuple(midi_bytes[:4]) == (240, 0, 32, 41) and midi_bytes[4] == 2 and len(midi_bytes) == 9:
            self.log_message(f"got sysex type 2. data: {midi_bytes[5]}-{midi_bytes[6]}-{midi_bytes[7]}")
        else:
            super().handle_sysex(midi_bytes)
