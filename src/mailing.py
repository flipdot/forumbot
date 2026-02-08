from client import DiscourseStorageClient
import imaplib
import email
import re
import logging
from datetime import datetime, timedelta

from constants import IMAP_HOST, IMAP_USERNAME, IMAP_PASSWORD
from tasks.voucher import process_email_voucheringress

logger = logging.getLogger(__name__)

matcher = re.compile(r"bot(?:\+(\w+)(?:-([\w-]+))?)?@flipdot\.org")


def imap_date_format(dt: datetime) -> str:
    """
    Format a datetime object to the format required by IMAP search queries.
    Using `.strftime("%d-%b-%Y")` is not reliable because it depends on the system locale.
    """
    MONTHS = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    return dt.strftime(f"%d-{MONTHS[dt.month - 1]}-%Y")


def read_emails(discourse_client: DiscourseStorageClient, days_back: int = 90):
    if not (IMAP_USERNAME and IMAP_PASSWORD):
        logger.error(
            "Environment variables `IMAP_USERNAME` and / or `IMAP_PASSWORD` missing. Skipping email processing."
        )
        return
    mail = imaplib.IMAP4_SSL(IMAP_HOST)
    mail.login(IMAP_USERNAME, IMAP_PASSWORD)
    mail.select("inbox")

    today = datetime.now()
    since_date = imap_date_format(today - timedelta(days=days_back))

    status, messages = mail.search(None, f"SINCE {since_date}")
    mail_ids = messages[0].split()

    for mail_id in mail_ids:
        status, msg_data = mail.fetch(mail_id, "(RFC822)")
        for response_part in msg_data:
            if not isinstance(response_part, tuple):
                continue
            msg = email.message_from_bytes(response_part[1])
            delivered_to = msg["Delivered-To"]

            match m.groups() if (m := matcher.search(delivered_to)) else None:
                case None:
                    logger.info(f"Email not addressed to bot: {delivered_to}")
                    continue
                case (None, _):
                    logger.info(f"Not triggering any task for email to: {delivered_to}")
                    continue
                case ("voucheringress", params):
                    process_email_voucheringress(discourse_client, params, msg)
                case (task_name, params):
                    logger.info(f"Unknown task '{task_name}' with params: {params}")
