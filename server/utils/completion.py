from lsprotocol.types import (
    CompletionParams,
    CompletionItem,
    CompletionItemKind,
    InsertTextFormat,
)

snippets = [
    {
        "label": "loop",
        "detail": "for loop",
        "documentation": "for loop in jac",
        "insert_text": "for ${1:item} in ${2:iterable}:\n    ${3:# body of the loop}",
    }
]
keywords = [
    "node",
    "walker",
    "edge",
    "architype",
    "import",
    "from",
    "with",
    "in",
    "graph",
    "report",
    "disengage",
    "take",
    "import:jac",
    "import:py",
]

default_completion_items = [
    CompletionItem(label=keyword, kind=CompletionItemKind.Keyword)
    for keyword in keywords
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


def _get_completion_items(params: CompletionParams | None) -> list:
    return default_completion_items
