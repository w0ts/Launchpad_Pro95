from functools import partial

from _Framework.Control import ButtonControl, PlayableControl, control_matrix
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from _Framework.Layer import Layer
from _Framework.ModesComponent import LayerMode, ModesComponent

from .consts import (
    DR_MAP_CHANNEL,
    DRUM_LAYOUT_SYSEX_BYTE,
    SESSION_LAYOUT_SYSEX_BYTE,
    SYSEX_PARAM_BYTE_STANDALONE_LAYOUT,
    USER_LAYOUT_SYSEX_BYTE,
)
from .NoteComponent import NoteComponent
from .ScaleComponent import ScaleComponent


class InstrumentComponent(ControlSurfaceComponent):
    """
    handles notes mode and switches between note, drum and dummy audio mode.
    """

    def __init__(self, control_surface, drum_component=None, *a, **k):

        self._control_surface = control_surface
        self._drum_component = drum_component
        self._implicit_arm = True
        self._modes = ModesComponent(name="Instrument_Modes", is_enabled=False)
        self._modes.set_enabled = self.set_enabled
        self._feedback_channels = [
            DR_MAP_CHANNEL,
            DR_MAP_CHANNEL + 1,
            DR_MAP_CHANNEL + 2,
            DR_MAP_CHANNEL + 3,
            DR_MAP_CHANNEL + 4,
        ]
        self._non_feedback_channel = DR_MAP_CHANNEL + 5

        self._common_component = CommonModeComponent(instrument_component=self, control_surface=self._control_surface)
        self._scale_component = ScaleComponent(control_surface=self._control_surface, enabled=True)
        self._note_component = NoteComponent(
            control_surface=self._control_surface,
            feedback_channels=self._feedback_channels,
            non_feedback_channel=self._non_feedback_channel,
            get_pattern=self._scale_component.get_pattern,
        )

        super().__init__(*a, **k)

    def _layout(self, layout_byte):
        """The layout sysex sent on entering an instrument sub mode."""
        setup = self._control_surface._layout_setup
        return [
            partial(setup, SESSION_LAYOUT_SYSEX_BYTE),
            partial(setup, layout_byte, SYSEX_PARAM_BYTE_STANDALONE_LAYOUT),
        ]

    def set_layers(self, midimap):
        scene_buttons = midimap["Scene_Launch_Button_Matrix_Raw"][0]
        common_layer_mode = LayerMode(
            self._common_component,
            layer=Layer(
                arrow_left_button=midimap["Arrow_Left_Button"],
                arrow_right_button=midimap["Arrow_Right_Button"],
                arrow_up_button=midimap["Arrow_Up_Button"],
                arrow_down_button=midimap["Arrow_Down_Button"],
                scale_button=scene_buttons[0],
                scale_up_button=scene_buttons[1],
                scale_down_button=scene_buttons[2],
                dummy_button=scene_buttons[3],
                play_button=scene_buttons[6],
                stop_button=scene_buttons[7],
            ),
        )
        self._add_drum_mode(midimap, common_layer_mode)
        self._add_matrix_mode("scale_mode", self._scale_component, midimap, common_layer_mode)
        self._add_matrix_mode("note_mode", self._note_component, midimap, common_layer_mode)
        self._add_audio_mode(midimap, common_layer_mode)

    def _add_drum_mode(self, midimap, common_layer_mode):
        scene_buttons = midimap["Scene_Launch_Button_Matrix_Raw"][0]
        drum_group_layer_mode = LayerMode(
            self._control_surface._drum_group,
            layer=Layer(
                mute_button=scene_buttons[4],
                solo_button=scene_buttons[5],
                drum_matrix=midimap["Main_Button_Matrix"],
            ),
        )
        self._modes.add_mode(
            "drum_mode",
            self._layout(USER_LAYOUT_SYSEX_BYTE)
            + [
                # called here, once: the mode gets its result (None)
                self._control_surface._setup_drum_group(),
                drum_group_layer_mode,
                common_layer_mode,
            ],
        )

    def _add_matrix_mode(self, name, component, midimap, common_layer_mode):
        """The scale editor or the note pads on the grid."""
        layer_mode = LayerMode(component, layer=Layer(matrix=midimap["Main_Button_Matrix"]))
        self._modes.add_mode(name, self._layout(USER_LAYOUT_SYSEX_BYTE) + [layer_mode, common_layer_mode])

    def _add_audio_mode(self, midimap, common_layer_mode):
        audio_layer_mode = LayerMode(AudioModeComponent(), layer=Layer(matrix=midimap["Main_Button_Matrix"]))
        self._modes.add_mode(
            "audio_mode",
            self._layout(DRUM_LAYOUT_SYSEX_BYTE)
            + [self._control_surface._clip_delete_layer_mode, common_layer_mode, audio_layer_mode],
        )

    def set_enabled(self, enabled):
        if not enabled:
            self._do_implicit_arm(enabled)
        ControlSurfaceComponent.set_enabled(self, enabled)
        ModesComponent.set_enabled(self._modes, enabled)
        if enabled:
            self._do_implicit_arm(enabled)

    def _detect_mode(self):
        track = self._control_surface._target_track_component.target_track
        # drum_device = self._control_surface._drum_group_finder.drum_group
        self._control_surface._setup_drum_group()
        if (
            track is None
            or track.is_foldable
            or track in self.song().return_tracks
            or track == self.song().master_track
            or track.is_frozen
            or track.has_audio_input
        ):
            self.set_mode("audio_mode")
            self._scale_component._is_drumrack = False
        elif self._control_surface._drum_group._drum_group_device:
            self._scale_component._is_drumrack = True
            self.set_mode("drum_mode")
        else:
            self._scale_component._is_drumrack = False
            self.set_mode("note_mode")

    def get_pattern(self):
        return self._scale_component.get_pattern()

    def on_selected_track_changed(self):
        if self._implicit_arm:
            # self._control_surface._setup_drum_group()
            self._detect_mode()
            self._do_implicit_arm()

    def update(self):
        self._modes.update()

    def on_selected_scene_changed(self):
        # self._do_implicit_arm()
        self.update()

    def set_mode(self, mode):
        self._modes.selected_mode = mode
        self._modes.update()

    def get_mode(self):
        return self._modes.selected_mode

    def can_implicit_arm_track(self, track):
        # todo
        return track.can_be_armed and track.has_midi_input

    def _do_implicit_arm(self, arm=True):
        if self._is_enabled:
            if self._implicit_arm and arm:
                self._control_surface.set_feedback_channels(self._feedback_channels)
                self._control_surface.set_controlled_track(self._control_surface._target_track_component.target_track)
            else:
                self._control_surface.release_controlled_track()

            for track in self.song().tracks:
                if self.can_implicit_arm_track(track):
                    track.implicit_arm = (
                        self._is_enabled
                        and self._implicit_arm
                        and arm
                        and self._control_surface._target_track_component.target_track == track
                    )


class AudioModeComponent(ControlSurfaceComponent):

    matrix = control_matrix(PlayableControl)

    def __init__(self, control_surface=None, *a, **k):
        self._control_surface = control_surface
        self._layout_set = False
        super().__init__(*a, **k)

    def set_matrix(self, matrix):
        if not matrix or not self._layout_set:
            self.matrix.set_control_element(matrix)
            for button in self.matrix:
                button.color = "DefaultButton.Disabled"
                # button.enabled = False
            self._layout_set = bool(matrix)


class CommonModeComponent(ControlSurfaceComponent):

    arrow_up_button = ButtonControl(
        color="Mode.Note.Off", pressed_color="Mode.Note.On", disabled_color="DefaultButton.Disabled"
    )
    arrow_down_button = ButtonControl(
        color="Mode.Note.Off", pressed_color="Mode.Note.On", disabled_color="DefaultButton.Disabled"
    )
    arrow_left_button = ButtonControl(
        color="Mode.Note.Off", pressed_color="Mode.Note.On", disabled_color="DefaultButton.Disabled"
    )
    arrow_right_button = ButtonControl(
        color="Mode.Note.Off", pressed_color="Mode.Note.On", disabled_color="DefaultButton.Disabled"
    )

    scale_button = ButtonControl(
        color="Mode.Note.Off", pressed_color="Mode.Note.On", disabled_color="DefaultButton.Disabled"
    )
    scale_up_button = ButtonControl(
        color="Mode.Note.Off", pressed_color="Mode.Note.On", disabled_color="DefaultButton.Disabled"
    )
    scale_down_button = ButtonControl(
        color="Mode.Note.Off", pressed_color="Mode.Note.On", disabled_color="DefaultButton.Disabled"
    )
    dummy_button = ButtonControl(
        color="DefaultButton.Disabled", pressed_color="DefaultButton.Disabled", disabled_color="DefaultButton.Disabled"
    )

    play_button = ButtonControl(
        color="Mode.Note.Off", pressed_color="Mode.Note.On", disabled_color="DefaultButton.Disabled"
    )
    stop_button = ButtonControl(
        color="Mode.Note.Off", pressed_color="Mode.Note.On", disabled_color="DefaultButton.Disabled"
    )

    def __init__(self, control_surface=None, instrument_component=None, *a, **k):
        self._control_surface = control_surface
        self._instrument_component = instrument_component
        super().__init__(*a, **k)

    @arrow_right_button.pressed
    def _next_track(self, button):
        if self.selected_track_idx < len(self.song().tracks) - 1:
            self.song().view.selected_track = self.song().tracks[self.selected_track_idx + 1]

    @arrow_left_button.pressed
    def _prev_track(self, button):
        if self.selected_track_idx > 0:
            self.song().view.selected_track = self.song().tracks[self.selected_track_idx - 1]

    @arrow_up_button.pressed
    def _prev_scene(self, button):
        if self.selected_scene_idx > 0:
            self.song().view.selected_scene = self.song().scenes[self.selected_scene_idx - 1]

    @arrow_down_button.pressed
    def _next_scene(self, button):
        if self.selected_scene_idx < len(self.song().scenes) - 1:
            self.song().view.selected_scene = self.song().scenes[self.selected_scene_idx + 1]

    @play_button.pressed
    def _play(self, button):
        if self.selected_scene != None:
            slot = self.selected_scene.clip_slots[self.selected_track_idx]
            slot.fire()
            self._control_surface.show_message("fire clip")

    @stop_button.pressed
    def _stop(self, button):
        if self.selected_scene != None:
            slot = self.selected_scene.clip_slots[self.selected_track_idx]
            slot.stop()
            self._control_surface.show_message("stop clip")

    @scale_up_button.pressed
    def _scale_up(self, button):
        if self._instrument_component.get_mode() == "drum_mode":
            self._instrument_component._drum_component.scroll_up()
        else:
            self._instrument_component._scale_component.octave_up()
        self._instrument_component._note_component.update_matrix_mapping()

    @scale_down_button.pressed
    def _scale_down(self, button):
        if self._instrument_component.get_mode() == "drum_mode":
            self._instrument_component._drum_component.scroll_down()
        else:
            self._instrument_component._scale_component.octave_down()
        self._instrument_component._note_component.update_matrix_mapping()

    @scale_button.pressed
    def enter_scale(self, button):
        self._instrument_component._scale_component.set_enabled(True)
        self._previous_mode = self._instrument_component.get_mode()
        self._previous_scale_mode = self._instrument_component._scale_component._is_drumrack
        self._instrument_component.set_mode("scale_mode")

    @scale_button.released
    def leave_scale(self, button):
        self._instrument_component._scale_component.set_enabled(False)
        if self._previous_scale_mode != self._instrument_component._scale_component._is_drumrack:
            if self._instrument_component._scale_component._is_drumrack:
                self._instrument_component.set_mode("drum_mode")
            else:
                self._instrument_component.set_mode("note_mode")
        else:
            self._instrument_component.set_mode(self._previous_mode)

    @property
    def selected_track(self):
        return self.song().view.selected_track

    @property
    def selected_track_idx(self):
        return list(self.song().tracks).index(self.song().view.selected_track)
        # return self.tuple_idx(self.song().tracks, self.song().view.selected_track)

    @property
    def selected_scene_idx(self):
        return list(self.song().scenes).index(self.song().view.selected_scene)
        # return self.tuple_idx(self.song().scenes, self.song().view.selected_scene)

    @property
    def selected_scene(self):
        return self.song().view.selected_scene
