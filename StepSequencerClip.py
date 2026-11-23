"""Which clip the step sequencers edit: the selected slot's MIDI clip, or with the lock button
the same clip, or (lock to track) the clip triggered or playing on the locked track."""

from .ClipNotes import read_all_notes

LOCKED_TRACK_REFRESH_TICKS = 5  # scene launches select the scene before the clip fires


class StepSequencerClipMixin:
    """Follows the clip and its notes, loop and playing position; mixed into
    StepSequencerComponent."""

    def _remove_clip_listeners(self, clip):
        if clip != None and clip.is_midi_clip:
            if clip.notes_has_listener(self._on_notes_changed):
                clip.remove_notes_listener(self._on_notes_changed)
            if clip.playing_status_has_listener(self._on_playing_status_changed):
                clip.remove_playing_status_listener(self._on_playing_status_changed)
            if clip.playing_position_has_listener(self._on_playing_position_changed):
                clip.remove_playing_position_listener(self._on_playing_position_changed)
            if clip.loop_start_has_listener(self._on_loop_changed):
                clip.remove_loop_start_listener(self._on_loop_changed)
            if clip.loop_end_has_listener(self._on_loop_changed):
                clip.remove_loop_end_listener(self._on_loop_changed)

    def _add_clip_listeners(self, clip):
        clip.add_notes_listener(self._on_notes_changed)
        clip.add_playing_status_listener(self._on_playing_status_changed)
        clip.add_playing_position_listener(self._on_playing_position_changed)
        clip.add_loop_start_listener(self._on_loop_changed)
        clip.add_loop_end_listener(self._on_loop_changed)

    # SONG CALLBACKS

    def on_track_list_changed(self):
        self.on_selected_track_changed()

    def on_scene_list_changed(self):
        self.on_selected_scene_changed()

    def on_selected_scene_changed(self):
        self.on_clip_slot_changed()
        self.update()

    def on_selected_track_changed(self):
        if not self._is_locked or self._clip == None:
            self.on_clip_slot_changed()
            self.update()

    def _on_loop_changed(self):
        if self.is_enabled() and self._clip != None:
            self._loop_selector._get_clip_loop()

    def on_clip_slot_has_clip_changed(self):
        # the clip was deleted. unlock.
        if not self._clip_slot.has_clip:
            self._is_locked = False
        self.on_clip_slot_changed()
        self.update()

    # FINDING THE CLIP

    def on_clip_slot_changed(self, scheduled=False):
        clip_slot = self._clip_slot
        if not self._is_locked or self._selected_track == None:
            self._selected_track = self.song().view.selected_track
        if self._selected_track != None:
            index = self._followed_slot_index(scheduled)
            if index != -1 and index < len(list(self._selected_track.clip_slots)):
                clip_slot = self._selected_track.clip_slots[index]
        self._listen_to_clip_slot(clip_slot)
        self._follow_slot_clip()

    def _followed_slot_index(self, scheduled):
        """The scene index of the slot to follow on the selected track, or -1 to keep the slot."""
        index = -1
        if self._lock_to_track and self._is_locked:
            if not scheduled:
                self._control_surface.schedule_message(LOCKED_TRACK_REFRESH_TICKS, self.on_clip_slot_changed, True)
            index = self._last_slot_index(lambda clip: clip.is_triggered)
            if index == -1:
                index = self._last_slot_index(lambda clip: clip.is_playing)
            if index == -1:
                index = self._selected_scene_index()
        if not self._is_locked:
            index = self._selected_scene_index()
        return index

    def _last_slot_index(self, wanted):
        """The last scene index whose slot on the selected track has a clip that is wanted."""
        index = -1
        for i in range(len(self.song().scenes)):
            slot = self._selected_track.clip_slots[i]
            if slot.has_clip and wanted(slot.clip):
                index = i
        return index

    def _selected_scene_index(self):
        try:
            return list(self.song().scenes).index(self.song().view.selected_scene)
        except ValueError:
            return -1

    def _listen_to_clip_slot(self, clip_slot):
        if clip_slot != self._clip_slot or self._clip_slot == None:
            if self._clip_slot != None and self._clip_slot.has_clip_has_listener(self.on_clip_slot_has_clip_changed):
                self._clip_slot.remove_has_clip_listener(self.on_clip_slot_has_clip_changed)
            self._clip_slot = clip_slot
            if self._clip_slot != None:
                if self._clip_slot.has_clip_has_listener(self.on_clip_slot_has_clip_changed):
                    self._clip_slot.remove_has_clip_listener(self.on_clip_slot_has_clip_changed)
                self._clip_slot.add_has_clip_listener(self.on_clip_slot_has_clip_changed)

    def _follow_slot_clip(self):
        slot = self._clip_slot
        if slot != None and slot.has_clip and slot.clip != None and slot.clip.is_midi_clip:
            if self._clip == None or self._clip != slot.clip:
                self._link_clip(slot.clip)
        else:
            self._remove_clip_listeners(self._clip)
            self._clip = None
            self._clip_changed()

    def _link_clip(self, clip):
        self._remove_clip_listeners(self._clip)
        self._add_clip_listeners(clip)
        self._clip = clip
        self._clip_changed()

    # CLIP CALLBACKS

    def _clip_changed(self):  # triggered by on_clip_slot_changed() or manually on enable.
        self._note_editor.set_clip(self._clip)
        self._note_selector.set_clip(self._clip)
        self._loop_selector.set_clip(self._clip)
        self._note_editor.set_playhead(None)
        self._note_selector.set_playhead(None)
        self._loop_selector.set_playhead(None)
        # reload notes (also when the new clip has the same notes, e.g. a duplicate)
        self._note_cache = None
        self._on_notes_changed()

    def _on_notes_changed(self):  # trigger by callback on clip or via _clip_changed.
        if self.is_enabled():
            note_cache = [] if self._clip == None else read_all_notes(self._clip)
            if note_cache != self._note_cache:
                self._note_cache = note_cache
                self._note_editor.set_note_cache(self._note_cache)
                self._note_selector.set_note_cache(self._note_cache)
                self._loop_selector.set_note_cache(self._note_cache)
                self._update_note_editor()

    def _on_playing_status_changed(self):
        if self.is_enabled():
            self._on_playing_position_changed()

    def _on_playing_position_changed(self):
        if self.is_enabled():
            if self._clip != None and self._clip.is_playing and self.song().is_playing:
                self._playhead = self._clip.playing_position
            else:
                self._playhead = None
            self._loop_selector.set_playhead(self._playhead)
            self._note_selector.set_playhead(self._playhead)
            self._note_editor.set_playhead(self._playhead)
