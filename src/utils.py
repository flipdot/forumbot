from jinja2 import Environment, FileSystemLoader

jinja_env = Environment(loader=FileSystemLoader("templates"))


def render(template_name: str, **kwargs):
    template = jinja_env.get_template(template_name)
    return template.render(**kwargs)