from __future__ import annotations
from typing import Any, List, Tuple, Union, Optional
import os
import pathlib
import sysconfig
import site
import sys

from lsprotocol.types import Position, Range, TextDocumentItem
from pygls.server import LanguageServer

from .symbols import Symbol, update_doc_deps
from .logging import log_to_output


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


def is_contained(sym_range: Range, hover_position: Position) -> bool:
    return (
        sym_range.start.line <= hover_position.line
        and sym_range.end.line >= hover_position.line
        and sym_range.start.character <= hover_position.character
        and sym_range.end.character >= hover_position.character
    )


def get_symbol_at_pos(
    ls: LanguageServer, doc: TextDocumentItem, pos: Position
) -> Optional[Symbol]:
    for sym in get_all_symbols(ls, doc):
        if sym.doc_uri != doc.uri:
            continue
        if is_contained(sym.location.range, pos):
            return sym
    return None


def get_relative_path(file_path, target_path):
    file_path = pathlib.Path(file_path)
    target_path = pathlib.Path(target_path)
    return os.path.relpath(target_path, start=file_path.parent)


def show_doc_info(ls, uri):
    doc = ls.workspace.get_document(uri)
    log_to_output(
        ls,
        f"""{'Symbols Attribute not found' if not hasattr(doc, 'symbols') else f'Symbols found: {len(doc.symbols)}'}
        {'Dependancies Attribute not found' if not hasattr(doc, 'dependencies') else f'Dependancies found: {len(doc.dependencies)}'}""",
    )


def get_all_children(
    ls: LanguageServer, sym: Symbol, return_uses: bool = False
) -> list[Symbol]:
    for child in sym.children:
        yield child
        if return_uses:
            yield from child.uses(ls)
        yield from get_all_children(ls, child)


def get_all_symbols(
    ls: LanguageServer,
    doc: TextDocumentItem,
    include_dep: bool = True,
    include_impl: bool = False,
) -> list[Symbol]:
    for sym in doc.symbols:
        if not include_impl and sym.sym_type == "impl":
            continue
        yield sym
        yield from sym.uses(ls)
        yield from get_all_children(ls, sym, True)
    if include_dep:
        if not hasattr(doc, "dependencies"):
            update_doc_deps(ls, doc.uri)
        for dep in doc.dependencies.values():
            for sym in dep["symbols"]:
                yield sym
                yield from sym.uses(ls)


def get_scope_at_pos(
    ls: LanguageServer, doc: TextDocumentItem, pos: Position, symbols: list[Symbol]
) -> Optional[Symbol]:
    for sym in symbols:
        if sym.doc_uri != doc.uri or sym.ws_symbol is None:
            continue
        if (
            sym.doc_sym.range.start.line <= pos.line
            and sym.doc_sym.range.end.line >= pos.line
        ):
            kid = get_scope_at_pos(ls, doc, pos, sym.children)
            if kid:
                return kid
            return sym
    return None
