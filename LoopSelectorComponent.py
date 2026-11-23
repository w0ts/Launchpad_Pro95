"""The step sequencer's loop selector: one pad per block of 8 steps, to page, set the loop
and delete, mute or extend the notes of a range of blocks."""

import time

from _Framework.ButtonElement import ButtonElement
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent

from .ClipNotes import write_all_notes
from .StepSequencerConsts import STEPSEQ_MODE_MULTINOTE


class LoopSelectorComponent(ControlSurfaceComponent):

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
        self._loop_point1 = -1
        self._loop_point2 = -1

        self._cache = [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]
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

    @property
    def _number_of_lines_per_note(self):
        if self._mode == STEPSEQ_MODE_MULTINOTE:
            return self._stepsequencer._number_of_lines_per_note
        else:
            return 1

    def set_clip(self, clip):
        self._clip = clip

    @property
    def _mode(self):
        return self._stepsequencer._mode

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
            # The order keeps start < end at every step.
            if start >= self._clip.loop_end:
                self._clip.loop_end = end
                self._clip.loop_start = start
                self._clip.end_marker = end
                self._clip.start_marker = start
            else:
                self._clip.loop_start = start
                self._clip.loop_end = end
                self._clip.start_marker = start
                self._clip.end_marker = end
            self._loop_start = start
            self._loop_end = end
            self.update()

    def _loop_button_value(self, value, sender):
        if self.is_enabled():
            x = self._buttons.index(sender)
            if value > 0:
                if self._loop_point1 == -1:
                    self._loop_point1 = x
                elif self._loop_point2 == -1:
                    self._loop_point2 = x

            elif self._loop_point1 != -1:
                setloop = self._loop_point2 != -1
                if self._loop_point2 == -1:
                    self._loop_point2 = x
                    if self._last_button == x and time.time() - self.last_button_time < 0.25:
                        setloop = True
                        self.last_button_time = time.time()
                        self._last_button = -1

                if self._loop_point1 != -1 and self._loop_point2 != -1:
                    if self._loop_point1 > self._loop_point2:
                        start = self._loop_point2
                        end = self._loop_point1
                    else:
                        start = self._loop_point1
                        end = self._loop_point2
                    end = end + 1
                    self._block = start
                    if setloop:
                        if self._is_mute_shifted:
                            if self._is_velocity_shifted:
                                self._mute_notes_in_range(
                                    start * self._blocksize * self._quantization,
                                    end * self._blocksize * self._quantization,
                                )
                            else:
                                self._delete_notes_in_range(
                                    start * self._blocksize * self._quantization,
                                    end * self._blocksize * self._quantization,
                                )
                        else:
                            if self._is_velocity_shifted:
                                self._extend_clip_content(
                                    self._loop_start, self._loop_end, end * self._blocksize * self._quantization
                                )
                            self.set_clip_loop(
                                start * self._blocksize * self._quantization, end * self._blocksize * self._quantization
                            )

                    self._stepsequencer.set_page(self._block)
                    self._loop_point1 = -1
                    self._loop_point2 = -1
                    self.update()
                self.last_button_time = time.time()
                self._last_button = x

    def can_scroll(self, blocks):
        if self._clip != None:
            if (blocks + self._block) < 0:
                return False
            if (blocks + self._block) * 8 * self._quantization * self._number_of_lines_per_note < self._clip.loop_start:
                return False
            if (
                blocks + self._block + 1
            ) * 8 * self._quantization * self._number_of_lines_per_note > self._clip.loop_end:
                return False
            return True
        return False

    def scroll(self, blocks):
        if self._clip != None and self.can_scroll(blocks):
            self._block = blocks + self._block
            self._stepsequencer.set_page(self._block)

    def update(self):
        if self.is_enabled() and self._buttons:
            self._get_clip_loop()
            i = 0
            for button in self._buttons:
                if self._clip == None:
                    button.set_on_off_values("DefaultButton.Disabled", "DefaultButton.Disabled")
                    if self._cache[i] != button._off_value:
                        button.turn_off()
                        self._cache[i] = button._off_value
                else:
                    in_loop = (i * self._blocksize * self._quantization < self._loop_end) and (
                        i * self._blocksize * self._quantization >= self._loop_start
                    )
                    playing = (
                        self._playhead != None
                        and self._playhead >= i * self._blocksize * self._quantization
                        and self._playhead < (i + 1) * self._blocksize * self._quantization
                    )
                    selected = i == self.block
                    if in_loop:
                        if playing:
                            if selected:
                                self._cache[i] = "StepSequencer.LoopSelector.SelectedPlaying"
                            else:
                                self._cache[i] = "StepSequencer.LoopSelector.Playing"
                        else:
                            if selected:
                                self._cache[i] = "StepSequencer.LoopSelector.Selected"
                            else:
                                self._cache[i] = "StepSequencer.LoopSelector.InLoop"
                    else:
                        if playing:
                            if selected:
                                self._cache[i] = "StepSequencer.LoopSelector.SelectedPlaying"
                            else:
                                self._cache[i] = "StepSequencer.LoopSelector.Playing"
                        else:
                            if selected:
                                self._cache[i] = "StepSequencer.LoopSelector.Selected"
                            else:
                                self._cache[i] = "DefaultButton.Disabled"

                    if self._cache[i] != button._on_value or self._force:
                        button.set_on_off_values(self._cache[i], self._cache[i])
                        button.turn_on()
                i = i + 1
            self._force = False

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
        new_notes = list()
        for note in list(self._note_cache):
            if note[1] < start or note[1] >= end:
                new_notes.append(note)
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
