import re
import inspect
import importlib
import os
from typing import Optional

from pygls.server import LanguageServer
from lsprotocol.types import (
    CompletionParams,
    CompletionItem,
    CompletionItemKind,
    InsertTextFormat,
    Position,
)

from .constants import JAC_KW, PY_LIBS, SNIPPETS
from .logging import log_to_output
from .symbols import get_symbol_by_name

DEFAULT_COMPLETION_ITEMS = [
    CompletionItem(label=keyword, kind=CompletionItemKind.Keyword, **info)
    for keyword, info in JAC_KW.items()
] + [
    CompletionItem(
        label=snippet["label"],
        kind=CompletionItemKind.Snippet,
        detail=snippet["detail"],
        documentation=snippet["documentation"],
        insert_text=snippet["insert_text"],
        insert_text_format=InsertTextFormat.Snippet,
    )
    for snippet in SNIPPETS
]


def _get_completion_kind(sym_type: str) -> CompletionItemKind:
    """
    Returns the completion kind based on the symbol type.

    Args:
        sym_type (str): The symbol type.

    Returns:
        CompletionItemKind: The completion kind.
    """
    architype_map = {
        "node": CompletionItemKind.Class,
        "walker": CompletionItemKind.Class,
        "edge": CompletionItemKind.Class,
        "enum_member": CompletionItemKind.EnumMember,
        "module": CompletionItemKind.Module,
        "mod_var": CompletionItemKind.Variable,
        "var": CompletionItemKind.Variable,
        "ability": CompletionItemKind.Function,
        "object": CompletionItemKind.Class,
        "enum": CompletionItemKind.Enum,
        "test": CompletionItemKind.Function,
        "type": CompletionItemKind.TypeParameter,
        "impl": CompletionItemKind.Method,
        "field": CompletionItemKind.Field,
        "method": CompletionItemKind.Method,
        "constructor": CompletionItemKind.Constructor,
    }
    return architype_map.get(sym_type, CompletionItemKind.Variable)


def get_completion_items(
    ls: LanguageServer, params: Optional[CompletionParams]
) -> list[CompletionItem]:
    """
    Returns a list of completion items based on the text document and cursor position.

    Args:
        ls (LanguageServer): The language server instance.
        params (Optional[CompletionParams]): The completion parameters.

    Returns:
        list: A list of completion items.
    """
    doc = ls.workspace.get_document(params.text_document.uri)
    line = doc.source.splitlines()[params.position.line]
    before_cursor = line[: params.position.character]

    completion_items = []

    symbols = doc.symbols
    dep_symbols = (
        [
            symbol
            for dep in doc.dependencies
            for symbol in doc.dependencies[dep]["symbols"]
        ]
        if hasattr(doc, "dependencies")
        else []
    )

    if before_cursor.endswith("."):
        last_symbol_name = before_cursor.split()[-1].split(".")[-1]
        last_symbol = get_symbol_by_name(last_symbol_name, symbols + dep_symbols)
        if last_symbol:
            for child in last_symbol.children:
                completion_items.append(
                    CompletionItem(
                        label=child.sym_name,
                        kind=_get_completion_kind(child.sym_type),
                        documentation=child.sym_doc,
                        insert_text=child.sym_name,
                    )
                )

    if before_cursor.endswith(":"):
        log_to_output(ls, "ENDS WITH COLON")
        if before_cursor.count(":") == 1:
            log_to_output(ls, "ONE COLON")
            completion_items += [
                CompletionItem(
                    label=f"{symbol.sym_name} ({symbol.sym_type})",
                    kind=_get_completion_kind(symbol.sym_type),
                    documentation=symbol.sym_doc,
                    insert_text=f"{symbol.sym_type}:{symbol.sym_name}",
                )
                for symbol in symbols + dep_symbols
                if symbol.sym_type == "walker" or symbol.sym_type == "node"
                if not symbol.is_use
            ]
            completion_items += [
                CompletionItem(
                    label="walker",
                    kind=CompletionItemKind.Keyword,
                    insert_text="walker:",
                ),
                CompletionItem(
                    label="node",
                    kind=CompletionItemKind.Keyword,
                    insert_text="node:",
                ),
            ]
        if before_cursor.count(":") == 2:
            """
            eg- :walker:, :node:
            """
            sym_type = before_cursor.replace(":", "").split()[-1]
            completion_items += [
                CompletionItem(
                    label=f"{symbol.sym_name} ({symbol.sym_type})",
                    kind=_get_completion_kind(symbol.sym_type),
                    documentation=symbol.sym_doc,
                    insert_text=symbol.sym_name,
                )
                for symbol in symbols + dep_symbols
                if symbol.sym_type == sym_type
                if not symbol.is_use
            ]
        if before_cursor.count(":") == 3:
            """
            eg- :walker:GuessGame:, :node:turn:"""
            log_to_output(ls, "THREE COLONS")
            sym_type = before_cursor.replace(":", " ").split()[-2]
            sym_name = before_cursor.replace(":", " ").split()[-1]
            symbol = get_symbol_by_name(sym_name, symbols + dep_symbols, sym_type)
            if symbol:
                completion_items += [
                    CompletionItem(
                        label=child.sym_name,
                        kind=_get_completion_kind(child.sym_type),
                        documentation=child.sym_doc,
                        insert_text=f"ability:{child.sym_name}",
                    )
                    for child in symbol.children
                    if child.sym_type == "ability"
                ]
        if before_cursor.count(":") == 4:
            """
            eg- :walker:GuessGame:ability:"""
            log_to_output(ls, "FOUR COLONS")
            sym_type = before_cursor.split()[-1].split(":")[-3]
            sym_name = before_cursor.split()[-1].split(":")[-2]
            symbol = get_symbol_by_name(sym_name, symbols + dep_symbols, sym_type)
            if symbol:
                completion_items += [
                    CompletionItem(
                        label=child.sym_name,
                        kind=_get_completion_kind(child.sym_type),
                        documentation=child.sym_doc,
                        insert_text=child.sym_name,
                    )
                    for child in symbol.children
                    if child.sym_type == "ability"
                ]

    return completion_items

    # last_word = before_cursor.split()[-1]

    # # Import Completions
    # # jac imports
    # if last_word == "include:jac":
    #     # getting all the jac files in the workspace
    #     file_dir = os.path.dirname(params.text_document.uri.replace("file://", ""))
    #     jac_imports = [
    #         os.path.join(root.replace(file_dir, "."), file)
    #         .replace(".jac", "")
    #         .replace("/", ".")
    #         .replace("..", "")
    #         for root, _, files in os.walk(file_dir)
    #         for file in files
    #         if file.endswith(".jac")
    #     ]
    #     return [
    #         CompletionItem(label=jac_import, kind=CompletionItemKind.Module)
    #         for jac_import in jac_imports
    #     ]

    # # python imports
    # if before_cursor in ["import:py from ", "import:py "]:
    #     return [
    #         CompletionItem(label=py_lib, kind=CompletionItemKind.Module)
    #         for py_lib in PY_LIBS
    #     ]
    # # functions and classes in the imported python library
    # py_import_match = re.match(r"import:py from (\w+),", before_cursor)
    # if py_import_match:
    #     py_module = py_import_match.group(1)
    #     return [
    #         CompletionItem(
    #             label=name,
    #             kind=CompletionItemKind.Function
    #             if inspect.isfunction(obj)
    #             else CompletionItemKind.Class,
    #             documentation=obj.__doc__,
    #         )
    #         for name, obj in inspect.getmembers(importlib.import_module(py_module))
    #     ]

    # return DEFAULT_COMPLETION_ITEMS
