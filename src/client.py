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
        page = 0
        while True:
            logger.info(f"Loading page {page} for initializing DiscourseStorage")
            messages = self.client.private_messages_sent(page=page)
            topics = messages["topic_list"]["topics"] if messages else []
            if not topics:
                break
            # Remove messages with participants
            # The config is only safe to be assumed when created by ourself
            topics = [
                t
                for t in topics
                if len(t["participants"]) == 0 and t["title"].startswith("STORAGE_")
            ]
            for topic in topics:
                key = topic["title"].replace("STORAGE_", "")
                # first is topic id, second is post id. Be lazy and fetch the post id later
                self._storage_ids[key] = topic["id"], None
                logger.info(
                    f'Topic id "{topic["id"]}" contains storage for key "{key}"'
                )
            page += 1

    def get(self, key, default=None) -> Dict:
        topic_id, post_id = self._storage_ids.get(key, (None, None))
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
        if key not in self._storage_ids:
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
            topic_id, post_id = self._storage_ids[key]
            if not post_id:
                post_id = self.client.posts(topic_id)["post_stream"]["posts"][0]["id"]
                self._storage_ids[key] = topic_id, post_id
            self.client.update_post(post_id, data)
