"""The melodic step sequencer (user mode, second sub mode)."""

from .LoopSelectorComponent import LoopSelectorComponent
from .MelodicNoteEditorComponent import MelodicNoteEditorComponent
from .NoteSelectorComponent import NoteSelectorComponent
from .ScaleComponent import ScaleComponent
from .StepSequencerComponent import StepSequencerComponent
from .StepSequencerConsts import STEPSEQ_MODE_SCALE_EDIT
from .TrackControllerComponent import TrackControllerComponent


class StepSequencerComponent2(StepSequencerComponent):

    def __init__(self, control_surface=None, side_buttons=None, top_buttons=None):
        super().__init__(control_surface)

    def _delegate_matrix(self):
        if self._matrix != None:
            self._loop_selector.set_buttons(
                [
                    self._matrix.get_button(0, 7),
                    self._matrix.get_button(1, 7),
                    self._matrix.get_button(2, 7),
                    self._matrix.get_button(3, 7),
                    self._matrix.get_button(4, 7),
                    self._matrix.get_button(5, 7),
                    self._matrix.get_button(6, 7),
                    self._matrix.get_button(7, 7),
                ]
            )
        else:
            self._loop_selector.set_buttons(None)
        self._note_editor.set_matrix(self._matrix)
        self._scale_component.set_matrix(self._matrix)

    def _set_scale_component(self):
        self._scale_component = self.register_component(
            ScaleComponent(control_surface=self._control_surface, enabled=False, mode="diatonic")
        )

    def _set_track_controller(self):
        self._track_controller = self.register_component(
            TrackControllerComponent(
                control_surface=self._control_surface, implicit_arm=False, skin_name="StepSequencer2", enabled=True
            )
        )

    def _set_note_editor(self):
        self._note_editor = self.register_component(MelodicNoteEditorComponent(self._control_surface, self))

    def _set_note_selector(self):
        self._note_selector = self.register_component(NoteSelectorComponent(self._control_surface, self))

    def _set_loop_selector(self):
        self._loop_selector = self.register_component(LoopSelectorComponent(self._control_surface, self))

    def _update_buttons(self):
        self._update_quantization_button()
        self._update_lock_button()
        self._update_scale_button()

    def _update_mode_button(self):
        if self.is_enabled():
            if self._mode_button != None:
                self._mode_button.set_on_off_values("DefaultButton.Disabled", "DefaultButton.Disabled")

    def _mode_button_value(self, value, sender):
        pass

    def _update_loop_selector(self):
        self._loop_selector.set_enabled(self._mode != STEPSEQ_MODE_SCALE_EDIT)
        self._loop_selector.update()

    def _update_note_editor(self):
        self._note_editor.set_enabled(self._mode != STEPSEQ_MODE_SCALE_EDIT)
        self._note_editor.update()

    def set_octave_button(self, button):
        self._note_editor.set_mode_notes_octaves_button(button)

    def set_pitch_button(self, button):
        self._note_editor.set_mode_notes_pitches_button(button)

    def set_length_button(self, button):
        self._note_editor.set_mode_notes_lengths_button(button)

    def set_velocity_button(self, button):
        self._note_editor.set_mode_notes_velocities_button(button)

    def set_random_button(self, button):
        self._note_editor.set_random_button(button)
