from client import DiscourseStorageClient
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta

from constants import IMAP_HOST, IMAP_USERNAME, IMAP_PASSWORD


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
    mail = imaplib.IMAP4_SSL(IMAP_HOST)
    mail.login(IMAP_USERNAME, IMAP_PASSWORD)
    mail.select("inbox")

    today = datetime.now()
    # since_date = (today - timedelta(days=30)).strftime("%d-%b-%Y")
    since_date = imap_date_format(today - timedelta(days=days_back))

    status, messages = mail.search(None, f"SINCE {since_date}")
    mail_ids = messages[0].split()

    for mail_id in mail_ids:
        status, msg_data = mail.fetch(mail_id, "(RFC822)")
        for response_part in msg_data:
            if not isinstance(response_part, tuple):
                continue
            msg = email.message_from_bytes(response_part[1])
            subject, encoding = decode_header(msg["Subject"])[0]
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))

                    body = part.get_payload(decode=True)

                    if (
                        body
                        # and content_type == "text/plain"
                        # and "attachment" not in content_disposition
                    ):
                        box_txt = f" Content type: {content_type}, disposition: {content_disposition} "
                        box_size = len(box_txt)
                        print("┌" + "─" * box_size + "┐")
                        print(f"│{box_txt}│")
                        print("└" + "─" * box_size + "┘")
                        print(body.decode())
            else:
                body = msg.get_payload(decode=True)
                print(body)

            # TODO:
            #  - Check X-Original-To header to route to correct task (voucher)
            #  - Pass email content to task handler
