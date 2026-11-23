"""The step sequencer's loop selector: one pad per block of 8 steps, to page, set the loop
and delete, mute or extend the notes of a range of blocks."""

import time

from _Framework.ButtonElement import ButtonElement
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent

from .ClipLoop import set_loop_and_markers
from .ClipNotes import write_all_notes

DOUBLE_TAP_SECONDS = 0.25


class LoopSelectorComponent(ControlSurfaceComponent):
    """Tap a block to show it. Hold a block and tap another (or double tap one) to set the loop
    to that range of blocks; with mute shift held the range's notes are deleted instead (muted
    with velocity held too); with velocity held alone a longer loop is filled with a copy of
    the current one."""

    def __init__(self, control_surface=None, stepsequencer=None, buttons=None):
        ControlSurfaceComponent.__init__(self)
        self.set_enabled(False)
        self._stepsequencer = stepsequencer
        self._control_surface = control_surface
        self._clip = None
        self._playhead = None
        self._buttons = None

        self._loop_end = 0
        self._loop_start = 0

        self._blocksize = 8  # number of note per block
        self._block = 0  # current block

        # used for loop selection
        self._last_button = -1
        self.last_button_time = 0
        self._loop_point1 = -1
        self._loop_point2 = -1

        self._cache = [-1] * 16
        if buttons != None:
            self.set_buttons(buttons)

    def set_buttons(self, buttons):
        if self._buttons:
            for button in self._buttons:
                assert isinstance(button, ButtonElement)
                button.remove_value_listener(self._loop_button_value)
        self._buttons = buttons
        if self._buttons:
            for button in self._buttons:
                assert isinstance(button, ButtonElement)
                button.add_value_listener(self._loop_button_value, identify_sender=True)

    def disconnect(self):
        self.set_buttons(None)
        super().disconnect()

    def set_clip(self, clip):
        self._clip = clip

    def set_note_cache(self, note_cache):
        self._note_cache = note_cache

    def set_playhead(self, playhead):
        self._playhead = playhead
        if self._buttons != None:
            self.update()

    @property
    def _is_mute_shifted(self):
        return self._stepsequencer._is_mute_shifted

    @property
    def _is_velocity_shifted(self):
        return self._stepsequencer._note_editor._is_velocity_shifted

    @property
    def _quantization(self):
        return self._stepsequencer._quantization

    @property
    def _block_length(self):
        """The length of a block in beats."""
        return self._blocksize * self._quantization

    @property
    def block(self):
        return self._block

    def set_enabled(self, enabled):
        self._force = True
        ControlSurfaceComponent.set_enabled(self, enabled)

    def _get_clip_loop(self):
        if self._clip != None:
            self._loop_start = self._clip.loop_start
            self._loop_end = self._clip.loop_end
        else:
            self._loop_start = 0
            self._loop_end = 0

    def set_clip_loop(self, start, end):
        if self._clip != None:
            # start and end are locals: the clip's loop listeners may call update(),
            # which reads the clip loop back into self._loop_start / self._loop_end.
            set_loop_and_markers(self._clip, start, end)
            self._loop_start = start
            self._loop_end = end
            self.update()

    # PADS

    def _loop_button_value(self, value, sender):
        if self.is_enabled():
            x = self._buttons.index(sender)
            if value > 0:
                if self._loop_point1 == -1:
                    self._loop_point1 = x
                elif self._loop_point2 == -1:
                    self._loop_point2 = x
            elif self._loop_point1 != -1:
                self._loop_button_released(x)
                self.last_button_time = time.time()
                self._last_button = x

    def _loop_button_released(self, x):
        """A pad was released while a first loop point is held: page, or act on the range."""
        apply_to_range = self._loop_point2 != -1
        if self._loop_point2 == -1:
            self._loop_point2 = x
            if self._last_button == x and time.time() - self.last_button_time < DOUBLE_TAP_SECONDS:
                apply_to_range = True
                self.last_button_time = time.time()
                self._last_button = -1
        start = min(self._loop_point1, self._loop_point2)
        end = max(self._loop_point1, self._loop_point2) + 1
        self._block = start
        if apply_to_range:
            self._apply_to_blocks(start, end)
        self._stepsequencer.set_page(self._block)
        self._loop_point1 = -1
        self._loop_point2 = -1
        self.update()

    def _apply_to_blocks(self, start, end):
        start_time = start * self._block_length
        end_time = end * self._block_length
        if self._is_mute_shifted:
            if self._is_velocity_shifted:
                self._mute_notes_in_range(start_time, end_time)
            else:
                self._delete_notes_in_range(start_time, end_time)
        else:
            if self._is_velocity_shifted:
                self._extend_clip_content(self._loop_start, self._loop_end, end_time)
            self.set_clip_loop(start_time, end_time)

    # LEDS

    def update(self):
        if self.is_enabled() and self._buttons:
            self._get_clip_loop()
            for i, button in enumerate(self._buttons):
                if self._clip == None:
                    button.set_on_off_values("DefaultButton.Disabled", "DefaultButton.Disabled")
                    if self._cache[i] != button._off_value:
                        button.turn_off()
                        self._cache[i] = button._off_value
                else:
                    self._cache[i] = self._block_color(i)
                    if self._cache[i] != button._on_value or self._force:
                        button.set_on_off_values(self._cache[i], self._cache[i])
                        button.turn_on()
            self._force = False

    def _block_color(self, i):
        block_start = i * self._block_length
        in_loop = self._loop_start <= block_start < self._loop_end
        playing = self._playhead != None and block_start <= self._playhead < (i + 1) * self._block_length
        selected = i == self.block
        if playing:
            return "StepSequencer.LoopSelector.SelectedPlaying" if selected else "StepSequencer.LoopSelector.Playing"
        if selected:
            return "StepSequencer.LoopSelector.Selected"
        return "StepSequencer.LoopSelector.InLoop" if in_loop else "DefaultButton.Disabled"

    # NOTES

    def _extend_clip_content(self, loop_start, old_loop_end, new_loop_end):
        # positions inside the loop are relative to loop_start
        loop_length = old_loop_end - loop_start
        if loop_length > 0 and self._no_notes_in_range(old_loop_end, new_loop_end, True):
            clip_looping_length = 0
            if loop_length > 1:
                power = 1
                while power * 2 < loop_length:
                    power *= 2
                clip_looping_length = power
            clone_length = new_loop_end - old_loop_end
            if clip_looping_length > 0:
                clone_start_point = loop_start + (loop_length % clip_looping_length)
            else:
                clone_start_point = loop_start
            self._copy_notes_in_range(clone_start_point, clone_start_point + clone_length, old_loop_end)

    def _no_notes_in_range(self, start, end, or_after):
        for note in list(self._note_cache):
            if note[1] >= start and (note[1] < end or or_after):
                return False
        return True

    def _delete_notes_in_range(self, start, end):
        new_notes = [note for note in self._note_cache if note[1] < start or note[1] >= end]
        write_all_notes(self._clip, new_notes)

    def _mute_notes_in_range(self, start, end):
        new_notes = list()
        for note in list(self._note_cache):
            if note[1] < start or note[1] >= end:
                new_notes.append(note)
            else:
                new_notes.append([note[0], note[1], note[2], note[3], not note[4]])
        write_all_notes(self._clip, new_notes)

    def _copy_notes_in_range(self, start, end, new_start):
        new_notes = list(self._note_cache)
        for note in self._note_cache:
            if note[1] >= start and note[1] < end:
                new_notes.append([note[0], note[1] + new_start - start, note[2], note[3], note[4]])
        write_all_notes(self._clip, new_notes)
