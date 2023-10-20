import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from unittest.mock import MagicMock

from lsp_utils import get_completion_items, default_completion_items
import lsprotocol.types as lsp


class MockDocument:
    def __init__(self, uri):
        with open(uri.replace("file://", ""), "r") as f:
            source = f.read()
        self.source = source
        self.uri = uri


class MockWorkspace:
    def get_document(self, uri):
        return MockDocument(uri)


ls_mock = MagicMock()
ls_mock.workspace = MockWorkspace()


class TestGetCompletionItems(unittest.TestCase):
    def test_empty_before_cursor(self):
        # Test when before_cursor is empty
        params = lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(uri="file:///path/to/file.jac"),
            position=lsp.Position(line=0, character=0),
        )

        expected = default_completion_items
        self.assertEqual(get_completion_items(ls_mock, params), expected)

    def test_jac_imports(self):
        # Test when last_word is "include:jac"
        params = lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(uri="file:///path/to/file.jac"),
            position=lsp.Position(line=0, character=10),
        )
        expected = [
            lsp.CompletionItem(label="module1", kind=lsp.CompletionItemKind.Module),
            lsp.CompletionItem(label="module2", kind=lsp.CompletionItemKind.Module),
            # ...
        ]
        self.assertEqual(get_completion_items(ls_mock, params), expected)

    def test_py_imports(self):
        # Test when before_cursor is "import:py from "
        params = lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(uri="file:///path/to/file.jac"),
            position=lsp.Position(line=0, character=14),
        )
        expected = [
            lsp.CompletionItem(label="math", kind=lsp.CompletionItemKind.Module),
            lsp.CompletionItem(label="os", kind=lsp.CompletionItemKind.Module),
        ]
        self.assertEqual(get_completion_items(ls_mock, params), expected)

    def test_py_module_imports(self):
        # Test when before_cursor is "import:py from module,"
        params = lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(uri="file:///path/to/file.jac"),
            position=lsp.Position(line=0, character=20),
        )
        expected = [
            lsp.CompletionItem(
                label="function1",
                kind=lsp.CompletionItemKind.Function,
                documentation="This is the documentation for function1",
            ),
            lsp.CompletionItem(
                label="class1",
                kind=lsp.CompletionItemKind.Class,
                documentation="This is the documentation for class1",
            ),
            # ...
        ]
        self.assertEqual(get_completion_items(ls_mock, params), expected)
