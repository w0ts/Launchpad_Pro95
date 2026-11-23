"""Checks on the script's source files that need no framework."""
import glob
import os
import warnings

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOURCES = sorted(glob.glob(os.path.join(REPO_ROOT, "*.py")))


def test_every_module_compiles_under_python3():
	for path in SOURCES:
		with open(path, encoding="utf-8") as source:
			compile(source.read(), path, "exec")


@pytest.mark.xfail(strict=True, reason="bug: 'value is 0' / 'value is not 0' identity comparisons with int literals "
	"(DeviceComponent.py:358,441,459,500,519, NoteEditorComponent.py:422,433, StepSequencerComponent.py:144,186,1353, "
	"SpecialSessionComponent.py _on_stop_scene_value, StepSequencerComponent2.py _random_button_value); "
	"Python 3.8+ warns, and they only work because CPython caches small ints")
def test_no_identity_comparison_with_literals():
	offenders = []
	for path in SOURCES:
		with open(path, encoding="utf-8") as source:
			text = source.read()
		with warnings.catch_warnings(record=True) as caught:
			warnings.simplefilter("always")
			compile(text, path, "exec")
		offenders += ["%s: %s" % (os.path.basename(path), w.message) for w in caught
			if issubclass(w.category, SyntaxWarning)]
	assert offenders == []
