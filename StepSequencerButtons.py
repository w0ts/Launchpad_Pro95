"""The step sequencers' round buttons that act on the sequencer itself: scale edit, mute shift,
mode (multinote), quantization and lock."""

import time

from .ButtonHelpers import is_press, rebind_button, show_disabled, show_on_off
from .Settings import STEPSEQ__SAVE_SCALE
from .StepSequencerConsts import (
    QUANTIZATION_COLOR_MAP,
    QUANTIZATION_MAP,
    QUANTIZATION_NAMES,
    STEPSEQ_MODE_MULTINOTE,
    STEPSEQ_MODE_NORMAL,
    STEPSEQ_MODE_SCALE_EDIT,
)

MUTE_SHIFT_LATCH_SECONDS = 0.25  # a release this soon after the last one keeps mute shift on
LOCK_LONG_PRESS_SECONDS = 0.5  # a longer press on lock switches between clip and track lock


class StepSequencerButtonsMixin:
    """Mixed into StepSequencerComponent."""

    def _update_buttons(self):
        self._update_quantization_button()
        self._update_lock_button()
        self._update_mode_button()
        self._update_mute_shift_button()
        self._update_scale_button()

    # SCALE: held, the grid edits the scale

    def set_scale_button(self, button):
        if self._scale_button != button:
            self._scale_button = rebind_button(self._scale_button, button, self._scale_button_value)

    def _update_scale_button(self):
        if self.is_enabled() and self._scale_button != None:
            if self._clip != None:
                self._scale_button.set_on_off_values("StepSequencer.Scale.On", "StepSequencer.Scale.Off")
            else:
                self._scale_button.set_on_off_values("DefaultButton.Disabled", "DefaultButton.Disabled")
            if self._mode == STEPSEQ_MODE_SCALE_EDIT:
                self._scale_button.turn_on()
            else:
                self._scale_button.turn_off()

    def _scale_button_value(self, value):
        if value != 0:
            self._mode_backup = self._mode
            if self._scale_component != None and self._note_selector != None:
                self._scale_component.set_octave(int(self._note_selector._root_note / 12))
                self._scale_component.set_key(self._note_selector._key)
                self.set_mode(STEPSEQ_MODE_SCALE_EDIT)
        else:
            if self._scale_component != None and self._note_selector != None:
                self._note_editor._force_update = True
                self._note_selector.set_scale(self._scale_component.notes, self._scale_component._key)
                self._note_selector.set_selected_note(self._scale_component._octave * 12 + self._scale_component._key)
                self._scale_updated()
                if STEPSEQ__SAVE_SCALE == "clip":
                    self._scale_component.update_object_name(self._clip)
            self.set_mode(self._mode_backup, self._number_of_lines_per_note)

    # MUTE SHIFT: held (or latched by a quick second release), pads mute instead of delete

    def set_mute_shift_button(self, button):
        if self._mute_shift_button != button:
            self._mute_shift_button = rebind_button(
                self._mute_shift_button, button, self._mute_shift_button_value, True
            )
            if button != None:
                self._last_mute_shift_button_press = time.time()
                self._is_mute_shifted = False

    def _update_mute_shift_button(self):
        if self.is_enabled() and self._mute_shift_button != None:
            if self._clip != None and self._clip.is_midi_clip:
                show_on_off(
                    self._mute_shift_button, "StepSequencer.Mute.On", "StepSequencer.Mute.Off", self._is_mute_shifted
                )
            else:
                show_disabled(self._mute_shift_button)

    def _mute_shift_button_value(self, value, sender):
        assert self._mute_shift_button != None
        assert value in range(128)
        if self.is_enabled() and self._clip != None:
            now = time.time()
            if is_press(value, sender):
                self._is_mute_shifted = True
            else:
                if now - self._last_mute_shift_button_press > MUTE_SHIFT_LATCH_SECONDS:
                    self._is_mute_shifted = False
                self._last_mute_shift_button_press = now
            self._note_editor._is_mute_shifted = self._is_mute_shifted
            self._update_mute_shift_button()

    # MODE: switches between one note (normal) and multinote

    def set_mode_button(self, button):
        if self._mode_button != button:
            self._mode_button = rebind_button(self._mode_button, button, self._mode_button_value, True)

    def _update_mode_button(self):
        if self.is_enabled() and self._mode_button != None:
            if self._clip != None:
                show_on_off(
                    self._mode_button,
                    "StepSequencer.Mode.On",
                    "StepSequencer.Mode.On",
                    self._mode == STEPSEQ_MODE_MULTINOTE,
                )
            else:
                show_disabled(self._mode_button)

    def _mode_button_value(self, value, sender):
        assert self._mode_button != None
        assert value in range(128)
        if self.is_enabled() and self._clip != None and not is_press(value, sender):
            if self._mode != STEPSEQ_MODE_MULTINOTE:
                self.set_mode(STEPSEQ_MODE_MULTINOTE, self._number_of_lines_per_note)
            else:
                self.set_mode(STEPSEQ_MODE_NORMAL, self._number_of_lines_per_note)

    # QUANTIZATION: cycles the step length (backwards in scale edit)

    def set_quantization_button(self, button):
        if self._quantization_button != button:
            # keep the quantization: the button is set again each time the sequencer is entered
            self._quantization_button = rebind_button(
                self._quantization_button, button, self._quantization_button_value
            )

    def _update_quantization_button(self):
        if self.is_enabled() and self._quantization_button != None:
            show_on_off(
                self._quantization_button,
                QUANTIZATION_COLOR_MAP[self._quantization_index],
                "DefaultButton.Disabled",
                self._clip != None,
            )

    def _quantization_button_value(self, value):
        if self.is_enabled() and self._clip != None and value != 0:
            step = -1 if self._mode == STEPSEQ_MODE_SCALE_EDIT else 1
            self._quantization_index = (self._quantization_index + step) % len(QUANTIZATION_MAP)
            self.set_quantization(QUANTIZATION_MAP[self._quantization_index])
            self._control_surface.show_message("quantisation : " + QUANTIZATION_NAMES[self._quantization_index])
            self._update_quantization_button()

    def set_quantization(self, quantization):
        self._quantization = quantization
        if self._note_editor != None:
            self._note_editor.set_quantization(self._quantization)
        if self._loop_selector != None:
            self._loop_selector.update()
        if self._note_selector != None:
            self._note_selector.update()
        if self._note_editor != None:
            self._update_note_editor()

    # LOCK: keeps the clip; a long press switches between clip lock and track lock

    def _init_lock(self):
        self._is_locked = False
        self._lock_to_track = False
        self._last_lock_button_press = time.time()
        self._long_press = LOCK_LONG_PRESS_SECONDS
        self._lock_button = None
        self._selected_track = None

    def set_lock_button(self, button):
        if self._lock_button != button:
            self._lock_button = rebind_button(self._lock_button, button, self._lock_button_value, True)
            if button != None:
                self._last_lock_button_press = time.time()

    def _update_lock_button(self):
        if self.is_enabled() and self._lock_button != None:
            if self._clip != None:
                if self._lock_to_track:
                    on, off = "StepSequencer.Lock.ToTrack.On", "StepSequencer.Lock.ToTrack.Off"
                else:
                    on, off = "StepSequencer.Lock.ToClip.On", "StepSequencer.Lock.ToClip.Off"
                show_on_off(self._lock_button, on, off, self._is_locked)
            else:
                show_disabled(self._lock_button)

    def _lock_button_value(self, value, sender):
        assert self._lock_button != None
        assert value in range(128)
        if self.is_enabled() and self._clip != None:
            now = time.time()
            if (value != 0) or (not self._lock_button.is_momentary()):
                self._last_lock_button_press = now
            else:
                if now - self._last_lock_button_press > self._long_press:
                    self._lock_to_track = not self._lock_to_track
                    if not self._is_locked:
                        self._show_locked_message()
                        self._is_locked = True
                else:
                    self._is_locked = not self._is_locked
                    if self._is_locked:
                        self._show_locked_message()
                self._update_lock_button()

    def _show_locked_message(self):
        self._control_surface.show_message("stepseq : locked to clip '" + str(self._clip.name) + "'")
