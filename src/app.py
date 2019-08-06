import logging
import sys

from pydiscourse import DiscourseClient
from pydiscourse.exceptions import DiscourseClientError

from constants import DISCOURSE_CREDENTIALS
from time import sleep

import locale
import schedule
import tasks

locale.setlocale(locale.LC_TIME, 'de_DE.UTF-8')


def test_login(client: DiscourseClient):
    try:
        client.latest_topics()
    except DiscourseClientError as e:
        logging.error(f'Could not perform login: {e}')
        sys.exit(-1)


def schedule_jobs(client: DiscourseClient):
    schedule.every().day.at('13:37').do(tasks.announce_plenum, client)


def main():
    logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s', level=logging.INFO)

    assert DISCOURSE_CREDENTIALS['api_key'], 'Environment variable DISCOURSE_API_KEY not set'
    client = DiscourseClient(**DISCOURSE_CREDENTIALS)
    test_login(client)

    schedule_jobs(client)

    for job in schedule.jobs:
        logging.info(f'Scheduled job: {job}')
    while True:
        schedule.run_pending()
        sleep(1)


if __name__ == '__main__':
    main()
