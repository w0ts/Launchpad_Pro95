"""After disconnect() the script should leave no listener on Live's objects (they outlive it)."""

import pytest
from harness.rig import BOTTOM, TOP, make_song


def live_objects(song):
    """The song and the Live objects reachable from it that the script listens to."""
    import Live

    objects = [song, song.view, Live.Application.get_application(), Live.Application.get_application().view]
    for track in tuple(song.tracks) + tuple(song.return_tracks) + (song.master_track,):
        objects += [track, track.view, track.mixer_device] + list(track.mixer_device.sends)
        objects += [track.mixer_device.volume, track.mixer_device.panning]
        for device in track.devices:
            objects += [device, device.view] + list(device.parameters)
        for clip_slot in getattr(track, "clip_slots", ()):
            objects.append(clip_slot)
            if clip_slot.clip is not None:
                objects.append(clip_slot.clip)
    objects += list(song.scenes)
    return objects


def script_listeners(song):
    """(object, event, listener) for every listener whose code is in the script package or _Framework."""
    found = []
    for obj in live_objects(song):
        listener_set = obj.__dict__.get("_listener_set")
        if listener_set is None:
            continue
        for name, listeners in listener_set._by_name.items():
            for listener in listeners:
                owner = getattr(listener, "__self__", None)
                module = type(owner).__module__ if owner is not None else getattr(listener, "__module__", "")
                if module.startswith(("Launchpad_Pro95", "_Framework")):
                    found.append((type(obj).__name__, name, getattr(listener, "__qualname__", repr(listener))))
    return found


def _run(make_rig, taps):
    song = make_song(clips=[(0, 0)])
    rig = make_rig(song=song)
    for kind, button in taps:
        if kind == "top":
            rig.tap_top(TOP[button])
        else:
            rig.tap_bottom(BOTTOM[button])
        rig.tick()
    rig.disconnect()
    return script_listeners(song)


def test_session_mode_leaves_no_listener(make_rig):
    leaks = _run(make_rig, ())
    assert leaks == [], "\n".join(map(str, leaks))


@pytest.mark.parametrize(
    "taps",
    [
        [("top", "note")],
        [("bottom", "volume")],
    ],
    ids=["instrument", "volume"],
)
def test_other_modes_leave_no_listener(make_rig, taps):
    leaks = _run(make_rig, taps)
    assert leaks == [], "\n".join(map(str, leaks))


def test_device_mode_leaves_no_listener(make_rig):
    import Live

    song = make_song()
    device = Live.Device.Device(name="Synth", class_name="TestSynth")
    device.canonical_parent = song.tracks[0]
    song.tracks[0].devices = (device,)
    song.tracks[0].view.selected_device = device
    song.appointed_device = device
    rig = make_rig(song=song)
    rig.tap_top(TOP["device"])
    rig.tick()
    rig.disconnect()
    leaks = script_listeners(song)
    assert leaks == [], "\n".join(map(str, leaks))


@pytest.mark.parametrize(
    "taps",
    [
        [("top", "user")],
        [("top", "user"), ("top", "user")],
    ],
    ids=["drum seq", "melodic seq"],
)
def test_step_sequencers_leave_no_listener(make_rig, taps):
    leaks = _run(make_rig, taps)
    assert leaks == [], "\n".join(map(str, leaks))


@pytest.mark.parametrize(
    "taps",
    [[("top", name)] for name in ("session", "note", "device", "user")]
    + [[("top", "user"), ("top", "user")]]
    + [[("bottom", name)] for name in sorted(BOTTOM)]
    + [[("top", "user"), ("top", "session"), ("top", "user"), ("top", "user"), ("bottom", "volume"), ("top", "note")]],
    ids=lambda taps: "+".join(name for _, name in taps),
)
def test_every_mode_leaves_no_listener(make_rig, taps):
    leaks = _run(make_rig, taps)
    assert leaks == [], "\n".join(map(str, leaks))


def _sequencer_rig(make_rig, user_taps):
    """A rig in the drum sequencer (one user tap) or the melodic sequencer (two)."""
    rig = make_rig(song=make_song(clips=[(0, 0)]))
    for _ in range(user_taps):
        rig.tap_top(TOP["user"])
        rig.tick()
    return rig


def test_every_component_runs_the_base_disconnect(make_rig, monkeypatch):
    """A component's disconnect must reach ControlSurfaceComponent.disconnect (it releases the
    component's slots, listeners and tasks)."""
    from _Framework.ControlSurfaceComponent import ControlSurfaceComponent

    rig = _sequencer_rig(make_rig, 2)
    components = list(rig.surface.components)
    reached = set()
    base_disconnect = ControlSurfaceComponent.disconnect

    def recording_disconnect(self):
        reached.add(id(self))
        base_disconnect(self)

    monkeypatch.setattr(ControlSurfaceComponent, "disconnect", recording_disconnect)
    rig.disconnect()
    skipped = [type(c).__name__ for c in components if id(c) not in reached]
    assert skipped == []


@pytest.mark.parametrize("melodic", [False, True], ids=["drum seq", "melodic seq"])
def test_note_editor_disconnect_releases_its_controls(make_rig, melodic):
    rig = _sequencer_rig(make_rig, 2 if melodic else 1)
    surface = rig.surface
    editor = (surface._step_sequencer2 if melodic else surface._step_sequencer)._note_editor
    names = [("_matrix", "_matrix_value")]
    if melodic:
        names += [
            ("_random_button", "_random_button_value"),
            ("_mode_notes_pitches_button", "_mode_button_notes_pitches_value"),
        ]
    else:
        names += [("_velocity_button", "_velocity_value")]
    pairs = [(getattr(editor, attr), getattr(editor, method)) for attr, method in names]
    assert all(element.value_has_listener(listener) for element, listener in pairs)
    # the editor alone: disconnecting the surface would also disconnect the controls
    editor.disconnect()
    still = [listener.__qualname__ for element, listener in pairs if element.value_has_listener(listener)]
    assert still == []


def test_scale_editor_gives_the_matrix_back(make_rig):
    rig = _sequencer_rig(make_rig, 1)
    scale = rig.surface._step_sequencer._scale_component
    rig.press_side(0)  # scale editor: the scale component takes the matrix
    rig.tick()
    matrix = scale._matrix
    assert matrix.value_has_listener(scale._matrix_pressed)
    rig.release_side(0)  # back to the sequencer
    rig.tick()
    assert scale._matrix is None
    assert not matrix.value_has_listener(scale._matrix_pressed)
