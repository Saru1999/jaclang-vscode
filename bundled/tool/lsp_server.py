# Copyright (c) Jaseci Labs. All rights reserved.
# Licensed under the MIT License.
"""Implementation of tool support over LSP."""
from __future__ import annotations

import json
import os
import pathlib
import sys
from typing import Optional


# **********************************************************
# Update sys.path before importing any bundled libraries.
# **********************************************************
def update_sys_path(path_to_add: str, strategy: str) -> None:
    """Add given path to `sys.path`."""
    if path_to_add not in sys.path and os.path.isdir(path_to_add):
        if strategy == "useBundled":
            sys.path.insert(0, path_to_add)
        else:
            sys.path.append(path_to_add)


# Ensure that we can import LSP libraries, and other bundled libraries.
BUNDLE_DIR = pathlib.Path(__file__).parent.parent
BUNDLED_LIBS = os.fspath(BUNDLE_DIR / "libs")
# Always use bundled server files.
update_sys_path(os.fspath(BUNDLE_DIR / "tool"), "useBundled")
update_sys_path(
    BUNDLED_LIBS,
    os.getenv("LS_IMPORT_STRATEGY", "useBundled"),
)

# **********************************************************
# Imports needed for the language server goes below this.
# **********************************************************
import lsp_utils as utils
import lsprotocol.types as lsp
from pygls import server, uris

WORKSPACE_SETTINGS = {}
GLOBAL_SETTINGS = {}

MAX_WORKERS = 5
LSP_SERVER = server.LanguageServer(
    name="Jaseci", version="v0.0.1", max_workers=MAX_WORKERS
)
LSP_SERVER.workspace_filled = False
LSP_SERVER.dep_table = {}

# **********************************************************
# Language Server features
# **********************************************************

# Handle Document Operations


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls, params: lsp.DidChangeTextDocumentParams):
    """
    Update the document tree and validate the changes made to the text document.

    Args:
        ls (LanguageServer): The language server instance.
        params (lsp.DidChangeTextDocumentParams): The parameters for the text document change.
    """
    utils.update_doc_tree(ls, params.text_document.uri)
    utils.validate(ls, params)


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
def did_save(ls, params: lsp.DidSaveTextDocumentParams):
    """
    Updates the document tree and validates the saved text document.

    Args:
        ls (LanguageServer): The language server instance.
        params (lsp.DidSaveTextDocumentParams): The parameters for the saved text document.
    """
    utils.update_doc_tree(ls, params.text_document.uri)
    utils.validate(ls, params)


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_CLOSE)
def did_close(ls, params: lsp.DidCloseTextDocumentParams):
    """
    Callback function for when a text document is closed in the language server.

    :param ls: The language server instance.
    :type ls: LanguageServer
    :param params: The parameters for the text document that was closed.
    :type params: lsp.DidCloseTextDocumentParams
    """
    pass


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls, params: lsp.DidOpenTextDocumentParams):
    """
    This function is called when a text document is opened in the client.
    It fills the workspace if it is not already filled and validates the parameters.
    """
    if not ls.workspace_filled:
        utils.fill_workspace(ls)
    utils.validate(ls, params)


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
    ls.workspace_filled = False
    utils.fill_workspace(ls)


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
                        log_to_output("Accepted")
    ls.workspace.remove_text_document(old_uri)
    del ls.dep_table[old_uri.replace("file://", "")]
    utils.fill_workspace(ls)


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
    ls.workspace_filled = False
    utils.fill_workspace(ls)


# Notebook Support


@LSP_SERVER.feature(lsp.NOTEBOOK_DOCUMENT_DID_OPEN)
async def did_open(ls, params: lsp.DidOpenNotebookDocumentParams):
    pass


@LSP_SERVER.feature(lsp.NOTEBOOK_DOCUMENT_DID_CLOSE)
async def did_open(ls, params: lsp.DidCloseNotebookDocumentParams):
    pass


@LSP_SERVER.feature(lsp.NOTEBOOK_DOCUMENT_DID_SAVE)
async def did_open(ls, params: lsp.DidSaveNotebookDocumentParams):
    pass


@LSP_SERVER.feature(lsp.NOTEBOOK_DOCUMENT_DID_CHANGE)
async def did_open(ls, params: lsp.DidChangeNotebookCellParams):
    pass


# Features


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_FORMATTING)
def formatting(ls, params: lsp.DocumentFormattingParams):
    """
    TODO: Selective Formatting needs to be implemented
    Formats the document.

    :param ls: The language server instance.
    :type ls: lsp.LanguageServer
    :param params: The document formatting parameters.
    :type params: lsp.DocumentFormattingParams
    :return: A list of text edits to apply to the document.
    :rtype: List[lsp.TextEdit]
    """
    doc_uri = params.text_document.uri
    formatted_text = utils.format_jac(doc_uri)
    return [
        lsp.TextEdit(
            range=lsp.Range(
                start=lsp.Position(line=0, character=0),
                end=lsp.Position(line=len(formatted_text), character=0),
            ),
            new_text=formatted_text,
        )
    ]


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_COMPLETION)
def completions(params: Optional[lsp.CompletionParams] = None) -> lsp.CompletionList:
    """
    TODO: More intelligent completions
    Returns a list of completion items for the given completion parameters.

    :param params: The completion parameters.
    :type params: Optional[lsp.CompletionParams]
    :return: A list of completion items.
    :rtype: lsp.CompletionList
    """
    completion_items = utils.get_completion_items(LSP_SERVER, params)
    return lsp.CompletionList(is_incomplete=False, items=completion_items)


# @LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DOCUMENT_HIGHLIGHT)
# def document_highlight(ls, params: lsp.DocumentHighlightParams):
#     """
#     TODO Things to happen on text document document highlight:
#     1. Highlight the Symbols
#     2. Use Python Syntax Highlighting for python blocks
#     """
#     higlights = []
#     doc = ls.workspace.get_document(params.text_document.uri)
#     for symbol in doc.symbols:
#         higlights.append(
#             lsp.DocumentHighlight(
#                 range=symbol.location.range,
#                 kind=lsp.DocumentHighlightKind.Read,
#             )
#         )
#     return higlights


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DEFINITION)
def definition(ls, params: lsp.DefinitionParams):
    pass


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_HOVER)
def hover(ls, params: lsp.HoverParams):
    """
    TODO: Add More information to the hover
    Returns information about the symbol at the specified position.

    :param ls: The Language Server instance.
    :type ls: LanguageServer
    :param params: The HoverParams object containing the URI and position of the symbol.
    :type params: lsp.HoverParams
    :return: A Hover object with information about the symbol.
    :rtype: lsp.Hover
    """
    uri = params.text_document.uri
    position = params.position
    lsp_document = ls.workspace.get_document(uri)
    if lsp_document is None:
        return None

    # Find the symbol at the specified position
    symbol = None
    for s in lsp_document.symbols:
        if utils.is_contained(s.location, position):
            symbol = s
            break

    # Create a new Hover object with information about the symbol and return it
    if symbol is not None:
        return lsp.Hover(
            contents=lsp.MarkupContent(
                kind=lsp.MarkupKind.PlainText, value=symbol.name
            ),
            range=symbol.location.range,
        )

    return None


# Symbol Handling


@LSP_SERVER.feature(lsp.WORKSPACE_SYMBOL)
def workspace_symbol(ls, params: lsp.WorkspaceSymbolParams):
    """Workspace symbols."""
    symbols = []
    for doc in ls.workspace.documents.values():
        if hasattr(doc, "symbols"):
            symbols.extend(doc.symbols)
        else:
            doc.symbols = utils.get_doc_symbols(ls, doc.uri)
            symbols.extend(doc.symbols)
    return symbols


@LSP_SERVER.feature(lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL)
def document_symbol(ls, params: lsp.DocumentSymbolParams):
    """Document symbols."""
    uri = params.text_document.uri
    doc = ls.workspace.get_document(uri)
    if not hasattr(doc, "symbols"):
        utils.update_doc_tree(ls, doc.uri)
        doc_symbols = utils.get_doc_symbols(ls, doc.uri)
        return [s for s in doc_symbols if s.location.uri == doc.uri]
    else:
        return [s for s in doc.symbols if s.location.uri == doc.uri]


# **********************************************************
# Required Language Server Initialization and Exit handlers.
# **********************************************************
@LSP_SERVER.feature(lsp.INITIALIZE)
def initialize(params: lsp.InitializeParams) -> None:
    """LSP handler for initialize request."""
    log_to_output(f"CWD Server: {os.getcwd()}")
    import_strategy = os.getenv("LS_IMPORT_STRATEGY", "useBundled")
    update_sys_path(os.getcwd(), import_strategy)

    GLOBAL_SETTINGS.update(**params.initialization_options.get("globalSettings", {}))

    settings = params.initialization_options["settings"]
    _update_workspace_settings(settings)
    log_to_output(
        f"Settings used to run Server:\r\n{json.dumps(settings, indent=4, ensure_ascii=False)}\r\n"
    )
    log_to_output(
        f"Global settings:\r\n{json.dumps(GLOBAL_SETTINGS, indent=4, ensure_ascii=False)}\r\n"
    )

    # Add extra paths to sys.path
    setting = _get_settings_by_path(pathlib.Path(os.getcwd()))
    for extra in setting.get("extraPaths", []):
        update_sys_path(extra, import_strategy)


# *****************************************************
# Internal functional and settings management APIs.
# *****************************************************
def _get_global_defaults():
    return {
        "path": GLOBAL_SETTINGS.get("path", []),
        "interpreter": GLOBAL_SETTINGS.get("interpreter", [sys.executable]),
        "args": GLOBAL_SETTINGS.get("args", []),
        "severity": GLOBAL_SETTINGS.get(
            "severity",
            {
                "error": "Error",
                "note": "Information",
            },
        ),
        "importStrategy": GLOBAL_SETTINGS.get("importStrategy", "useBundled"),
        "showNotifications": GLOBAL_SETTINGS.get("showNotifications", "off"),
        "extraPaths": GLOBAL_SETTINGS.get("extraPaths", []),
        "reportingScope": GLOBAL_SETTINGS.get("reportingScope", "file"),
    }


def _update_workspace_settings(settings):
    if not settings:
        key = utils.normalize_path(os.getcwd())
        WORKSPACE_SETTINGS[key] = {
            "cwd": key,
            "workspaceFS": key,
            "workspace": uris.from_fs_path(key),
            **_get_global_defaults(),
        }
        return

    for setting in settings:
        key = utils.normalize_path(uris.to_fs_path(setting["workspace"]))
        WORKSPACE_SETTINGS[key] = {
            **setting,
            "workspaceFS": key,
        }


def _get_settings_by_path(file_path: pathlib.Path):
    workspaces = {s["workspaceFS"] for s in WORKSPACE_SETTINGS.values()}

    while file_path != file_path.parent:
        str_file_path = utils.normalize_path(file_path)
        if str_file_path in workspaces:
            return WORKSPACE_SETTINGS[str_file_path]
        file_path = file_path.parent

    setting_values = list(WORKSPACE_SETTINGS.values())
    return setting_values[0]


# *****************************************************
# Logging and notification.
# *****************************************************
def log_to_output(
    message: str, msg_type: lsp.MessageType = lsp.MessageType.Log
) -> None:
    LSP_SERVER.show_message_log(message, msg_type)


def log_error(message: str) -> None:
    LSP_SERVER.show_message_log(message, lsp.MessageType.Error)
    if os.getenv("LS_SHOW_NOTIFICATION", "off") in ["onError", "onWarning", "always"]:
        LSP_SERVER.show_message(message, lsp.MessageType.Error)


def log_warning(message: str) -> None:
    LSP_SERVER.show_message_log(message, lsp.MessageType.Warning)
    if os.getenv("LS_SHOW_NOTIFICATION", "off") in ["onWarning", "always"]:
        LSP_SERVER.show_message(message, lsp.MessageType.Warning)


def log_always(message: str) -> None:
    LSP_SERVER.show_message_log(message, lsp.MessageType.Info)
    if os.getenv("LS_SHOW_NOTIFICATION", "off") in ["always"]:
        LSP_SERVER.show_message(message, lsp.MessageType.Info)


# *****************************************************
# Start the server.
# *****************************************************
if __name__ == "__main__":
    LSP_SERVER.start_io()
