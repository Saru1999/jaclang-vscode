from __future__ import annotations
from typing import Any, List, Tuple, Union, Optional
import os
import pathlib
import sysconfig
import site
import sys

from lsprotocol.types import Position, Location, TextDocumentItem

from .symbols import Symbol

def as_list(content: Union[Any, List[Any], Tuple[Any]]) -> List[Any]:
    """Ensures we always get a list"""
    if isinstance(content, (list, tuple)):
        return list(content)
    return [content]


def _get_sys_config_paths() -> List[str]:
    """Returns paths from sysconfig.get_paths()."""
    return [
        path
        for group, path in sysconfig.get_paths().items()
        if group not in ["data", "platdata", "scripts"]
    ]


def _get_extensions_dir() -> List[str]:
    """This is the extensions folder under ~/.vscode or ~/.vscode-server.
    The path here is calculated relative to the tool
    this is because users can launch VS Code with custom
    extensions folder using the --extensions-dir argument"""

    path = pathlib.Path(__file__).parent.parent.parent.parent
    #                              ^     bundled  ^  extensions
    #                            tool        <extension>
    if path.name == "extensions":
        return [os.fspath(path)]
    return []


_stdlib_paths = set(
    str(pathlib.Path(p).resolve())
    for p in (
        as_list(site.getsitepackages())
        + as_list(site.getusersitepackages())
        + _get_sys_config_paths()
        + _get_extensions_dir()
    )
)


def is_same_path(file_path1: str, file_path2: str) -> bool:
    """Returns true if two paths are the same."""
    return pathlib.Path(file_path1) == pathlib.Path(file_path2)


def normalize_path(file_path: str) -> str:
    """Returns normalized path."""
    return str(pathlib.Path(file_path).resolve())


def is_current_interpreter(executable) -> bool:
    """Returns true if the executable path is same as the current interpreter."""
    return is_same_path(executable, sys.executable)


def is_stdlib_file(file_path: str) -> bool:
    """Return True if the file belongs to the standard library."""
    normalized_path = str(pathlib.Path(file_path).resolve())
    return any(normalized_path.startswith(path) for path in _stdlib_paths)


def update_sys_path(path_to_add: str, strategy: str) -> None:
    """
    Add a given path to `sys.path`.

    Args:
        path_to_add (str): The path to add to `sys.path`.
        strategy (str): The strategy to use when adding the path. If "useBundled", the path will be added to the beginning of `sys.path`. Otherwise, it will be added to the end.

    Returns:
        None
    """
    if path_to_add not in sys.path and os.path.isdir(path_to_add):
        if strategy == "useBundled":
            sys.path.insert(0, path_to_add)
        else:
            sys.path.append(path_to_add)


def is_contained(sym_location: Location, hover_position: Position) -> bool:
    """
    Returns True if the hover position is contained within the symbol location.

    :param sym_location: The location of the symbol being checked.
    :type sym_location: Location
    :param hover_position: The position of the hover being checked.
    :type hover_position: Position
    :return: True if the hover position is contained within the symbol location, False otherwise.
    :rtype: bool
    """
    return (
        sym_location.range.start.line <= hover_position.line
        and sym_location.range.end.line >= hover_position.line
        and sym_location.range.start.character <= hover_position.character
        and sym_location.range.end.character >= hover_position.character
    )


def get_symbol_at_pos(doc: TextDocumentItem, pos: Position) -> Optional[Symbol]:
    """
    Returns the symbol at the given position.

    :param doc: The document to check.
    :type doc: TextDocumentItem
    :param pos: The position to check.
    :type pos: Position
    :return: The symbol at the given position, or None if no symbol is found.
    :rtype: Optional[Symbol]
    """
    for sym in doc.symbols:
        if is_contained(sym.location, pos):
            return sym
    return None