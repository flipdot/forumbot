import logging

from client import DiscourseStorageClient
from constants import DEBUG, CATEGORY_ID_MAPPING
from tasks.plenum import (
    get_next_plenum_date,
    topic_exists,
    PAD_BASE_URL,
    PROTOCOL_PLACEHOLDER,
    PLENUM_CATEGORY_NAME,
)
from utils import render
from datetime import datetime
import pytz
import requests


def main(client: DiscourseStorageClient) -> None:
    now = datetime.now(pytz.timezone("Europe/Berlin"))
    plenum_date, delta = get_next_plenum_date(now)
    if delta.days > 27:
        logging.info(
            f"Next plenum is too far in the future ({delta.days} days). Aborting."
        )
        return
    title = plenum_date.strftime("%Y-%m-%d Plenum")
    topics = [
        x["title"]
        for x in client.category_topics(PLENUM_CATEGORY_NAME)["topic_list"]["topics"]
    ]

    if topic_exists(title, topics):
        logging.info(f'"{title}" was already announced. Aborting.')
        return

    plenum_topics = client.storage.get("NEXT_PLENUM_TOPICS") or [
        {"title": "Dein Thema", "author": "flipbot"}
    ]
    pad_template = render(
        "plenum_pad_template.md", plenum_date=plenum_date, topics=plenum_topics
    ).encode("utf-8")
    res = requests.post(
        PAD_BASE_URL + "/new",
        data=pad_template,
        headers={
            "Content-Type": "text/markdown; charset=utf-8",
        },
    )
    if res.status_code != 200:
        logging.error("Could not generate a new pad")
        return
    pad_url = res.url
    mention = "AT_vertrauensstufe_0" if DEBUG else "@vertrauensstufe_0"
    post_content = render(
        "plenum.md",
        plenum_date=plenum_date,
        pad_url=pad_url,
        PROTOCOL_PLACEHOLDER=PROTOCOL_PLACEHOLDER,
        mention=mention,
    )

    category_id = CATEGORY_ID_MAPPING[PLENUM_CATEGORY_NAME]
    client.create_post(post_content, category_id=category_id, title=title)
    logging.info(f'Topic "{title}" created.')
