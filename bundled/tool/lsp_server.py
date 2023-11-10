# Copyright (c) Jaseci Labs. All rights reserved.
# Licensed under the MIT License.

import json
import os
import pathlib
from typing import Optional

from common.utils import (
    normalize_path,
    update_sys_path,
    get_symbol_at_pos,
    show_doc_info,
)


# Ensure that we can import LSP libraries, and other bundled libraries.
BUNDLE_DIR = pathlib.Path(__file__).parent.parent
BUNDLED_LIBS = os.fspath(BUNDLE_DIR / "libs")
update_sys_path(os.fspath(BUNDLE_DIR / "tool"), "useBundled")
update_sys_path(
    BUNDLED_LIBS,
    os.getenv("LS_IMPORT_STRATEGY", "useBundled"),
)

import lsprotocol.types as lsp  # noqa: E402
from pygls import server, uris  # noqa: E402

from common.validation import validate  # noqa: E402
from common.completion import get_completion_items  # noqa: E402
from common.format import format_jac  # noqa: E402
from common.symbols import (  # noqa: E402
    fill_workspace,
    update_doc_tree,
    update_doc_deps,
)
from common.hover import get_hover_info  # noqa: E402
from common.logging import log_to_output  # noqa: E402


class JacLanguageServer(server.LanguageServer):
    def __init__(self, name, version, max_workers):
        super().__init__(name=name, version=version, max_workers=max_workers)
        self.workspace_filled = False
        self.dep_table = {}


WORKSPACE_SETTINGS = {}
GLOBAL_SETTINGS = {}

MAX_WORKERS = 5
LSP_SERVER = JacLanguageServer(
    name="Jaclang Language Server",
    version="0.0.1",
    max_workers=MAX_WORKERS,
)

# ************** Language Server features ********************


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: server.LanguageServer, params: lsp.DidChangeTextDocumentParams):
    """
    Update the document tree and validate the changes made to the text document.

    Args:
        ls (LanguageServer): The language server instance.
        params (lsp.DidChangeTextDocumentParams): The parameters for the text document change.
    """
    show_doc_info(ls, params.text_document.uri)


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
def did_save(ls, params: lsp.DidSaveTextDocumentParams):
    """
    Updates the document tree and validates the saved text document.

    Args:
        ls (LanguageServer): The language server instance.
        params (lsp.DidSaveTextDocumentParams): The parameters for the saved text document.
    """
    doc = ls.workspace.get_text_document(params.text_document.uri)
    doc.version += 1

    diagnostics = validate(ls, params, False, True)
    ls.publish_diagnostics(params.text_document.uri, diagnostics)
    if not diagnostics:
        update_doc_tree(ls, params.text_document.uri)
        update_doc_deps(ls, params.text_document.uri)

    show_doc_info(ls, params.text_document.uri)


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: server.LanguageServer, params: lsp.DidOpenTextDocumentParams):
    """
    This function is called when a text document is opened in the client.
    It fills the workspace if it is not already filled and validates the parameters.
    """
    if not ls.workspace_filled:
        fill_workspace(ls)

    diagnostics = validate(ls, params)
    ls.publish_diagnostics(params.text_document.uri, diagnostics)

    if not diagnostics:
        update_doc_tree(ls, params.text_document.uri)
        update_doc_deps(ls, params.text_document.uri)

    show_doc_info(ls, params.text_document.uri)


# Handle File Operations


@LSP_SERVER.feature(
    lsp.WORKSPACE_DID_CREATE_FILES,
    lsp.FileOperationRegistrationOptions(
        filters=[lsp.FileOperationFilter(pattern=lsp.FileOperationPattern("**/*.jac"))]
    ),
)
def did_create_files(ls: server.LanguageServer, params: lsp.CreateFilesParams):
    """
    Callback function for when files are created in the workspace.

    Args:
        ls (LanguageServer): The language server instance.
        params (lsp.CreateFilesParams): The parameters for the file creation.
    """
    fill_workspace(ls)


@LSP_SERVER.feature(
    lsp.WORKSPACE_DID_RENAME_FILES,
    lsp.FileOperationRegistrationOptions(
        filters=[lsp.FileOperationFilter(pattern=lsp.FileOperationPattern("**/*.jac"))]
    ),
)
def did_rename_files(ls: server.LanguageServer, params: lsp.RenameFilesParams):
    """
    Callback function for when a file is renamed in the workspace.
    Updates the dependency table and handles renaming of import statements.
    """
    new_uri = params.files[0].new_uri
    old_uri = params.files[0].old_uri

    ls.workspace_filled = False
    dep_table_copy = ls.dep_table.copy()
    for doc in dep_table_copy.keys():
        if dep_table_copy[doc]:
            for dep in dep_table_copy[doc]:
                if dep["uri"] == old_uri:
                    ls.show_message(
                        f"Renamed {new_uri} is a dependency of {doc}",
                        lsp.MessageType.Warning,
                    )
                    del ls.dep_table[doc]
                    # FUTURE TODO: WINDOW_SHOW_MESSAGE_REQUEST is not yet supported by pygls
                    # request_result = await show_message_request(ls, f"Renamed {new_uri} is a dependency of {doc}. Do you want to change the import statement?", ["Yes", "No"])
                    request_result = "Yes"
                    if request_result == "Yes":
                        # TODO: Handle the rename of the import statement
                        log_to_output(ls, "Accepted")
    ls.workspace.remove_text_document(old_uri)
    del ls.dep_table[old_uri.replace("file://", "")]
    fill_workspace(ls)


@LSP_SERVER.feature(
    lsp.WORKSPACE_DID_DELETE_FILES,
    lsp.FileOperationRegistrationOptions(
        filters=[lsp.FileOperationFilter(pattern=lsp.FileOperationPattern("**/*.jac"))]
    ),
)
def did_delete_files(ls: server.LanguageServer, params: lsp.DeleteFilesParams):
    """
    Removes the specified files from the workspace and dependency table.
    If a file is a dependency of another file, it will also be removed from the dependency table.
    """
    for _file in params.files:
        ls.workspace.remove_text_document(_file.uri)
        del ls.dep_table[_file.uri.replace("file://", "")]
        dep_table_copy = ls.dep_table.copy()
        for doc in dep_table_copy.keys():
            if dep_table_copy[doc]:
                for dep in dep_table_copy[doc]:
                    if dep["uri"] == _file.uri:
                        ls.show_message(
                            f"Deleted {_file.uri} is a dependency of {doc}",
                            lsp.MessageType.Warning,
                        )
                        del ls.dep_table[doc]
    fill_workspace(ls)


# Notebook Support


@LSP_SERVER.feature(lsp.NOTEBOOK_DOCUMENT_DID_OPEN)
async def did_notebook_document_open(ls, params: lsp.DidOpenNotebookDocumentParams):
    pass


@LSP_SERVER.feature(lsp.NOTEBOOK_DOCUMENT_DID_CLOSE)
async def did_notebook_document_close(ls, params: lsp.DidCloseNotebookDocumentParams):
    pass


@LSP_SERVER.feature(lsp.NOTEBOOK_DOCUMENT_DID_SAVE)
async def did_notebook_document_save(ls, params: lsp.DidSaveNotebookDocumentParams):
    pass


@LSP_SERVER.feature(lsp.NOTEBOOK_DOCUMENT_DID_CHANGE)
async def did_notebook_document_change(ls, params: lsp.DidChangeNotebookDocumentParams):
    pass


# Features


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_FORMATTING)
def formatting(ls, params: lsp.DocumentFormattingParams):
    """
    TODO: Selective Formatting needs to be implemented
    """
    doc = ls.workspace.get_text_document(params.text_document.uri)
    source = doc.source
    formatted_text = format_jac(source)
    return [
        lsp.TextEdit(
            range=lsp.Range(
                start=lsp.Position(line=0, character=0),
                end=lsp.Position(line=len(formatted_text), character=0),
            ),
            new_text=formatted_text,
        )
    ]


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_COMPLETION, lsp.CompletionOptions(trigger_characters=[".", ":", ""]))
def completions(params: Optional[lsp.CompletionParams] = None) -> lsp.CompletionList:
    completion_items = get_completion_items(LSP_SERVER, params)
    return lsp.CompletionList(is_incomplete=False, items=completion_items)


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_INLINE_COMPLETION)
def inline_completions(ls, params: lsp.InlineCompletionParams):
    # https://www.youtube.com/watch?v=B89NXOqif-E
    pass


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_INLAY_HINT)
def inlay_hints(ls, params: lsp.InlayHintParams):
    # https://www.youtube.com/watch?v=uvrIFZYW7eg
    pass


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_SIGNATURE_HELP)
def signature_help(ls, params: lsp.SignatureHelpParams):
    # https://www.youtube.com/watch?v=vi2PLcLqVxI
    pass


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DEFINITION)
def definition(ls, params: lsp.DefinitionParams):
    doc = ls.workspace.get_text_document(params.text_document.uri)
    if not hasattr(doc, "symbols"):
        update_doc_tree(ls, doc.uri)
    symbol = get_symbol_at_pos(ls, doc, params.position)
    if symbol is not None:
        return symbol.defn_loc


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_HOVER)
def hover(ls, params: lsp.HoverParams):
    """
    TODO: Add More information to the hover
    """
    uri = params.text_document.uri
    position = params.position
    lsp_document = ls.workspace.get_text_document(uri)
    if lsp_document is None:
        return None
    return get_hover_info(ls, lsp_document, position)


# Symbol Handling


@LSP_SERVER.feature(lsp.WORKSPACE_SYMBOL)
def workspace_symbol(ls, params: lsp.WorkspaceSymbolParams):
    """Workspace symbols."""
    symbols = []
    for doc in ls.workspace.documents.values():
        if not hasattr(doc, "symbols"):
            update_doc_tree(ls, doc.uri)
        symbols.extend([s.sym_info for s in doc.symbols])
    return symbols


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL)
def document_symbol(ls, params: lsp.DocumentSymbolParams):
    """Document symbols."""
    uri = params.text_document.uri
    doc = ls.workspace.get_text_document(uri)
    if not hasattr(doc, "symbols"):
        update_doc_tree(ls, doc.uri)
    doc_syms = []
    for sym in doc.symbols:
        try:
            doc_syms.append(sym.doc_sym)
        except AttributeError:
            pass
    return doc_syms


# LSP Server Initialization


@LSP_SERVER.feature(lsp.INITIALIZE)
def initialize(params: lsp.InitializeParams) -> None:
    """LSP handler for initialize request."""
    log_to_output(LSP_SERVER, f"CWD Server: {os.getcwd()}")
    import_strategy = os.getenv("LS_IMPORT_STRATEGY", "useBundled")
    update_sys_path(os.getcwd(), import_strategy)

    GLOBAL_SETTINGS.update(**params.initialization_options.get("globalSettings", {}))

    settings = params.initialization_options["settings"]
    _update_workspace_settings(settings)
    log_to_output(
        LSP_SERVER,
        f"Settings used to run Server:\r\n{json.dumps(settings, indent=4, ensure_ascii=False)}\r\n",
    )
    log_to_output(
        LSP_SERVER,
        f"Global settings:\r\n{json.dumps(GLOBAL_SETTINGS, indent=4, ensure_ascii=False)}\r\n",
    )

    # Add extra paths to sys.path
    setting = _get_settings_by_path(pathlib.Path(os.getcwd()))
    for extra in setting.get("extraPaths", []):
        update_sys_path(extra, import_strategy)

    fill_workspace(LSP_SERVER)


@LSP_SERVER.feature(lsp.WORKSPACE_DID_CHANGE_CONFIGURATION)
def did_change_configuration(ls, params: lsp.DidChangeConfigurationParams):
    """LSP handler for didChangeConfiguration request."""
    settings = params.settings["jac"]
    _update_workspace_settings(settings)
    log_to_output(
        ls,
        f"Settings used to run Server:\r\n{json.dumps(settings, indent=4, ensure_ascii=False)}\r\n",
    )


# Internal functional and settings management APIs.


def _get_global_defaults():
    return {
        "path": GLOBAL_SETTINGS.get("path", []),
        "severity": GLOBAL_SETTINGS.get(
            "severity",
            {
                "error": "Error",
                "note": "Information",
            },
        ),
        "importStrategy": GLOBAL_SETTINGS.get("importStrategy", "useBundled"),
        "showNotifications": GLOBAL_SETTINGS.get("showNotifications", "off"),
        "reportingScope": GLOBAL_SETTINGS.get("reportingScope", "file"),
        "showWarnings": GLOBAL_SETTINGS.get("showWarnings", False),
    }


def _update_workspace_settings(settings):
    if not settings:
        key = normalize_path(os.getcwd())
        WORKSPACE_SETTINGS[key] = {
            "cwd": key,
            "workspaceFS": key,
            "workspace": uris.from_fs_path(key),
            **_get_global_defaults(),
        }
        return

    for setting in settings:
        key = normalize_path(uris.to_fs_path(setting["workspace"]))
        WORKSPACE_SETTINGS[key] = {
            **setting,
            "workspaceFS": key,
        }


def _get_settings_by_path(file_path: pathlib.Path):
    workspaces = {s["workspaceFS"] for s in WORKSPACE_SETTINGS.values()}

    while file_path != file_path.parent:
        str_file_path = normalize_path(file_path)
        if str_file_path in workspaces:
            return WORKSPACE_SETTINGS[str_file_path]
        file_path = file_path.parent

    setting_values = list(WORKSPACE_SETTINGS.values())
    return setting_values[0]


# Start the LSP Server
if __name__ == "__main__":
    LSP_SERVER.start_io()
