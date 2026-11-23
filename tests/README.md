# Launchpad_Pro95 tests

The tests run the script outside Ableton Live, against an emulated Launchpad Pro, with
Python 3.11 (the Python of Live 11+). They also run on GitHub Actions
(`.github/workflows/tests.yml`).

## Run

```sh
python3.11 -m pip install future pytest pytest-cov pytest-timeout
scripts/fetch_framework.sh /some/dir/ableton-framework      # once
ABLETON_FRAMEWORK_DIR=/some/dir/ableton-framework python3.11 -m pytest
```

Add `--cov` for the coverage of the script modules.

### Where `_Framework` comes from

The script imports Ableton's `_Framework` (plus `_Generic` and `pushbase`), which is not in
this repository. `ABLETON_FRAMEWORK_DIR` points at one of:

- **A fetched tree** (what CI uses): `scripts/fetch_framework.sh <dir>` clones a pinned
  commit of [w0ts/AbletonLive11_MIDIRemoteScripts](https://github.com/w0ts/AbletonLive11_MIDIRemoteScripts/tree/fix-decompiled-framework)
  (the Live 11.2.11 decompile with its decompiler mistakes fixed in `_Framework`) and keeps
  only `_Framework`, `_Generic` and `ableton/v2/base`. That tree has no usable `pushbase`
  (the decompiled one holds merge-conflict markers and needs `ableton.v2.control_surface`),
  so the tests then use `tests/stubs/pushbase`, a small test double of the one class the
  script uses (`ClipSlotCopyHandler`, for copying clips).
- **An installed Live**: `ABLETON_FRAMEWORK_DIR="/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/MIDI Remote Scripts"`.
  Its `.pyc` files load in a Python 3.11 of the same minor version, and its real `pushbase`
  is used. Use this to check that the fetched tree still behaves like the real one. The two
  sources should give the same results.

The `Live` module is always the fake one in `tests/fake_live/Live`.

## Layout

- `fake_live/Live/`: the fake `Live` API. It has a small object model (Song, Track,
  ClipSlot, Clip with the Live 11 note API, Scene, Device, RackDevice, MixerDevice...). Its
  listenable properties fire their listeners at once. Time moves only when a test calls
  `song.advance(beats)`, which launches fired clips and moves the playing position. The
  Clip records the deprecated note calls (`select_all_notes`, `get_selected_notes`,
  `replace_selected_notes`...) in `clip.deprecated_calls`, so tests can forbid them.
- `stubs/pushbase/`: see above; only on the path when the framework has no `pushbase`.
- `harness/`:
  - `c_instance.py`: `FakeCInstance`, which records sent MIDI, logs and translations.
  - `devices.py`: the emulated `LaunchpadPro` (the original model). It answers the identity
    request and the challenge, turns presses into MIDI (grid notes 11..88, round buttons
    CC 1..8, 10..80, 89..19, 91..98) and decodes LEDs, layout and fader sysex. Its
    docstring lists what is taken from the script rather than from real hardware.
  - `rig.py`: `Rig`, which wires everything together the way Live routes MIDI (forwarded,
    mapped, or sent to the track as notes), and the `TOP`, `LEFT` and `BOTTOM` button names.
  - `clock.py`: a fake clock for the script's long-press and double-tap timings. It moves
    100 ms per `rig.tick()`, so taps are always short; use `rig.wait(seconds)` for a long
    press.
- `conftest.py`: path setup, loads the repository as package `Launchpad_Pro95`, and
  provides the fixtures `rig` (a booted surface), `make_rig`, `model` and `clock`.
- `unit/`: no Live needed (ClipNotes, source checks).
- `emulated/`: boot and handshake, modes, session, mixer, device, instrument and drums,
  both step sequencers, ClipNotes on the fake clip, disconnect, known bugs.

## Known bugs

Tests marked `xfail(strict=True, reason="bug: ...")` describe bugs in the script that are
not fixed yet (most are in `emulated/test_known_bugs.py`). When a fix lands, the test
passes, strict xfail turns that into a failure, and the mark must be removed.

## Writing tests

```python
from harness.rig import LEFT, TOP, make_song

def test_delete_and_pad_deletes_the_clip(make_rig):
    rig = make_rig(song=make_song(clips=[(1, 1)]))
    rig.press_left(LEFT["delete"])
    rig.tap(1, 1)                 # grid x=1 (from the left), y=1 (from the top)
    rig.release_left(LEFT["delete"])
    assert not rig.song.tracks[1].clip_slots[1].has_clip
```

`rig.tap_top(i)`, `rig.tap_side(i)` (scene buttons, top first), `rig.tap_left(i)` (top
first) and `rig.tap_bottom(i)` tap the round buttons. `rig.device.led(x, y)` returns the
colour of a pad, `rig.mode` the selected mode.
