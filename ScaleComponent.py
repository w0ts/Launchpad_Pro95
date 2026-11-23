"""The scale editor (instrument mode and step sequencers) and the scales and note layouts.

Scale editor pads, top row first: absolute root, (unused), the layouts (chromatic guitar,
diatonic not staggered, diatonic chords, diatonic, chromatic) and drum rack; rows 2 and 3:
the keys as on a piano, with relative scale, circle of fifths (both ways) and quick scale on
the free pads; row 4: the octave; rows 5 to 8: the scales."""

from _Framework.ControlSurfaceComponent import ControlSurfaceComponent

KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
CIRCLE_OF_FIFTHS = [7 * k % 12 for k in range(12)]

MUSICAL_MODES = [
    "Major",
    [0, 2, 4, 5, 7, 9, 11],
    "Minor",
    [0, 2, 3, 5, 7, 8, 10],
    "Dorian",
    [0, 2, 3, 5, 7, 9, 10],
    "Mixolydian",
    [0, 2, 4, 5, 7, 9, 10],
    "Lydian",
    [0, 2, 4, 6, 7, 9, 11],
    "Phrygian",
    [0, 1, 3, 5, 7, 8, 10],
    "Locrian",
    [0, 1, 3, 5, 6, 8, 10],
    "Diminished",
    [0, 1, 3, 4, 6, 7, 9, 10],
    "Whole-half",
    [0, 2, 3, 5, 6, 8, 9, 11],
    "Whole Tone",
    [0, 2, 4, 6, 8, 10],
    "Minor Blues",
    [0, 3, 5, 6, 7, 10],
    "Minor Pentatonic",
    [0, 3, 5, 7, 10],
    "Major Pentatonic",
    [0, 2, 4, 7, 9],
    "Harmonic Minor",
    [0, 2, 3, 5, 7, 8, 11],
    "Melodic Minor",
    [0, 2, 3, 5, 7, 9, 11],
    "Super Locrian",
    [0, 1, 3, 4, 6, 8, 10],
    "Bhairav",
    [0, 1, 4, 5, 7, 8, 11],
    "Hungarian Minor",
    [0, 2, 3, 6, 7, 8, 11],
    "Minor Gypsy",
    [0, 1, 4, 5, 7, 8, 10],
    "Hirojoshi",
    [0, 2, 3, 7, 8],
    "In-Sen",
    [0, 1, 5, 7, 10],
    "Iwato",
    [0, 1, 5, 6, 10],
    "Kumoi",
    [0, 2, 3, 7, 9],
    "Pelog",
    [0, 1, 3, 4, 7, 8],
    "Spanish",
    [0, 1, 3, 4, 5, 6, 8, 10],
    "IonEol",
    [0, 2, 3, 4, 5, 7, 8, 9, 10, 11],
]


# Top row layout pads: column -> (mode, interval, horizontal, message).
LAYOUT_PADS = {
    2: ("chromatic_gtr", 3, True, "mode: chromatic gtr"),
    3: ("diatonic_ns", 3, True, "mode: diatonic not staggered"),
    4: ("diatonic_chords", 2, False, "mode: diatonic vertical (chords)"),
    5: ("diatonic", 3, True, "mode: diatonic"),
    6: ("chromatic", 3, True, "mode: chromatic"),
}
# C  D  E  F  G  A  B  (C)
WHITE_KEYS = [0, 2, 4, 5, 7, 9, 11, 12]
BLACK_KEY_COLUMNS = (0, 1, 3, 4, 5)  # on the second row, the key above each white key
MAJOR, MINOR, MINOR_PENTATONIC, MAJOR_PENTATONIC = 0, 1, 11, 12
MINOR_MODES = (1, 13, 14)  # scales whose relative is the major scale
SCALE_ROWS = 4  # the scales fill the 4 bottom rows


class ScaleComponent(ControlSurfaceComponent):

    def __init__(self, control_surface=None, enabled=False, mode="diatonic", *a, **k):
        self._modus_list = [Modus(MUSICAL_MODES[v], MUSICAL_MODES[v + 1]) for v in range(0, len(MUSICAL_MODES), 2)]
        self._modus_names = [MUSICAL_MODES[v] for v in range(0, len(MUSICAL_MODES), 2)]
        self._control_surface = control_surface
        self._modus = 0
        self._key = 0
        self._octave = 3
        self._mode = mode  # chromatic, diatonic
        self._is_drumrack = False
        self._custom_scale = False
        self._custom_keys = [True] * 12
        self._is_horizontal = True
        self._is_absolute = False
        self._interval = 3
        self._matrix = None

        # C  D  E  F  G  A  B
        self._white_notes_index = WHITE_KEYS[:7]

        self._current_minor_mode = MINOR

        super().__init__(*a, **k)
        self.set_enabled(enabled)

    @property
    def notes(self):
        return self.modus.scale(self._key).notes

    @property
    def modus(self):
        return self._modus_list[self._modus]

    def set_key(self, key, message=True):
        if key >= 0 and key <= 11:
            self._key = key % 12
            if message:
                self._control_surface.show_message(
                    str("selected key: " + KEY_NAMES[self._key]) + " " + str(self._modus_names[self._modus])
                )

    def set_octave(self, octave, message=True):
        if octave >= 0 and octave <= 7:
            self._octave = octave
            if message:
                self._control_surface.show_message("selected octave: " + str(octave))

    def octave_up(self, message=True):
        self.set_octave(self._octave + 1, message)

    def octave_down(self, message=True):
        self.set_octave(self._octave - 1, message)

    def set_modus(self, index, message=True):
        if index > -1 and index < len(self._modus_list):
            self._modus = index
            if message:
                self._control_surface.show_message(
                    str("selected scale: " + KEY_NAMES[self._key]) + " " + str(self._modus_names[self._modus])
                )

    def set_matrix(self, matrix):
        if matrix:
            matrix.reset()
        if matrix != self._matrix and self._matrix != None:
            self._matrix.remove_value_listener(self._matrix_pressed)
        self._matrix = matrix
        if self._matrix != None:
            self._matrix.add_value_listener(self._matrix_pressed)
        self.update()

    # LEDS

    def update(self):
        if self.is_enabled() and self._matrix != None:
            super().update()
            for button, (col, row) in self._matrix.iterbuttons():
                button.set_enabled(True)
                button.set_light(self._pad_color(col, row))
                if (col, row) == (2, 0):
                    button.turn_on()

    def _pad_color(self, col, row):
        if row == 0:
            return self._layout_pad_color(col)
        if row in (1, 2):
            return self._key_pad_color(col, row)
        if row == 3:
            return "Scale.Octave.On" if self._octave == col else "Scale.Octave.Off"
        return self._modus_pad_color(col, row)

    def _layout_pad_color(self, col):
        if col == 0:
            return "Scale.AbsoluteRoot.On" if self._is_absolute else "Scale.AbsoluteRoot.Off"
        if col == 1:
            return "DefaultButton.Disabled"
        if col == 7:
            return "Scale.Mode.On" if self.is_drumrack else "Scale.Mode.Off"
        selected = not self.is_drumrack and self._mode == LAYOUT_PADS[col][0]
        return "Scale.Mode.On" if selected else "Scale.Mode.Off"

    def _key_pad_color(self, col, row):
        if self.is_drumrack:
            return "DefaultButton.Disabled"
        if (col, row) == (2, 1):
            return "DefaultButton.Disabled" if self._custom_scale else "Scale.RelativeScale"
        if (col, row) in ((6, 1), (7, 2)):
            return "DefaultButton.Disabled" if self._custom_scale else "Scale.CircleOfFifths"
        if (col, row) == (7, 1):
            return "Scale.QuickScale.On" if self._custom_scale else "Scale.QuickScale.Off"
        key = self._white_notes_index[col] + (1 if row == 1 else 0)
        if self._custom_scale:
            return "Scale.Key.On" if self._custom_keys[key] else "Scale.Key.Off"
        return "Scale.Key.On" if self._key == key else "Scale.Key.Off"

    def _modus_pad_color(self, col, row):
        if self.is_drumrack or self._custom_scale:
            return "DefaultButton.Disabled"
        index = (row - SCALE_ROWS) * 8 + col
        if row == 7 and index > len(self._modus_list):
            return "DefaultButton.Disabled"
        return "Scale.Modus.On" if self._modus == index else "Scale.Modus.Off"

    # PADS

    def _matrix_pressed(self, value, x, y, is_momentary):
        if self.is_enabled() and value > 0:
            if y == 0:
                self._layout_pad_pressed(x)
            if not self.is_drumrack:
                self._key_pad_pressed(x, y)
            if y == 1 and x == 7 and not self.is_drumrack:
                self._custom_scale = not self._custom_scale
                self._control_surface.show_message("Quick scale : " + ("ON" if self._custom_scale else "OFF"))
            if y == 3:
                self._octave = x
                self._control_surface.show_message("octave : " + str(self._octave))
            if y >= SCALE_ROWS and not self.is_drumrack:
                self.set_modus((y - SCALE_ROWS) * 8 + x)
                self._control_surface.show_message("mode : " + str(self._modus_names[self._modus]))
            self.update()

    def _layout_pad_pressed(self, x):
        if not self.is_drumrack:
            if x == 0:
                self._is_absolute = not self._is_absolute
                self._control_surface.show_message("absolute root" if self._is_absolute else "relative root")
            if x == 1:
                self._is_horizontal = not self._is_horizontal
        if x in LAYOUT_PADS:
            self._mode, self._interval, self._is_horizontal, message = LAYOUT_PADS[x]
            self._is_drumrack = False
            self._control_surface.show_message(message)
        if x == 7:
            self._is_drumrack = True
            self._control_surface.show_message("mode: drumrack")

    def _key_pad_pressed(self, x, y):
        """Rows 2 and 3: a key (or a quick scale key), the circle of fifths or the relative scale."""
        root = -1
        selected_modus = self._modus
        if y == 1 and x in BLACK_KEY_COLUMNS or y == 2 and x < 7:
            key = WHITE_KEYS[x] + (1 if y == 1 else 0)
            if self._custom_scale:
                self._custom_keys[key] = not self._custom_keys[key]
            else:
                root = key
                self._control_surface.show_message("root " + KEY_NAMES[root])
        if y == 2 and x == 7:
            root = self._circle_of_fifths(1, "->")
        if y == 1 and x == 6:
            root = self._circle_of_fifths(-1, "<-")
        if y == 1 and x == 2:
            root, selected_modus = self._relative_scale()
        if root != -1:
            self.set_modus(selected_modus)
            self.set_key(root)

    def _circle_of_fifths(self, step, arrow):
        root = CIRCLE_OF_FIFTHS[(CIRCLE_OF_FIFTHS.index(self._key) + step + 12) % 12]
        scale = str(self._modus_names[self._modus])
        self._control_surface.show_message(
            f"circle of 5ths {arrow} " + KEY_NAMES[self._key] + " " + scale + " => " + KEY_NAMES[root] + " " + scale
        )
        return root

    def _relative_scale(self):
        """(root, scale) of the relative major or minor scale; root is -1 for the other scales."""
        root = -1
        selected_modus = self._modus
        position = CIRCLE_OF_FIFTHS.index(self._key)
        if self._modus == MAJOR:
            selected_modus = self._current_minor_mode
            root = CIRCLE_OF_FIFTHS[(position + 3) % 12]
        elif self._modus in MINOR_MODES:
            self._current_minor_mode = selected_modus
            selected_modus = MAJOR
            root = CIRCLE_OF_FIFTHS[(position - 3 + 12) % 12]
        elif self._modus == MINOR_PENTATONIC:
            selected_modus = MAJOR_PENTATONIC
            root = CIRCLE_OF_FIFTHS[(position + 3) % 12]
        elif self._modus == MAJOR_PENTATONIC:
            selected_modus = MINOR_PENTATONIC
            root = CIRCLE_OF_FIFTHS[(position - 3 + 12) % 12]
        # (for another scale root stays -1 and the message names "B")
        self._control_surface.show_message(
            "Relative scale : " + KEY_NAMES[root] + " " + str(self._modus_names[selected_modus])
        )
        return root, selected_modus

    @property
    def is_drumrack(self):
        return self._is_drumrack

    @property
    def is_diatonic(self):
        return not self.is_drumrack and (
            self._mode == "diatonic" or self._mode == "diatonic_ns" or self._mode == "diatonic_chords"
        )

    @property
    def is_chromatic(self):
        return not self.is_drumrack and (self._mode == "chromatic" or self._mode == "chromatic_gtr")

    @property
    def is_diatonic_ns(self):
        return self._mode == "diatonic_ns"

    @property
    def is_chromatic_gtr(self):
        return self._mode == "chromatic_gtr"

    def get_pattern(self):
        if self._custom_scale:
            notes = []
            for n in range(12):
                if self._custom_keys[n]:
                    notes.append(n)
            if len(notes) == 0:
                notes = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        else:
            notes = self.notes

        # origin
        if not self._is_absolute:
            origin = 0
        elif self.is_diatonic:
            origin = 0
            for k in range(len(notes)):
                if notes[k] >= 12:
                    origin = k - len(notes)
                    break
        else:
            origin = -notes[0]

        # interval
        if self._interval == None:
            interval = 8
        elif self.is_chromatic:
            interval = [0, 2, 4, 5, 7, 9, 10, 11][self._interval]
        else:
            interval = self._interval

        # layout
        if self._is_horizontal:
            steps = [1, interval]
            origin = [origin, 0]
        else:
            steps = [interval, 1]
            origin = [0, origin]

        return MelodicPattern(
            steps=steps,
            scale=notes,
            origin=origin,
            base_note=int((self._octave + 1) * 12),
            chromatic_mode=self.is_chromatic,
            chromatic_gtr_mode=self.is_chromatic_gtr,
            diatonic_ns_mode=self.is_diatonic_ns,
        )


class Scale:

    def __init__(self, name, notes, *a, **k):
        super().__init__(*a, **k)
        self.name = name
        self.notes = notes


class Modus(Scale):

    def __init__(self, *a, **k):
        super().__init__(*a, **k)

    def scale(self, base_note):
        return Scale(KEY_NAMES[base_note], [base_note + x for x in self.notes])


class MelodicPattern:

    def __init__(
        self,
        steps=None,
        scale=range(12),
        base_note=0,
        origin=None,
        valid_notes=range(128),
        chromatic_mode=False,
        chromatic_gtr_mode=False,
        diatonic_ns_mode=False,
        *a,
        **k,
    ):
        super().__init__(*a, **k)
        self.steps = steps if steps is not None else [0, 0]
        self.scale = scale
        self.base_note = base_note
        self.origin = origin if origin is not None else [0, 0]
        self.valid_notes = valid_notes
        self.chromatic_mode = chromatic_mode
        self.chromatic_gtr_mode = chromatic_gtr_mode
        self.diatonic_ns_mode = diatonic_ns_mode

    class NoteInfo:

        def __init__(self, index, channel, root=False, highlight=False, in_scale=False, valid=False):
            self.index = index
            self.channel = channel
            self.root = root
            self.highlight = highlight
            self.in_scale = in_scale
            self.valid = valid

    @property
    def _extended_scale(self):
        if self.chromatic_mode:
            first_note = self.scale[0]
            return range(first_note, first_note + 12)
        else:
            return self.scale

    def _octave_and_note(self, x, y):
        scale = self._extended_scale
        scale_size = len(scale)
        if self.chromatic_mode:
            self.steps[1] = 5
        else:
            if self.diatonic_ns_mode:
                self.steps[1] = scale_size
        index = self.steps[0] * (self.origin[0] + x) + self.steps[1] * (self.origin[1] + y)
        if self.chromatic_gtr_mode and y > 3:
            index = index - 1
        octave = index // scale_size
        note = scale[index % scale_size]
        return (octave, note)

    def note(self, x, y):
        octave, note = self._octave_and_note(x, y)
        index = self.base_note + 12 * octave + note
        if not 0 <= index < 128:
            index = None  # outside the MIDI range: the pad plays nothing
        root = note == self.scale[0]
        if len(self.scale) < 5:
            highlight = False
        else:
            highlight = note == self.scale[2] or note == self.scale[4]
        in_scale = note in self.scale
        valid = index is not None and index in self.valid_notes
        return self.NoteInfo(index, x, root=root, highlight=highlight, in_scale=in_scale, valid=valid)
