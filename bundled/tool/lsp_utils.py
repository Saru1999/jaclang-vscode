# Copyright (c) Jaseci Labs. All rights reserved.
# Licensed under the MIT License.

import os
from typing import List, Optional
import lsprotocol.types as lsp
from common.utils import normalize_path


# **********************************************************
# Jaseci Validation
# **********************************************************

from common.validation import validate

# **********************************************************
# Jaseci Completion
# **********************************************************

import re
from lsprotocol.types import Position, Range

from pygls.server import LanguageServer
from lsprotocol.types import (
    CompletionParams,
    CompletionItem,
    CompletionItemKind,
    InsertTextFormat,
)
import pkgutil
import inspect
import importlib
import os

# Jaclang snippets #TODO: add more
snippets = [
    {
        "label": "loop",
        "detail": "for loop",
        "documentation": "for loop in jac",
        "insert_text": "for ${1:item} in ${2:iterable}:\n    ${3:# body of the loop}",
    },
]
# Jaclang keywords #TODO: Update with all the keywords related to jaclang
keywords = {
    "node": {"insert_text": "node", "documentation": "node"},
    "walker": {"insert_text": "walker", "documentation": "walker"},
    "edge": {"insert_text": "edge", "documentation": "edge"},
    "architype": {"insert_text": "architype", "documentation": "architype"},
    "from": {"insert_text": "from", "documentation": "from"},
    "with": {"insert_text": "with", "documentation": "with"},
    "in": {"insert_text": "in", "documentation": "in"},
    "graph": {"insert_text": "graph", "documentation": "graph"},
    "report": {"insert_text": "report", "documentation": "report"},
    "disengage": {"insert_text": "disengage", "documentation": "disengage"},
    "take": {"insert_text": "take", "documentation": "take"},
    "include:jac": {"insert_text": "include:jac", "documentation": "Importing in JAC"},
    "import:py": {
        "insert_text": "import:py",
        "documentation": "Import Python libraries",
    },
}
# python libraries available to import
py_libraries = [name for _, name, _ in pkgutil.iter_modules() if "_" not in name]


# default completion items
default_completion_items = [
    CompletionItem(label=keyword, kind=CompletionItemKind.Keyword, **info)
    for keyword, info in keywords.items()
] + [
    CompletionItem(
        label=snippet["label"],
        kind=CompletionItemKind.Snippet,
        detail=snippet["detail"],
        documentation=snippet["documentation"],
        insert_text=snippet["insert_text"],
        insert_text_format=InsertTextFormat.Snippet,
    )
    for snippet in snippets
]


def get_completion_items(
    server: LanguageServer, params: Optional[CompletionParams]
) -> list:
    """Returns completion items."""
    doc = server.workspace.get_document(params.text_document.uri)
    line = doc.source.splitlines()[params.position.line]
    before_cursor = line[: params.position.character]

    if not before_cursor:
        return default_completion_items

    last_word = before_cursor.split()[-1]

    # Import Completions
    # jac imports
    if last_word == "include:jac":
        # getting all the jac files in the workspace
        file_dir = os.path.dirname(params.text_document.uri.replace("file://", ""))
        jac_imports = [
            os.path.join(root.replace(file_dir, "."), file)
            .replace(".jac", "")
            .replace("/", ".")
            .replace("..", "")
            for root, _, files in os.walk(file_dir)
            for file in files
            if file.endswith(".jac")
        ]
        return [
            CompletionItem(label=jac_import, kind=CompletionItemKind.Module)
            for jac_import in jac_imports
        ]

    # python imports
    if before_cursor in ["import:py from ", "import:py "]:
        return [
            CompletionItem(label=py_lib, kind=CompletionItemKind.Module)
            for py_lib in py_libraries
        ]
    # functions and classes in the imported python library
    py_import_match = re.match(r"import:py from (\w+),", before_cursor)
    if py_import_match:
        py_module = py_import_match.group(1)
        return [
            CompletionItem(
                label=name,
                kind=CompletionItemKind.Function
                if inspect.isfunction(obj)
                else CompletionItemKind.Class,
                documentation=obj.__doc__,
            )
            for name, obj in inspect.getmembers(importlib.import_module(py_module))
        ]

    return default_completion_items


# **********************************************************
# Jaseci Symbols
# **********************************************************

import os

from pathlib import Path

from lsprotocol.types import TextDocumentItem, SymbolInformation, SymbolKind, Location

from jaclang.jac.passes import Pass
from jaclang.jac.passes.blue import (
    ImportPass,
    JacFormatPass,
    pass_schedule as blue_ps,
)
import jaclang.jac.absyntree as ast
from jaclang.jac.transpiler import jac_file_to_pass
from jaclang.jac.workspace import Workspace


def format_jac(doc_uri: str) -> str:
    format_pass_schedule = [JacFormatPass]
    doc_url = doc_uri.replace("file://", "")
    prse = jac_file_to_pass(
        doc_url, target=JacFormatPass, schedule=format_pass_schedule
    )
    return prse.ir.meta["jac_code"]


def fill_workspace(ls: LanguageServer):
    """
    Fill the workspace with all the JAC files
    """
    ls.jlws = Workspace(path=ls.workspace.root_path)
    for mod_path, mod_info in ls.jlws.modules.items():
        doc = TextDocumentItem(
            uri=f"file://{mod_path}",
            language_id="jac",
            version=0,
            text=mod_info.ir.source.code,
        )
        ls.workspace.put_document(doc)
        doc = ls.workspace.get_document(doc.uri)
        update_doc_tree(ls, doc.uri)
    for doc in ls.workspace.documents.values():
        update_doc_deps(ls, doc.uri)
    ls.workspace_filled = True


def update_doc_tree(ls: LanguageServer, doc_uri: str):
    """
    Update the tree of a document and its symbols
    """
    doc = ls.workspace.get_document(doc_uri)
    doc.symbols = [s for s in get_doc_symbols(ls, doc.uri) if s.location.uri == doc.uri]
    update_doc_deps(ls, doc.uri)


def update_doc_deps(ls: LanguageServer, doc_uri: str):
    """
    Update the dependencies of a document
    """
    doc = ls.workspace.get_document(doc_uri)
    doc_url = doc.uri.replace("file://", "")
    doc.dependencies = {}
    imports = _get_imports_from_jac_file(doc_url)
    try:
        jlws_imports = ls.jlws.get_dependencies(doc_url)
    except:
        jlws_imports = []

    ls.dep_table[doc_url] = [s for s in imports if s["is_jac_import"]]
    for dep in imports:
        if dep["is_jac_import"]:
            import_file_path = (
                f"{os.path.join(os.path.dirname(doc_url), dep['path'])}.jac"
            )
            architypes = _get_architypes_from_jac_file(import_file_path)
            new_symbols = get_doc_symbols(
                ls,
                f"file://{import_file_path}",
                architypes=architypes,
            )
            dependencies = {
                dep["path"]: {"architypes": architypes, "symbols": new_symbols}
            }
            doc.dependencies.update(dependencies)
        else:
            # TODO: Add support for python file imports
            pass


def _get_imports_from_jac_file(file_path: str) -> list:
    """
    Return a list of imports in the document
    """
    imports = []
    import_prse = jac_file_to_pass(
        file_path=file_path, target=ImportPass, schedule=blue_ps
    )
    if hasattr(import_prse.ir, "body"):
        for i in import_prse.ir.body:
            if isinstance(i, ast.Import):
                imports.append(
                    {
                        "path": i.path.path_str.replace(".", os.sep),
                        "is_jac_import": i.lang.tag.value == "jac",
                        "line": i.loc.first_line,
                        "uri": f"file://{Path(file_path).parent.joinpath(i.path.path_str.replace('.', os.sep))}.jac",
                    }
                )
    return imports


def get_symbol_data(ls: LanguageServer, uri: str, name: str, architype: str):
    """
    Return the data of a symbol
    """
    doc = ls.workspace.get_document(uri)
    if not hasattr(doc, "symbols"):
        doc.symbols = get_doc_symbols(ls, doc.uri)

    symbols_pool = doc.symbols
    # TODO: Extend the symbols pool to include symbols from dependencies

    for symbol in symbols_pool:
        if symbol.name == name and symbol.kind == _get_symbol_kind(architype):
            return symbol
    else:
        return None


def is_contained(sym_location: lsp.Location, hover_position: lsp.Position) -> bool:
    """
    Returns True if the hover position is contained within the symbol location.
    """
    return (
        sym_location.range.start.line <= hover_position.line
        and sym_location.range.end.line >= hover_position.line
        and sym_location.range.start.character <= hover_position.character
        and sym_location.range.end.character >= hover_position.character
    )


def get_doc_symbols(
    ls: LanguageServer,
    doc_uri: str,
    architypes: dict[str, list] = None,
    shift_lines: int = 0,
) -> List[SymbolInformation]:
    """
    Return a list of symbols in the document
    """
    if architypes is None:
        architypes = _get_architypes(ls, doc_uri)

    symbols: List[SymbolInformation] = []

    for architype in architypes.keys():
        for element in architypes[architype]:
            symbols.append(
                SymbolInformation(
                    name=element["name"],
                    kind=_get_symbol_kind(architype),
                    location=Location(
                        uri=doc_uri,
                        range=Range(
                            start=Position(
                                line=(element["line"] - 1) + shift_lines,
                                character=element["col_start"],
                            ),
                            end=Position(
                                line=(element["line"] - 1) + shift_lines,
                                character=element["col_end"],
                            ),
                        ),
                    ),
                )
            )
            for var in element["vars"]:
                symbols.append(
                    SymbolInformation(
                        name=var["name"],
                        kind=_get_symbol_kind(var["type"]),
                        location=Location(
                            uri=doc_uri,
                            range=Range(
                                start=Position(
                                    line=var["line"] - 1 + shift_lines,
                                    character=var["col_start"],
                                ),
                                end=Position(
                                    line=var["line"] + shift_lines,
                                    character=var["col_end"],
                                ),
                            ),
                        ),
                        container_name=element["name"],
                    )
                )
    return symbols


def _get_architypes(ls: LanguageServer, doc_uri: str) -> dict[str, list]:
    """
    Return a dictionary of architypes in the document including their elements
    """
    doc = ls.workspace.get_document(doc_uri)
    architype_prse = jac_file_to_pass(
        file_path=doc.path, target=ArchitypePass, schedule=[ArchitypePass]
    )
    doc.architypes = architype_prse.output
    return doc.architypes if doc.architypes else {}


def _get_architypes_from_jac_file(file_path: str) -> dict[str, list]:
    """
    Return a dictionary of architypes in the document including their elements
    """
    architype_prse = jac_file_to_pass(
        file_path=file_path,
        target=ArchitypePass,
        schedule=[ArchitypePass],
    )
    return architype_prse.output


def get_symbol_at_position(doc, position: Position):
    """
    Return the symbol at a position
    """
    symbols = doc.symbols
    for symbol in symbols:
        if (
            symbol.location.range.start.line <= position.line
            and symbol.location.range.end.line >= position.line
        ):
            return symbol
    return None


def _get_symbol_kind(architype: str) -> SymbolKind:
    """
    Return the symbol kind of an architype
    """
    if architype == "walker":
        return SymbolKind.Class
    elif architype == "node":
        return SymbolKind.Class
    elif architype == "edge":
        return SymbolKind.Interface
    elif architype == "graph":
        return SymbolKind.Namespace
    elif architype == "ability":
        return SymbolKind.Method
    elif architype == "object":
        return SymbolKind.Object
    else:
        return SymbolKind.Variable


class ArchitypePass(Pass):
    """
    A pass that extracts architypes from a JAC file
    """

    output = {"walker": [], "node": [], "edge": [], "graph": [], "object": []}
    output_key_map = {
        "KW_NODE": "node",
        "KW_WALKER": "walker",
        "KW_EDGE": "edge",
        "KW_GRAPH": "graph",
        "KW_OBJECT": "object",
    }

    def extract_vars(self, nodes: List[ast.AstNode]):
        vars = []
        for node in nodes:
            if isinstance(node, ast.Ability):
                try:
                    vars.append(
                        {
                            "type": "ability",
                            "name": node.name_ref.value,
                            "line": node.loc.first_line,
                            "col_start": node.name_ref.loc.col_start,
                            "col_end": node.name_ref.loc.col_end,
                        }
                    )
                except Exception as e:
                    print(node.to_dict(), e)
            elif isinstance(node, ast.ArchHas):
                for var in node.vars.items:
                    vars.append(
                        {
                            "type": "has_var",
                            "name": var.name.value,
                            "line": var.loc.first_line,
                            "col_start": var.loc.col_start,
                            "col_end": var.loc.col_end,
                        }
                    )
        return vars

    def enter_architype(self, node: ast.Architype):
        architype = {}
        architype["name"] = node.name.value
        architype["line"] = node.name.loc.first_line
        architype["col_start"] = node.name.loc.col_start
        architype["col_end"] = node.name.loc.col_end

        architype["vars"] = self.extract_vars(node.body.kid)

        self.output[self.output_key_map[node.arch_type.name]].append(architype)
