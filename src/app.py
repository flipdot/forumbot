import argparse
import logging
import sys
from typing import Optional

from pydiscourse import DiscourseClient
from pydiscourse.exceptions import DiscourseClientError

from constants import DISCOURSE_CREDENTIALS
from time import sleep

import locale
import schedule
import tasks.announce_plenum

locale.setlocale(locale.LC_TIME, 'de_DE.UTF-8')


def test_login(client: DiscourseClient) -> None:
    try:
        client.latest_topics()
    except DiscourseClientError as e:
        logging.error(f'Could not perform login: {e}')
        sys.exit(-1)


def disable_request(client: DiscourseClient, disable_verb: Optional[str] = None, disable_path: Optional[str] = None):
    original_request = client._request

    def new_request_fn(verb, path, *args, **kwargs):
        if disable_verb and verb == disable_verb or disable_path and path == disable_path:
            logging.info(f'Dry run. {verb} request to {path} was not made. Data:')
            logging.info(kwargs.get('data'))
            return {}
        return original_request(verb, path, *args, **kwargs)

    client._request = new_request_fn


def schedule_jobs(client: DiscourseClient) -> None:
    schedule.every().day.at('13:37').do(tasks.announce_plenum.main, client)


def main():
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s: %(message)s', level=logging.INFO
    )

    parser = argparse.ArgumentParser(
        description='Updates voucher post, sends out vouchers via PM, receives returned vouchers via PM'
    )
    parser.add_argument('--dry', action='store_true', help='do not execute POST or PUT requests')
    parser.add_argument('--run_task', type=str, help='runs a specific task immediately and stops afterwards')

    args = parser.parse_args()

    client = DiscourseClient(**DISCOURSE_CREDENTIALS)
    if args.dry:
        disable_request(client, 'POST')
        disable_request(client, 'PUT')

    test_login(client)

    if args.run_task:
        import importlib
        try:
            task = importlib.import_module(f'tasks.{args.run_task}')
        except ModuleNotFoundError:
            logging.error(f'Task "{args.run_task}" does not exist')
            sys.exit(1)
        logging.info(f'Running task "{args.run_task}"')
        task.main(client)
        sys.exit()

    schedule_jobs(client)

    for job in schedule.jobs:
        logging.info(f'Scheduled job: {job}')
    while True:
        try:
            schedule.run_pending()
            sleep(1)
        except KeyboardInterrupt:
            logging.info(f'Shutting down')
            sys.exit(0)


if __name__ == '__main__':
    main()
