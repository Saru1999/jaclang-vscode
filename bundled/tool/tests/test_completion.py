import sys
import os
import unittest
import lsprotocol.types as lsp

from mocks import MockLanguageServer

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from common.completion import get_completion_items  # noqa: E402
from common.symbols import fill_workspace  # noqa: E402


class TestGetCompletionItems(unittest.TestCase):
    ls = MockLanguageServer("bundled/tool/tests/fixtures/completion")
    fill_workspace(ls)

    def test_empty_before_cursor(self):
        # Test when before_cursor is empty
        params = lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(
                uri="file://bundled/tool/tests/fixtures/completion/main.jac"
            ),
            position=lsp.Position(line=15, character=0),
        )
        completions = get_completion_items(self.ls, params)
        self.assertGreater(len(completions), 0)

    def test_jac_imports(self):
        # Test when last_word is "include:jac"
        params = lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(
                uri="file://bundled/tool/tests/fixtures/completion/main.jac"
            ),
            position=lsp.Position(line=3, character=12),
        )
        doc = self.ls.workspace.get_document(params.text_document.uri)
        # update the doc source by adding  "include:jac" to the 3rd line
        prev_source = doc.source
        doc.source = "\n".join(
            doc.source.splitlines()[:3] + ["include:jac "] + doc.source.splitlines()[3:]
        )
        completions = get_completion_items(self.ls, params)
        doc.source = prev_source  # reset the doc source
        self.assertGreater(len(completions), 0)

    def test_py_imports(self):
        # Test when before_cursor is "import:py from "
        params = lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(
                uri="file://bundled/tool/tests/fixtures/completion/main.jac"
            ),
            position=lsp.Position(line=3, character=10),
        )
        doc = self.ls.workspace.get_document(params.text_document.uri)
        prev_source = doc.source
        doc.source = "\n".join(
            doc.source.splitlines()[:3] + ["import:py "] + doc.source.splitlines()[3:]
        )
        completions = get_completion_items(self.ls, params)
        doc.source = prev_source  # reset the doc source
        self.assertGreater(len(completions), 0)

    def test_py_module_imports(self):
        # Test when before_cursor is "import:py from module,"
        params = lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(
                uri="file://bundled/tool/tests/fixtures/completion/main.jac"
            ),
            position=lsp.Position(line=3, character=21),
        )
        doc = self.ls.workspace.get_document(params.text_document.uri)
        prev_source = doc.source
        doc.source = "\n".join(
            doc.source.splitlines()[:3]
            + ["import:py from math, "]
            + doc.source.splitlines()[3:]
        )
        completions = get_completion_items(self.ls, params)
        doc.source = prev_source
        self.assertGreater(len(completions), 0)
