import base64
import logging
import re
import struct
from datetime import datetime, timedelta
from email.message import Message
from pathlib import Path
import random

import pytz
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

    data = client.storage.get("voucher", {"voucher": [], "queue": [], "demand": {}})
    demand = data.setdefault("demand", {})
    name = posts["post_stream"]["posts"][-1]["username"]

    if persons == 0:
        if name in demand:
            del demand[name]
            data["queue"] = [u for u in data.get("queue", []) if u != name]
            client.storage.put("voucher", data)
            client.create_post(
                "0 Voucher also? Okay, ich habe dich aus der Warteschlange entfernt.",
                topic_id=topic["id"],
            )
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

    demand[name] = persons
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
            "index": i,
            "voucher": v,
            "owner": None,
            "old_owner": username,
            "message_id": None,
            "persons": None,
            "received_at": datetime.now(pytz.timezone("Europe/Berlin")),
            "history": [],
        }
        for i, v in enumerate(received_voucher)
    ]

    client.storage.put("voucher", data)
    client.create_post(
        f"Danke für die Liste! Ich habe {len(received_voucher)} Voucher gefunden abgespeichert. "
        f"Ich werde sie nun an die Interessenten verteilen.",
        topic_id=topic["id"],
    )
    post_content = render(
        "voucher_list_received.md",
        reported_by=f"@{username}",
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
        "start": datetime.fromisoformat(phase_range[1]).astimezone(
            pytz.timezone("Europe/Berlin")
        ),
        "end": datetime.fromisoformat(phase_range[2]).astimezone(
            pytz.timezone("Europe/Berlin")
        ),
    }

    formatted_ranges = {
        "start": format_date(parsed_ranges["start"], format="long", locale="de_DE"),
        "end": format_date(parsed_ranges["end"], format="long", locale="de_DE"),
    }

    data["voucher_phase_range"][get_congress_id()] = {
        "start": parsed_ranges["start"],
        "end": parsed_ranges["end"],
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

    start_date = data["voucher_phase_range"][get_congress_id()]["start"]
    end_date = data["voucher_phase_range"][get_congress_id()]["end"]

    parsed_exhausted_at = datetime.fromisoformat(exhausted_at[1]).astimezone(
        pytz.timezone("Europe/Berlin")
    )

    if parsed_exhausted_at < start_date or parsed_exhausted_at > end_date:
        client.create_post(
            "Der Zeitpunkt, an dem die Voucher erschöpft sein sollen, liegt nicht innerhalb des "
            "Zeitraums, in dem die Voucher genutzt werden können. Bitte gib einen Zeitpunkt "
            "zwischen dem Start- und Enddatum der Voucherphase an.",
            topic_id=topic["id"],
        )
        return

    data["voucher_phase_range"][get_congress_id()]["exhausted_at"] = parsed_exhausted_at

    client.storage.put("voucher", data)
    client.create_post(
        "Danke für die Information! Ich aktualisiere die Grafik in meinem Post.",
        topic_id=topic["id"],
    )
    update_history_image(client)


def private_message_handler(client: DiscourseStorageClient, topic, posts) -> bool:
    posts_content = posts["post_stream"]["posts"][-1]["cooked"]
    username = posts["post_stream"]["posts"][-1]["username"]
    topic_id = topic["id"]

    if "VOUCHER_JETZT_EINLOESEN" in posts_content:
        data = client.storage.get("voucher")

        # Find if this topic belongs to an offer
        voucher_to_award = None
        for voucher in data.get("voucher", []):
            for offer in voucher.get("offered_to", []):
                if offer["message_id"] == topic_id and offer["username"] == username:
                    voucher_to_award = voucher
                    break
            if voucher_to_award:
                break

        if not voucher_to_award:
            # User sent the trigger in a random thread or they were not offered THIS voucher
            return False

        if voucher_to_award.get("owner"):
            # Voucher already gone (someone else accepted faster)
            client.create_post(
                "Dein Voucher ist ausgelaufen. Du erhältst eine Nachricht, wenn wieder ein Voucher verfügbar ist",
                topic_id=topic_id,
            )
            return True

        # Award the voucher
        voucher_to_award["owner"] = username
        # Removal from queue is needed
        data["queue"] = [u for u in data.get("queue", []) if u != username]

        # Send voucher code to THIS topic
        send_voucher_to_user(client, voucher_to_award, topic_id=topic_id)

        # Notify other people who had offers for this voucher
        for offer in voucher_to_award.get("offered_to", []):
            if offer["username"] != username:
                client.create_post(
                    "Dein Voucher ist ausgelaufen. Du erhältst eine Nachricht, wenn wieder ein Voucher verfügbar ist",
                    topic_id=offer["message_id"],
                )

        client.storage.put("voucher", data)
        return True

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


def decode_voucher_identifier(data: str) -> tuple[str, int, int]:
    data = data.strip().upper()

    if data.count("-") != 1:
        raise ValueError(
            "Invalid voucher identifier format: Expected two part identifier separated by a single hyphen"
        )

    congress_id, _, encoded_part = data.rpartition("-")

    if missing_padding := len(encoded_part) % 8:
        encoded_part += "=" * (8 - missing_padding)

    b32_decoded_data = base64.b32decode(encoded_part)
    try:
        index, history_length = struct.unpack(">BB", b32_decoded_data)
        return congress_id, index, history_length
    except struct.error as e:
        raise ValueError("Invalid voucher identifier format") from e


def encode_voucher_identifier(index: int, history_length: int, congress_id: str) -> str:
    try:
        encoded = (
            base64.b32encode(struct.pack(">BB", index, history_length))
            .rstrip(b"=")
            .decode()
            .lower()
        )
    except struct.error as e:
        raise ValueError("Index and history_length must be between 0 and 255") from e
    return f"{congress_id.lower()}-{encoded}"


def send_voucher_to_user(
    client: DiscourseClient,
    voucher: VoucherConfigElement,
    topic_id: Optional[int] = None,
):
    if voucher["message_id"]:
        raise ValueError("Voucher already sent")
    username = voucher["owner"]
    congress_id = get_congress_id()
    voucher_identifier = encode_voucher_identifier(
        voucher["index"], len(voucher["history"]) + 1, congress_id
    )
    voucher_ingress_email = f"bot+voucheringress-{voucher_identifier}@flipdot.org"
    message_content = render(
        "voucher_message.md",
        voucher=voucher,
        voucher_ingress_email=voucher_ingress_email,
    )
    logging.info(f"Sending voucher to {username}")
    if topic_id:
        client.create_post(
            message_content,
            topic_id=topic_id,
        )
        message_id = topic_id
    else:
        res = client.create_post(
            message_content,
            title=f"Dein {get_congress_id()} Voucher",
            archetype="private_message",
            target_recipients=username,
        )
        message_id = res.get("topic_id")

    logging.info(f"Sent, message_id is {message_id}")
    voucher["message_id"] = message_id
    now = datetime.now(pytz.timezone("Europe/Berlin"))
    voucher["received_at"] = now
    voucher["history"].append(
        {
            "username": voucher["owner"],
            "received_at": now.isoformat(),
        }
    )


def send_offer_to_user(
    client: DiscourseStorageClient, voucher: VoucherConfigElement, username: str
):
    message_content = render("voucher_offer.md")
    logging.info(f"Offering voucher to {username}")
    res = client.create_post(
        message_content,
        title=f"Dein {get_congress_id()} Voucher",
        archetype="private_message",
        target_recipients=username,
    )
    message_id = res.get("topic_id")
    logging.info(f"Offer sent, message_id is {message_id}")

    now = datetime.now(pytz.timezone("Europe/Berlin"))
    voucher.setdefault("offered_to", []).append(
        {
            "username": username,
            "offered_at": now.isoformat(),
            "message_id": message_id,
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
    data["demand"] = {}
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
    demand = data.get("demand", {})
    total_persons_reported = data.get("total_persons_reported")

    # Create alphabetically sorted demand list
    demand_list = [
        {"name": name, "count": count}
        for name, count in sorted(demand.items(), key=lambda item: item[0])
        if count > 0
    ]

    image_url = (
        data.get("voucher_history_image", {})
        .get(get_congress_id(), {})
        .get("short_url")
    )

    voucher_phase_range = data.get("voucher_phase_range", {}).get(get_congress_id(), {})
    if ts := voucher_phase_range.get("start"):
        voucher_phase_start = format_date(ts, format="long", locale="de_DE")
    else:
        voucher_phase_start = None
    if ts := voucher_phase_range.get("end"):
        voucher_phase_end = format_date(ts, format="long", locale="de_DE")
    else:
        voucher_phase_end = None

    return render(
        "voucher_announcement.md",
        vouchers=vouchers,
        queue=queue,
        demand_list=demand_list,
        total_persons_in_queue=(sum(demand.values()) + len(queue)),
        total_persons_reported=total_persons_reported,
        bot_name=constants.DISCOURSE_CREDENTIALS["api_username"],
        image_url=image_url,
        voucher_phase_start=voucher_phase_start,
        voucher_phase_end=voucher_phase_end,
        voucher_exhausted_at=voucher_phase_range.get("exhausted_at"),
    )


def process_voucher_distribution(client: DiscourseStorageClient):
    data = client.storage.get("voucher", {"voucher": [], "queue": [], "demand": {}})
    now = datetime.now(pytz.timezone("Europe/Berlin"))

    # Track who already has an active offer to avoid offering them multiple vouchers
    all_offered_users = set()
    for v in data.get("voucher", []):
        for offer in v.get("offered_to", []):
            all_offered_users.add(offer["username"])

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

                now = datetime.now(pytz.timezone("Europe/Berlin"))
                voucher["voucher"] = new_voucher_code
                voucher["old_owner"] = voucher["owner"]
                voucher["owner"] = None
                voucher["message_id"] = None
                voucher["history"][-1]["returned_at"] = now.isoformat()
                voucher["received_at"] = now

        if not voucher.get("owner"):
            # Check for active offers on this voucher
            offered_to = voucher.get("offered_to", [])
            last_offer = offered_to[-1] if offered_to else None

            needs_new_offer = False
            if not last_offer:
                needs_new_offer = True
            else:
                offered_at = datetime.fromisoformat(
                    last_offer["offered_at"]
                ).astimezone(pytz.timezone("Europe/Berlin"))
                if now - offered_at > timedelta(hours=3):
                    needs_new_offer = True

            if needs_new_offer:
                # Populate queue from demand if empty
                if not data.get("queue"):
                    demand = data.setdefault("demand", {})
                    potential_recipients = [
                        name for name, count in demand.items() if count > 0
                    ]
                    if potential_recipients:
                        random.shuffle(potential_recipients)
                        data["queue"] = potential_recipients
                        for name in potential_recipients:
                            demand[name] -= 1

                # Find someone in the queue who doesn't have an active offer or a voucher already
                next_recipient = None
                for user in data.get("queue", []):
                    if user not in all_offered_users:
                        next_recipient = user
                        break

                if next_recipient:
                    send_offer_to_user(client, voucher, next_recipient)
                    all_offered_users.add(next_recipient)

        # Legacy sending (still needed for when a voucher is finally accepted)
        if not voucher.get("message_id") and voucher.get("owner"):
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
        now = datetime.now(pytz.timezone("Europe/Berlin"))
    congress_number = now.year - 1986
    return f"{congress_number}C3"


def update_history_image(client: DiscourseStorageClient) -> None:
    now = datetime.now(pytz.timezone("Europe/Berlin"))
    if now.month not in [10, 11, 12] and not constants.FORCE_VOUCHER_PHASE:
        logging.info("Not voucher season. Skipping.")
        return

    data = client.storage.get("voucher", {})

    if not data.get("voucher"):
        return

    phase_range = data.get("voucher_phase_range", {}).get(get_congress_id(), {})
    if ts := phase_range.get("start"):
        start_date = ts
    else:
        return

    if ts := phase_range.get("end"):
        end_date = ts
    else:
        return

    if start_date > (now + timedelta(days=1)):
        return

    if end_date < (now - timedelta(days=3)):
        return

    exhausted_at = phase_range.get("exhausted_at")
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


def process_email_voucheringress(
    client: DiscourseStorageClient, mail_param: str | None, msg: Message
) -> None:
    if not mail_param:
        if not client.storage.get("voucher")["voucher"]:
            _mail_new_voucherlist(client, msg)
    else:
        _mail_voucher_returned(client, mail_param, msg)
    # subject, encoding = decode_header(msg["Subject"])[0]


def _mail_new_voucherlist(client: DiscourseStorageClient, msg: Message) -> None:
    """
    The mail that is processed by this function is supposed to contain a list of vouchers.
    We'll start a voucher distribution process with these vouchers.
    """
    content = _mail_msg_to_str(msg, accepted_content_types=("text/plain",))
    # Get every line between BEGIN VOUCHER LIST and END VOUCHER LIST
    voucher_match = re.search(
        r"BEGIN VOUCHER LIST(.*?)END VOUCHER LIST", content, re.DOTALL
    )
    if not voucher_match:
        logger.error(
            "No voucher list found in email",
            extra={
                "mail_content": content,
                "mail_to": msg.get("To"),
                "mail_from": msg.get("From"),
                "mail_subject": msg.get("Subject"),
                "mail_date": msg.get("Date"),
            },
        )
        return
    voucher_lines = voucher_match.group(1)
    voucher_codes = [line.strip() for line in voucher_lines.split()]
    data = client.storage.get("voucher", {})
    now = datetime.now(pytz.timezone("Europe/Berlin"))
    data["voucher"] = [
        {
            "index": i,
            "voucher": v,
            "owner": None,
            "old_owner": constants.DISCOURSE_CREDENTIALS["api_username"],
            "message_id": None,
            "received_at": now,
            "history": [],
        }
        for i, v in enumerate(voucher_codes)
    ]
    client.storage.put("voucher", data)
    logging.info(f"Stored {len(voucher_codes)} fresh vouchers from email")
    post_content = render(
        "voucher_list_received.md",
        reported_by="Der CCC",
        total_voucher=len(voucher_codes),
        bot_name=constants.DISCOURSE_CREDENTIALS["api_username"],
    )
    client.create_post(
        post_content,
        topic_id=data["voucher_topics"][get_congress_id()],
    )


def _mail_voucher_returned(
    client: DiscourseStorageClient, mail_param: str, msg: Message
) -> None:
    """
    The mail that is processed by this function is supposed to contain a voucher code that was returned by a user.
    We'll check if the voucher code is valid and if so, mark the voucher as returned and available
    for distribution again.
    """
    try:
        congress_id, voucher_index, history_length = decode_voucher_identifier(
            mail_param
        )
    except ValueError:
        logger.exception(
            "Invalid mail_param in email",
            extra={
                "mail_param": mail_param,
                "mail_to": msg.get("To"),
                "mail_from": msg.get("From"),
                "mail_subject": msg.get("Subject"),
                "mail_date": msg.get("Date"),
            },
        )
        return
    data = client.storage.get("voucher", {})

    if congress_id not in data.get("voucher_topics", {}):
        logger.info(
            f"No active voucher topic for {congress_id}, ignoring returned voucher."
        )
        return

    now = datetime.now(pytz.timezone("Europe/Berlin"))
    if phase_range := data.get("voucher_phase_range", {}).get(congress_id):
        end_date = phase_range.get("end")
        if end_date and now > end_date:
            logger.info(
                f"Voucher phase for {congress_id} ended on {end_date}, ignoring returned voucher."
            )
            return

    try:
        voucher = data["voucher"][voucher_index]
    except IndexError:
        logger.error(
            "Invalid voucher index in email",
            extra={
                "mail_param": mail_param,
                "voucher_index": voucher_index,
                "mail_to": msg.get("To"),
                "mail_from": msg.get("From"),
                "mail_subject": msg.get("Subject"),
                "mail_date": msg.get("Date"),
            },
        )
        return
    assert voucher["index"] == voucher_index, "List index and voucher index mismatch"
    if len(voucher["history"]) != history_length:
        logger.info(
            "Mail was already processed, because history length mismatched",
            extra={
                "mail_param": mail_param,
                "voucher_index": voucher_index,
                "expected_history_length": history_length,
                "actual_history_length": len(voucher["history"]),
                "mail_to": msg.get("To"),
                "mail_from": msg.get("From"),
                "mail_subject": msg.get("Subject"),
                "mail_date": msg.get("Date"),
            },
        )
        return
    if voucher["owner"] is None:
        logging.info(
            "Mail was already processed, because voucher is already available (owner is None)",
        )
        return

    content = _mail_msg_to_str(msg, accepted_content_types=("text/plain",))
    matches = re.search(r"CHAOS[a-zA-Z0-9]+", content)
    if not matches:
        logger.error(
            "Couldn't find voucher code in email",
            extra={
                "mail_to": msg.get("To"),
                "mail_from": msg.get("From"),
                "mail_subject": msg.get("Subject"),
                "mail_date": msg.get("Date"),
            },
        )
        return
    returned_voucher_code = matches.group(0)
    now = datetime.now(pytz.timezone("Europe/Berlin"))
    send_message_to_user(
        client,
        voucher,
        message="Vielen Dank, ich habe den replizierten Voucher erhalten!",
    )

    voucher["voucher"] = returned_voucher_code
    voucher["old_owner"] = voucher["owner"]
    voucher["owner"] = None
    voucher["message_id"] = None
    voucher["history"][-1]["returned_at"] = now.isoformat()
    voucher["received_at"] = now
    client.storage.put("voucher", data)
    logging.info(f"Voucher {returned_voucher_code} returned by email")


def _mail_msg_to_str(
    msg: Message, accepted_content_types=("text/plain", "text/html")
) -> str:
    """
    Convert an email.message.Message to a string by extracting its payload.
    Handles both plain text and multipart messages.
    """
    result = ""
    if msg.is_multipart():
        parts = []
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if (
                content_type in accepted_content_types
                and "attachment" not in content_disposition
            ):
                body = part.get_payload(decode=True)
                if body:
                    encoding = part.get_content_charset() or "utf-8"
                    parts.append(body.decode(encoding, errors="replace"))
        result = "\n".join(parts)
    else:
        body = msg.get_payload(decode=True)
        if body:
            encoding = msg.get_content_charset() or "utf-8"
            result = body.decode(encoding, errors="replace")
    return result


def main(client: DiscourseStorageClient) -> None:
    # voucher only relevant in october, november and maybe december
    now = datetime.now(pytz.timezone("Europe/Berlin"))
    if now.month not in [10, 11, 12] and not constants.FORCE_VOUCHER_PHASE:
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
