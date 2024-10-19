import logging

from pydiscourse import DiscourseClient

# from utils import render


def main(client: DiscourseClient) -> None:
    logging.info(
        "This is a minimal example of a task file. You have successfully run it!"
    )
    # This function may come in handy. Just drop your templates into the templates/ directory:
    # render('plenum.md', my_variable=15)
