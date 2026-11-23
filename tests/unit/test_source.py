"""Checks on the script's source files that need no framework."""
import glob
import os
import warnings

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOURCES = sorted(glob.glob(os.path.join(REPO_ROOT, "*.py")))


def test_every_module_compiles_under_python3():
	for path in SOURCES:
		with open(path, encoding="utf-8") as source:
			compile(source.read(), path, "exec")


def test_no_identity_comparison_with_literals():
	offenders = []
	for path in SOURCES:
		with open(path, encoding="utf-8") as source:
			text = source.read()
		with warnings.catch_warnings(record=True) as caught:
			warnings.simplefilter("always")
			compile(text, path, "exec")
		offenders += [f"{os.path.basename(path)}: {w.message}" for w in caught
			if issubclass(w.category, SyntaxWarning)]
	assert offenders == []
