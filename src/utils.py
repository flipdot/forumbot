from datetime import timedelta, datetime
from itertools import count
from typing import Tuple, List

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
    if title in topics:
        return True