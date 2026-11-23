"""Test setup: the fake ``Live`` module, Ableton's _Framework, and the script as package
``Launchpad_Pro95`` (whatever the checkout folder is called).

_Framework comes from ABLETON_FRAMEWORK_DIR: either a tree made by
``scripts/fetch_framework.sh <dir>`` or the "MIDI Remote Scripts" folder of an installed
Live 11+ (its .pyc files import fine with a matching Python 3.11).
"""
import importlib.util
import os
import sys

import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
FAKE_LIVE_DIR = os.path.join(TESTS_DIR, "fake_live")
STUBS_DIR = os.path.join(TESTS_DIR, "stubs")
PACKAGE_NAME = "Launchpad_Pro95"

# Never write .pyc files into the script folder (Live loads it).
sys.dont_write_bytecode = True

for path in (FAKE_LIVE_DIR, TESTS_DIR):
	if path not in sys.path:
		sys.path.insert(0, path)

FRAMEWORK_DIR = os.environ.get("ABLETON_FRAMEWORK_DIR", "")
FRAMEWORK_ERROR = None
if not FRAMEWORK_DIR:
	FRAMEWORK_ERROR = ("ABLETON_FRAMEWORK_DIR is not set: run scripts/fetch_framework.sh <dir> and set "
		"ABLETON_FRAMEWORK_DIR=<dir> (or point it at Live's 'MIDI Remote Scripts' folder)")
elif not os.path.isdir(os.path.join(FRAMEWORK_DIR, "_Framework")):
	FRAMEWORK_ERROR = "ABLETON_FRAMEWORK_DIR=%s has no _Framework folder" % FRAMEWORK_DIR
else:
	# After fake_live, so a 'Live' folder there could never shadow the fake.
	sys.path.insert(1, FRAMEWORK_DIR)
	if not os.path.isdir(os.path.join(FRAMEWORK_DIR, "pushbase")):
		# The fetched tree has no pushbase: use the test double (see tests/stubs).
		sys.path.append(STUBS_DIR)


def _load_package():
	if PACKAGE_NAME in sys.modules:
		return sys.modules[PACKAGE_NAME]
	spec = importlib.util.spec_from_file_location(PACKAGE_NAME, os.path.join(REPO_ROOT, "__init__.py"),
		submodule_search_locations=[REPO_ROOT])
	module = importlib.util.module_from_spec(spec)
	sys.modules[PACKAGE_NAME] = module
	try:
		spec.loader.exec_module(module)
	except BaseException:
		del sys.modules[PACKAGE_NAME]
		raise
	return module


def pytest_report_header(config):
	return "ABLETON_FRAMEWORK_DIR: %s" % (FRAMEWORK_DIR or "(not set)")


@pytest.fixture(scope="session")
def framework():
	"""The script package, importable with the framework. Fails (never skips) without one."""
	if FRAMEWORK_ERROR:
		pytest.fail(FRAMEWORK_ERROR, pytrace=False)
	return _load_package()


@pytest.fixture
def clock(framework, monkeypatch):
	"""The fake clock the script's modules read (it moves 100 ms per rig tick)."""
	from harness.clock import TIMED_MODULES, FakeTime

	fake = FakeTime()
	for name in TIMED_MODULES:
		monkeypatch.setattr(sys.modules["%s.%s" % (PACKAGE_NAME, name)], "time", fake)
	return fake


@pytest.fixture
def make_rig(framework, clock):
	"""make_rig(DeviceClass=LaunchpadPro, song=None, boot=True) -> a Rig; disconnected after the test."""
	import Live
	from harness.devices import LaunchpadPro
	from harness.rig import Rig

	Live.Application.reset_application()
	rigs = []

	def factory(device_class=LaunchpadPro, song=None, boot=True):
		rig = Rig(device_class(), song=song, clock=clock)
		rigs.append(rig)
		if boot:
			rig.boot()
		return rig

	yield factory
	errors = []
	for rig in rigs:
		try:
			rig.disconnect()
		except Exception as error:  # keep disconnecting the others, then report
			errors.append(error)
	if errors:
		raise errors[0]


def pytest_generate_tests(metafunc):
	"""Run every test that uses the ``model`` fixture once per emulated Launchpad (one today)."""
	if "model" in metafunc.fixturenames:
		from harness.devices import ALL_MODELS

		metafunc.parametrize("model", ALL_MODELS, ids=[cls.__name__ for cls in ALL_MODELS])


@pytest.fixture
def rig(make_rig, model):
	"""A booted surface, for each emulated model."""
	return make_rig(model)
