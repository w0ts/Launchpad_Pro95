"""The melodic step sequencer (user mode, second sub mode): the drum sequencer with the
melodic grid editor, a diatonic scale, the loop selector on the bottom row and the page
buttons on the right instead of the octave, mode and mute shift buttons."""

from .MelodicNoteEditorComponent import MelodicNoteEditorComponent
from .ScaleComponent import ScaleComponent
from .StepSequencerComponent import MULTINOTE_LOOP_PADS, StepSequencerComponent
from .StepSequencerConsts import STEPSEQ_MODE_SCALE_EDIT
from .TrackControllerComponent import TrackControllerComponent


class StepSequencerComponent2(StepSequencerComponent):

    def __init__(self, control_surface=None, side_buttons=None, top_buttons=None):
        super().__init__(control_surface)

    def _delegate_matrix(self):
        if self._matrix != None:
            self._loop_selector.set_buttons(self._pads(MULTINOTE_LOOP_PADS))
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

    def _update_buttons(self):  # no mode or mute shift button
        self._update_quantization_button()
        self._update_lock_button()
        self._update_scale_button()

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
