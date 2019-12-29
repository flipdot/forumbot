import logging

from client import DiscourseStorageClient

from datetime import timedelta, datetime
from typing import List, Optional
import re
from dateutil.parser import parse


def extract_plenum_date_from_topic(topic: dict) -> Optional[datetime]:
    extracted_date = re.search(r'\d{4}-\d{2}-\d{2}', topic["title"])
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


USERS_TO_BE_NOTIFIED = ["Lenny"]


def get_users_to_be_notified(client: DiscourseStorageClient, plenum_date: datetime) -> List[str]:
    # TODO: build private message based signup
    return [user for user in USERS_TO_BE_NOTIFIED if not is_user_notified(client, user, plenum_date)]


def is_user_notified(client: DiscourseStorageClient, username: str, plenum_date: datetime) -> bool:
    current_storage = client.storage.get(PLENUM_REMINDER_KEY)
    if plenum_date not in current_storage:
        return False

    if username not in current_storage[plenum_date]:
        return False

    return True


PLENUM_REMINDER_KEY = "plenum_reminder_v7"


def mark_user_notified(client: DiscourseStorageClient, username: str, plenum_date: datetime) -> None:
    current_storage = client.storage.get(PLENUM_REMINDER_KEY)
    if plenum_date not in current_storage:
        current_storage[plenum_date] = set()

    current_storage[plenum_date].add(username)

    client.storage.put(PLENUM_REMINDER_KEY, current_storage)


def is_day_before_plenum(date: datetime) -> bool:
    day_before_plenum = date-timedelta(1)

    if datetime.now() != day_before_plenum.date():
        return True

    return True


def main(client: DiscourseStorageClient) -> None:
    topics = client.category_topics('orga/plena')['topic_list']['topics']

    latest = latest_topic(topics)

    extracted_plenum_date = extract_plenum_date_from_topic(latest)
    if not is_day_before_plenum(extracted_plenum_date):
        return

    for user in get_users_to_be_notified(client, extracted_plenum_date):
        send_private_message(
            client, user, f"Plenum reminder: {extracted_plenum_date} @ 1800",
            "aa")

        mark_user_notified(client, user, extracted_plenum_date)
        logging.info(f'Notified: {user}')
