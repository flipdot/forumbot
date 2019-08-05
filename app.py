from datetime import datetime
from pprint import pprint

from pydiscourse import DiscourseClient
from constants import DISCOURSE_CREDENTIALS
from jinja2 import FileSystemLoader, Environment

import locale
locale.setlocale(locale.LC_TIME, 'de_DE.UTF-8')

jinja_env = Environment(
    loader=FileSystemLoader('templates'),
)


def render(template_name, **kwargs):
    template = jinja_env.get_template(template_name)
    return template.render(**kwargs)


def main():
    assert DISCOURSE_CREDENTIALS['api_key'], 'Environment variable DISCOURSE_API_KEY not set'
    client = DiscourseClient(**DISCOURSE_CREDENTIALS)
    plenum_date = datetime.now()

    post_content = render('plenum.md', plenum_date=plenum_date)
    title = plenum_date.strftime('%Y-%m-%d Plenum')

    # Here, we use the string representation of the category...
    # topics = client.category_topics('orga/plena')
    # But here, we need the integer id. D'oh!
    res = client.create_post(post_content, category_id=23, title=title)
    pprint(res)


if __name__ == '__main__':
    main()
