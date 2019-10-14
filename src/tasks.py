import logging
from datetime import datetime

from pydiscourse import DiscourseClient

from utils import render, get_next_plenum_date, topic_exists


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

    if topic_exists(title, topics):
        logging.info(f'"{title}" was already announced. Aborting.')
        return

    post_content = render("plenum.md", plenum_date=plenum_date)

    # Category 23 == 'orga/plena'. But we must use the id here. D'oh!
    client.create_post(post_content, category_id=23, title=title)
    logging.info(f'Topic "{title}" created.')
