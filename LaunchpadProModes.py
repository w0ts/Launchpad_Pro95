"""The Launchpad Pro's main modes (session, note, device, user and the mixer modes) and the
user button's sub modes (drum and melodic step sequencers, user)."""

from functools import partial

from _Framework.Layer import Layer
from _Framework.ModesComponent import AddLayerMode, LayerMode, ModesComponent, ReenterBehaviour

from .BackgroundComponent import BackgroundComponent
from .consts import (
    DRUM_LAYOUT_SYSEX_BYTE,
    FADER_LAYOUT_SYSEX_BYTE,
    PAN_MAP_CHANNEL,
    SESSION_LAYOUT_SYSEX_BYTE,
    SYSEX_PARAM_BYTE_STANDALONE_LAYOUT,
    USER_LAYOUT_SYSEX_BYTE,
    VOLUME_MAP_CHANNEL,
)
from .SpecialModesComponent import CancelingReenterBehaviour, SpecialReenterBehaviour
from .SpecialSessionComponent import SessionZoomingManagerComponent
from .TranslationComponent import TranslationComponent

# The user button's sub modes, in cycling order: name -> (LED skin of the user button, message).
USER_SUB_MODES = {
    "stepsequencer_mode": ("Mode.StepSequencer", "drum step sequencer"),
    "stepsequencer2_mode": ("Mode.StepSequencer2", "melodic step sequencer"),
    "user_mode": ("Mode.User", "user mode"),
}


class LaunchpadProModesMixin:
    """Builds self._modes; mixed into Launchpad_Pro95."""

    def _create_translation(self, comp_name, channel, button_layer, should_enable=True, should_reset=True):
        translation_component = TranslationComponent(
            name=comp_name,
            translated_channel=channel,
            should_enable=should_enable,
            should_reset=should_reset,
            is_enabled=False,
            layer=button_layer,
        )
        setattr(self, "_" + comp_name.lower(), translation_component)
        return translation_component

    def _scene_button(self, index):
        """The index-th round button on the right, top first."""
        return self._midimap["Scene_Launch_Button_Matrix_Raw"][0][index]

    def _create_modes(self):
        self._modes = ModesComponent(name="Launchpad_Modes", is_enabled=False)
        self._session_layer_mode = AddLayerMode(
            self._session,
            Layer(
                scene_launch_buttons=self._midimap["Scene_Launch_Button_Matrix"],
                clip_launch_buttons=self._midimap["Main_Button_Matrix"],
                delete_button=self._midimap["Delete_Button"],
                duplicate_button=self._midimap["Duplicate_Button"],
                double_button=self._midimap["Double_Loop_Button"],
                quantize_button=self._midimap["Quantize_Button"],
            ),
        )
        action_button_background = BackgroundComponent(name="No_Op_Buttons")
        self._action_button_background_layer_mode = LayerMode(
            action_button_background,
            Layer(
                delete_button=self._midimap["Delete_Button"],
                quantize_button=self._midimap["Quantize_Button"],
                duplicate_button=self._midimap["Duplicate_Button"],
                double_button=self._midimap["Double_Loop_Button"],
            ),
        )
        # used by the instrument component's audio mode
        self._clip_delete_layer_mode = AddLayerMode(
            self._clip_actions_component, layer=Layer(delete_button=self._midimap["Delete_Button"])
        )
        self._create_session_zooming_modes()
        self._create_session_mode()
        self._create_note_modes()
        self._create_device_mode()
        self._create_user_mode()
        self._create_record_arm_mode()
        self._create_track_select_mode()
        self._create_mute_mode()
        self._create_solo_mode()
        self._create_volume_mode()
        self._create_pan_mode()
        self._create_sends_mode()
        self._create_stop_clips_mode()
        self._modes.layer = Layer(
            session_mode_button=self._midimap["Session_Mode_Button"],
            note_mode_button=self._midimap["Note_Mode_Button"],
            device_mode_button=self._midimap["Device_Mode_Button"],
            user_mode_button=self._midimap["User_Mode_Button"],
            record_arm_mode_button=self._midimap["Record_Arm_Mode_Button"],
            track_select_mode_button=self._midimap["Track_Select_Mode_Button"],
            mute_mode_button=self._midimap["Mute_Mode_Button"],
            solo_mode_button=self._midimap["Solo_Mode_Button"],
            volume_mode_button=self._midimap["Volume_Mode_Button"],
            pan_mode_button=self._midimap["Pan_Mode_Button"],
            sends_mode_button=self._midimap["Sends_Mode_Button"],
            stop_clip_mode_button=self._midimap["Stop_Clip_Mode_Button"],
        )
        self._modes.selected_mode = "session_mode"
        self._on_layout_changed.subject = self._modes

    def _create_session_zooming_modes(self):
        session_zoom_layer = Layer(
            button_matrix=self._midimap["Main_Button_Matrix"],
            nav_left_button=self._midimap["Arrow_Left_Button"],
            nav_right_button=self._midimap["Arrow_Right_Button"],
            nav_up_button=self._midimap["Arrow_Up_Button"],
            nav_down_button=self._midimap["Arrow_Down_Button"],
        )
        session_zooming_layer_mode = LayerMode(self._session_zoom, session_zoom_layer)
        self._session_zooming_manager = SessionZoomingManagerComponent(self._modes, is_enabled=False)
        session_zooming_button_layer_mode = LayerMode(
            self._session_zooming_manager, Layer(session_zooming_button=self._midimap["Session_Mode_Button"])
        )
        self._prioritized_session_zooming_button_layer_mode = LayerMode(
            self._session_zooming_manager,
            Layer(session_zooming_button=self._midimap["Session_Mode_Button"], priority=1),
        )
        self._session_zooming_background = BackgroundComponent(name="Session_Zooming_Background")
        session_zooming_background_layer_mode = LayerMode(
            self._session_zooming_background,
            Layer(
                scene_launch_buttons=self._midimap["Scene_Launch_Button_Matrix"],
                delete_button=self._midimap["Delete_Button"],
                quantize_button=self._midimap["Quantize_Button"],
                duplicate_button=self._midimap["Duplicate_Button"],
                double_loop_button=self._midimap["Double_Loop_Button"],
            ),
        )
        self._modes.add_mode(
            "session_zooming_mode",
            [
                self._session_zooming_manager,
                session_zooming_button_layer_mode,
                session_zooming_layer_mode,
                session_zooming_background_layer_mode,
            ],
        )
        self._modes.add_mode(
            "prioritized_session_zooming_mode",
            [
                partial(self._layout_switch, SESSION_LAYOUT_SYSEX_BYTE),
                self._session_zooming_manager,
                self._prioritized_session_zooming_button_layer_mode,
                session_zooming_layer_mode,
                session_zooming_background_layer_mode,
                self.update,
            ],
        )

    def _create_session_mode(self):
        self._modes.add_mode(
            "session_mode",
            [
                partial(self._layout_setup, SESSION_LAYOUT_SYSEX_BYTE),
                self._session_layer_mode,
                self._session.update_navigation_buttons,
            ],
            behaviour=CancelingReenterBehaviour("session_zooming_mode"),
        )

    def _create_note_modes(self):
        self._instrument_component._modes.set_enabled(False)
        self._instrument_component.set_layers(self._midimap)
        self._modes.add_mode(
            "note_mode",
            [
                self._instrument_component._modes,
                self._instrument_component._detect_mode,
                self._select_target_track,
                self._clip_actions_component,
                self._show_playing_clip,
                self._set_clip_actions_type,
            ],
            behaviour=ReenterBehaviour(self.toggle_detail_view),
        )
        self._session_record.set_modes_component(self._modes)
        self._session_record.set_note_mode_name("note_mode")

    def _create_device_mode(self):
        device_layer_mode = LayerMode(
            self._device,
            layer=Layer(
                matrix=self._midimap["Main_Button_Matrix"],
                prev_track_button=self._midimap["Arrow_Left_Button"],
                next_track_button=self._midimap["Arrow_Right_Button"],
                prev_device_button=self._midimap["Arrow_Up_Button"],
                next_device_button=self._midimap["Arrow_Down_Button"],
                on_off_button=self._scene_button(0),
                prev_bank_button=self._scene_button(1),
                next_bank_button=self._scene_button(2),
                precision_button=self._scene_button(3),
                lock_button1=self._scene_button(4),
                lock_button2=self._scene_button(5),
                lock_button3=self._scene_button(6),
                lock_button4=self._scene_button(7),
            ),
        )
        self._modes.add_mode(
            "device_mode",
            [
                partial(self._layout_setup, DRUM_LAYOUT_SYSEX_BYTE, SYSEX_PARAM_BYTE_STANDALONE_LAYOUT),
                self._device,
                device_layer_mode,
                self._show_playing_clip,
                self._set_clip_actions_type,
            ],
            behaviour=ReenterBehaviour(self.toggle_detail_view),
        )

    # USER BUTTON

    def _step_sequencer_mode(self, sequencer, scene_button_names):
        """The mode of a step sequencer: the grid, the arrows and the 8 round buttons on the right
        (scene_button_names, top first)."""
        scene_buttons = {name: self._scene_button(index) for index, name in enumerate(scene_button_names)}
        return [
            partial(self._layout_switch, SESSION_LAYOUT_SYSEX_BYTE),
            partial(self._layout_setup, DRUM_LAYOUT_SYSEX_BYTE, SYSEX_PARAM_BYTE_STANDALONE_LAYOUT),
            LayerMode(
                sequencer,
                Layer(
                    matrix=self._midimap["Main_Button_Matrix"],
                    prev_track_button=self._midimap["Arrow_Left_Button"],
                    next_track_button=self._midimap["Arrow_Right_Button"],
                    prev_scene_button=self._midimap["Arrow_Up_Button"],
                    next_scene_button=self._midimap["Arrow_Down_Button"],
                    **scene_buttons,
                ),
            ),
        ]

    def _create_user_mode(self):
        self._user_button_modes = ModesComponent(name="User_Button_Modes", is_enabled=False)
        self._user_button_modes.add_mode(
            "stepsequencer_mode",
            self._step_sequencer_mode(
                self._step_sequencer,
                (
                    "scale_button",
                    "octave_up_button",
                    "octave_down_button",
                    "quantization_button",
                    "velocity_button",
                    "mode_button",
                    "mute_shift_button",
                    "lock_button",
                ),
            ),
        )
        self._user_button_modes.add_mode(
            "stepsequencer2_mode",
            self._step_sequencer_mode(
                self._step_sequencer2,
                (
                    "scale_button",
                    "octave_button",
                    "pitch_button",
                    "quantization_button",
                    "velocity_button",
                    "length_button",
                    "random_button",
                    "lock_button",
                ),
            ),
        )
        self._user_button_modes.add_mode(
            "user_mode",
            [
                partial(self._layout_switch, SESSION_LAYOUT_SYSEX_BYTE),
                partial(self._layout_setup, USER_LAYOUT_SYSEX_BYTE),
            ],
        )
        self._user_button_modes.selected_mode = "stepsequencer_mode"
        self._modes.add_mode(
            "user_mode",
            [
                partial(self._layout_switch, SESSION_LAYOUT_SYSEX_BYTE),
                partial(self._layout_setup, DRUM_LAYOUT_SYSEX_BYTE, SYSEX_PARAM_BYTE_STANDALONE_LAYOUT),
                self._enable_user_button_modes,
                self._user_button_modes,
            ],
            behaviour=ReenterBehaviour(self._toggle_user_button_modes),
        )

    def _toggle_user_button_modes(self):
        self._user_button_modes.cycle_mode()
        button = self._midimap["User_Mode_Button"]
        skin, message = USER_SUB_MODES[self._user_button_modes.selected_mode]
        button.default_states = {True: skin + ".On", False: skin + ".Off"}
        self.show_message(message)
        button.reset_state()
        button.turn_on()
        self._enable_user_button_modes()
        self._step_sequencer.update()
        self._step_sequencer2.update()

    def _enable_user_button_modes(self):
        self._step_sequencer.set_enabled(self._user_button_modes.selected_mode == "stepsequencer_mode")
        self._step_sequencer2.set_enabled(self._user_button_modes.selected_mode == "stepsequencer2_mode")

    # MIXER MODES

    def _add_session_overlay_mode(self, name, layer_mode):
        """A mixer mode that shows the session with layer_mode on the bottom row of pads."""
        self._modes.add_mode(
            name,
            [
                partial(self._layout_setup, SESSION_LAYOUT_SYSEX_BYTE),
                self._session_layer_mode,
                layer_mode,
                self._session_zooming_manager,
                self._prioritized_session_zooming_button_layer_mode,
                self._session.update_navigation_buttons,
            ],
            behaviour=SpecialReenterBehaviour("session_mode"),
        )

    def _add_fader_mode(self, name, layer_mode, scene_launch_translation=None):
        """A mixer mode with a fader per track."""
        translation = [scene_launch_translation] if scene_launch_translation is not None else []
        self._modes.add_mode(
            name,
            [
                partial(self._layout_setup, FADER_LAYOUT_SYSEX_BYTE),
                layer_mode,
                self._action_button_background_layer_mode,
                self._session_zooming_manager,
                self._prioritized_session_zooming_button_layer_mode,
                *translation,
                self._session.update_navigation_buttons,
            ],
            behaviour=SpecialReenterBehaviour("session_mode"),
        )

    def _mixer_pads_mode(self, buttons_name):
        return LayerMode(self._mixer, layer=Layer(**{buttons_name: self._midimap["Mixer_Button_Matrix"]}))

    def _create_record_arm_mode(self):
        self._add_session_overlay_mode("record_arm_mode", self._mixer_pads_mode("arm_buttons"))

    def _create_track_select_mode(self):
        self._add_session_overlay_mode("track_select_mode", self._mixer_pads_mode("track_select_buttons"))

    def _create_mute_mode(self):
        self._add_session_overlay_mode("mute_mode", self._mixer_pads_mode("mute_buttons"))

    def _create_solo_mode(self):
        self._add_session_overlay_mode("solo_mode", self._mixer_pads_mode("solo_buttons"))

    def _create_volume_mode(self):
        translation = self._create_translation(
            "Volume_Mode_Scene_Launch_Translation",
            VOLUME_MAP_CHANNEL,
            Layer(scene_launch_buttons=self._midimap["Scene_Launch_Button_Matrix"]),
        )
        volume_layer_mode = LayerMode(self._mixer, layer=Layer(volume_controls=self._midimap["Slider_Button_Matrix"]))
        self._add_fader_mode("volume_mode", volume_layer_mode, translation)

    def _create_pan_mode(self):
        translation = self._create_translation(
            "Pan_Mode_Scene_Launch_Translation",
            PAN_MAP_CHANNEL,
            Layer(scene_launch_buttons=self._midimap["Scene_Launch_Button_Matrix"]),
        )
        pan_layer_mode = LayerMode(self._mixer, layer=Layer(pan_controls=self._midimap["Slider_Button_Matrix"]))
        self._add_fader_mode("pan_mode", pan_layer_mode, translation)

    def _create_sends_mode(self):
        send_layer_mode = LayerMode(
            self._mixer,
            layer=Layer(
                send_controls=self._midimap["Slider_Button_Matrix"],
                send_select_buttons=self._midimap["Scene_Launch_Button_Matrix"],
            ),
        )
        self._add_fader_mode("sends_mode", send_layer_mode)

    def _create_stop_clips_mode(self):
        stop_layer_mode = AddLayerMode(
            self._session,
            Layer(
                stop_track_clip_buttons=self._midimap["Mixer_Button_Matrix"],
                stop_scene_clip_buttons=self._midimap["Scene_Stop_Button_Matrix"],
                stop_all_clips_button=self._midimap["Stop_All_Clips_Button"],
            ),
        )
        self._add_session_overlay_mode("stop_clip_mode", stop_layer_mode)
