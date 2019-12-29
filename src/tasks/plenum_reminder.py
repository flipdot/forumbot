import logging

from client import DiscourseStorageClient

from datetime import timedelta, datetime
from typing import List, Optional
import re
from dateutil.parser import parse
from constants import DISCOURSE_HOST


def extract_plenum_date_from_topic(topic: dict) -> Optional[datetime]:
    extracted_date = re.search(r'\d{4}-\d{2}-\d{2}', topic['title'])
    if not extracted_date:
        return None

    return parse(extracted_date.group())


def filter_non_extractable_dates(topics: List[dict]) -> List[dict]:
    return [topic for topic in topics if extract_plenum_date_from_topic(topic)]


def latest_topic(topics: List[dict]) -> Optional[dict]:
    dated_topics = filter_non_extractable_dates(topics)
    if not dated_topics:
        return None

    latest = dated_topics[0]
    latest_date = extract_plenum_date_from_topic(latest)
    for topic in dated_topics:
        date = extract_plenum_date_from_topic(topic)
        if date < latest_date:
            continue

        latest = topic
        latest_date = date

    return latest


def send_private_message(client: DiscourseStorageClient, username: str, title: str, message: str):
    client.create_post(message, title=title, archetype='private_message',
                       target_usernames=username)


PLENUM_REMINDER_KEY = 'plenum_reminder_v9'


def plenum_announced(client: DiscourseStorageClient, plenum_date: datetime) -> bool:
    current_storage = client.storage.get(PLENUM_REMINDER_KEY)
    if plenum_date not in current_storage:
        return False

    return True


def mark_plenum_announced(client: DiscourseStorageClient, plenum_date: datetime) -> None:
    current_storage = client.storage.get(PLENUM_REMINDER_KEY)

    current_storage[plenum_date] = 'announced'

    client.storage.put(PLENUM_REMINDER_KEY, current_storage)


def is_day_before_plenum(date: datetime) -> bool:
    day_before_plenum = date-timedelta(1)

    if datetime.now() != day_before_plenum.date():
        return False

    return True


PLENUM_NOTIFICATION_GROUP_NAME = 'notify_plena'

TOPIC_LINK_BASE = DISCOURSE_HOST + '/t/'


def main(client: DiscourseStorageClient) -> None:
    topics = client.category_topics('orga/plena')['topic_list']['topics']

    latest = latest_topic(topics)
    if not latest:
        return

    extracted_plenum_date = extract_plenum_date_from_topic(latest)
    if not extracted_plenum_date:
        logging.info(f'Failed to extract date from topic: {latest["title"]}')
        return

    if not is_day_before_plenum(extracted_plenum_date):
        return

    if plenum_announced(client, extracted_plenum_date):
        return

    send_private_message(
        client, PLENUM_NOTIFICATION_GROUP_NAME, f'Plenum reminder: {extracted_plenum_date}',
        'Morgen ist Plenum \\o/\n'
        f'{TOPIC_LINK_BASE + latest["id"]}')

    mark_plenum_announced(client, extracted_plenum_date)

    logging.info(f'Announed plenun: {extracted_plenum_date}')
