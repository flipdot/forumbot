import pytest


from client import DiscourseStorageClient, BaseDiscourseStorage


class DiscourseDummyStorage(BaseDiscourseStorage):
    """In-memory storage for tests."""

    def __init__(self, client: DiscourseStorageClient):
        super().__init__(client)
        self._storage = {}

    def get(self, key, default=None):
        if key not in self._storage:
            return default or {}
        return self._storage[key]

    def put(self, key, value):
        self._storage[key] = value


@pytest.fixture
def dummy_storage_client(responses):
    return DiscourseStorageClient(
        host="https://discourse.example.com",
        api_username="testuser",
        api_key="secret-key",
        storage_cls=DiscourseDummyStorage,
    )
