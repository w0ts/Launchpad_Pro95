"""The drum step sequencer (user mode, first sub mode), also the base of the melodic one.

In normal mode the top 4 rows of the grid are 32 steps of the selected note, the bottom-left
4x4 pads select the note and the bottom-right 4x4 pads are the loop selector. In multinote
mode the top 7 rows edit several notes and the bottom row is the loop selector. The clip
following is in StepSequencerClip.py, the round buttons in StepSequencerButtons.py."""

from _Framework.CompoundComponent import CompoundComponent

from .LoopSelectorComponent import LoopSelectorComponent
from .NoteEditorComponent import NoteEditorComponent
from .NoteSelectorComponent import NoteSelectorComponent
from .ScaleComponent import ScaleComponent
from .Settings import STEPSEQ__SAVE_SCALE
from .StepSequencerButtons import StepSequencerButtonsMixin
from .StepSequencerClip import StepSequencerClipMixin
from .StepSequencerConsts import (
    QUANTIZATION_MAP,
    STEPSEQ_MODE_MULTINOTE,
    STEPSEQ_MODE_NORMAL,
    STEPSEQ_MODE_SCALE_EDIT,
)
from .TrackControllerComponent import TrackControllerComponent

# (x, y) of the loop selector and note selector pads, in block / note order.
NORMAL_LOOP_PADS = [(x, y) for y in range(4, 8) for x in range(4, 8)]
NORMAL_NOTE_PADS = [(x, y) for y in range(7, 3, -1) for x in range(4)]
MULTINOTE_LOOP_PADS = [(x, 7) for x in range(8)]


class StepSequencerComponent(StepSequencerButtonsMixin, StepSequencerClipMixin, CompoundComponent):

    def __init__(self, control_surface=None, matrix=None, side_buttons=None, top_buttons=None):
        self._control_surface = control_surface
        super().__init__()

        # clip
        self._clip = None
        self._clip_slot = None
        self._note_cache = []
        self._playhead = 0
        # mode
        self._mode = -1
        self._mode_backup = self._mode
        # buttons
        self._is_mute_shifted = None
        self._scale_button = None
        self._quantization_button = None
        self._mode_button = None
        self._mute_shift_button = None
        self._matrix = None

        # scale
        self._root_note = 36
        # setup
        self._number_of_lines_per_note = 1
        self._quantization_index = 2  # 1/16
        self._quantization = QUANTIZATION_MAP[self._quantization_index]
        self._set_loop_selector()
        self._set_note_editor()
        # no clip yet: the editor only takes the quantization (no loop or note change)
        self._note_editor.set_quantization(self._quantization)
        self._set_note_selector()
        self._set_track_controller()
        self._set_scale_component()
        self._init_lock()

        self.set_enabled(False)

    # BUTTONS GIVEN TO THE PARTS

    def set_octave_down_button(self, button):
        self._note_selector.set_down_button(button)

    def set_octave_up_button(self, button):
        self._note_selector.set_up_button(button)

    def set_velocity_button(self, button):
        self._note_editor.set_velocity_button(button)

    def set_prev_scene_button(self, button):
        self._track_controller.set_prev_scene_button(button)

    def set_next_scene_button(self, button):
        self._track_controller.set_next_scene_button(button)

    def set_prev_track_button(self, button):
        self._track_controller.set_prev_track_button(button)

    def set_next_track_button(self, button):
        self._track_controller.set_next_track_button(button)

    # MATRIX

    def set_matrix(self, matrix):
        self._matrix = matrix
        if self._matrix != None:
            for x in range(self._matrix.width()):
                for y in range(self._matrix.height()):
                    self._matrix.get_button(x, y).set_enabled(True)
        self._delegate_matrix()
        if self._mode == -1:
            self.set_mode(STEPSEQ_MODE_NORMAL)
        self.set_enabled(self._matrix != None)

    def _pads(self, coordinates):
        return [self._matrix.get_button(x, y) for x, y in coordinates]

    def _delegate_matrix(self):
        if self._matrix == None:
            self._loop_selector.set_buttons(None)
            self._note_selector.set_buttons(None)
            self._scale_component.set_matrix(None)
            self._note_editor.set_matrix(None)
        elif self._mode == STEPSEQ_MODE_SCALE_EDIT:
            self._scale_component.set_matrix(self._matrix)
            self._loop_selector.set_buttons(None)
            self._note_selector.set_buttons(None)
            self._note_editor.set_matrix(None)
        elif self._mode == STEPSEQ_MODE_MULTINOTE:
            self._scale_component.set_matrix(None)
            self._note_selector.set_buttons(None)
            self._loop_selector.set_buttons(self._pads(MULTINOTE_LOOP_PADS))
            self._note_editor.set_matrix(self._matrix)
        elif self._mode == STEPSEQ_MODE_NORMAL:
            self._scale_component.set_matrix(None)
            self._loop_selector.set_buttons(self._pads(NORMAL_LOOP_PADS))
            self._note_selector.set_buttons(self._pads(NORMAL_NOTE_PADS))
            self._note_editor.set_matrix(self._matrix)

    def disconnect(self):
        if self._clip_slot != None and self._clip_slot.has_clip_has_listener(self.on_clip_slot_has_clip_changed):
            self._clip_slot.remove_has_clip_listener(self.on_clip_slot_has_clip_changed)
        self._clip_slot = None
        self._remove_clip_listeners(self._clip)
        self._clip = None
        self._lock_button = None
        self._quantization_button = None
        self._matrix = None
        super().disconnect()

    # PARTS

    def _set_loop_selector(self):
        self._loop_selector = self.register_component(LoopSelectorComponent(self._control_surface, self))

    def _set_note_editor(self):
        self._note_editor = self.register_component(
            NoteEditorComponent(control_surface=self._control_surface, stepsequencer=self)
        )

    def _set_note_selector(self):
        self._note_selector = self.register_component(
            NoteSelectorComponent(control_surface=self._control_surface, stepsequencer=self)
        )

    def _set_track_controller(self):
        self._track_controller = self.register_component(
            TrackControllerComponent(
                control_surface=self._control_surface, implicit_arm=False, enabled=True, skin_name="StepSequencer"
            )
        )

    def _set_scale_component(self):
        self._scale_component = self.register_component(
            ScaleComponent(control_surface=self._control_surface, enabled=False, mode="chromatic")
        )

    @property
    def _is_velocity_shifted(self):
        return self._note_editor._is_velocity_shifted

    # ENABLE, MODE, PAGE

    def set_enabled(self, enabled):
        if enabled:
            # restore mode backup when coming back
            if self._mode == STEPSEQ_MODE_SCALE_EDIT:
                self.set_mode(self._mode_backup, self._number_of_lines_per_note)
            # clear note editor cache
            self._note_editor._force_update = True
            if STEPSEQ__SAVE_SCALE == "clip":
                self._load_scale_from_clip()
            self._track_controller.set_enabled(enabled)
            # update clip notes as they might have changed while we were sleeping
            self.on_clip_slot_changed()
            CompoundComponent.set_enabled(self, enabled)
            if self._clip != None and self._is_locked:
                self._control_surface.show_message("stepseq : clip '" + str(self._clip.name) + "'")
            self._on_notes_changed()
        else:
            CompoundComponent.set_enabled(self, enabled)

    def _load_scale_from_clip(self):
        self._scale_component.from_object(self._clip)
        self._note_selector.set_scale(self._scale_component.notes, self._scale_component._selected_key)
        self._note_selector.set_selected_note(
            self._scale_component._octave_index * 12 + self._scale_component._selected_key
        )

    def set_mode(self, mode, number_of_lines_per_note=-1):
        if number_of_lines_per_note == -1:
            number_of_lines_per_note = self._number_of_lines_per_note
        if self._mode != mode or number_of_lines_per_note != self._number_of_lines_per_note:
            self._number_of_lines_per_note = number_of_lines_per_note
            self._note_editor.set_multinote(mode == STEPSEQ_MODE_MULTINOTE, number_of_lines_per_note)
            if self._mode != mode:
                self._note_editor.set_page(self._loop_selector._block)
            self._mode = mode
            self._delegate_matrix()
            self._note_editor._force_update = True
            self.update()

    def set_page(self, block):
        self._note_editor.set_page(block)
        self._update_note_editor()

    # SCALE

    def _scale_updated(self):
        selector = self._note_selector
        if selector.is_drumrack:
            keys = [selector.selected_note + i for i in range(8)]
            key_is_root_note = [(key + 12 + 16) % 16 == 0 for key in keys]
            key_is_in_scale = [(key + 12 + 16) % 4 == 0 for key in keys]
        elif selector.is_diatonic:
            keys, key_is_root_note, key_is_in_scale = self._diatonic_keys()
        else:
            keys = [selector.selected_note + i for i in range(8)]
            key_is_root_note = [(key + 12) % 12 == selector._key for key in keys]
            key_is_in_scale = [(key - selector._key + 12) % 12 in selector._scale for key in keys]
        self._note_editor.set_key_indexes(keys)
        self._note_editor.set_key_index_is_in_scale(key_is_in_scale)
        self._note_editor.set_key_index_is_root_note(key_is_root_note)
        self._update_note_editor()

    def _diatonic_keys(self):
        """The 8 notes of the scale from the selected one, and which are roots / in the scale."""
        selector = self._note_selector
        selector._scale_length = len(selector._scale)
        key_is_root_note = [False] * 8
        key_is_in_scale = [False] * 8
        try:
            idx = selector._scale.index(selector._offset)
        except ValueError:
            idx = -1
        if idx == -1:
            self._control_surface.log_message("not found : " + str(selector._offset) + " in " + str(selector._scale))
            keys = [selector._root_note + selector._offset + i for i in range(8)]
        else:
            length = selector._scale_length
            keys = [
                selector._root_note + selector._scale[(i + idx) % length] + ((i + idx) // length) * 12 for i in range(8)
            ]
            key_is_root_note = [(key + 12) % 12 == selector._key for key in keys]
            key_is_in_scale = [True] * 8
        return keys, key_is_root_note, key_is_in_scale

    # UPDATE

    def update(self):
        if self.is_enabled():
            self._update_track_controller()
            self._update_scale_component()
            self._update_loop_selector()
            self._update_note_selector()
            self._update_buttons()
            self._update_note_editor()
            if not self._is_locked and self._clip != None:
                self._show_clip_detail()

    def _show_clip_detail(self):
        view = self.application().view
        if (not view.is_view_visible("Detail")) or (not view.is_view_visible("Detail/Clip")):
            view.show_view("Detail")
            view.show_view("Detail/Clip")

    def _update_track_controller(self):
        self._track_controller.set_enabled(self.is_enabled())
        self._track_controller.update()

    def _update_scale_component(self):
        self._scale_component.set_enabled(self._mode == STEPSEQ_MODE_SCALE_EDIT)
        self._scale_component.update()

    def _update_loop_selector(self):
        self._loop_selector.set_enabled(self._mode != STEPSEQ_MODE_SCALE_EDIT)
        self._loop_selector.update()

    def _update_note_selector(self):
        self._note_selector.set_enabled(self._mode != STEPSEQ_MODE_SCALE_EDIT)
        self._note_selector.update()

    def _update_note_editor(self):
        self._note_editor.set_multinote(self._mode == STEPSEQ_MODE_MULTINOTE, self._number_of_lines_per_note)
        if self._matrix != None:
            self._note_editor.set_height(4 if self._mode == STEPSEQ_MODE_NORMAL else 8)
            self._note_editor.set_enabled(self._mode != STEPSEQ_MODE_SCALE_EDIT)
            self._note_editor.update()

    # CLIP CREATION

    def create_clip(self):
        clip_slot = self.song().view.highlighted_clip_slot
        if clip_slot != None and not clip_slot.has_clip:
            steps = 8 * 4 if self._mode == STEPSEQ_MODE_NORMAL else 8
            clip_slot.create_clip(QUANTIZATION_MAP[self._quantization_index] * steps)
            clip_slot.fire()
            self.on_clip_slot_changed()
            self.update()
