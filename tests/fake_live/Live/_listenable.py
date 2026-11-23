"""Listenable properties, the way the Live API exposes them.

A class decorated with ``@listenable(name=default, ...)`` gets for each name:
a property (setting a different value fires the listeners), ``add_<name>_listener``,
``remove_<name>_listener`` and ``<name>_has_listener``. Like Live, adding a listener
twice or removing an unknown one raises RuntimeError.
"""


class ListenerSet:
    def __init__(self):
        self._by_name = {}

    def listeners(self, name):
        return self._by_name.setdefault(name, [])

    def fire(self, name):
        for listener in tuple(self.listeners(name)):
            listener()


def _listeners_of(obj):
    if "_listener_set" not in obj.__dict__:
        obj.__dict__["_listener_set"] = ListenerSet()
    return obj.__dict__["_listener_set"]


def notify(obj, name):
    """Fire the listeners of a property (for values that change in place, e.g. lists)."""
    _listeners_of(obj).fire(name)


def add_event(cls, name):
    """Add the add/remove/has listener methods for an event that has no stored value."""

    def add(self, listener):
        listeners = _listeners_of(self).listeners(name)
        if listener in listeners:
            raise RuntimeError(f"Listener already connected: {name}")
        listeners.append(listener)

    def remove(self, listener):
        listeners = _listeners_of(self).listeners(name)
        if listener not in listeners:
            raise RuntimeError(f"Listener not connected: {name}")
        listeners.remove(listener)

    def has(self, listener):
        return listener in _listeners_of(self).listeners(name)

    setattr(cls, f"add_{name}_listener", add)
    setattr(cls, f"remove_{name}_listener", remove)
    setattr(cls, f"{name}_has_listener", has)


def add_property(cls, name, default):
    attr = "_lv_" + name

    def getter(self):
        if attr not in self.__dict__:
            self.__dict__[attr] = default() if callable(default) else default
        return self.__dict__[attr]

    def setter(self, value):
        if getter(self) != value or type(getter(self)) is not type(value):
            self.__dict__[attr] = value
            notify(self, name)

    setattr(cls, name, property(getter, setter))
    add_event(cls, name)


def listenable(**properties):
    def decorate(cls):
        for name, default in properties.items():
            add_property(cls, name, default)
        return cls

    return decorate


def events(*names):
    def decorate(cls):
        for name in names:
            add_event(cls, name)
        return cls

    return decorate


def listener_count(obj, name):
    return len(_listeners_of(obj).listeners(name))
