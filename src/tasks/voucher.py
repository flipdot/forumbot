import logging
import re
from datetime import datetime
from venv import logger
import random

import babel.dates
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
        persons = re.search(r"\d+", topic["title"])
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
        f"Alles klar! Ich habe dich für {persons} Voucher vorgemerkt.",
        topic_id=topic["id"],
    )


def handle_private_message_gesamtbedarf(
    client: DiscourseStorageClient, topic, posts, posts_content
):
    persons = re.search(r"\d+", posts_content)
    if not persons:
        client.create_post(
            "Ich konnte keine Anzahl an Personen in deiner Nachricht finden. "
            "Bitte gib an, wie viele Personen du den Organisatoren mitgeteilt hast.",
            topic_id=topic["id"],
        )
        return

    persons = int(persons[0])
    data = client.storage.get("voucher")
    if data.get("voucher"):
        client.create_post(
            "Wir haben doch schon Voucher erhalten. Ist jetzt ein bisschen spät für ne Abschätzung.",
            topic_id=topic["id"],
        )
        return
    if data.get("total_persons_reported"):
        client.create_post(
            "Es wurde bereits eine Anzahl an Personen gemeldet.",
            topic_id=topic["id"],
        )
        return
    data["total_persons_reported"] = persons

    # shuffle queue for fairness
    random.shuffle(data.get("queue", []))

    client.storage.put("voucher", data)
    client.create_post(
        f"Danke für die Information! Ich schreibe in meinen Post, dass du {persons} Personen "
        f"an die Congress Organisation gemeldet hast.",
        topic_id=topic["id"],
    )
    username = posts["post_stream"]["posts"][0]["username"]
    post_content = render(
        "voucher_gesamtbedarf_reported.md",
        reported_by=username,
        persons=persons,
        bot_name=constants.DISCOURSE_CREDENTIALS["api_username"],
    )

    client.create_post(
        post_content,
        topic_id=data["voucher_topics"][get_congress_id()],
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
    username = posts["post_stream"]["posts"][0]["username"]
    data["voucher"] = [
        {
            "voucher": v,
            "owner": None,
            "old_owner": username,
            "message_id": None,
            "persons": None,
            "received_at": datetime.now(),
        }
        for v in received_voucher
    ]

    client.storage.put("voucher", data)
    client.create_post(
        f"Danke für die Liste! Ich habe {len(received_voucher)} Voucher gefunden abgespeichert. "
        f"Ich werde sie nun an die Interessenten verteilen.",
        topic_id=topic["id"],
    )
    post_content = render(
        "voucher_list_received.md",
        reported_by=username,
        total_voucher=len(received_voucher),
        bot_name=constants.DISCOURSE_CREDENTIALS["api_username"],
    )
    client.create_post(
        post_content,
        topic_id=data["voucher_topics"][get_congress_id()],
    )


def private_message_handler(client: DiscourseStorageClient, topic, posts) -> bool:
    posts_content = posts["post_stream"]["posts"][-1]["cooked"]

    bedarf_strings = ["voucher-bedarf", "voucherbedarf", "voucher bedarf"]

    if any(s in posts_content.lower() for s in bedarf_strings) or any(
        s in topic["title"].lower() for s in bedarf_strings
    ):
        handle_private_message_bedarf(client, topic, posts, posts_content)
        return True

    gesamtbedarf_strings = [
        "voucher-gesamt-bedarf",
        "voucher-gesamtbedarf",
        "voucher gesamt bedarf",
        "voucher gesamtbedarf",
    ]

    if any(s in posts_content.lower() for s in gesamtbedarf_strings):
        handle_private_message_gesamtbedarf(client, topic, posts, posts_content)
        return True

    voucher_list_strings = [
        "voucher-list",
        "voucherlist",
        "voucher list",
    ]

    if any(s in topic["title"].lower() for s in voucher_list_strings):
        handle_private_message_voucher_list(client, topic, posts, posts_content)
        return True


def send_voucher_to_user(client: DiscourseClient, voucher: VoucherConfigElement):
    if voucher["message_id"]:
        raise ValueError("Voucher already sent")
    username = voucher["owner"]
    message_content = render("voucher_message.md", voucher=voucher)
    logging.info(f"Sending voucher to {username}")
    res = client.create_post(
        message_content,
        title=f"Dein {get_congress_id()} Voucher",
        archetype="private_message",
        target_recipients=username,
    )
    message_id = res.get("topic_id")
    logging.info(f"Sent, message_id is {message_id}")
    voucher["message_id"] = message_id
    voucher["received_at"] = datetime.now()


def send_message_to_user(
    client: DiscourseClient, voucher: VoucherConfigElement, message: str
) -> None:
    username = voucher["owner"]
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
        post
        for post in posts["post_stream"]["posts"]
        if post["username"] != constants.DISCOURSE_CREDENTIALS["api_username"]
    ]
    user_posts_content = " ".join([p["cooked"] for p in user_posts])
    new_voucher = re.search(r"CHAOS[a-zA-Z0-9]+", user_posts_content)
    if new_voucher:
        return new_voucher[0]


def get_topic(title: str, topics):
    for t in topics:
        if title == t["title"]:
            return t
    return None


def create_voucher_topic(
    client: DiscourseClient,
    data: dict,
    title: str,
    congress_id: str,
) -> None:
    logging.info(f"Creating new voucher topic: {title}")

    category_id = constants.CATEGORY_ID_MAPPING[constants.CCC_CATEGORY_NAME]

    data["voucher"] = []
    data["queue"] = []
    if "voucher_topics" not in data:
        data["voucher_topics"] = {}

    content = render_post_content(data)
    res = client.create_post(content, category_id=category_id, title=title)
    topic_id = res["topic_id"]

    data["voucher_topics"][congress_id] = topic_id


def update_voucher_topic(client: DiscourseClient, data: dict, post_id: int) -> None:
    content = render_post_content(data)
    client.update_post(post_id, content)


def render_post_content(data: dict) -> str:
    vouchers = data.get("voucher", [])
    queue = data.get("queue", [])
    total_persons_reported = data.get("total_persons_reported")

    now = datetime.now()
    for v in vouchers:
        if not v["received_at"]:
            continue
        delta = v["received_at"] - now
        v["received_delta"] = babel.dates.format_timedelta(
            delta, locale="de_DE", add_direction=True
        )

    return render(
        "voucher_announcement.md",
        vouchers=vouchers,
        queue=queue,
        total_persons_in_queue=sum([entry["persons"] for entry in queue]),
        total_persons_reported=total_persons_reported,
        bot_name=constants.DISCOURSE_CREDENTIALS["api_username"],
    )


def process_voucher_distribution(client: DiscourseStorageClient):
    data = client.storage.get("voucher", {"voucher": [], "queue": []})
    for voucher in data.get("voucher", []):
        if voucher.get("message_id"):
            # The voucher is already assigned to someone. Check if they returned it
            new_voucher_code = check_for_returned_voucher(client, voucher)
            if new_voucher_code:
                logging.info(f"Voucher returned by {voucher['owner']}")
                send_message_to_user(
                    client,
                    voucher,
                    message=f'Prima, vielen Dank für "{new_voucher_code}"!',
                )

                voucher["voucher"] = new_voucher_code
                voucher["old_owner"] = voucher["owner"]
                voucher["owner"] = None
                voucher["message_id"] = None
                voucher["persons"] = None
                voucher["received_at"] = datetime.now()
                voucher["persons"] = None

        if not voucher["owner"]:
            # The voucher is available. Assign it to the next person in the queue
            queue = data.get("queue")
            if not queue or type(queue) is not list:
                continue
            next_item = queue.pop(0)
            voucher["owner"] = next_item["name"]
            voucher["persons"] = next_item["persons"]

        if not voucher.get("message_id") and voucher["owner"]:
            # Voucher was assigned to someone but they haven't received it yet
            send_voucher_to_user(client, voucher)

    client.storage.put("voucher", data)


def get_congress_id(now: datetime | None = None) -> str:
    # assuming the number increases by one each year and
    # that we don't get another pandemic
    if not now:
        now = datetime.now()
    congress_number = now.year - 1986
    return f"{congress_number}C3"


def main(client: DiscourseStorageClient) -> None:
    # voucher only relevant in october, november and maybe december
    now = datetime.now()
    if now.month not in [10, 11, 12]:
        logging.info("Not voucher season")
        return

    process_voucher_distribution(client)

    topics = client.category_topics(constants.CCC_CATEGORY_NAME)["topic_list"]["topics"]

    congress_id = get_congress_id(now)
    title = f"Voucher {congress_id}"

    data = client.storage.get("voucher", {})
    if "voucher_topics" not in data:
        data["voucher_topics"] = {}
    voucher_topics = data["voucher_topics"]
    topic_id = voucher_topics.get(congress_id)

    if not topic_id:
        if topic := get_topic(title, topics):
            voucher_topics[congress_id] = topic["id"]
            topic_id = topic["id"]

    if topic_id:
        topic_posts = client.topic_posts(topic_id)
        post = topic_posts["post_stream"]["posts"][0]
        update_voucher_topic(client, data, post["id"])
    else:
        create_voucher_topic(client, data, title, congress_id)

    client.storage.put("voucher", data)
