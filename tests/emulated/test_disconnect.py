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
