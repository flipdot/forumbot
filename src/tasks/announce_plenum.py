import logging

from pydiscourse import DiscourseClient

from utils import render
from datetime import timedelta, datetime
from itertools import count
from typing import Tuple, List
import re


def get_next_plenum_date(now: datetime) -> Tuple[datetime, timedelta]:
    next_days = (now + timedelta(days=i) for i in count())
    first_sundays = (x for x in next_days if x.weekday() == 6 and x.day <= 7)
    plenum_date = next(first_sundays)
    delta = plenum_date - now
    return plenum_date, delta


def topic_exists(title: str, topics: List[str]):
    # Use the first 8 chars from the title, e.g: 2019-10-
    # Then, there need to come any two digits (\d{2} - the formatting is a bit fucked up since we use formatstrings),
    # followed by anything, as long as "plenum" appears anywhere
    pattern = re.compile(fr'^{title[:8]}\d{{2}} .*plenum.*$', re.IGNORECASE)
    matches = [pattern.search(t) for t in topics]
    return any(matches)


def main(client: DiscourseClient) -> None:
    now = datetime.now()
    plenum_date, delta = get_next_plenum_date(now)
    if delta.days > 9:
        logging.info(
            f'Next plenum is too far in the future ({delta.days} days). Aborting.'
        )
        return
    title = plenum_date.strftime('%Y-%m-%d Plenum')
    topics = [
        x['title'] for x in client.category_topics('orga/plena')['topic_list']['topics']
    ]

    if topic_exists(title, topics):
        logging.info(f'"{title}" was already announced. Aborting.')
        return

    post_content = render('plenum.md', plenum_date=plenum_date)

    # Category 23 == 'orga/plena'. But we must use the id here. D'oh!
    client.create_post(post_content, category_id=23, title=title)
    logging.info(f'Topic "{title}" created.')
