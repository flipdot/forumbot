import logging
import re
from datetime import datetime

import requests
import mistune
import numpy as np

from client import DiscourseStorageClient
from tasks.plenum import get_next_plenum_date, PROTOCOL_PLACEHOLDER
from utils import render


def iterate_sections(obj, indices):
    return [obj[start:end] for start, end in zip(indices, np.append(indices[1:], None))]


def parse_protocol(protocol):
    protocol_parsed = mistune.Markdown(mistune.AstRenderer()).parse(protocol)
    h2_indices = np.where([x['type'] == 'heading' and x['level'] == 2 for x in protocol_parsed])[0]

    result = {'topics': []}
    for section in iterate_sections(protocol_parsed, h2_indices):
        section_name = section[0]['children'][0]['text']
        if section_name != 'Tagesordnungspunkte':
            continue
        topic_indices = np.where([x['type'] == 'heading' and x['level'] == 3 for x in section])[0]
        for topic in iterate_sections(section, topic_indices):
            title = topic[0]['children'][0]['text'].strip()
            if 'Vorstellungsrunde' in title:
                continue
            title_text = ' '.join([x['text'] for x in topic[0]['children']])
            author_match = re.search(r'@(.+)?\]', title_text)
            if author_match:
                author = author_match.groups()[0]
            else:
                author = None
            was_discussed = 'Thema wurde nicht besprochen' not in str(topic[-1])
            result['topics'].append({
                'title': title,
                'author': author,
                'was_discussed': was_discussed,
            })
    return result


def main(client: DiscourseStorageClient) -> None:
    now = datetime.now()
    plenum_date, delta = get_next_plenum_date(now)
    if now.date() != plenum_date.date():
        logging.info('Today was no plenum. Aborting.')
        return
    title = plenum_date.strftime('%Y-%m-%d Plenum')
    topics = [x for x in client.category_topics('orga/plena')['topic_list']['topics'] if x['title'] == title]

    if not topics:
        logging.info(f'"{title}" does not exist, can\'t post protocol. Aborting.')
        return

    if len(topics) > 1:
        logging.error(f'There were multiple "{title}". Aborting.')
        return

    announcement_topic_id = topics[0]['id']
    topic_posts = client.topic_posts(announcement_topic_id)
    post = topic_posts['post_stream']['posts'][0]

    # Although the rendered content is already returned in the request above, we need another call to get the markdown
    post['raw'] = client.single_post(post['id'])['raw']

    pad_links = [x['url'] for x in post['link_counts'] if '://pad.flipdot' in x['url']]
    if not pad_links:
        logging.error(f'The first post in "{title}" does not contain a pad link. Aborting.')
        return

    if len(pad_links) > 1:
        logging.error(f'The first post in "{title}" does contains multiple pad links. Aborting.')
        return

    pad_link = pad_links[0]

    res = requests.get(pad_link + '/download')
    if res.status_code != 200:
        logging.error('Could not download protocol from pad. Aborting')
        return
    protocol = res.text

    protocol_topics = parse_protocol(protocol)['topics']
    undiscussed_topics = [x for x in protocol_topics if not x['was_discussed']]
    discussed_topics = [x for x in protocol_topics if x['was_discussed']]

    post_content = post['raw']

    if PROTOCOL_PLACEHOLDER not in post_content:
        logging.error('There is no placeholder for the protocol. Aborting.')
        return

    new_content = post_content.replace(PROTOCOL_PLACEHOLDER, protocol)
    client.update_post(post['id'], new_content, edit_reason='Added protocol')

    # TODO: this should actually be fixed inside DiscourseDB, not here
    if undiscussed_topics:
        client.storage.put('NEXT_PLENUM_TOPICS', undiscussed_topics)

    protocol_posted_content = render('protocol_posted.md', discussed_topics=discussed_topics,
                                     undiscussed_topics=undiscussed_topics).encode('utf-8')
    client.create_post(protocol_posted_content, topic_id=announcement_topic_id)
