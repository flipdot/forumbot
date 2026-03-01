from datetime import datetime
import pytz
from utils import jinja_env


def test_format_datetime_with_datetime_object():
    now = datetime(2026, 2, 28, 14, 30, tzinfo=pytz.timezone("Europe/Berlin"))
    template = jinja_env.from_string("{{ dt | format_datetime }}")
    rendered = template.render(dt=now)
    assert rendered == "2026-02-28 14:30"


def test_format_datetime_with_iso_string():
    iso_string = "2026-02-28T14:30:00+01:00"
    template = jinja_env.from_string("{{ dt | format_datetime }}")
    rendered = template.render(dt=iso_string)
    assert rendered == "2026-02-28 14:30"


def test_format_datetime_with_custom_format():
    now = datetime(2026, 2, 28, 14, 30, tzinfo=pytz.timezone("Europe/Berlin"))
    template = jinja_env.from_string("{{ dt | format_datetime('%Y/%m/%d') }}")
    rendered = template.render(dt=now)
    assert rendered == "2026/02/28"


def test_format_datetime_with_none():
    template = jinja_env.from_string("{{ dt | format_datetime }}")
    rendered = template.render(dt=None)
    assert rendered == ""


def test_format_datetime_with_invalid_string():
    template = jinja_env.from_string("{{ dt | format_datetime }}")
    rendered = template.render(dt="not-a-date")
    assert rendered == ""
