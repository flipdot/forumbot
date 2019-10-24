import logging
from typing import Dict

from pydiscourse import DiscourseClient
import yaml


class DiscourseStorageClient(DiscourseClient):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.storage = DiscourseStorage(self)

    # TODO: Add this method upstream
    def private_messages_sent(self, username=None, **kwargs):
        if username is None:
            username = self.api_username
        return self._get(f'/topics/private-messages-sent/{username}.json', **kwargs)

    # TODO: Maybe add this method upstream, too? Allows us to get raw post content
    def single_post(self, post_id, **kwargs):
        return self._get(f'/posts/{post_id}.json', **kwargs)


class DiscourseStorage:
    """
    Uses a PM to itself to persist data. This way, we won't need to care about storage.
    """

    def __init__(self, client: DiscourseStorageClient):
        self.client = client
        self._storage_ids = {}
        page = 0
        while True:
            messages = self.client.private_messages_sent(page=page)
            topics = messages['topic_list']['topics']
            if not topics:
                break
            # Remove messages with participants
            # The config is only safe to be assumed when created by ourself
            topics = [t for t in topics if len(t['participants']) == 0 and t['title'].startswith('STORAGE_')]
            for topic in topics:
                key = topic['title'].replace('STORAGE_', '')
                # first is topic id, second is post id. Be lazy and fetch the post id later
                self._storage_ids[key] = topic['id'], None
            page += 1

    def get(self, key) -> Dict:
        topic_id, post_id = self._storage_ids.get(key, (None, None))
        if not topic_id:
            logging.info(f'No storage "{key}" found.')
            return {}
        if not post_id:
            post_id = self.client.posts(topic_id)['post_stream']['posts'][0]['id']
            self._storage_ids[key] = topic_id, post_id
        return yaml.safe_load(self.client.single_post(post_id)['raw'])

    def put(self, key, value):
        data = yaml.safe_dump(value)
        if key not in self._storage_ids:
            logging.info(f'No storage "{key}" found. Creating a new storage by sending a message to ourself')
            res = self.client.create_post(data, title=f'STORAGE_{key}', archetype='private_message',
                                          target_usernames=self.client.api_username)
            self._storage_ids[key] = res.get('topic_id'), res.get('id')
        else:
            topic_id, post_id = self._storage_ids[key]
            if not post_id:
                post_id = self.client.posts(topic_id)['post_stream']['posts'][0]['id']
                self._storage_ids[key] = topic_id, post_id
            self.client.update_post(post_id, data)
