import logging

from pydiscourse import DiscourseClient
from constants import DISCOURSE_CREDENTIALS
from time import sleep

import locale
import schedule
import tasks

locale.setlocale(locale.LC_TIME, 'de_DE.UTF-8')


def main():
    logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s', level=logging.INFO)

    assert DISCOURSE_CREDENTIALS['api_key'], 'Environment variable DISCOURSE_API_KEY not set'
    client = DiscourseClient(**DISCOURSE_CREDENTIALS)

    schedule.every().day.at('13:37').do(tasks.announce_plenum, client)
    schedule.every(10).seconds.do(tasks.announce_plenum, client)

    while True:
        schedule.run_pending()
        sleep(1)


if __name__ == '__main__':
    main()
