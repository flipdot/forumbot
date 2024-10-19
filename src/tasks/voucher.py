import logging
import re
from datetime import datetime, timedelta

from pydiscourse import DiscourseClient
from client import DiscourseStorageClient

# custom types
# TypedDict is only available since python 3.8
# class VoucherConfigElement(TypedDict):
#     voucher: str
#     owner: Optional[str]
#     message_id: Optional[int]
#     persons: Optional[int]
from typing import Dict, List, Optional

from utils import render

VoucherConfigElement = Dict

VoucherConfig = List[VoucherConfigElement]


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
                'queue_topic': topic['id'],
            })


def get_username(voucher: VoucherConfigElement) -> Optional[str]:
    owner = voucher['owner']
    return re.search(r'@([^ ]+)', owner)[1] if owner else None


def send_voucher_to_user(client: DiscourseClient, voucher: VoucherConfigElement):
    assert not voucher['message_id'], 'Wanted to send a voucher, again'
    username = get_username(voucher)
    message_content = render('voucher_message.md', voucher=voucher)
    logging.info(f'Sending voucher to {username}')
    res = client.create_post(message_content, title='Dein 36C3 Voucher', archetype='private_message',
                             target_usernames=username)
    message_id = res.get('topic_id')
    logging.info(f'Sent, message_id is {message_id}')
    voucher['message_id'] = message_id
    voucher['received'] = datetime.now()


def send_message_to_user(client: DiscourseClient, voucher: VoucherConfigElement, message: str) -> None:
    username = get_username(voucher)
    message_id = voucher.get('message_id')
    if not message_id:
        return
    logging.info(f'Sending message to {username} (Thread {message_id})')
    client.create_post(message, topic_id=message_id)


def check_for_returned_voucher(client: DiscourseClient, voucher: VoucherConfigElement) -> Optional[str]:
    message_id = voucher['message_id']
    posts = client.posts(message_id)
    user_posts = [post for post in posts['post_stream']['posts'] if post['name'] != 'flipbot']
    user_posts_content = ' '.join([p['cooked'] for p in user_posts])
    new_voucher = re.search(r'CHAOS[a-zA-Z0-9]+', user_posts_content)
    if new_voucher:
        return new_voucher[0]


# TODO: think hard about maintaining the correct state. Not like this.
# def update_queue(client: DiscourseStorageClient):
#     data = client.storage.get('voucher')
#     topic_id = data.get('queue_topic')
#     queue_posts = [p for p in client.posts(topic_id)['post_stream']['posts'][0:] if not p['yours']]
#     for post in queue_posts:
#         pprint(post)
#         usernames = re.findall(r'@([^ ]+)', post['cooked'])
#         print(usernames)
#     import sys
#     sys.exit()


def main(client: DiscourseStorageClient) -> None:
    data = client.storage.get('voucher')
    for voucher in data.get('voucher', []):
        if not voucher['owner']:
            queue = data.get('queue')
            if not queue or type(queue) is not list:
                continue
            voucher['owner'] = queue.pop(0)
        if voucher.get('message_id'):
            new_voucher_code = check_for_returned_voucher(client, voucher)
            if new_voucher_code:
                logging.info(f'Voucher returned by {get_username(voucher)}')
                send_message_to_user(client, voucher, message=f'Prima, vielen Dank für "{new_voucher_code}"!')

                old_owner = get_username(voucher)
                voucher['voucher'] = new_voucher_code
                voucher['owner'] = None
                voucher['old_owner'] = old_owner
                voucher['message_id'] = None
                voucher['persons'] = None
                voucher['received'] = None
        elif voucher['owner']:
            send_voucher_to_user(client, voucher)

    post_content = render('voucher_table.md', vouchers=data.get('voucher', []), queue=data.get('queue', []))
    # TODO: voucher_table_post_id does not get saved. We need to create a post as soon as we received the voucher list
    client.update_post(data.get('voucher_table_post_id'), post_content)

    client.storage.put('voucher', data)
