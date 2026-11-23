"""Every skin colour the script asks for exists in the skin (adapted from Launchpad95's test_skins)."""

import ast
import glob
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKIN_KEY_CALLS = (
    "set_light",
    "set_on_off_values",
    "send_value",
    "set_empty_value",
    "set_stopped_value",
    "set_started_value",
    "set_triggered_to_play_value",
    "set_triggered_to_record_value",
    "set_recording_value",
    "set_record_button_value",
    "set_stop_clip_value",
    "set_stop_clip_triggered_value",
    "set_selected_value",
    "set_playing_value",
    "set_triggered_value",
    "set_scene_value",
    "set_no_scene_value",
)
SKIN_FILES = ("SkinMK2.py", "Colors.py")
# Constant tables of skin keys, read through an index.
KEY_LISTS = ("QUANTIZATION_COLOR_MAP", "velocity_color_map")
# Strings assigned to the grid buffers and drawn later with set_light.
BUFFER_NAMES = ("_grid_back_buffer", "_cache")


def _string_args(node):
    for arg in node.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            yield arg.value


def _target_name(target):
    while isinstance(target, ast.Subscript):
        target = target.value
    return getattr(target, "attr", getattr(target, "id", None))


def requested_keys():
    """(file:line, key, single_arg_on_off) for each literal skin key the script draws."""
    found = []
    for path in sorted(glob.glob(os.path.join(REPO, "*.py"))):
        if os.path.basename(path) in SKIN_FILES:
            continue
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            where = f"{os.path.basename(path)}:{getattr(node, 'lineno', 0)}"
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in SKIN_KEY_CALLS:
                single = node.func.attr == "set_on_off_values" and len(node.args) == 1
                for key in _string_args(node):
                    if "." in key:
                        found.append((where, key, single))
            elif isinstance(node, ast.Assign):
                names = [_target_name(t) for t in node.targets]
                if any(name in KEY_LISTS for name in names):
                    for element in getattr(node.value, "elts", ()):
                        found.append((where, element.value, False))
                elif any(name in BUFFER_NAMES for name in names):
                    value = node.value
                    if isinstance(value, ast.Constant) and isinstance(value.value, str) and "." in value.value:
                        found.append((where, value.value, False))
    return found


def dynamic_keys():
    """Keys the script builds at run time."""
    keys = [f"StepSequencer.NoteEditor.Velocity{index}" for index in range(5)]
    # TrackControllerComponent: set_on_off_values("Mode." + skin_name).
    for name in ("Session", "StepSequencer", "StepSequencer2"):
        keys += [f"Mode.{name}.On", f"Mode.{name}.Off"]
    return keys


def _has_key(skin, key):
    from _Framework.Skin import SkinColorMissingError

    try:
        skin[key]
        return True
    except SkinColorMissingError:
        return False


def test_requested_keys_are_found():
    keys = [key for _, key, _ in requested_keys()]
    assert "DefaultButton.Disabled" in keys and len(keys) > 100


def test_every_requested_skin_key_exists(rig):
    skin = rig.surface._skin
    missing = []
    for where, key, single in requested_keys():
        wanted = [key + ".On", key + ".Off"] if single else [key]
        missing += [f"{where} {k}" for k in wanted if not _has_key(skin, k)]
    missing += [f"dynamic {k}" for k in dynamic_keys() if not _has_key(skin, k)]
    assert missing == []
