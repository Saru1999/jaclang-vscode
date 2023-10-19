import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from unittest.mock import MagicMock

from lsp_server import formatting
import lsprotocol.types as lsp


class TestFormattingIntegration(unittest.TestCase):
    def test_formatting(self):
        # Set up mock LanguageServer instance
        ls_mock = MagicMock()

        # Set up mock DocumentFormattingParams instance
        class MockTextDocument:
            def __init__(self, uri):
                self.uri = uri

        params_mock = MagicMock()
        params_mock.text_document = MockTextDocument(
            "file:///Users/chandralegend/Desktop/Jaseci/jaclang-vscode/bundled/tool/test.jac"
        )

        # Call the function
        result = formatting(ls_mock, params_mock)

        # Assert that the result is a list of TextEdit objects
        self.assertIsInstance(result, list)
        for edit in result:
            self.assertIsInstance(edit, lsp.TextEdit)

        print(result[0].new_text)
        assert isinstance(result[0].new_text, str)
