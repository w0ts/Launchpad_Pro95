from _Framework.ButtonElement import ButtonElement
from _Framework.MixerComponent import MixerComponent


class TrackControllerComponent(MixerComponent):
    """step sequencer arrows: navigate in tracks left/right and in scenes up/down,
    and implicit arm of the selected track.
    """

    def __init__(self, control_surface=None, implicit_arm=False, skin_name="Session", enabled=False):
        self._prev_track_button = None
        self._next_track_button = None
        self._prev_scene_button = None
        self._next_scene_button = None
        self._control_surface = control_surface
        self._implicit_arm = implicit_arm
        self._skin_name = skin_name
        MixerComponent.__init__(self, 1)
        self.set_enabled(enabled)

    def disconnect(self):
        self.set_prev_scene_button(None)
        self.set_next_scene_button(None)
        self.set_prev_track_button(None)
        self.set_next_track_button(None)

        MixerComponent.disconnect(self)

    def set_enabled(self, enabled):
        if self.is_enabled() and not enabled:
            # disable implicit arm while leaving.
            if self._implicit_arm:
                if self.selected_track.can_be_armed:
                    self.selected_track.implicit_arm = False
        MixerComponent.set_enabled(self, enabled)

    # def _do_select_scene(self, scene):
    # 	view = self.song().view
    # 	if view.selected_scene != self.selected_scene:
    # 		view.selected_scene = self._scene

    def set_prev_scene_button(self, prev_scene=None):
        assert isinstance(prev_scene, (ButtonElement, type(None)))
        if self._prev_scene_button != None:
            self._prev_scene_button.remove_value_listener(self._prev_scene_value)
        self._prev_scene_button = prev_scene
        if self._prev_scene_button != None:
            self._prev_scene_button.add_value_listener(self._prev_scene_value, identify_sender=True)
            self._prev_scene_button.turn_off()

    def set_next_scene_button(self, next_scene=None):
        assert isinstance(next_scene, (ButtonElement, type(None)))
        if self._next_scene_button != None:
            self._next_scene_button.remove_value_listener(self._next_scene_value)
        self._next_scene_button = next_scene
        if self._next_scene_button != None:
            self._next_scene_button.add_value_listener(self._next_scene_value, identify_sender=True)
            self._next_scene_button.turn_off()

    # TRACKS Buttons
    def update_track_buttons(self):
        # tracks
        if self.is_enabled():
            if self._prev_track_button != None:
                self._prev_track_button.set_on_off_values("Mode." + self._skin_name)
                if self.selected_track_idx is not None and self.selected_track_idx > 0:
                    self._prev_track_button.turn_on()
                else:
                    self._prev_track_button.turn_off()
            if self._next_track_button != None:
                self._next_track_button.set_on_off_values("Mode." + self._skin_name)
                if self.selected_track_idx is not None and self.selected_track_idx < len(self.song().tracks) - 1:
                    self._next_track_button.turn_on()
                else:
                    self._next_track_button.turn_off()

    def set_next_track_button(self, button):
        assert isinstance(button, (ButtonElement, type(None)))
        if self._next_track_button != button:
            if self._next_track_button != None:
                self._next_track_button.remove_value_listener(self._next_track_value)
            self._next_track_button = button
            if self._next_track_button != None:
                assert isinstance(button, ButtonElement)
                self._next_track_button.add_value_listener(self._next_track_value, identify_sender=True)

    def _next_track_value(self, value, sender):
        assert self._next_track_button != None
        assert value in range(128)
        if self.is_enabled():
            if (not sender.is_momentary()) or (value != 0):
                if self.selected_track_idx is not None and self.selected_track_idx < len(self.song().tracks) - 1:
                    self.song().view.selected_track = self.song().tracks[self.selected_track_idx + 1]
                    self._do_implicit_arm()

    def set_prev_track_button(self, button):
        assert isinstance(button, (ButtonElement, type(None)))
        if self._prev_track_button != button:
            if self._prev_track_button != None:
                self._prev_track_button.remove_value_listener(self._prev_track_value)
            self._prev_track_button = button
            if self._prev_track_button != None:
                assert isinstance(button, ButtonElement)
                self._prev_track_button.add_value_listener(self._prev_track_value, identify_sender=True)

    def _prev_track_value(self, value, sender):
        assert self._prev_track_button != None
        assert value in range(128)
        if (not sender.is_momentary()) or (value != 0):
            if self.is_enabled():
                if self.selected_track_idx is not None and self.selected_track_idx > 0:
                    self.song().view.selected_track = self.song().tracks[self.selected_track_idx - 1]
                    self._do_implicit_arm()

    def update_scene_buttons(self):
        # tracks
        if self.is_enabled():
            if self._prev_scene_button != None:
                self._prev_scene_button.set_on_off_values("Mode." + self._skin_name)
                if self.selected_scene_idx > 0:
                    self._prev_scene_button.turn_on()
                else:
                    self._prev_scene_button.turn_off()

            if self._next_scene_button != None:
                self._next_scene_button.set_on_off_values("Mode." + self._skin_name)
                if self.selected_scene_idx < len(self.song().scenes) - 1:
                    self._next_scene_button.turn_on()
                else:
                    self._next_scene_button.turn_off()

    def _prev_scene_value(self, value, sender):
        assert self._prev_scene_button != None
        assert value in range(128)
        if not sender.is_momentary() or value != 0:
            if self.is_enabled():
                if self.selected_scene_idx > 0:
                    self.song().view.selected_scene = self.song().scenes[self.selected_scene_idx - 1]

    def _next_scene_value(self, value, sender):
        assert self._next_scene_button != None
        assert value in range(128)
        if not sender.is_momentary() or value != 0:
            if self.is_enabled():
                if not sender.is_momentary() or value != 0:
                    if self.selected_scene_idx < len(self.song().scenes) - 1:
                        self.song().view.selected_scene = self.song().scenes[self.selected_scene_idx + 1]

    def update(self):
        if self.is_enabled():
            self.update_track_buttons()
            self.update_scene_buttons()

        MixerComponent.update(self)

    def can_implicit_arm_track(self, track):
        return track.can_be_armed and track.has_midi_input

    def _do_implicit_arm(self, arm=True):
        if self.is_enabled():
            if self._implicit_arm:
                self._control_surface.set_controlled_track(self.selected_track)
            else:
                self._control_surface.release_controlled_track()
            for track in self.song().tracks:
                if self.can_implicit_arm_track(track):
                    track.implicit_arm = self._implicit_arm and arm and self.selected_track == track

    def on_selected_track_changed(self):
        self._do_implicit_arm()
        self.update()

    def on_selected_scene_changed(self):
        self.update()

    @property
    def selected_track(self):
        return self.song().view.selected_track

    @property
    def selected_track_idx(self):
        tracks = list(self.song().tracks)
        track = self.song().view.selected_track
        return tracks.index(track) if track in tracks else None  # None: a return or the master track

    @property
    def selected_scene_idx(self):
        return list(self.song().scenes).index(self.song().view.selected_scene)
