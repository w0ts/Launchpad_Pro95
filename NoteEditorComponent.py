"""The drum step sequencer's note grid: in normal mode 4 rows of 8 steps of the selected note,
in multinote mode one or more rows per note. Pads add, delete, mute (mute shift) or change the
velocity (velocity held) of notes; the velocity button picks the velocity of new notes."""

import time

from _Framework.ControlSurfaceComponent import ControlSurfaceComponent

from .ButtonHelpers import rebind_button
from .ClipNotes import read_all_notes, write_all_notes
from .GridBuffer import GridBufferMixin

VELOCITY_LONG_PRESS_SECONDS = 0.5  # a shorter tap on velocity (no pad pressed) cycles the velocity


class NoteEditorComponent(GridBufferMixin, ControlSurfaceComponent):

    def __init__(self, stepsequencer=None, matrix=None, control_surface=None):
        ControlSurfaceComponent.__init__(self)
        self.set_enabled(False)
        self._stepsequencer = stepsequencer
        self._control_surface = control_surface
        self._clip = None
        self._note_cache = None
        self._playhead = None

        # playback step indicator
        self.display_metronome = True

        # playback page indicator
        self._current_page = -1

        # velocities of new notes, and their colours
        self.velocity_map = [20, 50, 80, 105, 127]
        self.velocity_color_map = [
            "StepSequencer.NoteEditor.Velocity0",
            "StepSequencer.NoteEditor.Velocity1",
            "StepSequencer.NoteEditor.Velocity2",
            "StepSequencer.NoteEditor.Velocity3",
            "StepSequencer.NoteEditor.Velocity4",
        ]

        # other colors
        self.muted_note_color = "StepSequencer.NoteEditor.Muted"
        self.playing_note_color = "StepSequencer.NoteEditor.Playing"

        self.long_button_press = VELOCITY_LONG_PRESS_SECONDS

        # buttons
        self._matrix = None
        self._velocity_button = None

        # displayed page
        self._page = 0

        # notes
        self._key_indexes = [36, 37, 38, 39, 40, 41, 42, 43]
        self._key_index_is_in_scale = [True, False, True, True, False, True, False, True]
        self._key_index_is_root_note = [True, False, False, False, False, False, False, False]
        self._number_of_lines_per_note = 1

        # clip
        self._force_update = True

        # quantization
        self._quantization = 16

        # velocity
        self._velocity_index = 2
        self._velocity = self.velocity_map[self._velocity_index]
        self._is_velocity_shifted = False
        self._velocity_notes_pressed = 0
        self._velocity_last_press = time.time()

        # modes
        self._is_mute_shifted = False
        self._is_mutlinote = False

        if matrix != None:
            self.set_matrix(matrix)

    def disconnect(self):
        self.set_matrix(None)
        self.set_velocity_button(None)
        self._clip = None
        super().disconnect()

    @property
    def is_multinote(self):
        return self._is_mutlinote

    def set_multinote(self, is_mutlinote, number_of_lines_per_note):
        self._is_mutlinote = is_mutlinote
        self._number_of_lines_per_note = number_of_lines_per_note

    @property
    def quantization(self):
        return self._quantization

    def set_quantization(self, quantization):
        self._quantization = quantization

    @property
    def key_indexes(self):
        return self._key_indexes

    def set_key_indexes(self, key_indexes):
        self._key_indexes = key_indexes

    def set_key_index_is_in_scale(self, key_index_is_in_scale):
        self._key_index_is_in_scale = key_index_is_in_scale

    def set_key_index_is_root_note(self, key_index_is_root_note):
        self._key_index_is_root_note = key_index_is_root_note

    @property
    def height(self):
        return self._height

    def set_height(self, height):
        self._height = height

    @property
    def width(self):
        return self._width

    @property
    def number_of_lines_per_note(self):
        if self.is_multinote:
            return self._number_of_lines_per_note
        else:
            return self.height

    def set_page(self, page):
        if self.is_multinote:
            self._page = page
        else:
            self._page = int(page / 4)  # 4 lines per note (32 steps seq)

    def set_clip(self, clip):
        self._clip = clip

    def set_note_cache(self, note_cache):
        self._note_cache = note_cache

    def set_playhead(self, playhead):  # Playing cursor
        self._playhead = playhead
        self._update_matrix()

    def update(self, force=False):
        if self.is_enabled():
            if force:
                self._force_update = True
            self._update_velocity_button()
            self._update_matrix()

    # MATRIX

    def set_matrix(self, matrix):
        if matrix != self._matrix:
            if self._matrix != None:
                self._matrix.remove_value_listener(self._matrix_value)
            self._matrix = matrix
            if self._matrix != None:
                self._matrix.add_value_listener(self._matrix_value)
                self._width = self._matrix.width()
                self._reset_grid_buffers()

    def _update_matrix(self):
        if self.is_enabled() and self._matrix != None:
            self._fill_grid(self.width, self.height, "DefaultButton.Disabled")
            if self._clip != None and self._note_cache != None:
                self._draw_clip()
            self._flush_grid(self.width, self.height)

    def _play_position(self):
        """(page, row, x, y) of the playhead, all -1 when the clip does not play."""
        if self._playhead == None:
            return -1, -1, -1, -1
        steps = self._playhead / self.quantization
        page = int(steps / self.width / self.number_of_lines_per_note)
        row = int(steps / self.width) % self.number_of_lines_per_note
        return page, row, int(steps) % self.width, int(steps / self.width) % self.height

    def _draw_clip(self):
        play_page, play_row, play_x, play_y = self._play_position()
        if self.display_metronome and self._clip.is_playing and self.song().is_playing:
            self._grid_back_buffer[play_x][play_y] = "StepSequencer.NoteEditor.Metronome"
        if self.is_multinote:
            # notes in the left column, then the page being played
            self._display_note_markers()
            if self._current_page != play_page:
                self._current_page = play_page
                self._display_current_page()
        for note in self._note_cache:
            self._draw_note(note, play_page, play_row, play_x, play_y)

    def _note_grid_position(self, pitch, position):
        """(page, x, y, row in the note's lines) of a note; x and y are -1 off the grid."""
        steps = position / self.quantization
        page = int(steps / self.width / self.number_of_lines_per_note)
        x = int(steps) % self.width
        row = int(steps / self.width) % self.number_of_lines_per_note
        try:
            note_index = self.key_indexes.index(pitch)
        except ValueError:
            note_index = -1
        if self.is_multinote:
            base_y = note_index * self.number_of_lines_per_note
            if base_y >= 0:
                base_y = (7 - base_y) - (self.number_of_lines_per_note - 1)
            if base_y < 0:
                base_y = -1
        else:
            base_y = 0 if note_index == 0 else -1
        if base_y != -1 and base_y < self.height:
            return page, x, base_y + row, row
        return page, -1, -1, row

    def _velocity_color(self, velocity):
        color = self.velocity_color_map[0]
        for index in range(len(self.velocity_map)):
            if velocity >= self.velocity_map[index]:
                color = self.velocity_color_map[index]
        return color

    def _draw_note(self, note, play_page, play_row, play_x, play_y):
        pitch, position, _duration, velocity, muted = note
        page, x, y, row = self._note_grid_position(pitch, position)
        if x < 0:
            return
        on_play_cell = (play_y == y and not self.is_multinote) or (self.is_multinote and row == play_row)
        if (
            not muted
            and page == play_page
            and play_x == x
            and on_play_cell
            and self.song().is_playing
            and self._clip.is_playing
        ):
            # highlight playing notes, even if they are from other pages
            self._grid_back_buffer[x][y] = self.playing_note_color
        elif page == self._page and self._grid_back_buffer[x][y] != self.playing_note_color:
            self._grid_back_buffer[x][y] = self.muted_note_color if muted else self._velocity_color(velocity)

    def _display_note_markers(self):
        """Marks the root notes (3 pads) and the other notes of the scale (1 pad) on the left."""
        for i in range(0, int(self.height / self.number_of_lines_per_note)):
            if self._key_index_is_root_note[i]:
                columns = (0, 1, 2)
            elif self._key_index_is_in_scale[i]:
                columns = (0,)
            else:
                continue
            for j in range(0, self.number_of_lines_per_note):
                y = self.height - i * self.number_of_lines_per_note - j - 1
                for x in columns:
                    self._grid_back_buffer[x][y] = "StepSequencer.NoteEditor.NoteMarker"

    def _display_current_page(self):
        """Marks the column of the page being played (in multinote mode)."""
        for i in range(0, self._height):
            if self._page == self._current_page:
                self._grid_back_buffer[self._current_page % self.width][
                    i
                ] = "StepSequencer.NoteEditor.CurrentPageMarkerPlay"
            else:
                self._grid_back_buffer[self._current_page % self.width][
                    i
                ] = "StepSequencer.NoteEditor.CurrentPageMarker"

    # PADS: add, delete, mute (mute shift) or change the velocity (velocity held) of a note

    def _matrix_value(self, value, x, y, is_momentary):
        # height is 8 (multinote) or 4 (normal)
        if self.is_enabled() and y < self.height and (value != 0 or not is_momentary):
            self._matrix_value_message([value, x, y, is_momentary])

    def _matrix_value_message(self, values):  # (value=127/0, x=idx, y=idx, is_momentary=True)
        value, x, y, is_momentary = values
        assert self._matrix != None
        assert value in range(128)
        assert x in range(self._matrix.width())
        assert y in range(self._matrix.height())
        assert isinstance(is_momentary, bool)

        if self.is_enabled() and self._clip == None:
            self._stepsequencer.create_clip()
        elif self.is_enabled() and self._clip != None and (value != 0 or not is_momentary):
            if self._is_velocity_shifted:
                self._velocity_notes_pressed = self._velocity_notes_pressed + 1
            pitch, step_time = self._pad_pitch_and_time(x, y)
            self._refresh_note_cache()
            write_all_notes(self._clip, self._toggled_notes(pitch, step_time))
            self._refresh_note_cache()

    def _pad_pitch_and_time(self, x, y):
        lines = self.number_of_lines_per_note
        if self.is_multinote:
            step = self._page * self.width * lines + x + (y % lines * self.width)
            pitch = self._key_indexes[int(8 / lines) - 1 - int(y / lines)]
        else:
            step = self._page * self.width * lines + y * self.width + x
            pitch = self._key_indexes[0]
        return pitch, self.quantization * step

    def _refresh_note_cache(self):
        note_cache = read_all_notes(self._clip)
        if self._note_cache != note_cache:
            self._note_cache = note_cache

    def _toggled_notes(self, pitch, step_time):
        """The notes with the pad's note changed: next velocity (velocity held), mute toggled
        (mute shift) or deleted; or a new note when the pad has none."""
        note_cache = list(self._note_cache)
        for note in note_cache:
            if pitch == note[0] and step_time == note[1]:
                note_cache.remove(note)
                if self._is_velocity_shifted:
                    note_cache.append([note[0], note[1], note[2], self._next_velocity(note[3]), note[4]])
                elif self._is_mute_shifted:
                    note_cache.append([note[0], note[1], note[2], note[3], not note[4]])
                return note_cache
        note_cache.append([pitch, step_time, self.quantization, self._velocity, self._is_mute_shifted])
        return note_cache

    def _next_velocity(self, velocity):
        new_velocity_index = 0
        for index in range(len(self.velocity_map)):
            if velocity >= self.velocity_map[index]:
                new_velocity_index = (index + 1) % len(self.velocity_map)
        return self.velocity_map[new_velocity_index]

    # VELOCITY BUTTON: a tap cycles the velocity of new notes; held, pads change the velocity of
    # notes and the note selector pads play the track

    def _update_velocity_button(self):
        if self.is_enabled() and self._velocity_button != None:
            if self._clip != None:
                if self._is_velocity_shifted:
                    self._velocity_button.set_on_off_values("StepSequencer.NoteEditor.VelocityShifted")
                    self._velocity_button.turn_on()
                else:
                    self._velocity_button.set_light("StepSequencer.NoteEditor.Velocity" + str(self._velocity_index))
            else:
                self._velocity_button.set_light("DefaultButton.Disabled")

    def set_velocity_button(self, button):
        if button != self._velocity_button:
            self._velocity_button = rebind_button(self._velocity_button, button, self._velocity_value, True)

    def _velocity_value(self, value, sender):
        assert self._velocity_button != None
        assert value in range(128)
        if self.is_enabled():
            if (value == 0) or (not sender.is_momentary()):
                self._velocity_released()
            if (value != 0) or (not sender.is_momentary()):
                self._velocity_pressed()
            self._stepsequencer._note_selector.update()

    def _velocity_released(self):
        tapped = time.time() - self._velocity_last_press < self.long_button_press
        if self._velocity_notes_pressed == 0 and tapped:
            self._velocity_index = (len(self.velocity_map) + self._velocity_index + 1) % len(self.velocity_map)
            self._velocity = self.velocity_map[self._velocity_index]
        self._stepsequencer._track_controller._implicit_arm = False
        if self._is_velocity_shifted:
            self._stepsequencer._track_controller._do_implicit_arm(False)
        self._is_velocity_shifted = False
        self._update_velocity_button()

    def _velocity_pressed(self):
        self._velocity_notes_pressed = 0
        self._is_velocity_shifted = True
        # arm the track so that the note selector pads play it
        self._stepsequencer._track_controller._implicit_arm = True
        self._stepsequencer._track_controller._do_implicit_arm(True)
        self._velocity_last_press = time.time()
        self._update_velocity_button()

    # MUTE SHIFT ON A NOTE SELECTOR PAD

    def mute_lane(self, pitch_to_mute):
        """Toggle the mute of every note of that pitch."""
        if self.is_enabled() and self._clip != None:
            self._refresh_note_cache()
            note_cache = list(self._note_cache)
            notes_changed = 0
            for note in self._note_cache:
                if note[0] == pitch_to_mute:
                    notes_changed = notes_changed + 1
                    note_cache.remove(note)
                    note_cache.append([note[0], note[1], note[2], note[3], not note[4]])
            if notes_changed > 0:
                write_all_notes(self._clip, note_cache)
            self.update()
