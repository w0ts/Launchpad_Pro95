"""Emulated Launchpad Pro (the original, 2015): it answers the script's handshake, turns
button presses into the MIDI the hardware sends, and decodes the LED state from the MIDI
the script sends.

Layout (from Launchpad_Pro95.py's MidiMap, channel 1 = MIDI channel 0):

- grid ``(x, y)``: x = column 0..7 left to right, y = row 0..7 top to bottom; note
  ``81 - 10 * y + x`` (top row 81..88, bottom row 11..18).
- ``top(i)``: round buttons above the grid, CC 91..98: up, down, left, right, session,
  note, device, user.
- ``side(i)``: scene launch buttons right of the grid, top first, CC 89, 79, ... 19.
- ``left(i)``: buttons left of the grid, top first, CC 80, 70, ... 10: shift, click,
  undo, delete, quantise, duplicate, double, record.
- ``bottom(i)``: buttons below the grid, left to right, CC 1..8: record arm, track select,
  mute, solo, volume, pan, sends, stop clip.

LEDs: a note-on (pads) or CC (round buttons) whose value is a palette index; MIDI channel
0 is a static colour, 1 flashing, 2 pulsing (consts.BLINK_LED_CHANNEL / PULSE_LED_CHANNEL).

Unverified on hardware (taken from the script, not from a capture of a real device):
- the identity reply after the family code (model 00 00 and the firmware bytes), and its
  device id byte (byte 2);
- that the pads keep sending the programmer-style notes 11..88 on channel 0 in every
  layout the script selects (sysex 0x22 Live layout and 0x2C standalone layout); the
  emulator records the layout commands but does not change its note map;
- that the challenge answer is ``F0 00 20 29 02 10 40 <lo> <hi> F7`` (the script's
  _is_challenge_response); ``encrypt_challenge2`` is the fake Live one.
"""
from collections import deque

import Live

NOTE_ON = 0x90
CC = 0xB0
SYSEX_START = 0xF0
SYSEX_END = 0xF7

IDENTITY_REQUEST = (240, 126, 127, 6, 1, 247)
NOVATION_PREFIX = (240, 0, 32, 41, 2, 16)  # Novation, Launchpad Pro
CHALLENGE_COMMAND = 64
LIVE_LAYOUT_COMMAND = 34        # 0x22
MODE_COMMAND = 33               # 0x21: 0 = Live mode, 1 = standalone
STANDALONE_LAYOUT_COMMAND = 44  # 0x2C
FADER_SETUP_COMMAND = 43        # 0x2B
LEDS_OFF_COMMAND = 14           # 0x0E

# LED channels: 0 = static colour, 1 = flashing, 2 = pulsing.
STATIC, FLASH, PULSE = 0, 1, 2
LED_CHANNELS = (STATIC, FLASH, PULSE)


class Led:
	"""The state of one LED: the static value, and the flash/pulse value if any."""

	def __init__(self):
		self.static = None
		self.flash = None
		self.pulse = None
		self.channel = None

	def apply(self, channel, value):
		self.channel = channel
		if channel == FLASH:
			self.flash = value
		elif channel == PULSE:
			self.pulse = value
		else:
			self.static = value
			self.flash = None
			self.pulse = None

	@property
	def value(self):
		for value in (self.pulse, self.flash, self.static):
			if value is not None:
				return value
		return None

	def __repr__(self):
		return f"Led(static={self.static!r}, flash={self.flash!r}, pulse={self.pulse!r})"


class LaunchpadPro:
	name = "Launchpad Pro"
	# Universal identity reply: F0 7E <device id> 06 02 <Novation 00 20 29> <family 51 00>
	# <model 00 00> <firmware x4> F7. The script checks bytes 5..9 (00 20 29 51 00).
	identity_reply = (240, 126, 0, 6, 2, 0, 32, 41, 81, 0, 0, 0, 0, 1, 5, 4, 247)

	def __init__(self):
		self.outbox = deque()
		self.leds = {}
		self.other_channel_values = {}
		self.received = []
		self.sysex_commands = []
		self.fader_setups = {}
		self.answered_handshake = False
		self.answered_challenge = False

	# -- layout
	def grid_identifier(self, x, y):
		return 81 - 10 * y + x

	def top_identifier(self, index):
		return 91 + index

	def side_identifier(self, index):
		return 89 - 10 * index

	def left_identifier(self, index):
		return 80 - 10 * index

	def bottom_identifier(self, index):
		return 1 + index

	# -- input (what the user does)
	def grid_message(self, x, y, velocity=127):
		return (NOTE_ON, self.grid_identifier(x, y), velocity)

	def top_message(self, index, value=127):
		return (CC, self.top_identifier(index), value)

	def side_message(self, index, value=127):
		return (CC, self.side_identifier(index), value)

	def left_message(self, index, value=127):
		return (CC, self.left_identifier(index), value)

	def bottom_message(self, index, value=127):
		return (CC, self.bottom_identifier(index), value)

	def fader_message(self, index, value):
		"""A touch on fader ``index`` of the fader layout (CC 21..28, from the script)."""
		return (CC, 21 + index, value)

	def layout_status(self, layout):
		"""The layout status the device sends (F0 00 20 29 02 10 2E <layout> F7); unverified."""
		return NOVATION_PREFIX + (46, layout, SYSEX_END)

	# -- output (what the script sends us)
	def receive(self, midi_bytes):
		self.received.append(midi_bytes)
		if midi_bytes[0] == SYSEX_START:
			self.receive_sysex(midi_bytes)
			return
		status = midi_bytes[0] & 0xF0
		channel = midi_bytes[0] & 0x0F
		if status in (NOTE_ON, CC) and len(midi_bytes) == 3:
			self.receive_short(status, channel, midi_bytes[1], midi_bytes[2])

	def receive_short(self, status, channel, identifier, value):
		if channel in LED_CHANNELS:
			self.leds.setdefault((status, identifier), Led()).apply(channel, value)
		else:
			# The script also lights its user-layout channels (MultiButtonElement slaves).
			self.other_channel_values[(status, channel, identifier)] = value

	def receive_sysex(self, midi_bytes):
		if midi_bytes == IDENTITY_REQUEST:
			self.answer(self.identity_reply)
			return
		if midi_bytes[:6] != NOVATION_PREFIX:
			return
		body = midi_bytes[6:-1]
		self.sysex_commands.append(body)
		if body[0] == CHALLENGE_COMMAND and len(body) == 5:
			challenge = sum(body[1 + i] << (8 * i) for i in range(4))
			response = Live.Application.encrypt_challenge2(challenge)
			self.answered_challenge = True
			self.answer(NOVATION_PREFIX + (CHALLENGE_COMMAND, response & 0x7F, (response >> 8) & 0x7F, SYSEX_END))
		elif body[0] == FADER_SETUP_COMMAND and len(body) == 5:
			index, kind, colour, value = body[1:]
			self.fader_setups[index] = (kind, colour, value)
		elif body[0] == LEDS_OFF_COMMAND:
			self.leds = {}

	def answer(self, midi_bytes):
		self.answered_handshake = True
		self.outbox.append(tuple(midi_bytes))

	# -- state
	def commands(self, command):
		return [body[1:] for body in self.sysex_commands if body[0] == command]

	@property
	def live_layout(self):
		layouts = self.commands(LIVE_LAYOUT_COMMAND)
		return layouts[-1][0] if layouts else None

	@property
	def standalone_layout(self):
		layouts = self.commands(STANDALONE_LAYOUT_COMMAND)
		return layouts[-1][0] if layouts else None

	@property
	def in_live_mode(self):
		modes = self.commands(MODE_COMMAND)
		return bool(modes) and modes[-1][0] == 0

	# -- LED access
	def _led(self, status, identifier):
		return self.leds.get((status, identifier), Led())

	def grid_led(self, x, y):
		return self._led(NOTE_ON, self.grid_identifier(x, y))

	def top_led(self, index):
		return self._led(CC, self.top_identifier(index))

	def side_led(self, index):
		return self._led(CC, self.side_identifier(index))

	def left_led(self, index):
		return self._led(CC, self.left_identifier(index))

	def bottom_led(self, index):
		return self._led(CC, self.bottom_identifier(index))

	def led(self, x, y):
		"""Colour value of grid button (x, y) (flash/pulse value wins over static)."""
		return self.grid_led(x, y).value

	def grid_values(self):
		return [[self.led(x, y) for x in range(8)] for y in range(8)]


ALL_MODELS = (LaunchpadPro,)
