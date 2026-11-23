"""A small, deterministic stand-in for Live's object model (Song, Track, Clip, ...).

Only what Launchpad_Pro95 and _Framework touch. Values change synchronously and fire
their listeners at once; nothing runs in the background. Transport and clip
launching are simulated by the test (see ``Song.advance`` and ``ClipSlot.fire``).
"""
from ._listenable import events, listenable, notify


class LimitationError(Exception):
	pass


class _Object:
	canonical_parent = None

	def __init__(self, **values):
		for name, value in values.items():
			setattr(self, name, value)

	@property
	def _live_ptr(self):
		return id(self)


# --------------------------------------------------------------------------- parameters

@listenable(value=0.0, name="", is_enabled=True, automation_state=0, state=0)
class DeviceParameter(_Object):
	def __init__(self, name="Param", value=0.0, min=0.0, max=1.0, is_quantized=False, value_items=(), **k):
		self.min = min
		self.max = max
		self.is_quantized = is_quantized
		self.value_items = tuple(value_items)
		self.default_value = value
		self.original_name = name
		super().__init__(name=name, value=value, **k)

	def __setattr__(self, name, value):
		if name == "value" and "max" in self.__dict__:
			if not (self.min <= value <= self.max):
				raise RuntimeError("Invalid value %r for parameter %s" % (value, self.name))
		object.__setattr__(self, name, value)

	def str_for_value(self, value):
		return "%.2f" % value

	def __str__(self):
		return self.str_for_value(self.value)

	def re_enable_automation(self):
		pass

	def begin_gesture(self):
		pass

	def end_gesture(self):
		pass


@listenable(crossfade_assign=1)
@events("sends")
class MixerDevice(_Object):
	def __init__(self, track, num_sends=2):
		self.canonical_parent = track
		self.volume = DeviceParameter("Track Volume", 0.85, 0.0, 1.0)
		self.panning = DeviceParameter("Track Panning", 0.0, -1.0, 1.0)
		self.track_activator = DeviceParameter("Speaker On", 1.0, 0.0, 1.0, is_quantized=True)
		self.crossfader = DeviceParameter("Crossfader", 0.0, -1.0, 1.0)
		self.cue_volume = DeviceParameter("Cue Volume", 0.85, 0.0, 1.0)
		self.song_tempo = DeviceParameter("Song Tempo", 120.0, 20.0, 999.0)
		self.sends = tuple(DeviceParameter("Send %s" % chr(65 + i), 0.0, 0.0, 1.0) for i in range(num_sends))
		for param in (self.volume, self.panning, self.track_activator) + self.sends:
			param.canonical_parent = self


# --------------------------------------------------------------------------- devices

class DeviceType:
	undefined = 0
	instrument = 1
	audio_effect = 2
	midi_effect = 4


@listenable(name="", is_active=True, parameters=tuple)
@events("chains", "has_macro_mappings", "drum_pads", "visible_drum_pads", "return_chains")
class Device(_Object):
	can_have_chains = False
	can_have_drum_pads = False

	def __init__(self, name="Device", class_name="OriginalSimpler", type=DeviceType.instrument, num_parameters=8, parameters=None):
		super().__init__(name=name)
		self.class_name = class_name
		self.class_display_name = class_name
		self.type = type
		if parameters is None:
			parameters = [DeviceParameter("Device On", 1.0, 0.0, 1.0, is_quantized=True)]
			parameters += [DeviceParameter("%s P%d" % (name, i + 1), 0.0, 0.0, 1.0) for i in range(num_parameters)]
		for param in parameters:
			param.canonical_parent = self
		self.parameters = tuple(parameters)
		self.view = DeviceView(self)

	def store_chosen_bank(self, *a):
		pass


@listenable(is_collapsed=False, selected_drum_pad=None, selected_chain=None, drum_pads_scroll_position=0)
class DeviceView(_Object):
	def __init__(self, device):
		self.canonical_parent = device


@listenable(name="", mute=False, solo=False, color=0, devices=tuple)
class Chain(_Object):
	def __init__(self, name="Chain", devices=()):
		super().__init__(name=name)
		self.devices = tuple(devices)
		for device in self.devices:
			device.canonical_parent = self


@listenable(name="", mute=False, solo=False)
class DrumPad(_Object):
	def __init__(self, note, chains=()):
		super().__init__(name="Pad %d" % note)
		self.note = note
		self.chains = tuple(chains)


@listenable(chains=tuple, drum_pads=tuple, visible_drum_pads=tuple, has_macro_mappings=False)
class RackDevice(Device):
	can_have_chains = True

	def __init__(self, name="Rack", chains=(), drum=False, **k):
		super().__init__(name=name, class_name="DrumGroupDevice" if drum else "InstrumentGroupDevice", **k)
		self.chains = tuple(chains)
		for chain in self.chains:
			chain.canonical_parent = self
		self.can_have_drum_pads = drum
		self.has_drum_pads = drum
		self.return_chains = ()
		if drum:
			self.drum_pads = tuple(DrumPad(note) for note in range(128))
			self.visible_drum_pads = self.drum_pads[36:52]
			self.view.selected_drum_pad = self.drum_pads[36]


# --------------------------------------------------------------------------- clips

# Clip colours are RGB ints in Live; this one is in its clip colour palette.
DEFAULT_CLIP_COLOR = 15549221


class MidiNoteSpecification:
	"""Live 11 Live.Clip.MidiNoteSpecification (keyword arguments)."""

	def __init__(self, pitch, start_time, duration, velocity=100.0, mute=False, probability=1.0,
			velocity_deviation=0.0, release_velocity=64.0):
		self.pitch = int(pitch)
		self.start_time = float(start_time)
		self.duration = float(duration)
		self.velocity = float(velocity)
		self.mute = bool(mute)
		self.probability = float(probability)
		self.velocity_deviation = float(velocity_deviation)
		self.release_velocity = float(release_velocity)


class MidiNote:
	_next_id = 1

	def __init__(self, spec):
		for name in ("pitch", "start_time", "duration", "velocity", "mute", "probability",
				"velocity_deviation", "release_velocity"):
			setattr(self, name, getattr(spec, name))
		self.note_id = MidiNote._next_id
		MidiNote._next_id += 1

	def as_tuple(self):
		return (self.pitch, self.start_time, self.duration, self.velocity, self.mute)

	def __repr__(self):
		return "MidiNote%r" % (self.as_tuple(),)


@listenable(name="", color=DEFAULT_CLIP_COLOR, color_index=0, is_playing=False, is_triggered=False,
	is_recording=False, will_record_on_start=False, playing_status=0, playing_position=0.0, loop_start=0.0, loop_end=4.0, start_marker=0.0,
	end_marker=4.0, looping=True, muted=False, signature_numerator=4, signature_denominator=4, has_envelopes=False)
@events("notes")
class Clip(_Object):
	def __init__(self, length=4.0, is_midi=True, notes=(), name="Clip"):
		super().__init__(name=name, loop_end=float(length), end_marker=float(length))
		self.is_midi_clip = is_midi
		self.is_audio_clip = not is_midi
		self._notes = [MidiNote(MidiNoteSpecification(*note)) for note in notes]
		self._selected = False
		self.deprecated_calls = []
		self.fire_button_states = []
		self.view = _Object(grid_quantization=0, grid_is_triplet=False, show_loop=lambda: None,
			show_envelope=lambda: None, hide_envelope=lambda: None)

	@property
	def length(self):
		return self.loop_end - self.loop_start

	# -- Live 11+ note API
	def get_all_notes_extended(self):
		return tuple(sorted(self._notes, key=lambda n: (n.start_time, n.pitch)))

	def get_notes_extended(self, from_pitch, pitch_span, from_time, time_span):
		return tuple(n for n in self.get_all_notes_extended() if self._in_range(n, from_pitch, pitch_span, from_time, time_span))

	def remove_notes_extended(self, from_pitch, pitch_span, from_time, time_span):
		before = len(self._notes)
		self._notes = [n for n in self._notes if not self._in_range(n, from_pitch, pitch_span, from_time, time_span)]
		if len(self._notes) != before:
			notify(self, "notes")

	def remove_notes_by_id(self, ids):
		ids = set(ids)
		before = len(self._notes)
		self._notes = [n for n in self._notes if n.note_id not in ids]
		if len(self._notes) != before:
			notify(self, "notes")

	def add_new_notes(self, specs):
		specs = tuple(specs)
		for spec in specs:
			if not isinstance(spec, MidiNoteSpecification):
				raise TypeError("add_new_notes expects MidiNoteSpecification, got %r" % (spec,))
		new = [MidiNote(spec) for spec in specs]
		self._notes.extend(new)
		if new:
			notify(self, "notes")
		return tuple(n.note_id for n in new)

	@staticmethod
	def _in_range(note, from_pitch, pitch_span, from_time, time_span):
		return from_pitch <= note.pitch < from_pitch + pitch_span and from_time <= note.start_time < from_time + time_span

	# -- deprecated selection API (still present in Live 11/12; recorded so tests can forbid it)
	def select_all_notes(self):
		self.deprecated_calls.append("select_all_notes")
		self._selected = True

	def deselect_all_notes(self):
		self.deprecated_calls.append("deselect_all_notes")
		self._selected = False

	def get_selected_notes(self):
		self.deprecated_calls.append("get_selected_notes")
		return tuple(n.as_tuple() for n in self.get_all_notes_extended()) if self._selected else ()

	def replace_selected_notes(self, notes):
		self.deprecated_calls.append("replace_selected_notes")
		self._notes = [MidiNote(MidiNoteSpecification(*n)) for n in notes]
		notify(self, "notes")

	def set_notes(self, notes):
		self.deprecated_calls.append("set_notes")
		self._notes.extend(MidiNote(MidiNoteSpecification(*n)) for n in notes)
		notify(self, "notes")

	# -- helpers for tests
	def note_tuples(self):
		return tuple(n.as_tuple() for n in self.get_all_notes_extended())

	def fire(self):
		if self.canonical_parent is not None:
			self.canonical_parent.fire()

	def stop(self):
		if self.canonical_parent is not None:
			self.canonical_parent.stop()

	def set_fire_button_state(self, state):
		# Live 11+: drives every launch mode (gate and legato need the release)
		self.fire_button_states.append(bool(state))
		if state:
			self.fire()

	def quantize(self, grid, amount):
		self.quantized_with = (grid, amount)

	def move_playing_pos(self, beats):
		pass

	def duplicate_loop(self):
		"""Double the loop, copying the notes of the loop into the new half (MIDI clips)."""
		length = self.length
		copies = [MidiNoteSpecification(n.pitch, n.start_time + length, n.duration, n.velocity, n.mute,
			n.probability, n.velocity_deviation, n.release_velocity)
			for n in self.get_notes_extended(0, 128, self.loop_start, length)]
		self.loop_end = self.loop_start + 2 * length
		self.end_marker = max(self.end_marker, self.loop_end)
		if copies:
			self.add_new_notes(copies)


def _set_slot_state(slot, triggered, playing):
	"""Set the launch state of a slot and its clip; fires playing_status as Live does."""
	status = 1 if playing else (2 if triggered else 0)
	targets = (slot, slot.clip) if slot.clip is not None else (slot,)
	for target in targets:
		target.is_triggered = triggered
		target.is_playing = playing
		target.__dict__["_lv_playing_status"] = status
		notify(target, "playing_status")


@listenable(clip=None, has_clip=False, is_playing=False, is_triggered=False, is_recording=False,
	playing_status=0, will_record_on_start=False, has_stop_button=True, controls_other_clips=False, color=None)
class ClipSlot(_Object):
	"""Launching is immediate on the next ``Song.advance`` (no quantization)."""

	is_group_slot = False

	def __init__(self, track):
		super().__init__()
		self.canonical_parent = track
		self.fire_count = 0

	@property
	def index(self):
		return list(self.canonical_parent.clip_slots).index(self)

	def create_clip(self, length):
		if self.has_clip:
			raise RuntimeError("Clip slot already has a clip")
		if not self.canonical_parent.has_midi_input:
			raise RuntimeError("Cannot create MIDI clip on audio track")
		self.set_clip(Clip(length=length))
		return self.clip

	def set_clip(self, clip):
		if clip is not None:
			clip.canonical_parent = self
		self.clip = clip
		self.has_clip = clip is not None
		self.color = clip.color if clip is not None else None
		song = getattr(self.canonical_parent, "canonical_parent", None)
		view = getattr(song, "view", None)
		if view is not None and view.highlighted_clip_slot is self:
			view.detail_clip = clip  # Like Live, the detail view shows the new clip of the highlighted slot.
		notify(self.canonical_parent, "clip_slots")

	def delete_clip(self):
		self.set_clip(None)

	def duplicate_clip_to(self, target):
		if not self.has_clip:
			raise RuntimeError("No clip to duplicate")
		source = self.clip
		copy = Clip(length=source.length, is_midi=source.is_midi_clip, notes=source.note_tuples(), name=source.name)
		target.set_clip(copy)

	def fire(self, force_legato=False, launch_quantization=None, record_length=None):
		self.fire_count += 1
		_set_slot_state(self, triggered=True, playing=self.is_playing)
		self.canonical_parent._fire_slot(self)

	def set_fire_button_state(self, state):
		if state:
			self.fire()

	def stop(self):
		self.canonical_parent.stop_all_clips()


# --------------------------------------------------------------------------- tracks and scenes

@listenable(selected_device=None, is_collapsed=False)
class TrackView(_Object):
	def __init__(self, track):
		self.canonical_parent = track
		self.device_insert_mode = 0

	def select_instrument(self):
		for device in self.canonical_parent.devices:
			if device.type == DeviceType.instrument:
				self.selected_device = device
				return True
		return False


@listenable(name="", arm=False, mute=False, solo=False, color=0, color_index=0, implicit_arm=False,
	playing_slot_index=-1, fired_slot_index=-1, devices=tuple, clip_slots=tuple, fold_state=0,
	is_visible=True, input_routing_type=None, output_meter_level=0.0, output_meter_left=0.0,
	output_meter_right=0.0, current_monitoring_state=1, muted_via_solo=False, is_frozen=False)
@events("data", "available_input_routing_types", "input_routing_channel", "output_routing_type")
class Track(_Object):
	def __init__(self, song, name="Track", is_midi=True, num_scenes=8, num_sends=2, can_be_armed=True, devices=()):
		super().__init__(name=name)
		self.canonical_parent = song
		self.has_midi_input = is_midi
		self.has_audio_input = not is_midi
		self.has_midi_output = not is_midi
		self.has_audio_output = True
		self.can_be_armed = can_be_armed
		self.is_foldable = False
		self.is_grouped = False
		self.is_part_of_selection = False
		self.mixer_device = MixerDevice(self, num_sends)
		self.view = TrackView(self)
		self.clip_slots = tuple(ClipSlot(self) for _ in range(num_scenes))
		self.devices = tuple(devices)
		for device in self.devices:
			device.canonical_parent = self

	def _fire_slot(self, slot):
		if slot.has_clip:
			self.fired_slot_index = slot.index
		elif slot.has_stop_button:
			self.fired_slot_index = -2

	def stop_all_clips(self, quantized=True):
		self.fired_slot_index = -2

	def duplicate_clip_slot(self, index):
		target = index + 1
		while target < len(self.clip_slots) and self.clip_slots[target].has_clip:
			target += 1
		if target >= len(self.clip_slots):
			self.canonical_parent.create_scene(-1)
		self.clip_slots[index].duplicate_clip_to(self.clip_slots[target])
		return target

	def jump_in_running_session_clip(self, beats):
		pass

	def get_data(self, key, default):
		return default

	def set_data(self, key, value):
		pass

	def _add_slot(self, index):
		slots = list(self.clip_slots)
		slots.insert(index, ClipSlot(self))
		self.clip_slots = tuple(slots)

	def _remove_slot(self, index):
		slots = list(self.clip_slots)
		del slots[index]
		self.clip_slots = tuple(slots)


@listenable(name="", color=0, is_triggered=False, tempo=-1.0, is_empty=False)
class Scene(_Object):
	def __init__(self, song, name=""):
		super().__init__(name=name)
		self.canonical_parent = song
		self.fire_count = 0

	@property
	def clip_slots(self):
		index = list(self.canonical_parent.scenes).index(self)
		return tuple(track.clip_slots[index] for track in self.canonical_parent.tracks)

	def fire(self, force_legato=False, can_select_scene_on_launch=True):
		self.fire_count += 1
		for slot in self.clip_slots:
			if slot.has_clip:
				slot.fire()
			else:
				slot.canonical_parent.stop_all_clips()

	def fire_as_selected(self, force_legato=False):
		self.fire()

	def set_fire_button_state(self, state):
		if state:
			self.fire()


# --------------------------------------------------------------------------- song

@listenable(selected_track=None, selected_scene=None, detail_clip=None, highlighted_clip_slot=None,
	selected_chain=None, selected_parameter=None, follow_song=False, draw_mode=True)
class SongView(_Object):
	def __init__(self, song):
		self.canonical_parent = song
		# Like Live, the detail view shows the clip of the highlighted slot.
		self.add_highlighted_clip_slot_listener(self._show_highlighted_clip)

	def _show_highlighted_clip(self):
		slot = self.highlighted_clip_slot
		self.detail_clip = slot.clip if slot is not None else None

	def select_device(self, device, should_appoint_device=True):
		track = device.canonical_parent
		while track is not None and not isinstance(track, Track):
			track = track.canonical_parent
		if track is not None:
			track.view.selected_device = device
		if should_appoint_device:
			self.canonical_parent.appointed_device = device


@listenable(tempo=120.0, is_playing=False, metronome=False, overdub=False, session_record=False,
	session_record_status=0, record_mode=False, clip_trigger_quantization=4,
	midi_recording_quantization=0, signature_numerator=4, signature_denominator=4, root_note=0,
	scale_name="Major", scale_mode=True, swing_amount=0.0, current_song_time=0.0, nudge_up=False,
	nudge_down=False, can_undo=False, can_redo=False, appointed_device=None, select_on_launch=True,
	exclusive_arm=True, exclusive_solo=False, tracks=tuple, visible_tracks=tuple, return_tracks=tuple,
	scenes=tuple, re_enable_automation_enabled=False, groove_amount=1.0, song_length=0.0,
	is_counting_in=False, punch_in=False, punch_out=False, loop=False, back_to_arranger=False,
	arrangement_overdub=False, session_automation_record=False, count_in_duration=0,
	scale_intervals=lambda: (0, 2, 4, 5, 7, 9, 11))
@events("data", "cue_points")
class Song(_Object):
	def __init__(self, num_tracks=8, num_scenes=8, num_returns=2, midi_tracks=None):
		super().__init__()
		self.view = SongView(self)
		self.undo_steps = []
		self.tap_count = 0
		midi_tracks = range(num_tracks) if midi_tracks is None else midi_tracks
		self.tracks = tuple(Track(self, "%d-%s" % (i + 1, "MIDI" if i in midi_tracks else "Audio"),
			is_midi=i in midi_tracks, num_scenes=num_scenes, num_sends=num_returns) for i in range(num_tracks))
		self.visible_tracks = self.tracks
		self.return_tracks = tuple(Track(self, "%s-Return" % chr(65 + i), is_midi=False, num_scenes=0,
			num_sends=num_returns, can_be_armed=False) for i in range(num_returns))
		self.master_track = Track(self, "Master", is_midi=False, num_scenes=0, num_sends=0, can_be_armed=False)
		self.scenes = tuple(Scene(self, "Scene %d" % (i + 1)) for i in range(num_scenes))
		self.view.selected_track = self.tracks[0] if self.tracks else None
		self.view.selected_scene = self.scenes[0] if self.scenes else None
		self.view.highlighted_clip_slot = self.tracks[0].clip_slots[0] if self.tracks and self.scenes else None

	# -- transport
	def start_playing(self):
		self.is_playing = True

	def stop_playing(self):
		self.is_playing = False

	def continue_playing(self):
		self.is_playing = True

	def stop_all_clips(self, quantized=True):
		for track in self.tracks:
			track.stop_all_clips()

	def tap_tempo(self):
		self.tap_count += 1

	def undo(self):
		self.undo_steps.append("undo")

	def redo(self):
		self.undo_steps.append("redo")

	def begin_undo_step(self):
		pass

	def end_undo_step(self):
		pass

	def trigger_session_record(self, record_length=None):
		self.session_record = not self.session_record

	def re_enable_automation(self):
		pass

	def jump_by(self, beats):
		self.current_song_time = max(0.0, self.current_song_time + beats)

	def scrub_by(self, beats):
		self.jump_by(beats)

	def get_data(self, key, default):
		return default

	def set_data(self, key, value):
		pass

	def get_beats_loop_length(self):
		return _Object(bars=1, beats=0, sub_division=0, ticks=0)

	def get_current_beats_song_time(self):
		return _Object(bars=1, beats=1, sub_division=1, ticks=0)

	# -- scenes
	def create_scene(self, index):
		scenes = list(self.scenes)
		index = len(scenes) if index < 0 else index
		scene = Scene(self, "Scene %d" % (len(scenes) + 1))
		scenes.insert(index, scene)
		for track in self.tracks:
			track._add_slot(index)
		self.scenes = tuple(scenes)
		return scene

	def delete_scene(self, index):
		if len(self.scenes) <= 1:
			raise RuntimeError("Cannot delete the last scene")
		scenes = list(self.scenes)
		del scenes[index]
		for track in self.tracks:
			track._remove_slot(index)
		self.scenes = tuple(scenes)
		if self.view.selected_scene not in self.scenes:
			self.view.selected_scene = self.scenes[min(index, len(self.scenes) - 1)]

	def duplicate_scene(self, index):
		new = self.create_scene(index + 1)
		for track in self.tracks:
			source = track.clip_slots[index]
			if source.has_clip:
				source.duplicate_clip_to(track.clip_slots[index + 1])
		return new

	def capture_and_insert_scene(self, mode=None):
		return self.create_scene(list(self.scenes).index(self.view.selected_scene) + 1)

	# -- helpers for tests (not Live API)
	def advance(self, beats=1.0):
		"""Launch fired clips and move playing clips forward by ``beats``."""
		self.is_playing = True
		self.current_song_time += beats
		for track in self.tracks:
			fired = track.fired_slot_index
			if fired >= 0 or fired == -2:
				for slot in track.clip_slots:
					if slot.is_playing or slot.is_triggered:
						_set_slot_state(slot, triggered=False, playing=False)
				if fired >= 0:
					slot = track.clip_slots[fired]
					slot.clip.playing_position = slot.clip.loop_start
					_set_slot_state(slot, triggered=False, playing=True)
				track.playing_slot_index = fired
				track.fired_slot_index = -1
			for slot in track.clip_slots:
				if slot.is_playing and slot.clip is not None:
					clip = slot.clip
					position = clip.playing_position + beats
					if position >= clip.loop_end:
						position = clip.loop_start + (position - clip.loop_end) % max(clip.length, 1e-9)
					clip.playing_position = position

