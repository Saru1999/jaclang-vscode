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

from common.completion import get_completion_items


# **********************************************************
# Jaseci Symbols
# **********************************************************

import os

from lsprotocol.types import Position, Range

from pygls.server import LanguageServer

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
