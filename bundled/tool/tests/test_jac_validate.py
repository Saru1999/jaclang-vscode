import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from unittest.mock import MagicMock

from common.validation import validate
import lsprotocol.types as lsp


class TestValidate(unittest.TestCase):
    def test_validate(self):
        # Set up mock LanguageServer instance
        ls_mock = MagicMock()

        class MockDocument:
            def __init__(self, uri):
                with open(uri.replace("file://", ""), "r") as f:
                    source = f.read()
                self.source = source
                self.uri = uri

        class MockWorkspace:
            def get_document(self, uri):
                return MockDocument(uri)

        ls_mock.workspace = MockWorkspace()

        # Set up mock Params instance
        class MockTextDocument:
            def __init__(self, uri):
                self.uri = uri

        params_mock = MagicMock()
        params_mock.text_document = MockTextDocument(
            "file:///Users/chandralegend/Desktop/Jaseci/jaclang-vscode/bundled/tool/test.jac"
        )

        # Call the function
        result = validate(ls_mock, params_mock)

        # Assert that the result is a list of Diagnostic objects
        self.assertIsInstance(result, list)
        for diag in result:
            self.assertIsInstance(diag, lsp.Diagnostic)
