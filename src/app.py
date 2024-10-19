import argparse
import logging
import sys
from datetime import datetime
from typing import Optional

from client import DiscourseClient, DiscourseStorageClient
from pydiscourse.exceptions import DiscourseClientError

from constants import DISCOURSE_CREDENTIALS, SENTRY_DSN
from time import sleep

import locale
import schedule
import tasks.voucher
import tasks.plenum.announce
import tasks.plenum.remind
import tasks.plenum.post_protocol

import sentry_sdk

logging.basicConfig(
    format="%(asctime)s - %(levelname)s: %(message)s", level=logging.INFO
)

sentry_sdk.init(dsn=SENTRY_DSN)

locale.setlocale(locale.LC_TIME, "de_DE.UTF-8")


def test_login(client: DiscourseClient) -> None:
    try:
        client.latest_topics()
    except DiscourseClientError as e:
        logging.error(f"Could not perform login: {e}")
        sys.exit(-1)


def disable_request(
    client: DiscourseClient,
    disable_verb: Optional[str] = None,
    disable_path: Optional[str] = None,
):
    original_request = client._request

    def new_request_fn(verb, path, *args, **kwargs):
        if (
            disable_verb
            and verb == disable_verb
            or disable_path
            and path == disable_path
        ):
            logging.info(f"Dry run. {verb} request to {path} was not made. Data:")
            logging.info(kwargs.get("data"))
            return {}
        return original_request(verb, path, *args, **kwargs)

    client._request = new_request_fn


def fetch_unread_messages(client: DiscourseStorageClient):
    if datetime.now().month not in [10, 11, 12]:
        # PN feature currently only used for voucher distribution.
        # Voucher distribution is only relevant in october, november and maybe december
        return

    # TODO: Something is still wrong about the unseen thingy. Dunno when it get's set.
    topics = [
        t for t in client.private_messages()["topic_list"]["topics"] if t["unseen"]
    ]
    for topic in topics:
        posts = client.topic_posts(topic["id"])
        if datetime.now().month in [10, 11, 12]:
            tasks.voucher.private_message_handler(client, topic, posts)


def schedule_jobs(client: DiscourseStorageClient) -> None:
    # TODO: timezone is not correct, quickfix by subtracting an hour
    schedule.every().day.at("12:37").do(tasks.plenum.announce.main, client)
    schedule.every().day.at("12:37").do(tasks.plenum.remind.main, client)
    schedule.every().day.at("20:00").do(tasks.plenum.post_protocol.main, client)

    schedule.every(30).seconds.do(fetch_unread_messages, client)
    schedule.every().minute.do(tasks.voucher.main, client)

    # schedule.every(15).seconds.do(fetch_unread_messages, client)
    # schedule.every(15).seconds.do(tasks.voucher.main, client)

    fetch_unread_messages(client)


def main():
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s: %(message)s", level=logging.INFO
    )

    parser = argparse.ArgumentParser(
        description="Updates voucher post, sends out vouchers via PM, receives returned vouchers via PM"
    )
    parser.add_argument(
        "--dry", action="store_true", help="do not execute POST or PUT requests"
    )
    parser.add_argument(
        "--run_task",
        type=str,
        help="runs a specific task immediately and stops afterwards",
    )
    parser.add_argument(
        "--test_connection",
        action="store_true",
        help="checks if a connection to discourse is possible and exits",
    )

    args = parser.parse_args()

    client = DiscourseStorageClient(**DISCOURSE_CREDENTIALS)
    if args.dry:
        disable_request(client, "POST")
        disable_request(client, "PUT")

    test_login(client)

    if args.test_connection:
        logging.info(
            f'Connection to "{DISCOURSE_CREDENTIALS["host"]}" with user"'
            f' {DISCOURSE_CREDENTIALS["api_username"]}" tested successfully'
        )
        sys.exit(0)

    if args.run_task:
        import importlib

        try:
            task = importlib.import_module(f"tasks.{args.run_task}")
        except ModuleNotFoundError:
            logging.error(f'Task "{args.run_task}" does not exist')
            sys.exit(1)
        logging.info(f'Running task "{args.run_task}"')
        task.main(client)
        sys.exit()

    schedule_jobs(client)

    for job in schedule.jobs:
        logging.info(f"Scheduled job: {job}")
    while True:
        try:
            schedule.run_pending()
            sleep(1)
        except KeyboardInterrupt:
            logging.info("Shutting down")
            sys.exit(0)


if __name__ == "__main__":
    main()
