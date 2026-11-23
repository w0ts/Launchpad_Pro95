"""Helpers for the components that wire their own buttons (the step sequencers and their parts)."""

from _Framework.ButtonElement import ButtonElement


def rebind_button(old, new, listener, identify_sender=False):
    """Move a value listener from the old button to the new one (either may be None) and return
    the new button."""
    assert isinstance(new, (ButtonElement, type(None)))
    if old != None:
        old.remove_value_listener(listener)
    if new != None:
        new.add_value_listener(listener, identify_sender=identify_sender)
    return new


def is_press(value, sender):
    """True for a press, and for any value of a toggle (not momentary) button."""
    return value != 0 or not sender.is_momentary()


def show_disabled(button):
    button.set_on_off_values("DefaultButton.Disabled", "DefaultButton.Disabled")
    button.turn_off()


def show_on_off(button, on_value, off_value, is_on):
    button.set_on_off_values(on_value, off_value)
    if is_on:
        button.turn_on()
    else:
        button.turn_off()
