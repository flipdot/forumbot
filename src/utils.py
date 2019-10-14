from datetime import timedelta, datetime
from itertools import count
from typing import Tuple, List
import re

from jinja2 import Environment, FileSystemLoader

jinja_env = Environment(loader=FileSystemLoader("templates"))


def render(template_name: str, **kwargs):
    template = jinja_env.get_template(template_name)
    return template.render(**kwargs)


def get_next_plenum_date(now: datetime) -> Tuple[datetime, timedelta]:
    next_days = (now + timedelta(days=i) for i in count())
    first_sundays = (x for x in next_days if x.weekday() == 6 and x.day <= 7)
    plenum_date = next(first_sundays)
    delta = plenum_date - now
    return plenum_date, delta


def topic_exists(title: str, topics: List[str]):
    # Use the first 8 chars from the title, e.g: 2019-10-
    # Then, there need to come any two digits (\d{2} - the formatting is a bit fucked up since we use formatstrings),
    # followed by anything, as long as "plenum" appears anywhere
    pattern = re.compile(fr'^{title[:8]}\d{{2}} .*plenum.*$', re.IGNORECASE)
    matches = [pattern.search(t) for t in topics]
    return any(matches)
