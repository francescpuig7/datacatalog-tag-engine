
class FakeDb:
    def __init__(self):
        pass

    def collection(self, *collection_path: str):
        return FakeCollection(collection_path)


class FakeCollection:
    def __init__(self, collection_path):
        self.collection_path = collection_path

    def document(self, document_path):
        return FakeDocument(document_path)


class FakeDocument:
    def __init__(self, document_path):
        self.document_path = document_path
        self.configs = dict()

    def get(self):
        return self.configs[self.document_path]

    def set(self, confs):
        self.configs[self.document_path] = confs
