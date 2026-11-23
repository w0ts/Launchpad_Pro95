"""The Launchpad Pro control surface: creates the components. The modes are built in
LaunchpadProModes.py, the handshake and layout sysex are in LaunchpadProHandshake.py and the
buttons are named in LaunchpadProMidiMap.py."""

import Live
from _Framework.ControlSurface import OptimizedControlSurface
from _Framework.Dependency import inject
from _Framework.IdentifiableControlSurface import IdentifiableControlSurface
from _Framework.Layer import Layer
from _Framework.SubjectSlot import subject_slot
from _Framework.Util import const

from .ActionsComponent import ActionsComponent
from .BackgroundComponent import BackgroundComponent, ModifierBackgroundComponent
from .ClipActionsComponent import ClipActionsComponent
from .Colors import CLIP_COLOR_TABLE, RGB_COLOR_TABLE
from .consts import (
    DEVICE_CODE,
    DR_MAP_CHANNEL,
    MANUFACTURER_ID,
    QUIT_MESSAGE,
    SYSEX_IDENTITY_REQUEST,
    TURN_OFF_LEDS,
)
from .DeviceComponent import DeviceComponent
from .DrumGroupComponent import DrumGroupComponent
from .DrumGroupFinderComponent import DrumGroupFinderComponent
from .InstrumentComponent import InstrumentComponent
from .LaunchpadProHandshake import LaunchpadProHandshakeMixin
from .LaunchpadProMidiMap import NUM_SCENES, NUM_TRACKS, MidiMap
from .LaunchpadProModes import LaunchpadProModesMixin
from .SkinMK2 import make_skin
from .SpecialMixerComponent import SpecialMixerComponent
from .SpecialSessionComponent import SpecialSessionComponent as SessionComponent
from .SpecialSessionComponent import SpecialSessionZoomingComponent as SessionZoomingComponent
from .SpecialSessionRecordingComponent import SpecialSessionRecordingComponent
from .StepSequencerComponent import StepSequencerComponent
from .StepSequencerComponent2 import StepSequencerComponent2
from .TargetTrackComponent import TargetTrackComponent


class Launchpad_Pro95(
    LaunchpadProModesMixin, LaunchpadProHandshakeMixin, IdentifiableControlSurface, OptimizedControlSurface
):
    identity_request = SYSEX_IDENTITY_REQUEST

    def __init__(self, c_instance, *a, **k):
        self._copied_slot = None
        product_id_bytes = MANUFACTURER_ID + DEVICE_CODE
        super().__init__(*a, c_instance=c_instance, product_id_bytes=product_id_bytes, **k)
        self._challenge = Live.Application.get_random_int(0, 400000000) & 2139062143
        with self.component_guard():
            self._skin = make_skin()
            with inject(skin=const(self._skin)).everywhere():
                self._midimap = MidiMap()
            self._target_track_component = TargetTrackComponent(name="Target_Track")
            self._create_background()
            self._create_global_component()
            self._last_sent_mode_byte = None
            with inject(layout_setup=const(self._layout_setup), should_arm=const(self._should_arm_track)).everywhere():
                self._create_session()
                self._create_recording()
                self._create_actions()
                self._create_drums()
                self._create_instrument_component()
                self._create_step_sequencer()
                self._create_step_sequencer2()
                self._create_mixer()
                self._create_device()
                self._create_modes()

            self._on_session_record_changed.subject = self.song()
        # the session is highlighted once the handshake succeeds
        self.set_device_component(self._device)
        self._device_selection_follows_track_selection = True
        self._on_session_record_changed()

    def disconnect(self):
        self._send_midi(TURN_OFF_LEDS)
        self._send_midi(QUIT_MESSAGE)
        super().disconnect()

    def _create_background(self):
        self._modifier_background_component = ModifierBackgroundComponent(
            name="Background_Component", is_enabled=False, layer=Layer(shift_button=self._midimap["Shift_Button"])
        )
        self._shifted_background = BackgroundComponent(
            name="No_Op_Shifted_Buttons",
            is_enabled=False,
            layer=Layer(
                delete_button=self._midimap.with_shift("Delete_Button"),
                duplicate_button=self._midimap.with_shift("Duplicate_Button"),
                double_button=self._midimap.with_shift("Double_Loop_Button"),
                session_record_button=self._midimap.with_shift("Session_Record_Button"),
            ),
        )

    def _create_global_component(self):
        self._actions_component = ActionsComponent(
            name="Global_Actions",
            is_enabled=False,
            layer=Layer(
                undo_button=self._midimap["Undo_Button"],
                redo_button=self._midimap.with_shift("Undo_Button"),
                metronome_button=self._midimap["Click_Button"],
                tap_button=self._midimap.with_shift("Click_Button"),
                quantization_on_button=self._midimap.with_shift("Quantize_Button"),
                duplicate_button=self._midimap["Duplicate_Button"],
            ),
        )

    def _create_session(self):
        self._session = SessionComponent(
            NUM_TRACKS,
            NUM_SCENES,
            auto_name=True,
            is_enabled=False,
            enable_skinning=True,
            layer=Layer(
                track_bank_left_button=self._midimap["Arrow_Left_Button"],
                track_bank_right_button=self._midimap["Arrow_Right_Button"],
                scene_bank_up_button=self._midimap["Arrow_Up_Button"],
                scene_bank_down_button=self._midimap["Arrow_Down_Button"],
            ),
        )
        self._session.set_enabled(True)
        self._session.set_rgb_mode(CLIP_COLOR_TABLE, RGB_COLOR_TABLE)
        for scene_index in range(NUM_SCENES):
            scene = self._session.scene(scene_index)
            scene.layer = Layer(
                select_button=self._midimap["Shift_Button"],
                delete_button=self._midimap["Delete_Button"],
                duplicate_button=self._midimap["Duplicate_Button"],
            )
            for track_index in range(NUM_TRACKS):
                slot = scene.clip_slot(track_index)
                slot.quantization_component = self._actions_component
                slot.layer = Layer(
                    select_button=self._midimap["Shift_Button"],
                    delete_button=self._midimap["Delete_Button"],
                    duplicate_button=self._midimap["Duplicate_Button"],
                    double_loop_button=self._midimap["Double_Loop_Button"],
                    quantize_button=self._midimap["Quantize_Button"],
                )

        self._session_zoom = SessionZoomingComponent(
            self._session, name="Session_Overview", is_enabled=True, enable_skinning=True
        )

    def _create_recording(self):
        self._session_record = SpecialSessionRecordingComponent(
            self._target_track_component,
            name="Session_Recording",
            is_enabled=False,
            layer=Layer(record_button=self._midimap["Session_Record_Button"]),
        )

    def _create_actions(self):
        self._clip_actions_component = ClipActionsComponent(
            self._target_track_component,
            name="Clip_Actions",
            is_enabled=False,
            layer=Layer(
                duplicate_button=self._midimap["Duplicate_Button"],
                double_button=self._midimap["Double_Loop_Button"],
                quantize_button=self._midimap["Quantize_Button"],
            ),
        )
        self._clip_actions_component.quantization_component = self._actions_component

    def _create_drums(self):
        self._drum_group_finder = DrumGroupFinderComponent(
            self._target_track_component, name="Drum_Group_Finder", is_enabled=False, layer=None
        )
        self._on_drum_group_changed.subject = self._drum_group_finder
        self._drum_group_finder.set_enabled(True)
        self._drum_group = DrumGroupComponent(
            self._clip_actions_component,
            control_surface=self,
            name="Drum_Group_Control",
            translation_channel=DR_MAP_CHANNEL,
        )
        self._drum_group.set_enabled(True)

    def _create_step_sequencer(self):
        self._step_sequencer = StepSequencerComponent(self)

    def _create_step_sequencer2(self):
        self._step_sequencer2 = StepSequencerComponent2(self)

    def _create_instrument_component(self):
        self._instrument_component = InstrumentComponent(self, self._drum_group)

    def _create_mixer(self):
        self._mixer = SpecialMixerComponent(NUM_TRACKS, auto_name=True, is_enabled=True, invert_mute_feedback=True)
        self._mixer.name = "Mixer_Control"
        self._session.set_mixer(self._mixer)

    def _create_device(self):
        self._device = DeviceComponent(control_surface=self, name="Device_Control", is_enabled=False)

    def _setup_drum_group(self):
        self._drum_group.set_drum_group_device(self._drum_group_finder.drum_group)

    def toggle_detail_view(self):
        view = self.application().view
        if view.is_view_visible("Detail"):
            if view.is_view_visible("Detail/DeviceChain"):
                view.show_view("Detail/Clip")
            else:
                view.show_view("Detail/DeviceChain")

    @subject_slot("drum_group")
    def _on_drum_group_changed(self):
        self._instrument_component._detect_mode()
        if self._instrument_component._modes.selected_mode == "drum_mode":
            self._setup_drum_group()
        if self._modes.selected_mode == "note_mode":
            self._select_note_mode()
        else:
            self.release_controlled_track()

    def _select_note_mode(self):
        self._instrument_component._detect_mode()
        self._update_note_mode_button()

    def _select_target_track(self):
        track = self._target_track_component.target_track
        if track != self.song().view.selected_track:
            self.song().view.selected_track = track

    def _update_note_mode_button(self):
        focused_track_is_drum_track = self._drum_group_finder.drum_group is not None
        button = self._midimap["Note_Mode_Button"]
        if focused_track_is_drum_track:
            button.default_states = {True: "Mode.Drum.On", False: "Mode.Drum.Off"}
        else:
            button.default_states = {True: "Mode.Note.On", False: "Mode.Note.Off"}
        button.reset_state()
        self._modes.update()

    def _show_playing_clip(self):
        track = None
        if self._use_sel_track():
            track = self.song().view.selected_track
        else:
            track = self._target_track_component.target_track
        if track in self.song().tracks:
            slot_index = track.fired_slot_index
            if slot_index < 0:
                slot_index = track.playing_slot_index
            if slot_index >= 0:
                clip_slot = track.clip_slots[slot_index]
                self.song().view.highlighted_clip_slot = clip_slot

    def _set_clip_actions_type(self):
        self._clip_actions_component.use_selected_track(self._use_sel_track())
        self._clip_actions_component.update()

    def _use_sel_track(self):
        return self._modes.selected_mode == "device_mode"

    def _should_arm_track(self):
        return self._modes.selected_mode == "record_arm_mode"

    @subject_slot("selected_mode")
    def _on_layout_changed(self, mode):
        self._session_record.set_enabled(mode != "user_mode")

    @subject_slot("session_record")
    def _on_session_record_changed(self):
        status = self.song().session_record
        feedback_color = int(self._skin["Note.FeedbackRecord"] if status else self._skin["Note.Feedback"])
        self._c_instance.set_feedback_velocity(feedback_color)
