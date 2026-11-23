"""Boot, identity, challenge handshake and disconnect of the Launchpad Pro."""
from harness.devices import CHALLENGE_COMMAND, IDENTITY_REQUEST, LEDS_OFF_COMMAND, MODE_COMMAND, NOVATION_PREFIX


def test_identity_then_challenge_then_live_mode(rig):
	device = rig.device
	assert IDENTITY_REQUEST in device.received
	assert device.answered_challenge
	sysex = [m for m in device.received if m[0] == 0xF0]
	identity_at = sysex.index(IDENTITY_REQUEST)
	challenge_at = next(i for i, m in enumerate(sysex) if m[:7] == NOVATION_PREFIX + (CHALLENGE_COMMAND,))
	live_mode_at = sysex.index(NOVATION_PREFIX + (MODE_COMMAND, 0, 247))
	assert identity_at < challenge_at < live_mode_at
	assert device.in_live_mode


def test_boot_enables_the_modes_in_session_mode(rig):
	assert rig.modes.is_enabled()
	assert rig.mode == "session_mode"
	assert rig.device.live_layout == 0  # session layout


def test_boot_logs_no_errors(rig):
	problems = [line for line in rig.log if "Traceback" in line or "rror" in line or "xception" in line]
	assert problems == []


def test_boot_lights_the_session_mode_button(rig):
	skin = rig.surface._skin
	assert rig.device.top_led(4).value == skin["Mode.Session.On"].midi_value


def test_wrong_product_id_does_not_start(make_rig):
	rig = make_rig(boot=False)
	rig.device.identity_reply = rig.device.identity_reply[:8] + (105,) + rig.device.identity_reply[9:]  # a Launchpad MK2
	rig.create()
	rig.tick(20)
	assert not rig.device.answered_challenge
	assert not rig.modes.is_enabled()
	assert any("wrong product id" in line for line in rig.log)


def test_wrong_challenge_answer_does_not_start(make_rig):
	rig = make_rig(boot=False)
	answer = rig.device.answer

	def bad_answer(midi_bytes):
		if midi_bytes[:7] == NOVATION_PREFIX + (CHALLENGE_COMMAND,):
			midi_bytes = midi_bytes[:7] + ((midi_bytes[7] + 1) & 0x7F,) + midi_bytes[8:]
		answer(midi_bytes)

	rig.device.answer = bad_answer
	rig.create()
	rig.tick(20)
	assert not rig.modes.is_enabled()


def test_no_answer_means_no_modes(make_rig):
	rig = make_rig(boot=False)
	rig.device.answer = lambda midi: None  # an unplugged / silent device
	rig.create()
	rig.tick(20)
	assert not rig.modes.is_enabled()


def test_disconnect_turns_the_leds_off_and_quits(make_rig):
	rig = make_rig()
	rig.disconnect()
	tail = rig.device.sysex_commands[-2:]
	assert tail == [(LEDS_OFF_COMMAND, 0), (CHALLENGE_COMMAND,)]


def test_layout_status_from_the_device_redraws(rig):
	rig.device.leds = {}
	rig.send(rig.device.layout_status(2))  # note layout status: the script redraws everything
	rig.tick()
	assert rig.device.top_led(4).value is not None
