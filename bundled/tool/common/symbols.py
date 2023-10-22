import os
from pathlib import Path
from typing import List

from lsprotocol.types import Position, Range
from pygls.server import LanguageServer
from lsprotocol.types import TextDocumentItem, SymbolInformation, SymbolKind, Location

from jaclang.jac.passes import Pass
from jaclang.jac.passes.blue import (
    ImportPass,
    pass_schedule as blue_ps,
)
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
        doc = ls.workspace.get_document(doc.uri)
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
    Given a file path to a Jaseci Abstract Code (JAC) file, returns a list of
    dictionaries representing the imports in the file. Each dictionary contains
    the path to the imported module, a boolean indicating whether the import is a
    JAC import, the line number of the import statement, and the URI of the imported
    module.

    Args:
        file_path (str): The path to the JAC file.

    Returns:
        list: A list of dictionaries representing the imports in the file.
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


def get_doc_symbols(
    ls: LanguageServer,
    doc_uri: str,
    architypes: dict[str, list] = None,
    shift_lines: int = 0,
) -> List[SymbolInformation]:
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


def get_doc_symbols(
    ls: LanguageServer,
    doc_uri: str,
    architypes: dict[str, list] = None,
    shift_lines: int = 0,
) -> List[SymbolInformation]:
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
    Retrieves the architypes for a given document URI.

    Args:
        ls (LanguageServer): The LanguageServer instance.
        doc_uri (str): The URI of the document.

    Returns:
        dict[str, list]: A dictionary containing the architypes for the document.
    """
    doc = ls.workspace.get_document(doc_uri)
    architype_prse = jac_file_to_pass(
        file_path=doc.path, target=ArchitypePass, schedule=[ArchitypePass]
    )
    doc.architypes = architype_prse.output
    return doc.architypes if doc.architypes else {}


def _get_architypes_from_jac_file(file_path: str) -> dict[str, list]:
    """
    Return a dictionary of archetypes in the document including their elements

    :param file_path: The path to the JAC file to parse
    :type file_path: str
    :return: A dictionary of archetypes in the document including their elements
    :rtype: dict[str, list]
    """
    architype_prse = jac_file_to_pass(
        file_path=file_path,
        target=ArchitypePass,
        schedule=[ArchitypePass],
    )
    return architype_prse.output


def _get_symbol_kind(architype: str) -> SymbolKind:
    """
    Return the symbol kind of an architype

    Parameters:
    architype (str): The archetype of the symbol

    Returns:
    SymbolKind: The kind of symbol that corresponds to the archetype
    """
    architype_map = {
        "walker": SymbolKind.Class,
        "node": SymbolKind.Class,
        "edge": SymbolKind.Interface,
        "graph": SymbolKind.Namespace,
        "ability": SymbolKind.Method,
        "object": SymbolKind.Object,
    }
    return architype_map.get(architype, SymbolKind.Variable)


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
        """
        Extracts variables from a list of AST nodes.

        Args:
            nodes (List[ast.AstNode]): A list of AST nodes.

        Returns:
            List[Dict[str, Union[str, int]]]: A list of dictionaries containing information about each variable.
        """
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


def get_symbol_at_position(doc, position: Position):
    """
    Return the symbol at a given position in the document.

    Args:
        doc (Document): The document to search for symbols.
        position (Position): The position to search for a symbol.

    Returns:
        Symbol: The symbol at the given position, or None if no symbol is found.
    """
    symbols = doc.symbols
    for symbol in symbols:
        if (
            symbol.location.range.start.line <= position.line
            and symbol.location.range.end.line >= position.line
        ):
            return symbol
    return None
