import re
import inspect
import importlib
from typing import Optional

from pygls.server import LanguageServer
from lsprotocol.types import (
    CompletionParams,
    CompletionItem,
    CompletionItemKind,
    InsertTextFormat,
)

from .constants import JAC_KW, PY_LIBS, SNIPPETS, WALKER_SNIPPET
from .logging import log_to_output
from .symbols import get_symbol_by_name
from .utils import get_relative_path, get_all_symbols, get_scope_at_pos


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
    last_word = before_cursor.split()[-1] if len(before_cursor.split()) else ""

    scope = get_scope_at_pos(ls, doc, params.position, get_all_symbols(ls, doc, False, True))

    completion_items = []

    """
    eg- {node}. {walker}. {object}.
    """
    if before_cursor.endswith("."):
        last_symbol_name = re.match(r"(\w+).", last_word).group(1)
        last_symbol = get_symbol_by_name(last_symbol_name, get_all_symbols(ls, doc))
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
        if before_cursor == ":":
            completion_items += [
                CompletionItem(
                    label=f"{symbol.sym_name} ({symbol.sym_type})",
                    kind=_get_completion_kind(symbol.sym_type),
                    documentation=symbol.sym_doc,
                    insert_text=f"{symbol.sym_type}:{symbol.sym_name}",
                )
                for symbol in get_all_symbols(ls, doc)
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
        """
        eg- :walker:, :node:
        """
        match = re.match(r":(\w+):", before_cursor)
        if match:
            sym_type = match.group(1)
            completion_items += [
                CompletionItem(
                    label=f"{symbol.sym_name} ({symbol.sym_type})",
                    kind=_get_completion_kind(symbol.sym_type),
                    documentation=symbol.sym_doc,
                    insert_text=symbol.sym_name,
                )
                for symbol in get_all_symbols(ls, doc)
                if symbol.sym_type == sym_type and not symbol.is_use
            ]
        """
        eg- :walker:GuessGame:, :node:turn:
        """
        match = re.match(r":(\w+):(\w+):", before_cursor)
        if match:
            sym_type = match.group(1)
            sym_name = match.group(2)
            symbol = get_symbol_by_name(sym_name, get_all_symbols(ls, doc), sym_type)
            if symbol:
                completion_items += [
                    CompletionItem(
                        label=child.sym_name,
                        kind=_get_completion_kind(child.sym_type),
                        documentation=child.sym_doc,
                        insert_text=f"ability:{child.sym_name}",
                    )
                    for child in symbol.children
                    if child.sym_type == "ability" and not child.is_use
                ]
        """
        eg- :walker:GuessGame:ability:
        """
        match = re.match(r":(\w+):(\w+):ability:", before_cursor)
        if match:
            sym_type = match.group(1)
            sym_name = match.group(2)
            symbol = get_symbol_by_name(sym_name, get_all_symbols(ls, doc), sym_type)
            if symbol:
                completion_items += [
                    CompletionItem(
                        label=child.sym_name,
                        kind=_get_completion_kind(child.sym_type),
                        documentation=child.sym_doc,
                        insert_text=child.sym_name,
                    )
                    for child in symbol.children
                    if child.sym_type == "ability" and not child.is_use
                ]

    # Snippets at the start of the line
    if params.position.character == 0:
        completion_items += [
            CompletionItem(
                label=snippet["label"],
                kind=CompletionItemKind.Snippet,
                detail=snippet["detail"],
                documentation=snippet["documentation"],
                insert_text=snippet["insert_text"],
                insert_text_format=InsertTextFormat.Snippet,
            )
            for snippet in SNIPPETS
            if "at_start" in snippet["positions"]
        ]

    # Start of the line Keywords handling
    """
    'node', 'walker', ':node:', ':walker:', 'include:jac', 'import:py',
    'import:py from','object', 'enum', 'can', 'test', 'with entry',
    'global'
    """
    if params.position.character == 0:
        completion_items += [
            CompletionItem(
                label=kw,
                kind=CompletionItemKind.Keyword,
                insert_text=JAC_KW[kw]["insert_text"],
                documentation=JAC_KW[kw]["documentation"],
            )
            for kw in JAC_KW
            if "at_start" in JAC_KW[kw]["positions"]
        ]

    # Hnadling Imports
    """
    1. include:jac {jac_files_in_workspace}
    2. import:py {py_libs}
    3. import:py from {py_libs}, {classes_and_functions_in_py_lib}
    """
    if before_cursor in ["import:py from ", "import:py "]:
        completion_items += [
            CompletionItem(
                label=py_lib,
                kind=CompletionItemKind.Module,
                insert_text=py_lib,
                documentation="",
            )
            for py_lib in PY_LIBS
        ]
    py_import_match = re.match(r"import:py from (\w+),", before_cursor)
    if py_import_match:
        py_module = py_import_match.group(1)
        completion_items += [
            CompletionItem(
                label=name,
                kind=CompletionItemKind.Function
                if inspect.isfunction(obj)
                else CompletionItemKind.Class,
                documentation=obj.__doc__,
            )
            for name, obj in inspect.getmembers(importlib.import_module(py_module))
        ]
    if last_word == "include:jac":
        for mod, mod_info in ls.jlws.modules.items():
            rel_path = get_relative_path(doc.uri.replace("file://", ""), mod).replace(
                ".jac", ""
            )
            text = (
                rel_path.replace("/", "")
                if rel_path.startswith("..")
                else rel_path.replace("/", ".")
            )
            completion_items.append(
                CompletionItem(
                    label=text,
                    kind=CompletionItemKind.File,
                    insert_text=text,
                    documentation=mod_info.ir.doc.value if mod_info.ir.doc else "",
                )
            )

    # Snippets inside a node, walker, object
    # checks if the last word is just spaces/tabs
    if params.position.character > 0 and last_word == "":
        completion_items += [
            CompletionItem(
                label=snippet["label"],
                kind=CompletionItemKind.Snippet,
                detail=snippet["detail"],
                documentation=snippet["documentation"],
                insert_text=snippet["insert_text"],
                insert_text_format=InsertTextFormat.Snippet,
            )
            for snippet in SNIPPETS
            if "inside" in snippet["positions"]
        ]

    # inside a node, walker, object, enum
    """
    walker {walker_name} {
        has {var_name}: {var_type} ...;

        can {ability_name} {...}
        can {ability_name}( {var_name}: {var_type} );
        with entry {...}
        with exit {...}
    }

    node {node_name} {
        has {var_name}: {var_type} ...;

        can {ability_name} {...}
        can {ability_name}( {var_name}: {var_type} );
        can {ability_name} with {walker_name} entry;
    }

    object {Child}:{Super}: {
        <super>.<init>(...);
        has {var_name}: {var_type} ...;
        can <init>;
        can {ability_name} -> {return_type};
    }

    enum {enum_name} {
        {enum_key} = {enum_value},
    }
    """
    if scope.sym_type in ["node", "walker", "object", "enum"]:


    

    # inside a ability
    """
    can {ability_name} {
        {everything else}
        visit -->;
    }
    :(walker/node):{walker/node_name}:ability:{ability_name} {
        {everything else}
        visit -->;
    }
    """

    # inside a python block
    """
    {normal python stuff}
    """

    return completion_items
