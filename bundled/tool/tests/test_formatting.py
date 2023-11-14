import sys
import os
import unittest

from mocks import MockLanguageServer

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from common.format import format_jac  # noqa: E402
from common.symbols import fill_workspace  # noqa: E402


class TestFormattingIntegration(unittest.TestCase):
    ls = MockLanguageServer("bundled/tool/tests/fixtures")
    fill_workspace(ls)

    def test_formatting(self):
        doc = self.ls.workspace.get_text_document(uri="file://bundled/tool/tests/fixtures/format.jac")
        source = doc.source
        formatted = format_jac(source)
        with open("bundled/tool/tests/fixtures/formatted.txt") as f:
            self.assertEqual(formatted, f.read())