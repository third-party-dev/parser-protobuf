from __future__ import annotations

import logging
log = logging.getLogger(__name__)

from importlib.metadata import entry_points
from typing import Any, Callable

CommandRegistrar = Callable[[Any], None]

_COMMANDS: dict[str, CommandRegistrar] = {}

def register_command(name: str, registrar: CommandRegistrar) -> None:
    if name in _COMMANDS and _COMMANDS[name] != registrar:
        raise ValueError(f"Command '{name}' already registered")
    _COMMANDS[name] = registrar

def get_commands() -> Any:
    return _COMMANDS.values()

def load_entrypoint_plugins(entrypoint_group: str) -> None:

    if isinstance(entry_points(), dict):
        # Python 3.9
        eps = []
        for ep in entry_points()['pparse_command']:
            if not ep in eps:
                eps.append(ep)
    else:
        # Python 3.10+
        eps = entry_points(group=entrypoint_group)

    for ep in eps:
        register_command(ep.name, ep.load())
