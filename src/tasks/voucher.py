import logging
import re
from datetime import datetime
from venv import logger
import random

from pydiscourse import DiscourseClient

import constants
from client import DiscourseStorageClient

# custom types
# TypedDict is only available since python 3.8
# class VoucherConfigElement(TypedDict):
#     voucher: str
#     owner: Optional[str]
#     message_id: Optional[int]
#     persons: Optional[int]
from typing import Dict, List, Optional

from utils import render

VoucherConfigElement = Dict

VoucherConfig = List[VoucherConfigElement]


def handle_private_message_bedarf(
    client: DiscourseStorageClient, topic, posts, posts_content
):
    persons = re.search(r"\d+", posts_content)
    if not persons:
        persons = 1
    else:
        persons = int(persons[0])

    data = client.storage.get("voucher")
    queue = data.get("queue", [])
    name = posts["post_stream"]["posts"][0]["username"]

    # Search for the user in the queue, update the number of persons
    for entry in queue:
        if entry["name"] == name:
            entry["persons"] = persons
            break
    else:
        queue.append(
            {
                "name": name,
                "persons": persons,
            }
        )
    client.storage.put("voucher", data)
    # send a confirmation to the user
    client.create_post(
        "Alles klar! Ich habe dich in die Liste aufgenommen.",
        topic_id=topic["id"],
    )


def handle_private_message_voucher_list(
    client: DiscourseStorageClient, topic, posts, posts_content
):
    received_voucher = set(re.findall(r"CHAOS[a-zA-Z0-9]+", posts_content))

    if not received_voucher:
        logger.error("Got a voucher list, but no vouchers were found")
        client.create_post(
            "Es tut mir wirklich leid, aber ich konnte keine Voucher in deiner Nachricht finden. "
            "Ich suche nach Vouchern mit diesem Regex: `CHAOS[a-zA-Z0-9]+`. "
            "Vielleicht hat sich das Format geändert? Dann bräuchte ich ein Update.",
            topic_id=topic["id"],
        )
        return

    data = client.storage.get("voucher")

    if data["voucher"]:
        logger.error("Voucher list already exists. Is somebody trolling us?")
        client.create_post(
            "Es existiert bereits eine Voucher-Liste. Ich kann nur eine Liste verwalten.",
            topic_id=topic["id"],
        )
        return

    logging.info("Saving new vouchers to storage")
    data["voucher"] = [
        {
            "voucher": v,
            "owner": None,
            "old_owner": posts["post_stream"]["posts"][0]["username"],
            "message_id": None,
            "persons": None,
            "received_at": None,
        }
        for v in received_voucher
    ]
    # shuffle queue for fairness
    random.shuffle(data["queue"])

    client.storage.put("voucher", data)
    client.create_post(
        f"Danke für die Liste! Ich habe {len(received_voucher)} Voucher gefunden abgespeichert. "
        f"Ich werde sie nun an die Interessenten verteilen.",
        topic_id=topic["id"],
    )


def private_message_handler(client: DiscourseStorageClient, topic, posts) -> None:
    posts_content = posts["post_stream"]["posts"][-1]["cooked"]

    bedarf_strings = ["voucher-bedarf", "voucherbedarf", "voucher bedarf"]

    if any(s in posts_content.lower() for s in bedarf_strings):
        # We received a message with a voucher request
        handle_private_message_bedarf(client, topic, posts, posts_content)
        return

    if "voucher-liste" in topic["title"].lower():
        handle_private_message_voucher_list(client, topic, posts, posts_content)
        return


def get_username(voucher: VoucherConfigElement) -> Optional[str]:
    owner = voucher["owner"]
    return re.search(r"@([^ ]+)", owner)[1] if owner else None


def send_voucher_to_user(client: DiscourseClient, voucher: VoucherConfigElement):
    if voucher["message_id"]:
        raise ValueError("Voucher already sent")
    username = get_username(voucher)
    message_content = render("voucher_message.md", voucher=voucher)
    logging.info(f"Sending voucher to {username}")
    res = client.create_post(
        message_content,
        title="Dein 36C3 Voucher",
        archetype="private_message",
        target_usernames=username,
    )
    message_id = res.get("topic_id")
    logging.info(f"Sent, message_id is {message_id}")
    voucher["message_id"] = message_id
    voucher["received_at"] = datetime.now()


def send_message_to_user(
    client: DiscourseClient, voucher: VoucherConfigElement, message: str
) -> None:
    username = get_username(voucher)
    message_id = voucher.get("message_id")
    if not message_id:
        return
    logging.info(f"Sending message to {username} (Thread {message_id})")
    client.create_post(message, topic_id=message_id)


def check_for_returned_voucher(
    client: DiscourseClient, voucher: VoucherConfigElement
) -> Optional[str]:
    message_id = voucher["message_id"]
    posts = client.posts(message_id)
    user_posts = [
        post for post in posts["post_stream"]["posts"] if post["name"] != "flipbot"
    ]
    user_posts_content = " ".join([p["cooked"] for p in user_posts])
    new_voucher = re.search(r"CHAOS[a-zA-Z0-9]+", user_posts_content)
    if new_voucher:
        return new_voucher[0]


# TODO: think hard about maintaining the correct state. Not like this.
# def update_queue(client: DiscourseStorageClient):
#     data = client.storage.get('voucher')
#     topic_id = data.get('queue_topic')
#     queue_posts = [p for p in client.posts(topic_id)['post_stream']['posts'][0:] if not p['yours']]
#     for post in queue_posts:
#         pprint(post)
#         usernames = re.findall(r'@([^ ]+)', post['cooked'])
#         print(usernames)
#     import sys
#     sys.exit()


def get_topic(title: str, topics):
    for t in topics:
        if title == t["title"]:
            return t
    return None


def create_voucher_topic(client: DiscourseStorageClient, title: str) -> None:
    logging.info(f"Creating new voucher topic: {title}")

    category_id = constants.CATEGORY_ID_MAPPING[constants.CCC_CATEGORY_NAME]

    key = f"voucher_thread_for_{datetime.now().year}_created"
    if client.storage.get(key):
        # failsafe: we should not create the thread twice,
        # and not accidentally overwrite the voucher list
        raise ValueError("Voucher thread already created")
    client.storage.put("voucher", {"voucher": [], "queue": []})

    content = render_post_content(client.storage.get("voucher"))
    client.create_post(content, category_id=category_id, title=title)
    client.storage.put(key, "Storage for this year was created")


def update_voucher_topic(client: DiscourseStorageClient, post_id: int) -> None:
    content = render_post_content(client.storage.get("voucher"))
    client.update_post(post_id, content)


def render_post_content(data: dict) -> str:
    vouchers = data.get("voucher", [])
    queue = data.get("queue", [])

    return render(
        "voucher_announcement.md",
        vouchers=vouchers,
        queue=queue,
        total_persons_in_queue=sum([entry["persons"] for entry in queue]),
    )


def main(client: DiscourseStorageClient) -> None:
    # voucher only relevant in october, november and maybe december
    now = datetime.now()
    if now.month not in [10, 11, 12]:
        logging.info("Not voucher season")
        return

    topics = client.category_topics(constants.CCC_CATEGORY_NAME)["topic_list"]["topics"]

    # assuming the number increases by one each year and
    # that we don't get another pandemic
    congress_number = now.year - 1986
    title = f"Voucher {congress_number}C3"

    if topic := get_topic(title, topics):
        topic_posts = client.topic_posts(topic["id"])
        post = topic_posts["post_stream"]["posts"][0]
        update_voucher_topic(client, post["id"])
    else:
        create_voucher_topic(client, title)

    return

    data = client.storage.get("voucher")
    for voucher in data.get("voucher", []):
        if not voucher["owner"]:
            queue = data.get("queue")
            if not queue or type(queue) is not list:
                continue
            voucher["owner"] = queue.pop(0)
        if voucher.get("message_id"):
            new_voucher_code = check_for_returned_voucher(client, voucher)
            if new_voucher_code:
                logging.info(f"Voucher returned by {get_username(voucher)}")
                send_message_to_user(
                    client,
                    voucher,
                    message=f'Prima, vielen Dank für "{new_voucher_code}"!',
                )

                old_owner = get_username(voucher)
                voucher["voucher"] = new_voucher_code
                voucher["owner"] = None
                voucher["old_owner"] = old_owner
                voucher["message_id"] = None
                voucher["persons"] = None
                voucher["received_at"] = None
        elif voucher["owner"]:
            send_voucher_to_user(client, voucher)

    post_content = render(
        "voucher_table.md",
        vouchers=data.get("voucher", []),
        queue=data.get("queue", []),
    )
    # TODO: voucher_table_post_id does not get saved. We need to create a post as soon as we received the voucher list
    client.update_post(data.get("voucher_table_post_id"), post_content)

    client.storage.put("voucher", data)
