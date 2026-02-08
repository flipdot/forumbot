from typing import Dict
from abc import ABC, abstractmethod

from pydiscourse import DiscourseClient
import yaml

from logging import getLogger

logger = getLogger(__name__)


class DiscourseStorageError(Exception):
    pass


class DiscourseStorageClient(DiscourseClient):
    def __init__(
        self, *args, storage_cls: type["BaseDiscourseStorage"] | None = None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        storage_cls = storage_cls or DiscourseStorage
        self.storage: BaseDiscourseStorage = storage_cls(self)

    # TODO: Add this method upstream
    def private_messages_sent(self, username=None, **kwargs):
        if username is None:
            username = self.api_username
        return self._get(f"/topics/private-messages-sent/{username}.json", **kwargs)

    # TODO: Maybe add this method upstream, too? Allows us to get raw post content
    def single_post(self, post_id, **kwargs):
        return self._get(f"/posts/{post_id}.json", **kwargs)

    def single_topic(self, topic_id, **kwargs):
        return self._get(f"/t/{topic_id}.json", **kwargs)

    def search(self, query, **kwargs):
        # Original method forces a "term" parameter but q works fine for us.
        return self._get("/search.json", q=query, **kwargs)


class BaseDiscourseStorage(ABC):
    def __init__(self, client: "DiscourseStorageClient"):
        self.client = client

    @abstractmethod
    def get(self, key, default=None) -> Dict: ...

    @abstractmethod
    def put(self, key, value): ...


class DiscourseStorage(BaseDiscourseStorage):
    """
    Uses a PM to itself to persist data. This way, we won't need to care about storage.
    """

    def __init__(self, client: DiscourseStorageClient):
        super().__init__(client)
        self._storage_ids: Dict[str, tuple[int | None, int | None]] = {}

    def _resolve_key(self, key: str) -> tuple[int | None, int | None]:
        if key in self._storage_ids:
            return self._storage_ids[key]

        logger.info(f'Resolving storage key "{key}" via search')
        query = f"STORAGE_{key} @{self.client.api_username} in:title in:messages"
        search_results = self.client.search(query)

        topics = search_results.get("topics", [])
        # Filter for exact title match and where the bot is the only participant (message to self)
        for topic in topics:
            if topic["title"] == f"STORAGE_{key}":
                topic_id = topic["id"]
                # Search results only give us the topic ID. Fetch the first post ID.
                post_id = self.client.posts(topic_id)["post_stream"]["posts"][0]["id"]
                self._storage_ids[key] = topic_id, post_id
                logger.info(f'Resolved storage key "{key}" to topic {topic_id}')
                return topic_id, post_id

        logger.info(f'No storage topic found for key "{key}"')
        return None, None

    def get(self, key, default=None) -> Dict:
        topic_id, post_id = self._resolve_key(key)
        if not topic_id:
            logger.info(f'No storage "{key}" found.')
            return default or {}
        if not post_id:
            post_id = self.client.posts(topic_id)["post_stream"]["posts"][0]["id"]
            self._storage_ids[key] = topic_id, post_id
        post = self.client.single_post(post_id)
        if post["yours"] is not True:
            raise DiscourseStorageError(
                f'The "STORAGE_{key}" was not created by ourself (post_id: {post_id})'
            )
        return yaml.safe_load(post["raw"])

    def put(self, key, value):
        data = yaml.safe_dump(value)
        topic_id, post_id = self._resolve_key(key)
        if not topic_id:
            logger.info(
                f'No storage "{key}" found. Creating a new storage by sending a message to ourself'
            )
            res = self.client.create_post(
                data,
                title=f"STORAGE_{key}",
                archetype="private_message",
                target_recipients=self.client.api_username,
            )
            self._storage_ids[key] = res.get("topic_id"), res.get("id")
        else:
            self.client.update_post(post_id, data)
