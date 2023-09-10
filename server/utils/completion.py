from pygls.server import LanguageServer
from typing import Optional
from lsprotocol.types import (
    CompletionParams,
    CompletionItem,
    CompletionItemKind,
    InsertTextFormat,
)
import pkgutil
import re
import inspect
import importlib
import os

py_import_regex = r"import:py from (\w+),"

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


def _get_completion_items(
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
    ## jac imports
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

    ## python imports
    if before_cursor in ["import:py from ", "import:py "]:
        return [
            CompletionItem(label=py_lib, kind=CompletionItemKind.Module)
            for py_lib in py_libraries
        ]
    ### functions and classes in the imported python library
    py_import_match = re.match(py_import_regex, before_cursor)
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
