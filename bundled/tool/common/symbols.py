import os
from pathlib import Path
from typing import List

from lsprotocol.types import Position, Range
from pygls.server import LanguageServer
from lsprotocol.types import (
    TextDocumentItem,
    SymbolInformation,
    SymbolKind,
    Location,
    DocumentSymbol,
)

from jaclang.jac.workspace import Workspace
from jaclang.jac.absyntree import AstNode, AbilityDef


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


class Symbol:
    def __init__(self, doc_uri: str, node: AstNode) -> None:
        self.node = node
        self.ws_symbol = self.node.sym_link
        self.sym_info = SymbolInformation(
            name=self.ws_symbol.sym_name,
            kind=_get_symbol_kind(str(self.ws_symbol.sym_type)),
            location=Location(
                uri=doc_uri,
                range=Range(
                    start=Position(
                        line=self.node.sym_name_node.loc.first_line - 1,
                        character=self.node.sym_name_node.loc.col_start,
                    ),
                    end=Position(
                        line=self.node.sym_name_node.loc.last_line - 1,
                        character=self.node.sym_name_node.loc.col_end,
                    ),
                ),
            ),
        )
        self.doc_sym = DocumentSymbol(
            name=self.sym_info.name,
            kind=self.sym_info.kind,
            range=self.sym_info.location.range,
            selection_range=self.sym_info.location.range,
            detail="",
            children=[],
        )
        self.sym_doc = "Need to replace with self.ws_symbol.docstring"
        self.sym_type = str(self.ws_symbol.sym_type)
        self.sym_name = self.ws_symbol.sym_name
        self.location = self.sym_info.location
        self.defn_loc = Location(
            uri=doc_uri,
            range=Range(
                start=Position(
                    line=self.ws_symbol.decl.sym_name_node.loc.first_line - 1,
                    character=self.ws_symbol.decl.sym_name_node.loc.col_start,
                ),
                end=Position(
                    line=self.ws_symbol.decl.sym_name_node.loc.last_line - 1,
                    character=self.ws_symbol.decl.sym_name_node.loc.col_end,
                ),
            ),
        )


def get_doc_symbols(ls: LanguageServer, doc_uri: str) -> List[Symbol]:
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
    symbols: List[Symbol] = []
    doc_url = doc_uri.replace("file://", "")
    # Symbol Definitions
    defn_nodes = ls.jlws.get_definitions(doc_url)
    uses_nodes = ls.jlws.get_uses(doc_url)
    for node in defn_nodes + uses_nodes:
        if isinstance(node, AbilityDef):
            continue
        symbol = Symbol(doc_uri, node)
        symbols.append(symbol)
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
        "mod_var": SymbolKind.Variable,
        "var": SymbolKind.Variable,
        "immutable": SymbolKind.Variable,
        "ability": SymbolKind.Function,
        "object": SymbolKind.Class,
        "node": SymbolKind.Class,
        "edge": SymbolKind.Class,
        "walker": SymbolKind.Class,
        "enum": SymbolKind.Enum,
        "test": SymbolKind.Function,
        "type": SymbolKind.TypeParameter,
        "impl": SymbolKind.Method,
        "field": SymbolKind.Field,
        "method": SymbolKind.Method,
        "constructor": SymbolKind.Constructor,
        "enum_member": SymbolKind.EnumMember,
    }
    return architype_map.get(architype, SymbolKind.Variable)
