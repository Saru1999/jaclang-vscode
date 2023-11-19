import sys
import os
import unittest
from lsprotocol.types import DocumentSymbol

from mocks import MockLanguageServer

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from common.symbols import fill_workspace  # noqa: E402


class TestSymbols(unittest.TestCase):
    ls = MockLanguageServer("bundled/tool/tests/fixtures")
    fill_workspace(ls)

    def test_symbols(self):
        doc = self.ls.workspace.get_text_document(
            "file://bundled/tool/tests/fixtures/main.jac"
        )
        self.assertGreater(len(doc.symbols), 0)
        self.assertGreater(len(list(doc.symbols[0].children)), 0)
        self.assertIsInstance(doc.symbols[0].doc_sym, DocumentSymbol)
