"""The melodic step sequencer's page buttons (pitch, octave, velocity, length) and random button.

A tap on a page button shows its page. Held, a pad edits every step of the loop (pitch: the
pad's degree; the other pages: the left half sets the row, the right half moves one up or
down). A double tap on pitch switches monophonic on and off."""

import time

from .ButtonHelpers import rebind_button, show_disabled, show_on_off

STEPSEQ_MODE_NOTES = 1
STEPSEQ_MODE_NOTES_OCTAVES = 2
STEPSEQ_MODE_NOTES_VELOCITIES = 3
STEPSEQ_MODE_NOTES_LENGTHS = 4

PITCH_DOUBLE_TAP_SECONDS = 0.5


def _is_release(value, sender):
    return value == 0 and sender.is_momentary()


class MelodicPageButtonsMixin:
    """Mixed into MelodicNoteEditorComponent."""

    def _init_page_buttons(self):
        self._random_button = None
        self._mode_notes_lengths_button = None
        self._mode_notes_octaves_button = None
        self._mode_notes_velocities_button = None
        self._mode_notes_pitches_button = None
        self._is_notes_pitches_shifted = False
        self._last_notes_pitches_button_press = time.time()
        self._is_notes_lengths_shifted = False

    def _update_page_buttons(self):
        self._update_mode_notes_octaves_button()
        self._update_mode_notes_lengths_button()
        self._update_mode_notes_velocities_button()
        self._update_mode_notes_pitches_button()
        self._update_random_button()

    def _update_page_button(self, button, on_key, dim_key, mode):
        if self.is_enabled() and button != None:
            if self._clip != None:
                show_on_off(button, on_key, dim_key, self._mode == mode)
            else:
                button.set_light("DefaultButton.Disabled")

    # RANDOM

    def set_random_button(self, button):
        if self._random_button != button:
            self._random_button = rebind_button(self._random_button, button, self._random_button_value, True)

    def _update_random_button(self):
        if self.is_enabled() and self._random_button != None:
            if self._clip != None:
                self._random_button.set_on_off_values("StepSequencer2.Random.On", "StepSequencer2.Random.Off")
                self._random_button.turn_off()
            else:
                self._random_button.set_light("DefaultButton.Disabled")

    def _random_button_value(self, value, sender):
        assert self._random_button != None
        assert value in range(128)
        if self.is_enabled() and self._clip != None:
            self._random_button.set_on_off_values("StepSequencer2.Random.On", "StepSequencer2.Random.Off")
            if _is_release(value, sender):
                self._random_button.turn_off()
                self._control_surface.show_message("randomise")
                self._randomise()
            else:
                self._random_button.turn_on()

    # PITCHES

    def set_mode_notes_pitches_button(self, button):
        if self._mode_notes_pitches_button != button:
            self._mode_notes_pitches_button = rebind_button(
                self._mode_notes_pitches_button, button, self._mode_button_notes_pitches_value, True
            )

    def _update_mode_notes_pitches_button(self):
        button = self._mode_notes_pitches_button
        if self.is_enabled() and button != None:
            if self._clip != None:
                show_on_off(
                    button, "StepSequencer2.Pitch.On", "StepSequencer2.Pitch.Dim", self._mode == STEPSEQ_MODE_NOTES
                )
            else:
                show_disabled(button)

    def _mode_button_notes_pitches_value(self, value, sender):
        assert self._mode_notes_pitches_button != None
        assert value in range(128)
        if self.is_enabled() and self._clip != None:
            shifted = not _is_release(value, sender)
            self._is_notes_pitches_shifted = shifted
            self._is_mute_shifted = shifted
            self._is_velocity_shifted = shifted
            if not shifted:
                if time.time() - self._last_notes_pitches_button_press < PITCH_DOUBLE_TAP_SECONDS:
                    self._is_monophonic = not self._is_monophonic
                    self._update_clip_notes()
                else:
                    self.set_mode(STEPSEQ_MODE_NOTES)
                    self._control_surface.show_message("pitch")
                    self.update()
                self._last_notes_pitches_button_press = time.time()

    # OCTAVES

    def set_mode_notes_octaves_button(self, button):
        if self._mode_notes_octaves_button != button:
            self._mode_notes_octaves_button = rebind_button(
                self._mode_notes_octaves_button, button, self._mode_button_notes_octaves_value, True
            )

    def _update_mode_notes_octaves_button(self):
        self._update_page_button(
            self._mode_notes_octaves_button,
            "StepSequencer2.Octave.On",
            "StepSequencer2.Octave.Dim",
            STEPSEQ_MODE_NOTES_OCTAVES,
        )

    def _mode_button_notes_octaves_value(self, value, sender):
        assert self._mode_notes_octaves_button != None
        assert value in range(128)
        if self.is_enabled() and self._clip != None:
            if _is_release(value, sender):
                self._is_notes_octaves_shifted = False
                self.set_mode(STEPSEQ_MODE_NOTES_OCTAVES)
                self._control_surface.show_message("octave")
                self.update()
            else:
                self._is_notes_octaves_shifted = True

    # VELOCITIES

    def set_mode_notes_velocities_button(self, button):
        if self._mode_notes_velocities_button != button:
            self._mode_notes_velocities_button = rebind_button(
                self._mode_notes_velocities_button, button, self._mode_button_notes_velocities_value, True
            )

    def _update_mode_notes_velocities_button(self):
        self._update_page_button(
            self._mode_notes_velocities_button,
            "StepSequencer2.Velocity.On",
            "StepSequencer2.Velocity.Dim",
            STEPSEQ_MODE_NOTES_VELOCITIES,
        )

    def _mode_button_notes_velocities_value(self, value, sender):
        assert self._mode_notes_velocities_button != None
        assert value in range(128)
        if self.is_enabled() and self._clip != None:
            if _is_release(value, sender):
                self._is_mute_shifted = False
                self._is_notes_velocities_shifted = False
                self.set_mode(STEPSEQ_MODE_NOTES_VELOCITIES)
                self._control_surface.show_message("velocity")
                self.update()
            else:
                self._is_mute_shifted = True
                self._is_notes_velocities_shifted = True
            self._step_sequencer._is_mute_shifted = self._is_mute_shifted

    # LENGTHS

    def set_mode_notes_lengths_button(self, button):
        if self._mode_notes_lengths_button != button:
            self._mode_notes_lengths_button = rebind_button(
                self._mode_notes_lengths_button, button, self._mode_button_notes_lengths_value, True
            )

    def _update_mode_notes_lengths_button(self):
        self._update_page_button(
            self._mode_notes_lengths_button,
            "StepSequencer2.Length.On",
            "StepSequencer2.Length.Dim",
            STEPSEQ_MODE_NOTES_LENGTHS,
        )

    def _mode_button_notes_lengths_value(self, value, sender):
        assert self._mode_notes_lengths_button != None
        assert value in range(128)
        if self.is_enabled() and self._clip != None:
            if _is_release(value, sender):
                self._is_notes_lengths_shifted = False
                self.set_mode(STEPSEQ_MODE_NOTES_LENGTHS)
                self.update()
                self._control_surface.show_message("length")
            else:
                self._is_notes_lengths_shifted = True
