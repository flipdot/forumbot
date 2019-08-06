import logging
from datetime import datetime, timedelta
from itertools import count
from typing import Tuple

from pydiscourse import DiscourseClient

from utils import render


def get_next_plenum_date(now: datetime) -> Tuple[datetime, timedelta]:
    next_days = (now + timedelta(days=i) for i in count())
    first_sundays = (x for x in next_days if x.weekday() == 6 and x.day <= 7)
    plenum_date = next(first_sundays)
    delta = plenum_date - now
    return plenum_date, delta


def announce_plenum(client: DiscourseClient) -> None:
    now = datetime.now()
    plenum_date, delta = get_next_plenum_date(now)
    if delta.days > 7:
        logging.info(
            f"Next plenum is too far in the future ({delta.days} days). Aborting."
        )
        return
    title = plenum_date.strftime("%Y-%m-%d Plenum")
    topics = [
        x["title"] for x in client.category_topics("orga/plena")["topic_list"]["topics"]
    ]
    if title in topics:
        logging.info(f'"{title}" was already announced. Aborting.')
        return

    post_content = render("plenum.md", plenum_date=plenum_date)

    # Category 23 == 'orga/plena'. But we must use the id here. D'oh!
    client.create_post(post_content, category_id=23, title=title)
    logging.info(f'Topic "{title}" created.')
