from jinja2 import Environment, FileSystemLoader
from datetime import datetime

jinja_env = Environment(loader=FileSystemLoader("templates"))


def _parse_datetime(value):
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def format_datetime_filter(value, format="%Y-%m-%d %H:%M"):
    dt = _parse_datetime(value)
    if dt:
        return dt.strftime(format)
    return ""


jinja_env.filters["format_datetime"] = format_datetime_filter


def render(template_name: str, **kwargs):
    template = jinja_env.get_template(template_name)
    return template.render(**kwargs)
