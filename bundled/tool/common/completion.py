import re
import inspect
import importlib
import os
from typing import Optional

from pygls.server import LanguageServer
from lsprotocol.types import (
    CompletionParams,
    CompletionItem,
    CompletionItemKind,
    InsertTextFormat,
)

from .constants import JAC_KW, PY_LIBS, SNIPPETS

DEFAULT_COMPLETION_ITEMS = [
    CompletionItem(label=keyword, kind=CompletionItemKind.Keyword, **info)
    for keyword, info in JAC_KW.items()
] + [
    CompletionItem(
        label=snippet["label"],
        kind=CompletionItemKind.Snippet,
        detail=snippet["detail"],
        documentation=snippet["documentation"],
        insert_text=snippet["insert_text"],
        insert_text_format=InsertTextFormat.Snippet,
    )
    for snippet in SNIPPETS
]


def get_completion_items(
    server: LanguageServer, params: Optional[CompletionParams]
) -> list[CompletionItem]:
    """
    Returns a list of completion items based on the text document and cursor position.

    Args:
        server (LanguageServer): The language server instance.
        params (Optional[CompletionParams]): The completion parameters.

    Returns:
        list: A list of completion items.
    """
    doc = server.workspace.get_document(params.text_document.uri)
    line = doc.source.splitlines()[params.position.line]
    before_cursor = line[: params.position.character]

    if not before_cursor:
        return DEFAULT_COMPLETION_ITEMS

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
            for py_lib in PY_LIBS
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

    return DEFAULT_COMPLETION_ITEMS
