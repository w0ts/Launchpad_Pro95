"""A fake ``Live`` module for running Launchpad_Pro95 and _Framework outside Ableton Live.

It covers only what the script and the framework use. The object model (Song, Track,
Clip, ...) is deterministic: setters fire listeners synchronously, and time only moves
when a test calls ``Song.advance``.
"""
from . import Application, Base, Chain, Clip, ClipSlot, Device, DeviceParameter, DrumPad
from . import MidiMap, MixerDevice, RackDevice, Scene, SimplerDevice, Song, Track

__all__ = ["Application", "Base", "Chain", "Clip", "ClipSlot", "Device", "DeviceParameter", "DrumPad", "MidiMap", "MixerDevice", "RackDevice", "Scene", "SimplerDevice", "Song", "Track"]
