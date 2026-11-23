"""The Launchpad Pro's buttons, pads and faders, by name."""

from _Framework.ButtonMatrixElement import ButtonMatrixElement
from _Framework.ComboElement import ComboElement
from _Framework.InputControlElement import MIDI_CC_TYPE, MIDI_NOTE_TYPE

from .consts import (
    CHROM_MAP_CHANNEL,
)
from .SpecialMidiMap import SpecialMidiMap, make_button, make_multi_button, make_slider

NUM_TRACKS = 8
NUM_SCENES = 8


# Round buttons on the left, top first (CC 10, 20... 80).
LEFT_BUTTONS = (
    "Session_Record_Button",
    "Double_Loop_Button",
    "Duplicate_Button",
    "Quantize_Button",
    "Delete_Button",
    "Undo_Button",
    "Click_Button",
    "Shift_Button",
)
# Round buttons at the bottom, left first (CC 1 to 8): name, skin of their LED.
BOTTOM_BUTTONS = (
    ("Record_Arm_Mode_Button", "Mode.RecordArm"),
    ("Track_Select_Mode_Button", "Mode.TrackSelect"),
    ("Mute_Mode_Button", "Mode.Mute"),
    ("Solo_Mode_Button", "Mode.Solo"),
    ("Volume_Mode_Button", "Mode.Volume"),
    ("Pan_Mode_Button", "Mode.Pan"),
    ("Sends_Mode_Button", "Mode.Sends"),
    ("Stop_Clip_Mode_Button", "Mode.StopClip"),
)


def _states(skin):
    return {True: skin + ".On", False: skin + ".Off"}


class MidiMap(SpecialMidiMap):

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._add_left_buttons()
        self._add_bottom_buttons()
        self._add_top_buttons()
        self._add_scene_buttons()
        self._add_main_matrix()
        self._add_note_matrix()
        self["Drum_Button_Matrix"] = ButtonMatrixElement(rows=self._make_raw_drum_matrix(), name="Drum_Button_Matrix")
        self._add_sliders()

    def _add_left_buttons(self):
        default_states = {True: "DefaultButton.On", False: "DefaultButton.Off"}
        rec_states = {True: "Recording.On", False: "Recording.Off"}
        shift_states = {True: "Misc.ShiftOn", False: "Misc.Shift"}
        for index, name in enumerate(LEFT_BUTTONS):
            identifier = (index + 1) * 10
            if name in ("Session_Record_Button", "Undo_Button", "Click_Button"):
                states = rec_states if name == "Session_Record_Button" else default_states
                self.add_button(name, 0, identifier, MIDI_CC_TYPE, default_states=states)
            else:
                states = shift_states if name == "Shift_Button" else default_states
                self.add_modifier_button(name, 0, identifier, MIDI_CC_TYPE, default_states=states)

    def _add_bottom_buttons(self):
        for index, (name, skin) in enumerate(BOTTOM_BUTTONS):
            self.add_button(name, 0, index + 1, MIDI_CC_TYPE, default_states=_states(skin))

    def _add_top_buttons(self):
        self._arrow_button_names = ["Arrow_Up_Button", "Arrow_Down_Button", "Arrow_Left_Button", "Arrow_Right_Button"]
        arrow_button_states = {
            "Pressed": "DefaultButton.On",
            "Enabled": "DefaultButton.Off",
            True: "DefaultButton.On",
            False: "DefaultButton.Disabled",
        }
        for index, name in enumerate(self._arrow_button_names):
            self.add_button(name, 0, index + 91, MIDI_CC_TYPE, default_states=arrow_button_states)
        self.add_modifier_button(
            "Session_Mode_Button",
            0,
            95,
            MIDI_CC_TYPE,
            default_states=_states("Mode.Session"),
            element_factory=make_multi_button,
        )
        self.add_button(
            "Note_Mode_Button",
            0,
            96,
            MIDI_CC_TYPE,
            element_factory=make_multi_button,
            default_states=_states("Mode.Drum"),
        )
        self.add_button(
            "Device_Mode_Button",
            0,
            97,
            MIDI_CC_TYPE,
            default_states=_states("Mode.Device"),
            element_factory=make_multi_button,
        )
        self.add_button(
            "User_Mode_Button",
            0,
            98,
            MIDI_CC_TYPE,
            default_states=_states("Mode.User"),
            element_factory=make_multi_button,
            color_slaves=True,
        )

    def _add_scene_buttons(self):
        self.add_matrix(
            "Scene_Launch_Button_Matrix",
            make_button,
            0,
            [[identifier for identifier in range(89, 18, -10)]],
            MIDI_CC_TYPE,
        )
        self["Scene_Stop_Button_Matrix"] = self["Scene_Launch_Button_Matrix"].submatrix[:7, :]
        self["Scene_Stop_Button_Matrix"].name = "Scene_Stop_Button_Matrix"
        self["Stop_All_Clips_Button"] = self["Scene_Launch_Button_Matrix_Raw"][0][7]

    def _add_main_matrix(self):
        self.add_matrix(
            "Main_Button_Matrix",
            make_button,
            0,
            [[identifier for identifier in range(start, start + NUM_TRACKS)] for start in range(81, 10, -10)],
            MIDI_NOTE_TYPE,
        )
        # the bottom row, for the mixer modes
        self["Mixer_Button_Matrix"] = self["Main_Button_Matrix"].submatrix[:, 7:]
        self["Mixer_Button_Matrix"].name = "Mixer_Button_Matrix"
        # the pads with the session button held
        matrix_rows_with_session_button_raw = [
            [self.with_session_button(self["Main_Button_Matrix_Raw"][row][column]) for column in range(8)]
            for row in range(8)
        ]
        self["Main_Button_Matrix_With_Session_Button"] = ButtonMatrixElement(
            rows=matrix_rows_with_session_button_raw, name="Main_Button_Matrix_With_Session_Button"
        )

    def _add_note_matrix(self):
        """Every other note, for the instrument mode's translations."""
        note_buttons_raw = []
        for identifier in range(128):
            if identifier not in self["Main_Button_Matrix_Ids"]:
                button = make_button("Note_Button_" + str(identifier), 0, identifier, MIDI_NOTE_TYPE)
                button.set_enabled(False)
                button.set_channel(CHROM_MAP_CHANNEL)
                note_buttons_raw.append(button)
        self["Note_Button_Matrix"] = ButtonMatrixElement(rows=[note_buttons_raw], name="Note_Button_Matrix")

    def _make_raw_drum_matrix(self):
        result = []
        for row in range(7, -1, -1):
            button_row = []
            row_offset = 8 + (7 - row) * 4
            for column in range(8):
                column_offset = 28 if column >= 4 else 0
                identifier = row * 8 + column + row_offset + column_offset
                # this Main_Button_Matrix_Ids seems not to be set anywhere....
                matrix_coords = self["Main_Button_Matrix_Ids"].get(identifier)
                if matrix_coords:
                    button_row.append(self["Main_Button_Matrix_Raw"][matrix_coords[1]][matrix_coords[0]])
                else:
                    button_row.append(make_button("Drum_Note_Button_" + str(identifier), 0, identifier, MIDI_NOTE_TYPE))
            result.append(button_row)
        return result

    def _add_sliders(self):
        self.add_matrix(
            "Slider_Button_Matrix", make_slider, 0, [[identifier for identifier in range(21, 29)]], MIDI_CC_TYPE
        )
        for index, slider in enumerate(self["Slider_Button_Matrix_Raw"][0]):
            slider.set_index(index)

    def with_shift(self, button_name):
        return ComboElement(self[button_name], modifiers=[self["Shift_Button"]], name="Shifted_" + button_name)

    def with_session_button(self, button):
        return ComboElement(button, modifiers=[self["Session_Mode_Button"]], name=button.name + "_With_Session_Button")
