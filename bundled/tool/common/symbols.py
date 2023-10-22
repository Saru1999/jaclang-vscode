import os
from pathlib import Path
from typing import List

from lsprotocol.types import Position, Range
from pygls.server import LanguageServer
from lsprotocol.types import TextDocumentItem, SymbolInformation, SymbolKind, Location

from jaclang.jac.passes import Pass
import jaclang.jac.absyntree as ast
from jaclang.jac.transpiler import jac_file_to_pass
from jaclang.jac.workspace import Workspace


def fill_workspace(ls: LanguageServer) -> None:
    """
    Fills the workspace with the modules and their dependencies.

    Args:
        ls (LanguageServer): The LanguageServer instance.

    Returns:
        None
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
        update_doc_tree(ls, doc.uri)
    for doc in ls.workspace.documents.values():
        update_doc_deps(ls, doc.uri)
    ls.workspace_filled = True


def update_doc_tree(ls: LanguageServer, doc_uri: str) -> None:
    """
    Updates the document tree with the symbols in the given document URI.

    Args:
        ls (LanguageServer): The language server instance.
        doc_uri (str): The URI of the document to update.

    Returns:
        None
    """
    doc = ls.workspace.get_document(doc_uri)
    doc.symbols = [s for s in get_doc_symbols(ls, doc.uri) if s.location.uri == doc.uri]
    update_doc_deps(ls, doc.uri)


def update_doc_deps(ls: LanguageServer, doc_uri: str) -> None:
    """
    Update the dependencies of a document in the given LanguageServer instance.

    Args:
        ls (LanguageServer): The LanguageServer instance to use.
        doc_uri (str): The URI of the document to update.

    Returns:
        None
    """
    doc = ls.workspace.get_document(doc_uri)
    doc_url = doc.uri.replace("file://", "")
    doc.dependencies = {}

    jlws_imports = ls.jlws.get_dependencies(doc_url)
    imports = [
        {
            "path": i.path.path_str.replace(".", os.sep),
            "is_jac_import": i.lang.tag.value == "jac",
            "line": i.loc.first_line,
            "uri": f"file://{Path(doc_url).parent.joinpath(i.path.path_str.replace('.', os.sep))}.jac",
        }
        for i in jlws_imports
    ]

    ls.dep_table[doc_url] = [s for s in imports if s["is_jac_import"]]
    for dep in imports:
        if dep["is_jac_import"]:
            import_file_path = (
                f"{os.path.join(os.path.dirname(doc_url), dep['path'])}.jac"
            )
            dep_symbols = get_doc_symbols(
                ls,
                f"file://{import_file_path}",
            )
            dependencies = {dep["path"]: {"symbols": dep_symbols}}
            doc.dependencies.update(dependencies)
        else:
            # TODO: Add support for python file imports
            pass


def get_symbol_data(
    ls: LanguageServer, uri: str, name: str, architype: str
) -> SymbolInformation | None:
    """
    Retrieves symbol information for a given symbol name and archetype from a document.

    Args:
        ls (LanguageServer): The language server instance.
        uri (str): The URI of the document to retrieve symbol information from.
        name (str): The name of the symbol to retrieve information for.
        architype (str): The archetype of the symbol to retrieve information for.

    Returns:
        SymbolInformation | None: The symbol information if found, else None.
    """
    doc = ls.workspace.get_document(uri)
    if not hasattr(doc, "symbols"):
        doc.symbols = get_doc_symbols(ls, doc.uri)

    symbols_pool = doc.symbols

    for symbol in symbols_pool:
        if symbol.name == name and symbol.kind == _get_symbol_kind(architype):
            return symbol
    else:
        return None


def get_doc_symbols(ls: LanguageServer, doc_uri: str) -> List[SymbolInformation]:
    """
    Returns a list of SymbolInformation objects representing the symbols defined in the given document.

    Parameters:
    ls (LanguageServer): The LanguageServer instance to use.
    doc_uri (str): The URI of the document to analyze.
    architypes (dict[str, list], optional): A dictionary mapping archetype names to lists of elements of that archetype. If not provided, it will be computed automatically. Defaults to None.
    shift_lines (int, optional): The number of lines to shift the symbol positions by. Defaults to 0.

    Returns:
    List[SymbolInformation]: A list of SymbolInformation objects representing the symbols defined in the document.
    """
    symbols: List[SymbolInformation] = []

    doc_url = doc_uri.replace("file://", "")
    jl_symbols = ls.jlws.get_symbols(doc_url)

    for symbol in jl_symbols:
        try:
            symbols.append(
                SymbolInformation(
                    name=symbol.name,
                    kind=_get_symbol_kind(symbol.sym_type.value),
                    location=Location(
                        uri=doc_uri,
                        range=Range(
                            start=Position(
                                line=symbol.decl.loc.first_line - 1,
                                character=symbol.decl.loc.col_start,
                            ),
                            end=Position(
                                line=symbol.decl.loc.last_line - 1,
                                character=symbol.decl.loc.col_end,
                            ),
                        ),
                    ),
                )
            )
            if hasattr(symbol.decl, "body"):
                for var in symbol.decl.body.kid:
                    if not isinstance(var, (ast.Ability, ast.ArchHas)):
                        continue
                    try:
                        symbols.append(
                            SymbolInformation(
                                name=var.py_resolve_name(),
                                kind=_get_symbol_kind(str(type(var))),
                                location=Location(
                                    uri=doc_uri,
                                    range=Range(
                                        start=Position(
                                            line=var.loc.first_line - 1,
                                            character=var.loc.col_start,
                                        ),
                                        end=Position(
                                            line=var.loc.last_line - 1,
                                            character=var.loc.col_end,
                                        ),
                                    ),
                                ),
                                container_name=symbol.name,
                            )
                        )
                    except Exception as e:
                        print(e)
        except Exception as e:
            print(e)
    return symbols


def _get_symbol_kind(architype: str) -> SymbolKind:
    """
    Return the symbol kind of an architype

    Parameters:
    architype (str): The archetype of the symbol

    Returns:
    SymbolKind: The kind of symbol that corresponds to the archetype
    """
    architype_map = {
        "mod": SymbolKind.Module,
        "ability": SymbolKind.Method,
        "var": SymbolKind.Variable,
        "object": SymbolKind.Object,
        "node": SymbolKind.Class,
        "edge": SymbolKind.Interface,
        "walker": SymbolKind.Class,
        "enum": SymbolKind.Enum,
        "impl": SymbolKind.Method,
        "field": SymbolKind.Field,
    }
    return architype_map.get(architype, SymbolKind.Variable)
