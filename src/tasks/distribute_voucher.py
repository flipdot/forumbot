import logging
from pprint import pprint

from client import DiscourseStorageClient


def main(client: DiscourseStorageClient) -> None:
    # client.storage.put('voucher', [{'asdf': 'hjfdfdkl'}, {'qwer': [23, 51]}])
    pprint(client.storage.get('voucher'))
    # This function may come in handy. Just drop your templates into the templates/ directory:
    # render('plenum.md', my_variable=15)
