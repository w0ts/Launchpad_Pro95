"""The melodic step sequencer's grid: one column per step, the 7 scale degrees as rows, with
pitch, octave, velocity and length pages (see MelodicPageButtons.py)."""

from random import randrange

from _Framework.ButtonMatrixElement import ButtonMatrixElement
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent

from .ClipLoop import set_loop_and_markers
from .ClipNotes import write_all_notes
from .GridBuffer import GridBufferMixin
from .MelodicPageButtons import (
    STEPSEQ_MODE_NOTES,
    STEPSEQ_MODE_NOTES_LENGTHS,
    STEPSEQ_MODE_NOTES_OCTAVES,
    STEPSEQ_MODE_NOTES_VELOCITIES,
    MelodicPageButtonsMixin,
)

LANES = 7  # scale degrees shown, one per row
OCTAVES = 7  # octave index 0..6 = octave offset -2..+4
MIN_STEPS = 128  # the step lists grow past this when the clip needs more
STEPS_PER_PAGE = 8
TOP_VALUE = 6  # the top row of the octave, velocity and length pages

# TODO :
# extend / clear region (possible via drum step seq for now)
# not even clip lengths (using shift notes ?)
# store scale settings per clip or track ?
# display current scale mode in osd


class MelodicNoteEditorComponent(MelodicPageButtonsMixin, GridBufferMixin, ControlSurfaceComponent):

    def __init__(self, control_surface=None, step_sequencer=None, matrix=None, side_buttons=None):
        ControlSurfaceComponent.__init__(self)
        self._control_surface = control_surface
        self._step_sequencer = step_sequencer

        # clip
        self._clip = None
        self._note_cache = []
        self._force_update = True
        self._init_data()

        self._velocity_map = [0, 30, 60, 80, 100, 115, 127]
        self._length_map = [1, 2, 3, 4, 8, 16, 32]

        # time
        self._playhead = 0
        self._page = 0

        # notes
        self._key_indexes = [36, 37, 38, 39, 40, 41, 42, 43]
        self._key_index_is_in_scale = [True, False, True, True, False, True, False, True]
        self._key_index_is_root_note = [True, False, False, False, False, False, False, False]
        self._is_monophonic = False

        # quantization
        self._quantization = 16

        # MODE
        self._mode = STEPSEQ_MODE_NOTES

        # buttons
        self._init_page_buttons()
        self._matrix = None

        self._is_velocity_shifted = False
        self._is_mute_shifted = False

    def disconnect(self):
        self._step_sequencer = None
        self.set_matrix(None)
        self.set_random_button(None)
        self.set_mode_notes_lengths_button(None)
        self.set_mode_notes_octaves_button(None)
        self.set_mode_notes_velocities_button(None)
        self.set_mode_notes_pitches_button(None)
        self._notes_pitches = None
        self._notes_velocities = None
        self._notes_octaves = None
        self._notes_lengths = None
        self._clip = None
        super().disconnect()

    def _init_data(self):
        self._notes_pitches = [0] * (LANES * MIN_STEPS)
        self._notes_velocities = [4] * MIN_STEPS
        self._notes_octaves = [2] * MIN_STEPS
        self._notes_lengths = [3] * MIN_STEPS
        # Notes of the clip that light a pad, by step; notes the grid cannot show (muted,
        # extra notes in mono mode, before time 0, off the scale lanes or octaves) are kept untouched.
        self._shown_notes = {}
        self._kept_notes = []
        # What the grid gave, by step, when the clip was last read or written: a step whose
        # grid notes did not change keeps the clip's own notes.
        self._grid_steps = {}

    def _ensure_steps(self, count):
        """Grow the per-step lists so that steps 0..count-1 exist."""
        missing = count - len(self._notes_velocities)
        if missing > 0:
            self._notes_pitches.extend([0] * (LANES * missing))
            self._notes_velocities.extend([4] * missing)
            self._notes_octaves.extend([2] * missing)
            self._notes_lengths.extend([3] * missing)

    def set_mode(self, mode):
        self._mode = mode
        self._force_update = True
        self.update()

    def set_clip(self, clip):
        if self._clip != clip:
            self._init_data()
            self._clip = clip
            # a new clip with the same notes (a duplicate) must still be parsed
            self._note_cache = None

    def set_note_cache(self, note_cache):
        if self._note_cache != note_cache:
            self._note_cache = note_cache
            self._parse_notes()

    def set_playhead(self, playhead):
        self._playhead = playhead
        self._update_matrix()

    def set_multinote(self, x=0, y=0):
        pass

    @property
    def quantization(self):
        return self._quantization

    def set_quantization(self, quantization):
        old_quantize = self._quantization
        self._quantization = quantization
        # keep the loop on the same steps
        if self._clip != None and old_quantize != self._quantization:
            loop_start = self._clip.loop_start * self._quantization / old_quantize
            loop_end = self._clip.loop_end * self._quantization / old_quantize
            set_loop_and_markers(self._clip, loop_start, loop_end)
        self._update_clip_notes()

    def set_key_indexes(self, key_indexes):
        if self._key_indexes != key_indexes:
            self._key_indexes = key_indexes
            self._update_clip_notes()

    def set_key_index_is_in_scale(self, key_index_is_in_scale):
        self._key_index_is_in_scale = key_index_is_in_scale

    def set_key_index_is_root_note(self, key_index_is_root_note):
        self._key_index_is_root_note = key_index_is_root_note

    def set_page(self, page):
        self._page = page
        self._ensure_steps((page + 1) * 8)

    def _step_of(self, time):
        """The step a note time falls in, or None before time 0."""
        if time < 0:
            return None
        return int(time // self._quantization)

    def _lane_of(self, pitch, octave):
        """The lane (scale degree row) showing pitch in the given octave index, or None."""
        for lane in range(min(LANES, len(self._key_indexes))):
            if pitch == self._key_indexes[lane] + 12 * (octave - 2):
                return lane
        return None

    def _lane_and_octave_of(self, pitch):
        for lane in range(min(LANES, len(self._key_indexes))):
            for octave in range(OCTAVES):
                if pitch == self._key_indexes[lane] + 12 * (octave - 2):
                    return lane, octave
        return None

    def _set_step_from_note(self, step, note):
        """The first note of a step sets the step's velocity and length."""
        velocity, length = note[3], note[2]
        for x in range(7):
            if velocity >= self._velocity_map[x]:
                self._notes_velocities[step] = x
        for x in range(7):
            if length * 4 >= self._length_map[x] * self._quantization:
                self._notes_lengths[step] = x

    def _parse_notes(self):
        notes = list(self._note_cache or ())
        steps = [self._step_of(note[1]) for note in notes]
        self._ensure_steps(max([s + 1 for s in steps if s is not None] + [0]))
        self._notes_pitches = [0] * len(self._notes_pitches)

        # the first unmuted note of a step that fits a lane sets the step's octave
        first = {}
        for index, note in enumerate(notes):
            step = steps[index]
            if step is None or note[4] or step in first:
                continue
            found = self._lane_and_octave_of(note[0])
            if found is not None:
                first[step] = index
                self._notes_octaves[step] = found[1]
                self._set_step_from_note(step, note)

        # a note is shown when it is on a lane in its step's octave; the others are kept
        shown = {}
        kept = []
        for index, note in enumerate(notes):
            step = steps[index]
            lane = None if step is None else self._lane_of(note[0], self._notes_octaves[step])
            if lane is None or note[4] or (self._is_monophonic and first.get(step) != index):
                kept.append(note)
                continue
            self._notes_pitches[step * LANES + lane] = 1
            shown.setdefault(step, []).append(note)
        self._shown_notes = shown
        self._kept_notes = kept
        self._grid_steps = self._notes_from_grid()
        self._update_matrix()

    def _notes_from_grid(self):
        """step -> the (pitch, time, length, velocity) notes the grid gives for that step."""
        steps = {}
        for x in range(len(self._notes_velocities)):
            for note_index in range(LANES):
                if self._notes_pitches[x * LANES + note_index] == 1:
                    time = x * self._quantization
                    velocity = self._velocity_map[self._notes_velocities[x]]
                    length = self._length_map[self._notes_lengths[x]] * self._quantization / 4.0
                    pitch = self._key_indexes[note_index] + 12 * (self._notes_octaves[x] - 2)
                    if pitch >= 0 and pitch < 128 and velocity >= 0 and velocity < 128 and length >= 0:
                        steps.setdefault(x, []).append((pitch, time, length, velocity))
        return steps

    def _update_clip_notes(self):
        """Write the grid to the clip. Only the steps the grid changed are rewritten: other
        steps keep the clip's notes as they are, and notes the grid cannot show are kept."""
        if self._clip != None and self._step_sequencer.is_enabled():
            grid = self._notes_from_grid()
            note_cache = list(self._kept_notes)
            shown = {}
            for step in sorted(set(grid) | set(self._shown_notes)):
                if grid.get(step) == self._grid_steps.get(step):
                    step_notes = self._shown_notes.get(step, [])
                else:
                    step_notes = [
                        (pitch, time, length, velocity, False) for (pitch, time, length, velocity) in grid.get(step, ())
                    ]
                if step_notes:
                    shown[step] = step_notes
                note_cache.extend(step_notes)
            # before writing: Live may call the notes listener (and parse) during the write
            self._shown_notes = shown
            self._grid_steps = grid
            write_all_notes(self._clip, note_cache)

    def update(self, force=False):
        if force:
            self._force_update = True
        if self.is_enabled():
            self._update_page_buttons()
            self._update_matrix()

    def request_display_page(self):
        pass

    def set_height(self, height):
        pass

    # MATRIX

    def set_matrix(self, matrix):
        assert isinstance(matrix, (ButtonMatrixElement, type(None)))
        self._reset_grid_buffers()
        if matrix != self._matrix:
            if self._matrix != None:
                self._matrix.remove_value_listener(self._matrix_value)
            self._matrix = matrix
            if self._matrix != None:
                self._matrix.add_value_listener(self._matrix_value)

    def _pitch_index(self, step, y):
        return step * LANES + 6 - y

    def _update_matrix(self):  # step grid LEDs are updated here
        if self.is_enabled() and self._matrix != None:
            self._fill_grid(8, 8, 0)
            if self._clip != None:
                self._draw_steps()
                if self._playhead != None:
                    self._draw_playhead()
            else:
                self._fill_grid(8, LANES, "DefaultButton.Disabled")
            self._flush_grid(8, LANES)

    def _draw_steps(self):
        self._ensure_steps((self._page + 1) * STEPS_PER_PAGE)
        if self._playhead != None:
            self._ensure_steps(int(self._playhead / self.quantization) + 1)
        for x in range(STEPS_PER_PAGE):
            step = x + STEPS_PER_PAGE * self._page
            has_note = any(self._notes_pitches[self._pitch_index(step, y)] == 1 for y in range(LANES))
            for y in range(LANES):
                self._grid_back_buffer[x][y] = self._step_color(step, y, has_note)

    def _step_color(self, step, y, has_note):
        """The colour of row y of a step on the current page."""
        if self._mode == STEPSEQ_MODE_NOTES:
            if self._notes_pitches[self._pitch_index(step, y)] == 1:
                return "StepSequencer2.Pitch.On"
            return "StepSequencer2.Pitch.Off"
        if self._mode == STEPSEQ_MODE_NOTES_OCTAVES:
            if self._notes_octaves[step] != TOP_VALUE - y:
                return "StepSequencer2.Octave.Off"
            return "StepSequencer2.Octave.On" if has_note else "StepSequencer2.Octave.Dim"
        if self._mode == STEPSEQ_MODE_NOTES_VELOCITIES:
            if self._notes_velocities[step] < TOP_VALUE - y:
                return "StepSequencer2.Velocity.Off"
            return "StepSequencer2.Velocity.On" if has_note else "StepSequencer2.Velocity.Dim"
        if self._mode == STEPSEQ_MODE_NOTES_LENGTHS:
            if self._notes_lengths[step] < TOP_VALUE - y:
                return "StepSequencer2.Length.Off"
            return "StepSequencer2.Length.On" if has_note else "StepSequencer2.Length.Dim"
        return 0

    def _draw_playhead(self):
        """The metronome on the lowest row, and the notes being played on the pitch page."""
        play_position = int(self._playhead / self.quantization)
        play_x_position = int(self._playhead / self.quantization) % STEPS_PER_PAGE
        in_page = int(self._playhead / self.quantization / STEPS_PER_PAGE) == self._page
        if in_page:
            self._grid_back_buffer[play_x_position][6] = "StepSequencer2.NoteEditor.MetronomeInPage"
        else:
            self._grid_back_buffer[play_x_position][6] = "StepSequencer2.NoteEditor.MetronomeInOtherPage"
        if self._mode == STEPSEQ_MODE_NOTES:
            for y in range(LANES):
                if self._notes_pitches[self._pitch_index(play_position, y)] == 1:
                    if in_page:
                        self._grid_back_buffer[play_x_position][y] = "StepSequencer2.NoteEditor.PlayInPage"
                    else:
                        self._grid_back_buffer[play_x_position][y] = "StepSequencer2.NoteEditor.PlayInOtherPage"

    # PADS

    def _edited_steps(self):
        """(start, end) steps a held page button edits: the loop, or this page when the page is
        outside the loop."""
        start = int(self._clip.loop_start / self._quantization)
        end = int(self._clip.loop_end / self._quantization)
        if (self._page + 1) * STEPS_PER_PAGE > end or self._page * STEPS_PER_PAGE < start:
            start = self._page * STEPS_PER_PAGE
            end = (self._page + 1) * STEPS_PER_PAGE
        return max(start, 0), end

    def _matrix_value(self, value, x, y, is_momentary):  # matrix buttons listener
        if self.is_enabled() and self._matrix != None:
            if self._clip == None:
                self._step_sequencer.create_clip()
            else:
                start, end = self._edited_steps()
                self._ensure_steps(max(end, (self._page + 1) * STEPS_PER_PAGE))
                if ((value != 0) or (not is_momentary)) and y < LANES:
                    self._edit_page(x, y, start, end)
                    self._update_matrix()
                    self._update_clip_notes()

    def _edit_page(self, x, y, start, end):
        if self._mode == STEPSEQ_MODE_NOTES:
            self._edit_pitches(x, y, start, end)
        elif self._mode == STEPSEQ_MODE_NOTES_OCTAVES:
            self._edit_step_values(self._notes_octaves, x, y, start, end, self._is_notes_octaves_shifted)
        elif self._mode == STEPSEQ_MODE_NOTES_VELOCITIES:
            self._edit_step_values(self._notes_velocities, x, y, start, end, self._is_notes_velocities_shifted)
        elif self._mode == STEPSEQ_MODE_NOTES_LENGTHS:
            self._edit_step_values(self._notes_lengths, x, y, start, end, self._is_notes_lengths_shifted)

    def _edit_pitches(self, x, y, start, end):
        if self._is_notes_pitches_shifted:
            # every step of the loop plays this degree only
            for step in range(start, end):
                for row in range(LANES):
                    self._notes_pitches[self._pitch_index(step, row)] = 0
                self._notes_pitches[self._pitch_index(step, y)] = 1
            return
        index = self._pitch_index(x + STEPS_PER_PAGE * self._page, y)
        if self._notes_pitches[index] == 1:
            self._notes_pitches[index] = 0
        else:
            if self._is_monophonic:
                for row in range(LANES):
                    self._notes_pitches[self._pitch_index(x + STEPS_PER_PAGE * self._page, row)] = 0
            self._notes_pitches[index] = 1

    def _edit_step_values(self, values, x, y, start, end, shifted):
        """Octave, velocity or length page: the pad's row for its step; with the page button held,
        the left half sets every step of the loop to the row and the right half moves them one
        up (top rows) or down (bottom rows)."""
        if not shifted:
            values[x + STEPS_PER_PAGE * self._page] = TOP_VALUE - y
        elif x < 4:
            for step in range(start, end):
                values[step] = TOP_VALUE - y
        else:
            for step in range(start, end):
                if y < 3 and values[step] < TOP_VALUE:
                    values[step] = values[step] + 1
                if y > 3 and values[step] > 0:
                    values[step] = values[step] - 1

    # RANDOM

    def _randomise(self):
        start, end = self._edited_steps()
        self._ensure_steps(end)
        for x in range(start, end):
            if self._mode == STEPSEQ_MODE_NOTES:
                val2 = randrange(0, 9)
                for y in range(LANES):
                    self._notes_pitches[self._pitch_index(x, y)] = val2 == y
            elif self._mode == STEPSEQ_MODE_NOTES_OCTAVES:
                self._notes_octaves[x] = randrange(2, 6)
            elif self._mode == STEPSEQ_MODE_NOTES_VELOCITIES:
                self._notes_velocities[x] = randrange(0, 7)
            elif self._mode == STEPSEQ_MODE_NOTES_LENGTHS:
                self._notes_lengths[x] = randrange(0, 4)
        self._update_clip_notes()
