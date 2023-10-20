# Copyright (c) Jaseci Labs. All rights reserved.
# Licensed under the MIT License.
"""Utility functions and classes for use with running tools over LSP."""
from __future__ import annotations

import contextlib
import io
import os
import pathlib
import runpy
import site
import subprocess
import sys
import sysconfig
import threading
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

# Save the working directory used when loading this module
SERVER_CWD = os.getcwd()
CWD_LOCK = threading.Lock()
ERROR_CODE_BASE_URL = "INCLUDE ERROR CODE BASE URL HERE"
SEE_HREF_PREFIX = "See LINK"
SEE_PREFIX_LEN = len("See ")
NOTE_CODE = "note"
LINE_OFFSET = CHAR_OFFSET = 1


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
    """This is the extensions folder under ~/.vscode or ~/.vscode-server."""

    # The path here is calculated relative to the tool
    # this is because users can launch VS Code with custom
    # extensions folder using the --extensions-dir argument
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


# pylint: disable-next=too-few-public-methods
class RunResult:
    """Object to hold result from running tool."""

    def __init__(
        self, stdout: str, stderr: str, exit_code: Optional[Union[int, str]] = None
    ):
        self.stdout: str = stdout
        self.stderr: str = stderr
        self.exit_code: Optional[Union[int, str]] = exit_code


class CustomIO(io.TextIOWrapper):
    """Custom stream object to replace stdio."""

    name = None

    def __init__(self, name, encoding="utf-8", newline=None):
        self._buffer = io.BytesIO()
        self._buffer.name = name
        super().__init__(self._buffer, encoding=encoding, newline=newline)

    def close(self):
        """Provide this close method which is used by some tools."""
        # This is intentionally empty.

    def get_value(self) -> str:
        """Returns value from the buffer as string."""
        self.seek(0)
        return self.read()


@contextlib.contextmanager
def substitute_attr(obj: Any, attribute: str, new_value: Any):
    """Manage object attributes context when using runpy.run_module()."""
    old_value = getattr(obj, attribute)
    setattr(obj, attribute, new_value)
    yield
    setattr(obj, attribute, old_value)


@contextlib.contextmanager
def redirect_io(stream: str, new_stream):
    """Redirect stdio streams to a custom stream."""
    old_stream = getattr(sys, stream)
    setattr(sys, stream, new_stream)
    yield
    setattr(sys, stream, old_stream)


@contextlib.contextmanager
def change_cwd(new_cwd):
    """Change working directory before running code."""
    os.chdir(new_cwd)
    yield
    os.chdir(SERVER_CWD)


def _run_module(
    module: str, argv: Sequence[str], use_stdin: bool, source: str = None
) -> RunResult:
    """Runs as a module."""
    str_output = CustomIO("<stdout>", encoding="utf-8")
    str_error = CustomIO("<stderr>", encoding="utf-8")
    exit_code = None

    try:
        with substitute_attr(sys, "argv", argv):
            with redirect_io("stdout", str_output):
                with redirect_io("stderr", str_error):
                    if use_stdin and source is not None:
                        str_input = CustomIO("<stdin>", encoding="utf-8", newline="\n")
                        with redirect_io("stdin", str_input):
                            str_input.write(source)
                            str_input.seek(0)
                            runpy.run_module(module, run_name="__main__")
                    else:
                        runpy.run_module(module, run_name="__main__")
    except SystemExit as ex:
        exit_code = ex.code

    return RunResult(str_output.get_value(), str_error.get_value(), exit_code)


def run_module(
    module: str, argv: Sequence[str], use_stdin: bool, cwd: str, source: str = None
) -> RunResult:
    """Runs as a module."""
    with CWD_LOCK:
        if is_same_path(os.getcwd(), cwd):
            return _run_module(module, argv, use_stdin, source)
        with change_cwd(cwd):
            return _run_module(module, argv, use_stdin, source)


def run_path(argv: Sequence[str], cwd: str, env: Dict[str, str] = None) -> RunResult:
    """Runs as an executable."""
    new_env = os.environ.copy()
    if env is not None:
        new_env.update(env)
    result = subprocess.run(
        argv,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        cwd=cwd,
        env=new_env,
    )
    return RunResult(result.stdout, result.stderr, result.returncode)


def run_api(
    callback: Callable[[Sequence[str], Optional[CustomIO]], Tuple[str, str, int]],
    argv: Sequence[str],
    use_stdin: bool,
    cwd: str,
    source: str = None,
) -> RunResult:
    """Run a API."""
    with CWD_LOCK:
        if is_same_path(os.getcwd(), cwd):
            return _run_api(callback, argv, use_stdin, source)
        with change_cwd(cwd):
            return _run_api(callback, argv, use_stdin, source)


def _run_api(
    callback: Callable[[Sequence[str], Optional[CustomIO]], Tuple[str, str, int]],
    argv: Sequence[str],
    use_stdin: bool,
    source: str = None,
) -> RunResult:
    str_output = None
    str_error = None

    try:
        with substitute_attr(sys, "argv", argv):
            if use_stdin and source is not None:
                str_input = CustomIO("<stdin>", encoding="utf-8", newline="\n")
                with redirect_io("stdin", str_input):
                    str_input.write(source)
                    str_input.seek(0)
                    str_output, str_error, exit_code = callback(argv, str_input)
            else:
                str_output, str_error, exit_code = callback(argv, None)
    except SystemExit:
        pass

    return RunResult(str_output, str_error, exit_code)


# **********************************************************
# Jaseci Validation
# **********************************************************

from jaclang.jac.passes.transform import Alert
from jaclang.jac.parser import JacParser
from jaclang.jac.absyntree import SourceString
from jaclang.jac.passes.blue import pass_schedule

import re
from lsprotocol.types import Diagnostic, DiagnosticSeverity, Position, Range


def jac_to_errors(
    file_path: str, source: str, base_dir: str = "", schedule=pass_schedule
) -> list[Alert]:
    """Converts JAC source to errors if any"""
    source = SourceString(source)
    prse = JacParser(mod_path=file_path, input_ir=source, base_path=base_dir, prior=source)
    for i in schedule:
        prse = i(mod_path=file_path, input_ir=prse.ir, base_path=base_dir, prior=prse)
    return prse.errors_had


def validate(ls, params):
    ls.show_message_log("Validating jac file...")

    text_doc = ls.workspace.get_document(params.text_document.uri)
    source = text_doc.source
    doc_path = params.text_document.uri.replace("file://", "")
    diagnostics = _validate_jac(doc_path, source) if source else []
    ls.publish_diagnostics(text_doc.uri, diagnostics)
    return diagnostics


def _validate_jac(doc_path: str, source: str) -> list:
    """validate jac file"""
    diagnostics = []
    errors = jac_to_errors(doc_path, source)
    for err in errors:
        msg = err.msg
        loc = err.loc
        diagnostics.append(
            Diagnostic(
                range=Range(
                    start=Position(line=loc.first_line, character=loc.col_start),
                    end=Position(line=loc.last_line, character=loc.col_end),
                ),
                message=msg,
                severity=DiagnosticSeverity.Error,
            )
        )
    return diagnostics


# **********************************************************
# Jaseci Completion
# **********************************************************


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
            uri=f"file://{mod_path}", language_id="jac", version=0, text=mod_info.ir.source.code
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
    jlws_imports= ls.jlws.get_dependencies(doc_url) #TODO: Update this to make sense for use case
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
