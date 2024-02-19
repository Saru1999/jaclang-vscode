import os
from pathlib import Path
from typing import List

from pygls.server import LanguageServer
from lsprotocol.types import (
    TextDocumentItem,
    SymbolInformation,
    SymbolKind,
    Range,
    Position,
    Location,
    DocumentSymbol,
)

from jaclang.compiler.workspace import Workspace
from jaclang.compiler.absyntree import (
    AstNode,
    Ability,
    Architype,
    HasVar,
    ParamVar,
    IfStmt,
    WhileStmt,
    WithStmt,
    IterForStmt,
    ModuleCode,
    AstImplOnlyNode,
)
from jaclang.compiler.symtable import SymbolTable, Symbol as JSymbol

OFFSET = 1


def fill_workspace(ls: LanguageServer) -> None:
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
    doc = ls.workspace.get_text_document(doc_uri)
    try:
        doc.symbols = get_doc_symbols(ls, doc.uri)
        doc.use_symbols = get_use_symbols(ls, doc.uri)
    except Exception:
        doc.symbols = []
        doc.use_symbols = []


def update_doc_deps(ls: LanguageServer, doc_uri: str) -> None:
    doc = ls.workspace.get_text_document(doc_uri)
    doc_url = doc.uri.replace("file://", "")
    doc.dependencies = {}

    jlws_imports = ls.jlws.get_dependencies(doc_url)
    imports = [
        {
            "path": f"{Path(doc_url).parent.joinpath(i.path_str.replace('.', os.sep))}.jac",
            "is_jac_import": i.parent.lang.tag.value == "jac",
            "line": i.loc.first_line,
            "uri": f"file://{Path(doc_url).parent.joinpath(i.path_str.replace('.', os.sep))}.jac",
        }
        for i in jlws_imports
    ]

    ls.dep_table[doc_url] = [s for s in imports if s["is_jac_import"]]
    for dep in imports:
        if dep["is_jac_import"]:
            dep_doc = ls.workspace.get_text_document(dep["uri"])
            if not hasattr(dep_doc, "symbols"):
                update_doc_tree(ls, dep_doc.uri)
            doc.dependencies[dep["path"]] = {"symbols": dep_doc.symbols}
        else:
            # TODO: Add support for python file imports
            pass


class Symbol:
    def __init__(
        self,
        node: SymbolTable | AstNode | JSymbol,
        doc_uri: str,
        is_use: "Symbol" = None,
    ):
        if isinstance(node, SymbolTable):
            self.sym_tab = node
        self.is_use = is_use
        self.node = (
            node.owner
            if isinstance(node, SymbolTable)
            else node.decl if isinstance(node, JSymbol) else node
        )
        self.doc_uri = doc_uri

    @property
    def sym_name(self):
        return self.node.sym_name

    @property
    def ws_symbol(self):
        return self.node.sym_link

    @property
    def sym_type(self):
        if self.is_use:
            return self.is_use.sym_type
        return str(self.node.sym_type)

    @property
    def sym_doc(self):
        try:
            return self.ws_symbol.decl.doc.value[3:-3]
        except Exception:
            return ""

    @property
    def defn_loc(self):
        if self.is_use is None and self.sym_type != "impl":
            return None
        defn_node = (
            self.ws_symbol.decl.decl_link
            if self.sym_type == "impl"
            else self.ws_symbol.decl
        )
        return Location(
            uri=f"file://{os.path.join(os.getcwd(), defn_node.loc.mod_path)}",
            range=Range(
                start=Position(
                    line=defn_node.sym_name_node.loc.first_line - OFFSET,
                    character=defn_node.sym_name_node.loc.col_start - OFFSET,
                ),
                end=Position(
                    line=defn_node.sym_name_node.loc.last_line - OFFSET,
                    character=defn_node.sym_name_node.loc.col_end - OFFSET,
                ),
            ),
        )

    @property
    def sym_info(self):
        return SymbolInformation(
            name=self.sym_name,
            kind=self._get_symbol_kind(self.sym_type),
            location=Location(
                uri=self.doc_uri,
                range=Range(
                    start=Position(
                        line=self.node.sym_name_node.loc.first_line - OFFSET,
                        character=self.node.sym_name_node.loc.col_start - OFFSET,
                    ),
                    end=Position(
                        line=self.node.sym_name_node.loc.last_line - OFFSET,
                        character=self.node.sym_name_node.loc.col_end - OFFSET,
                    ),
                ),
            ),
        )

    @property
    def doc_sym(self):
        return DocumentSymbol(
            name=self.sym_name,
            kind=self.sym_info.kind,
            range=Range(
                start=Position(
                    line=self.node.loc.first_line - OFFSET,
                    character=self.node.loc.col_start - OFFSET,
                ),
                end=Position(
                    line=self.node.loc.last_line - OFFSET,
                    character=self.node.loc.col_end - OFFSET,
                ),
            ),
            selection_range=self.sym_info.location.range,
            detail=self.sym_doc,
            children=self._get_children_doc_sym(),
        )

    @property
    def impl_loc(self):
        try:
            ws_symbol = self.is_use.ws_symbol if self.is_use else self.ws_symbol
            if isinstance(ws_symbol.decl.body, AstImplOnlyNode):
                return Location(
                    uri=f"file://{os.path.join(os.getcwd(), ws_symbol.decl.body.loc.mod_path)}",
                    range=Range(
                        start=Position(
                            line=ws_symbol.decl.body.loc.first_line - OFFSET,
                            character=ws_symbol.decl.body.loc.col_start - OFFSET,
                        ),
                        end=Position(
                            line=ws_symbol.decl.body.loc.last_line - OFFSET,
                            character=ws_symbol.decl.body.loc.col_end - OFFSET,
                        ),
                    ),
                )
        except Exception:
            return None

    @property
    def semantic_token(self):
        location = self.location
        token = [
            location.range.start.line,  # deltaLine
            location.range.start.character,  # deltaStart
            len(self.sym_name),  # length
            self._get_token_type(self.sym_type),  # tokenType
            self._get_token_modifier(self.sym_type),  # tokenModifiers
        ]
        return token

    @property
    def location(self):
        return self.sym_info.location

    @property
    def children(self):
        if hasattr(self, "sym_tab"):
            for kid_sym_tab in self.sym_tab.kid:
                if isinstance(
                    kid_sym_tab.owner,
                    (IfStmt, WhileStmt, WithStmt, IterForStmt),
                ):
                    for kid_sym in kid_sym_tab.tab.values():
                        kid_symbol = Symbol(kid_sym, self.doc_uri)
                        yield kid_symbol
                    continue
                kid_symbol = Symbol(kid_sym_tab, self.doc_uri)
                yield kid_symbol
        vars = (
            self.node.get_all_sub_nodes(HasVar)
            if isinstance(self.node, Architype)
            else (
                self.node.get_all_sub_nodes(ParamVar)
                if isinstance(self.node, Ability)
                else []
            )
        )
        for var in vars:
            var_symbol = Symbol(var, self.doc_uri)
            yield var_symbol

    def uses(self, ls: LanguageServer) -> List["Symbol"]:
        for mod_url in ls.jlws.modules.keys():
            for x in ls.jlws.get_uses(mod_url):
                try:
                    if x.sym_link == self.ws_symbol:
                        yield Symbol(x, f"file://{mod_url}", is_use=self)
                except Exception:
                    continue

    def _get_children_doc_sym(self):
        children = []
        for kid_symbol in self.children:
            try:
                children.append(kid_symbol.doc_sym)
            except Exception:
                pass
        return children

    @staticmethod
    def _get_symbol_kind(sym_type: str) -> SymbolKind:
        sym_type_map = {
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
        return sym_type_map.get(sym_type, SymbolKind.Variable)

    @staticmethod
    def _get_token_type(sym_type: str) -> int:
        sym_type_map = {
            "mod": 14,
            "mod_var": 7,
            "var": 7,
            "immutable": 7,
            "ability": 11,
            "object": 1,
            "node": 1,
            "edge": 1,
            "walker": 1,
            "enum": 2,
            "test": 11,
            "type": 5,
            "impl": 12,
            "field": 8,
            "method": 12,
            "constructor": 12,
            "enum_member": 9,
        }
        return sym_type_map.get(sym_type, 14)

    @staticmethod
    def _get_token_modifier(sym_type: str) -> int:
        # TODO: Add support for modifiers
        return 0

    def __repr__(self) -> str:
        return f"Symbol({self.sym_name}:{self.sym_type} Location:{self.location.range} {f'Use of {self.is_use.sym_name}' if self.is_use is not None else ''})"


def get_doc_symbols(ls: LanguageServer, doc_uri: str) -> List[Symbol]:
    symbols: List[Symbol] = []
    doc_url = doc_uri.replace("file://", "")
    module = ls.jlws.modules[doc_url]
    for sym_tab in module.ir.sym_tab.kid:
        if isinstance(sym_tab.owner, ModuleCode):
            continue
        symbols.append(Symbol(sym_tab, doc_uri))
    for sym in module.ir.sym_tab.tab.values():
        if str(sym.sym_type) != "var" or sym.decl.loc.first_line == 0:
            continue
        symbols.append(Symbol(sym, doc_uri)) 
    return symbols

def get_use_symbols(ls: LanguageServer, doc_uri: str) -> List[Symbol]:
    symbols: List[Symbol] = []
    doc_url = doc_uri.replace("file://", "")
    module = ls.jlws.modules[doc_url]
    for sym_tab in module.ir.sym_tab.uses:
        if sym_tab.name != "NAME":
            continue
        symbols.append(Symbol(sym_tab, doc_uri))
    return symbols


def get_symbol_by_name(
    name: str, symbol_list: List[Symbol], sym_type: str = None
) -> Symbol:
    for symbol in symbol_list:
        if symbol.sym_name == name and not symbol.is_use:
            if sym_type:
                if symbol.sym_type == sym_type:
                    return symbol
            else:
                continue
            return symbol
    return None
