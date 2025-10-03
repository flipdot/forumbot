import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
import random

from pydiscourse import DiscourseClient
from pydiscourse.exceptions import DiscourseClientError

import constants
from client import DiscourseStorageClient
from gantt import plot_gantt_chart
from babel.dates import format_date

# custom types
# TypedDict is only available since python 3.8
# class VoucherConfigElement(TypedDict):
#     voucher: str
#     owner: Optional[str]
#     message_id: Optional[int]
#     persons: Optional[int]
from typing import Dict, List, Optional

from utils import render

logger = logging.getLogger(__name__)
VoucherConfigElement = Dict

VoucherConfig = List[VoucherConfigElement]


def handle_private_message_bedarf(
    client: DiscourseStorageClient, topic, posts, posts_content
):
    persons = re.search(r"\d+", posts_content)
    if persons is None:
        persons = re.search(r"\d+", topic["title"])
    if persons is None:
        persons = 1
    else:
        persons = int(persons[0])

    data = client.storage.get("voucher")
    queue = data.get("queue", [])
    name = posts["post_stream"]["posts"][-1]["username"]

    if persons == 0:
        for entry in queue:
            if entry["name"] == name:
                queue.remove(entry)
                client.storage.put("voucher", data)
                client.create_post(
                    "0 Voucher also? Okay, ich habe dich aus der Warteschlange entfernt.",
                    topic_id=topic["id"],
                )
                break
        else:
            client.create_post(
                'Ich habe "0 Voucher" verstanden und wollte dich aus der Warteschlange entfernen, '
                "aber ich konnte dich nicht finden. Vielleicht hast du dich vertippt?\n"
                "\n"
                "Falls du bereits einen Voucher erhalten hast und ihn zurückgeben möchtest, "
                "öffne den Thread **in dem ich dir den Voucher bereits zugesendet habe**, "
                "und schreibe mir einfach den Voucher-Code zurück.",
                topic_id=topic["id"],
            )
        return

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
        f"Alles klar! Ich habe dich für {persons} Voucher vorgemerkt. Falls du es dir anders überlegst, "
        'schreibe mir "VOUCHER-BEDARF 0" und ich entferne dich aus der Warteschlange.',
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
            "history": [],
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


def handle_private_message_voucher_phase_range(
    client: DiscourseStorageClient, topic, posts, posts_content
):
    phase_range = re.search(
        r"(\d{4}-\d{2}-\d{2}) bis (\d{4}-\d{2}-\d{2})", posts_content
    )
    if not phase_range:
        client.create_post(
            "Ich konnte keinen Zeitraum in deiner Nachricht finden. "
            "Nutze das Format `YYYY-MM-DD bis YYYY-MM-DD`.",
            topic_id=topic["id"],
        )
        return

    data = client.storage.get("voucher")

    if "voucher_phase_range" not in data:
        data["voucher_phase_range"] = {}

    parsed_ranges = {
        "start": datetime.fromisoformat(phase_range[1]),
        "end": datetime.fromisoformat(phase_range[2]),
    }

    formatted_ranges = {
        "start": format_date(parsed_ranges["start"], format="long", locale="de_DE"),
        "end": format_date(parsed_ranges["end"], format="long", locale="de_DE"),
    }

    data["voucher_phase_range"][get_congress_id()] = {
        "start": phase_range[1],
        "end": phase_range[2],
    }

    client.storage.put("voucher", data)
    client.create_post(
        f"Danke für die Information! Ich schreibe in meinen Post, dass die Voucher "
        f"vom {formatted_ranges['start']} bis {formatted_ranges['end']} genutzt werden können.",
        topic_id=topic["id"],
    )
    update_history_image(client)


def handle_private_message_voucher_exhausted_at(
    client: DiscourseStorageClient, topic, posts, posts_content
):
    exhausted_at = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2})", posts_content)
    if not exhausted_at:
        client.create_post(
            "Ich konnte keinen Zeitpunkt in deiner Nachricht finden. "
            "Nutze das Format `YYYY-MM-DD HH:MM`.",
            topic_id=topic["id"],
        )
        return

    data = client.storage.get("voucher")

    if (
        "voucher_phase_range" not in data
        or get_congress_id() not in data["voucher_phase_range"]
    ):
        client.create_post(
            "Ich konnte keinen Zeitraum für die Voucher finden. "
            "Bitte gib zuerst den Zeitraum mittels `VOUCHER-PHASE YYYY-MM-DD bis YYYY-MM-DD` an, bevor du mir "
            "mitteilst, dass die Voucher erschöpft sind.",
            topic_id=topic["id"],
        )
        return

    start_date = datetime.fromisoformat(
        data["voucher_phase_range"][get_congress_id()]["start"]
    )
    end_date = datetime.fromisoformat(
        data["voucher_phase_range"][get_congress_id()]["end"]
    )

    parsed_exhausted_at = datetime.fromisoformat(exhausted_at[1])

    if parsed_exhausted_at < start_date or parsed_exhausted_at > end_date:
        client.create_post(
            "Der Zeitpunkt, an dem die Voucher erschöpft sein sollen, liegt nicht innerhalb des "
            "Zeitraums, in dem die Voucher genutzt werden können. Bitte gib einen Zeitpunkt "
            "zwischen dem Start- und Enddatum der Voucherphase an.",
            topic_id=topic["id"],
        )
        return

    data["voucher_phase_range"][get_congress_id()]["exhausted_at"] = exhausted_at[1]

    client.storage.put("voucher", data)
    client.create_post(
        "Danke für die Information! Ich aktualisiere die Grafik in meinem Post.",
        topic_id=topic["id"],
    )
    update_history_image(client)


def private_message_handler(client: DiscourseStorageClient, topic, posts) -> bool:
    posts_content = posts["post_stream"]["posts"][-1]["cooked"]

    bedarf_strings = ["voucher-bedarf", "voucherbedarf", "voucher bedarf"]

    if any(s in posts_content.lower() for s in bedarf_strings) or any(
        s in topic["title"].lower() for s in bedarf_strings
    ):
        handle_private_message_bedarf(client, topic, posts, posts_content)
        return True

    gesamtbedarf_strings = [
        "voucher-gesamt-bedarf-gemeldet",
        "voucher-gesamtbedarf-gemeldet",
        "voucher gesamt bedarf gemeldet",
        "voucher gesamtbedarf gemeldet",
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

    voucher_phase_range_strings = [
        "voucher-phase",
        "voucherphase",
    ]

    if any(s in posts_content.lower() for s in voucher_phase_range_strings):
        handle_private_message_voucher_phase_range(client, topic, posts, posts_content)
        return True

    voucher_exhausted_at_strings = [
        "voucher-exhausted-at",
    ]

    if any(s in posts_content.lower() for s in voucher_exhausted_at_strings):
        handle_private_message_voucher_exhausted_at(client, topic, posts, posts_content)
        return True

    if re.search(r"CHAOS[a-zA-Z0-9]+", posts_content):
        # will be handled by the voucher distribution function,
        # as it knows which thread ID is related to which voucher.
        # Just return True to not return a "I didn't understand your message" error message
        # to the user
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
    now = datetime.now()
    voucher["received_at"] = now
    voucher["history"].append(
        {
            "username": voucher["owner"],
            "received_at": now.isoformat(),
            "persons": voucher["persons"],
        }
    )


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
    data["total_persons_reported"] = None
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

    # now = datetime.now()
    for v in vouchers:
        if not v["received_at"]:
            continue
        # delta = v["received_at"] - now
        # v["received_delta"] = babel.dates.format_timedelta(
        #     delta, locale="de_DE", add_direction=True
        # )

    image_url = (
        data.get("voucher_history_image", {})
        .get(get_congress_id(), {})
        .get("short_url")
    )

    voucher_phase_range = data.get("voucher_phase_range", {}).get(get_congress_id(), {})
    if ts := voucher_phase_range.get("start"):
        voucher_phase_start = format_date(
            datetime.fromisoformat(ts), format="long", locale="de_DE"
        )
    else:
        voucher_phase_start = None
    if ts := voucher_phase_range.get("end"):
        voucher_phase_end = format_date(
            datetime.fromisoformat(ts), format="long", locale="de_DE"
        )
    else:
        voucher_phase_end = None
    return render(
        "voucher_announcement.md",
        vouchers=vouchers,
        queue=queue,
        total_persons_in_queue=sum([entry["persons"] for entry in queue]),
        total_persons_reported=total_persons_reported,
        bot_name=constants.DISCOURSE_CREDENTIALS["api_username"],
        image_url=image_url,
        voucher_phase_start=voucher_phase_start,
        voucher_phase_end=voucher_phase_end,
        voucher_exhausted_at=voucher_phase_range.get("exhausted_at"),
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
            voucher["retry_counter"] = 0

        if not voucher.get("message_id") and voucher["owner"]:
            # Voucher was assigned to someone but they haven't received it yet
            try:
                send_voucher_to_user(client, voucher)
            except DiscourseClientError:
                logging.exception(
                    f"Failed to send voucher {voucher['voucher']} to {voucher['owner']}"
                )
                voucher["retry_counter"] = voucher.get("retry_counter", 0) + 1
                if voucher["retry_counter"] >= 10:
                    logging.error(
                        f"Giving up sending voucher {voucher['voucher']} to {voucher['owner']} after 10 attempts"
                    )
                    voucher["owner"] = None
                    voucher["retry_counter"] = 0

    client.storage.put("voucher", data)


def get_congress_id(now: datetime | None = None) -> str:
    # assuming the number increases by one each year and
    # that we don't get another pandemic
    if not now:
        now = datetime.now()
    congress_number = now.year - 1986
    return f"{congress_number}C3"


def update_history_image(client: DiscourseStorageClient) -> None:
    now = datetime.now()
    if now.month not in [10, 11, 12]:
        logging.info("Not voucher season. Skipping.")
        return

    data = client.storage.get("voucher", {})

    if not data.get("voucher"):
        return

    phase_range = data.get("voucher_phase_range", {}).get(get_congress_id(), {})
    if ts := phase_range.get("start"):
        start_date = datetime.fromisoformat(ts).date()
    else:
        return

    if ts := phase_range.get("end"):
        end_date = datetime.fromisoformat(ts).date()
    else:
        return

    if start_date > (now.date() + timedelta(days=1)):
        return

    if end_date < (now.date() - timedelta(days=3)):
        return

    if ts := phase_range.get("exhausted_at"):
        exhausted_at = datetime.fromisoformat(ts)
    else:
        exhausted_at = None
    fig = plot_gantt_chart(
        data["voucher"],
        start_date=start_date,
        end_date=end_date,
        exhausted_at=exhausted_at,
    )
    path = Path("gantt.png")

    fig.savefig(path)
    res = client.upload_image(path, "png", synchronous=True)

    if "voucher_history_image" not in data:
        data["voucher_history_image"] = {}

    if "short_url" in res:
        data["voucher_history_image"][get_congress_id()] = res
    else:
        logger.error(f"Unexpected response from Discourse: {res}")

    client.storage.put("voucher", data)


def main(client: DiscourseStorageClient) -> None:
    # voucher only relevant in october, november and maybe december
    now = datetime.now()
    if now.month not in [10, 11, 12]:
        logging.info("Not voucher season. Skipping.")
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
