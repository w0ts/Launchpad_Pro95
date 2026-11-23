# Launchpad Pro95

> ## [→ w0ts.github.io/Launchpad_Pro95](https://w0ts.github.io/Launchpad_Pro95/)
> **The manual, the download and the install steps: on the site.**

**Ableton Live scripts for the Novation Launchpad Pro.**

**Sequence your clips from the pads.** Two step sequencers, a drum one and a melodic one, edit the MIDI clips of
Live right on the Launchpad Pro.

**Play in key.** An instrument mode in the style of Push, with scales, layouts and octaves picked on the grid.

A plain Live control surface script in Python: no Max for Live, no other tool.

---

## What it does

* **Drum step sequencer**: a drum rack layout (note selector, loop selector, note editor) and a multinote layout
  (one note of the scale per row), with velocity, mute, quantization and clip or track lock.
* **Melodic step sequencer**: pitch, velocity, length and octave pages, mono or poly, following the scale. It only
  rewrites the notes it shows.
* **Instrument mode**: drum rack, chromatic and diatonic layouts (3rd, 4th or 6th), 26 scales, root note, octave and
  orientation, set in the scale edition mode.
* **Device controller**: eight parameters at once, drawn by type (on/off, lists of values, continuous), a precision
  mode, and four device locks on the scene buttons.
* **Everything else of Live's own Launchpad Pro script**: session, mixer modes, shift functions.

For Launchpad models other than the Pro, see [Launchpad95](https://w0ts.github.io/Launchpad95/).

## Install

Needs **Ableton Live 11 or later**. Download
[Launchpad_Pro95.zip](https://github.com/w0ts/Launchpad_Pro95/releases/latest/download/Launchpad_Pro95.zip) from the
[latest release](https://github.com/w0ts/Launchpad_Pro95/releases/latest), put the `Launchpad_Pro95` folder in the
`Remote Scripts` folder of your User Library, and choose it as a control surface in Live's settings. The
[site](https://w0ts.github.io/Launchpad_Pro95/#install) has the steps with screenshots.

Live 9.5 and Live 10: use the archived release
[legacy-live9-10](https://github.com/w0ts/Launchpad_Pro95/releases/tag/legacy-live9-10).

What changed in each version: [CHANGELOG.md](CHANGELOG.md).

## Troubleshooting

* **The Launchpad does not light up**: check the folder name (`Launchpad_Pro95`) and place, the Input and Output of
  the control surface (the Launchpad Pro's Live port), and that you run Live 11 or later. The
  [F.A.Q.](https://w0ts.github.io/Launchpad_Pro95/#faq) has more.
* **Logs**: Live writes the script's errors to its `Log.txt` (in Live's preferences folder).

## Development

The tests run the script outside Live, against a fake Live API and an emulated Launchpad Pro, with Python 3.11 (the
Python of Live 11+). They also run on GitHub Actions, with ruff and black. How to run them and where Ableton's
`_Framework` comes from: [tests/README.md](tests/README.md).

| Path | What |
|---|---|
| `*.py` | The script (Live loads `__init__.py`) |
| `Settings.py` | Experimental options |
| `tests/` | The test suite, the fake Live API and the emulated Launchpad Pro |
| `scripts/fetch_framework.sh` | Fetches the decompiled `_Framework` the tests import |
| `site/` | The user site, deployed by `.github/workflows/pages.yml` |

## Contributing

Bug reports and ideas go to the [issue tracker](https://github.com/w0ts/Launchpad_Pro95/issues). Please say which Live
version you use. Pull requests are welcome; run the tests first.

## Licence and attribution

Launchpad Pro95 is a modified version of the Launchpad Pro script that came with Ableton Live 9.5, and shares code with
[Launchpad95](https://w0ts.github.io/Launchpad95/). By w0ts, with contributions from boblemarin (custom scales),
marctdt (duplicate clip), jefffm (Python 3) and John (step sequencer fixes).

Launchpad Pro95 is free software, released under the GNU General Public License version 3 (GPL-3.0): see
[LICENSE](LICENSE).

### Not affiliated with Novation or Ableton

Launchpad Pro95 is an independent project. It is **not affiliated with, endorsed by, or sponsored by Novation
(Focusrite) or Ableton**. "Launchpad" is a trademark of Focusrite Audio Engineering; "Ableton", "Live" and "Push" are
trademarks of Ableton AG. They are used here only to describe what this script works with.
