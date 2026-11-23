"""The step sequencer's note selector: the pads and octave buttons that pick the edited note."""

from _Framework.ButtonElement import ButtonElement
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent

from .ButtonHelpers import is_press, rebind_button, show_disabled

FEEDBACK_CHANNEL = 11  # the pads play the track on this channel while velocity is held


class NoteSelectorComponent(ControlSurfaceComponent):

    def __init__(self, control_surface=None, stepsequencer=None, buttons=None):
        ControlSurfaceComponent.__init__(self)
        self._control_surface = control_surface
        self._stepsequencer = stepsequencer
        self.set_enabled(False)

        self._clip = None
        self._track = None
        self._playhead = None

        self._root_note = 36
        self._offset = 0
        self._key = 0
        self._scale = [0, 2, 4, 5, 7, 9, 11, 12]
        self._force = True

        self._up_button = None
        self._down_button = None

        self._buttons = None
        # cache to optimise display for offset buttons minimizing midi traffic
        self._cache = [-1] * 16
        self._was_velocity_shifted = False

        if buttons != None:
            self.set_buttons(buttons)

    def set_buttons(self, buttons):
        if self._buttons:
            for button in self._buttons:
                assert isinstance(button, ButtonElement)
                button.remove_value_listener(self.note_offset_button_value)
        self._buttons = buttons
        if self._buttons:
            for button in self._buttons:
                assert isinstance(button, ButtonElement)
                button.add_value_listener(self.note_offset_button_value, identify_sender=True)

    def set_clip(self, clip):
        self._clip = clip

    def set_note_cache(self, note_cache):
        self._note_cache = note_cache

    def set_playhead(self, playhead):
        self._playhead = playhead
        if self._buttons != None:
            self._update_buttons()

    @property
    def _is_mute_shifted(self):
        return self._stepsequencer._is_mute_shifted

    @property
    def _is_velocity_shifted(self):
        return self._stepsequencer._is_velocity_shifted

    @property
    def _plays_the_track(self):
        """While velocity is held (and the clip not locked) the pads play the track."""
        return self._is_velocity_shifted and not self._stepsequencer._is_locked

    @property
    def _drum_group_device(self):
        return None

    @property
    def is_drumrack(self):
        return self._stepsequencer._scale_component.is_drumrack

    @property
    def is_chromatic(self):
        return self._stepsequencer._scale_component.is_chromatic

    @property
    def is_diatonic(self):
        return self._stepsequencer._scale_component.is_diatonic

    # OCTAVE BUTTONS: an octave (a drum rack page) per press, a semitone with mute shift

    def set_down_button(self, button):
        if self._down_button != button:
            self._down_button = rebind_button(self._down_button, button, self._down_button_value, True)
            self._update_down_button()

    def set_up_button(self, button):
        if self._up_button != button:
            self._up_button = rebind_button(self._up_button, button, self._up_button_value, True)
            self._update_up_button()

    def _update_down_button(self):
        self._update_octave_button(self._down_button, self.can_scroll_down, self.can_page_down)

    def _update_up_button(self):
        self._update_octave_button(self._up_button, self.can_scroll_up, self.can_page_up)

    def _update_octave_button(self, button, can_scroll, can_page):
        if self.is_enabled() and button != None:
            if self._clip == None:
                show_disabled(button)
            else:
                button.set_on_off_values("StepSequencer.Octave.On", "StepSequencer.Octave.Off")
                can_move = can_scroll() if self._is_mute_shifted else can_page()
                if can_move:
                    button.turn_on()
                else:
                    button.turn_off()

    def _down_button_value(self, value, sender):
        assert self._down_button != None
        self._octave_button_value(value, sender, self.scroll_down, self.page_down)

    def _up_button_value(self, value, sender):
        assert self._up_button != None
        self._octave_button_value(value, sender, self.scroll_up, self.page_up)

    def _octave_button_value(self, value, sender, scroll, page):
        assert value in range(128)
        if self.is_enabled() and self._clip != None and is_press(value, sender):
            if self._is_mute_shifted:
                scroll()
            else:
                page()
            self._stepsequencer.update()

    # NOTE PADS

    def note_offset_button_value(self, value, sender):
        if self.is_enabled() and value > 0:
            index = self._buttons.index(sender) if sender in self._buttons else -1
            if self._is_mute_shifted:
                self._stepsequencer._note_editor.mute_lane(self._root_note + index)
            else:
                self._offset = index
                self.update()
                self._stepsequencer._scale_updated()

    def update(self):
        if self.is_enabled():
            track_controller = self._stepsequencer._track_controller
            track_controller._implicit_arm = self._plays_the_track
            if track_controller._implicit_arm:
                track_controller._do_implicit_arm()
            if self._plays_the_track:
                self._control_surface.set_feedback_channels([FEEDBACK_CHANNEL])
                self._was_velocity_shifted = True
            elif self.is_drumrack and self._was_velocity_shifted:
                self._was_velocity_shifted = False
                # FIXME: _drum_group_device is always None, so this raises AttributeError.
                self._offset = self._drum_group_device.view.selected_drum_pad.note - self._root_note
                self._stepsequencer._scale_updated()
            self._update_up_button()
            self._update_down_button()
            self._update_buttons()

    def _update_buttons(self):
        if self.is_enabled() and self._buttons != None:
            for index, button in enumerate(self._buttons):
                if self._clip == None:
                    show_disabled(button)
                else:
                    self._update_note_pad(index, button)
            self._force = False

    def _update_note_pad(self, index, button):
        note = self._root_note + index
        self._set_pad_colors(index, button)
        if self._plays_the_track:
            button.force_next_send()
            button.set_enabled(False)
            button.set_channel(FEEDBACK_CHANNEL)
            button.set_identifier(note)
        else:
            button.set_enabled(True)
            button.use_default_message()
            if self._playhead != None and self.note_is_playing(self._clip, self._note_cache, note, self._playhead):
                button.set_on_off_values("StepSequencer.NoteSelector.Playing", "StepSequencer.NoteSelector.Playing")

        value = button._on_value if self.selected_note == note else button._off_value
        if self._cache[index] != value or self._force:
            if self.selected_note == note:
                button.turn_on()
            else:
                button.turn_off()
            self._cache[index] = value

    def _set_pad_colors(self, index, button):
        if self.is_drumrack:
            button.set_on_off_values("DrumGroup.PadSelected", "DrumGroup.PadFilled")
            return
        degree = index % 12
        if degree == self._scale[0]:
            off = "Note.Pads.Root"
        elif degree == self._scale[2] or degree == self._scale[4]:
            off = "Note.Pads.Highlight"
        elif self._scale != None and degree in self._scale:
            off = "Note.Pads.InScale"
        else:
            off = "Note.Pads.OutOfScale"
        button.set_on_off_values("StepSequencer.NoteSelector.Selected", off)

    def set_enabled(self, enabled):
        if enabled:
            self._cache = [-1] * 16
        ControlSurfaceComponent.set_enabled(self, enabled)

    def set_scale(self, scale, key=-1):
        if key != -1:
            self._key = key
        self._scale = scale
        # relativise scale
        for i in range(len(self._scale)):
            self._scale[i] = self._scale[i] - self._key

    def note_is_playing(self, clip, note_cache, midi_note, playhead):
        if clip != None and clip.is_playing and note_cache != None:
            for pitch, position, length, _velocity, muted in note_cache:
                if midi_note == pitch and position <= playhead <= position + length and not muted:
                    return True
        return False

    # MOVING THE SELECTED NOTE

    @property
    def _page_size(self):
        return 16 if self.is_drumrack else 12

    def scroll_down(self):
        self.move(-1)

    def scroll_up(self):
        self.move(1)

    def page_down(self):
        self.move(-self._page_size)

    def page_up(self):
        self.move(self._page_size)

    def can_scroll_down(self):
        return self.can_move(-1)

    def can_scroll_up(self):
        return self.can_move(1)

    def can_page_down(self):
        return self.can_move(-self._page_size)

    def can_page_up(self):
        return self.can_move(self._page_size)

    def can_move(self, steps):
        return self.selected_note + steps >= 0 and self.selected_note + steps < 128

    def move(self, steps):
        if self.can_move(steps):
            if self.is_diatonic:
                self.set_selected_note(self._diatonic_move_target(steps))
            else:
                self.set_selected_note(self._root_note + self._offset + steps)

    def _diatonic_move_target(self, steps):
        """The note of the scale reached by moving steps semitones (rounded away from the
        selected note to the next note of the scale)."""
        octave = 0
        if steps > 0:
            while self._offset + steps >= 12:
                steps = steps - 12
                octave = octave + 1
            while steps != 0 and self._offset + steps not in self._scale:
                steps = steps + 1
                while self._offset + steps > 12:
                    steps = steps - 12
                    octave = octave + 1
        elif steps < 0:
            while self._offset + steps < 0:
                steps = steps + 12
                octave = octave - 1
            while steps != 0 and self._offset + steps not in self._scale:
                steps = steps - 1
                if self._offset + steps < 0:
                    steps = steps + 12
                    octave = octave - 1
        try:
            index = self._scale.index(self._offset + steps)
        except ValueError:
            index = -1
        return self._root_note + octave * 12 + self._scale[index]

    def set_selected_note(self, selected_note):
        if self.is_drumrack:
            self._root_note = ((selected_note + 12) // 16 - 1) * 16 + 4
            self._offset = (selected_note - self._root_note + 16) % 16
        else:
            self._root_note = (selected_note - self._key) // 12 * 12 + self._key
            self._offset = (selected_note + 12 - self._root_note) % 12
        self.update()
        self._stepsequencer._scale_updated()

    def set_key(self, key):
        self._key = key

    @property
    def selected_note(self):
        return self._root_note + self._offset
