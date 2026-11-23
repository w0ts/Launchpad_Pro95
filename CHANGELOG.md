# Changelog

What changed in Launchpad Pro95, newest first. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- Launchpad Pro95 now needs **Live 11 or later**. For Live 9.5 and Live 10, use the archived release
  [legacy-live9-10](https://github.com/w0ts/Launchpad_Pro95/releases/tag/legacy-live9-10).
- The step sequencers use Live 11's note API. They no longer use the calls Live deprecated (which log warnings in
  newer Lives), and the notes they rewrite keep their probability, velocity deviation and release velocity.
- Python 3 only (the Python of Live 11+): the Python 2 code paths are gone.
- The project moves to [w0ts](https://w0ts.github.io/), with its manual at
  [w0ts.github.io/Launchpad_Pro95](https://w0ts.github.io/Launchpad_Pro95/).

### Fixed

- Entering a step sequencer no longer rescales the clip's loop, rewrites its notes or resets the quantization: the
  sequencer keeps the quantization you chose last time.
- Melodic step sequencer: it only rewrites the notes it shows. Muted notes, notes outside the scale rows or octaves it
  displays, notes before the clip start and extra notes in mono mode stay untouched. Notes are no longer written with
  a length of 0, and clips longer than 32 beats work.
- Drum step sequencer: velocity and mute edits no longer duplicate the note; the note selector of the drum rack layout
  no longer fails on releasing velocity.
- Loop selector: selecting a loop after the current one sets the right loop, and extending the loop (velocity held)
  copies from the loop start.
- Melodic layouts and the melodic sequencer under Python 3: no fractional pitches, no octave too high below the root,
  the right root in the note selector.
- Device mode with a device inside a rack, or with a return or the master track selected; the sequencers' arrow
  buttons with a return or the master track selected.
- Device mode: parameters with 9 values are drawn as long lists instead of failing.
- A track armed before the script started is followed; two Launchpad Pros in the same Live each keep their own
  quantization.
- Session: the stop buttons of stopped tracks show a dimmed red instead of their on colour; colours the skin was
  missing or misspelled are added.
- The script releases its listeners when a mode or the script is switched off.

### Removed

- The `STEPSEQ__SAVE_SCALE` option of `Settings.py`: the code behind it never existed and it crashed the sequencers.
- Dead code, the unused on-screen display code and the code for Lives older than 10.

### Development

- A test suite runs the script outside Live, against a fake Live API and an emulated Launchpad Pro
  ([tests/README.md](tests/README.md)), on GitHub Actions with ruff and black.
- The manual moves to `site/`, published by GitHub Pages; the README is `README.md`; this change log replaces the
  manual's history list.

## 2025-01-28

- Step sequencer fixes (thanks John).

## 2023-02-01

- Python 3 fixes (thanks jefffm).

## 2021-02-05

- Live 11 support.

## 2018-06-08

- Duplicate clip in session view (thanks marctdt).

## 2018-01-29

- Fixes for Ableton Live 10.

## 2017-01-04

- Custom scale mode, a contribution from boblemarin.

## 2016-04-09

- Bug fixes, minor skin updates.

## 2016-03-28

- Bug fixes; part of the code merged with Launchpad95.

## 2016-01-10

- Bug fixes.

## 2015-12-28

- First public version.

## 2015-10

- Work on an initial version.
