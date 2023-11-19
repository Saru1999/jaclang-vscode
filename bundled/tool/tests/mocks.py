from unittest.mock import MagicMock


class MockLanguageServer(MagicMock):
    def __init__(self, root_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workspace = MockWorkspace(root_path)
        self.dep_table = {}


class MockWorkspace:
    def __init__(self, root_path):
        self.documents = {}
        self.root_path = root_path

    def put_document(self, doc):
        self.documents[doc.uri] = MockDocument(doc)

    def get_text_document(self, uri):
        return self.documents[uri]

    def get_document(self, uri):
        return self.get_text_document(uri)


class MockDocument:
    def __init__(self, doc):
        self.source = doc.text
        self.uri = doc.uri
        self.version = doc.version
        self.language_id = doc.language_id
