import logging
import re
from datetime import datetime, timedelta
from pprint import pprint

from client import DiscourseStorageClient


def private_message_handler(client: DiscourseStorageClient, topic, posts) -> None:
    if 'voucher' not in topic['title'].lower():
        return
    posts_content = ' '.join(p['cooked'] for p in posts['post_stream']['posts'])
    received_voucher = set(re.findall(r'CHAOS[a-zA-Z0-9]+', posts_content))
    # Maybe something just looked like a voucher. If we find more than 3, we probably really received some:
    if len(received_voucher) > 3:
        old_storage = client.storage.get('voucher')
        received_on = old_storage.get('received_on')
        save_new_voucher = False
        if not received_on:
            # seems like we have not stored old vouchers. Overwrite them
            save_new_voucher = True
        if received_on:
            now = datetime.now()
            delta = now - received_on
            if delta > timedelta(days=60):
                # the last vouchers which were stored are older than 60 days. We can probably overwrite them
                save_new_voucher = True

        if save_new_voucher:
            logging.info('Saving new vouchers to storage')
            client.storage.put('voucher', {
                'voucher': [{
                    'voucher': v,
                } for v in received_voucher],
                'received_on': datetime.now(),
            })


def main(client: DiscourseStorageClient) -> None:
    client.storage.put('voucher', {})
    pprint(client.storage.get('voucher'))
    # This function may come in handy. Just drop your templates into the templates/ directory:
    # render('plenum.md', my_variable=15)
