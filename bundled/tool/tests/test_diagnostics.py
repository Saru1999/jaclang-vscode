import sys
import os
import unittest
from unittest.mock import MagicMock

from mocks import MockLanguageServer

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from common.validation import validate # noqa: E402
from common.symbols import fill_workspace # noqa: E402


class TestValidate(unittest.TestCase):
    ls = MockLanguageServer("bundled/tool/tests/fixtures")
    fill_workspace(ls)

    def test_validate(self):
        self.ls.settings = {"showWarning": True}
        mock_params = MagicMock()
        mock_params.text_document.uri = "file://bundled/tool/tests/fixtures/validate.jac"
        daignostics = validate(self.ls, mock_params)
        self.assertGreater(len(daignostics), 0)
