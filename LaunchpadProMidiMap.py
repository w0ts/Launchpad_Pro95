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


class MidiMap(SpecialMidiMap):

    def __init__(self, *a, **k):

        super().__init__(*a, **k)

        # left buttons
        left_button_names = (
            "Session_Record_Button",
            "Double_Loop_Button",
            "Duplicate_Button",
            "Quantize_Button",
            "Delete_Button",
            "Undo_Button",
            "Click_Button",
            "Shift_Button",
        )
        default_states = {True: "DefaultButton.On", False: "DefaultButton.Off"}
        rec_states = {True: "Recording.On", False: "Recording.Off"}
        shift_states = {True: "Misc.ShiftOn", False: "Misc.Shift"}

        for index, val in enumerate(left_button_names):
            if val in ("Session_Record_Button", "Undo_Button", "Click_Button"):
                self.add_button(
                    val,
                    0,
                    (index + 1) * 10,
                    MIDI_CC_TYPE,
                    default_states=rec_states if val == "Session_Record_Button" else default_states,
                )
            else:
                self.add_modifier_button(
                    val,
                    0,
                    (index + 1) * 10,
                    MIDI_CC_TYPE,
                    default_states=shift_states if val == "Shift_Button" else default_states,
                )

        # bottom buttons
        self.add_button(
            "Record_Arm_Mode_Button",
            0,
            1,
            MIDI_CC_TYPE,
            default_states={True: "Mode.RecordArm.On", False: "Mode.RecordArm.Off"},
        )
        self.add_button(
            "Track_Select_Mode_Button",
            0,
            2,
            MIDI_CC_TYPE,
            default_states={True: "Mode.TrackSelect.On", False: "Mode.TrackSelect.Off"},
        )
        self.add_button(
            "Mute_Mode_Button", 0, 3, MIDI_CC_TYPE, default_states={True: "Mode.Mute.On", False: "Mode.Mute.Off"}
        )
        self.add_button(
            "Solo_Mode_Button", 0, 4, MIDI_CC_TYPE, default_states={True: "Mode.Solo.On", False: "Mode.Solo.Off"}
        )
        self.add_button(
            "Volume_Mode_Button", 0, 5, MIDI_CC_TYPE, default_states={True: "Mode.Volume.On", False: "Mode.Volume.Off"}
        )
        self.add_button(
            "Pan_Mode_Button", 0, 6, MIDI_CC_TYPE, default_states={True: "Mode.Pan.On", False: "Mode.Pan.Off"}
        )
        self.add_button(
            "Sends_Mode_Button", 0, 7, MIDI_CC_TYPE, default_states={True: "Mode.Sends.On", False: "Mode.Sends.Off"}
        )
        self.add_button(
            "Stop_Clip_Mode_Button",
            0,
            8,
            MIDI_CC_TYPE,
            default_states={True: "Mode.StopClip.On", False: "Mode.StopClip.Off"},
        )

        # top buttons
        self._arrow_button_names = ["Arrow_Up_Button", "Arrow_Down_Button", "Arrow_Left_Button", "Arrow_Right_Button"]
        arrow_button_states = {
            "Pressed": "DefaultButton.On",
            "Enabled": "DefaultButton.Off",
            True: "DefaultButton.On",
            False: "DefaultButton.Disabled",
        }
        for index, val in enumerate(self._arrow_button_names):
            self.add_button(val, 0, index + 91, MIDI_CC_TYPE, default_states=arrow_button_states)

        self.add_modifier_button(
            "Session_Mode_Button",
            0,
            95,
            MIDI_CC_TYPE,
            default_states={True: "Mode.Session.On", False: "Mode.Session.Off"},
            element_factory=make_multi_button,
        )
        self.add_button(
            "Note_Mode_Button",
            0,
            96,
            MIDI_CC_TYPE,
            element_factory=make_multi_button,
            default_states={True: "Mode.Drum.On", False: "Mode.Drum.Off"},
        )
        self.add_button(
            "Device_Mode_Button",
            0,
            97,
            MIDI_CC_TYPE,
            default_states={True: "Mode.Device.On", False: "Mode.Device.Off"},
            element_factory=make_multi_button,
        )
        self.add_button(
            "User_Mode_Button",
            0,
            98,
            MIDI_CC_TYPE,
            default_states={True: "Mode.User.On", False: "Mode.User.Off"},
            element_factory=make_multi_button,
            color_slaves=True,
        )

        # scene buttons
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

        # main matrix
        self.add_matrix(
            "Main_Button_Matrix",
            make_button,
            0,
            [[identifier for identifier in range(start, start + NUM_TRACKS)] for start in range(81, 10, -10)],
            MIDI_NOTE_TYPE,
        )

        # User
        # self.add_matrix('User_Button_Matrix', make_button, 5, [ [ identifier for identifier in xrange(start, start + NUM_TRACKS) ] for start in xrange(81, 10, -10) ], MIDI_NOTE_TYPE)
        # self.add_button('User_Scene_1', 5, 99, MIDI_NOTE_TYPE, default_states={True: 'Mode.User.On', False: 'Mode.User.Off'})
        # self.add_button('User_Scene_2', 5, 100, MIDI_NOTE_TYPE, default_states={True: 'Mode.User.On', False: 'Mode.User.Off'})
        # self.add_button('User_Scene_3', 5, 101, MIDI_NOTE_TYPE, default_states={True: 'Mode.User.On', False: 'Mode.User.Off'})
        # self.add_button('User_Scene_4', 5, 102, MIDI_NOTE_TYPE, default_states={True: 'Mode.User.On', False: 'Mode.User.Off'})
        # self.add_button('User_Scene_5', 5, 103, MIDI_NOTE_TYPE, default_states={True: 'Mode.User.On', False: 'Mode.User.Off'})
        # self.add_button('User_Scene_6', 5, 104, MIDI_NOTE_TYPE, default_states={True: 'Mode.User.On', False: 'Mode.User.Off'})
        # self.add_button('User_Scene_7', 5, 105, MIDI_NOTE_TYPE, default_states={True: 'Mode.User.On', False: 'Mode.User.Off'})
        # self.add_button('User_Scene_8', 5, 106, MIDI_NOTE_TYPE, default_states={True: 'Mode.User.On', False: 'Mode.User.Off'})

        # mixer button matrix
        self["Mixer_Button_Matrix"] = self["Main_Button_Matrix"].submatrix[:, 7:]
        self["Mixer_Button_Matrix"].name = "Mixer_Button_Matrix"

        # matrix with session button pressed ?
        matrix_rows_with_session_button_raw = [
            [self.with_session_button(self["Main_Button_Matrix_Raw"][row][column]) for column in range(8)]
            for row in range(8)
        ]
        self["Main_Button_Matrix_With_Session_Button"] = ButtonMatrixElement(
            rows=matrix_rows_with_session_button_raw, name="Main_Button_Matrix_With_Session_Button"
        )

        # note matrix
        note_buttons_raw = []
        for identifier in range(128):
            if identifier not in self["Main_Button_Matrix_Ids"]:
                button = make_button("Note_Button_" + str(identifier), 0, identifier, MIDI_NOTE_TYPE)
                button.set_enabled(False)
                button.set_channel(CHROM_MAP_CHANNEL)
                note_buttons_raw.append(button)
        self["Note_Button_Matrix"] = ButtonMatrixElement(rows=[note_buttons_raw], name="Note_Button_Matrix")

        def make_raw_drum_matrix():
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
                        button_row.append(
                            make_button("Drum_Note_Button_" + str(identifier), 0, identifier, MIDI_NOTE_TYPE)
                        )

                result.append(button_row)

            return result

        # drum matrix
        self["Drum_Button_Matrix"] = ButtonMatrixElement(rows=make_raw_drum_matrix(), name="Drum_Button_Matrix")

        # slider matrix
        self.add_matrix(
            "Slider_Button_Matrix", make_slider, 0, [[identifier for identifier in range(21, 29)]], MIDI_CC_TYPE
        )
        for index, slider in enumerate(self["Slider_Button_Matrix_Raw"][0]):
            slider.set_index(index)

    def with_shift(self, button_name):
        return ComboElement(self[button_name], modifiers=[self["Shift_Button"]], name="Shifted_" + button_name)

    def with_session_button(self, button):
        return ComboElement(button, modifiers=[self["Session_Mode_Button"]], name=button.name + "_With_Session_Button")
