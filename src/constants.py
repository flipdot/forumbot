import os
from dotenv import load_dotenv

load_dotenv()

DISCOURSE_HOST = (
    os.getenv("DISCOURSE_HOST", "").rstrip("/") or "https://forum.flipdot.org"
)

DISCOURSE_CREDENTIALS = {
    "api_key": os.getenv("DISCOURSE_API_KEY"),
    "api_username": os.getenv("DISCOURSE_USERNAME") or "flipbot",
    "host": DISCOURSE_HOST,
}

CCC_CATEGORY_NAME = os.getenv("CCC_CATEGORY_NAME", "ccc")

CATEGORY_ID_MAPPING = {
    "orga/plena": os.environ.get("CATEGORY_ID_PLENUM", 23),
    "ccc": os.environ.get("CATEGORY_ID_CCC", 17),
    "test": 24,
}

SENTRY_DSN = os.getenv("SENTRY_DSN")

DEBUG = "test" in DISCOURSE_CREDENTIALS["api_username"]

assert DISCOURSE_CREDENTIALS[
    "api_key"
], "Environment variable DISCOURSE_API_KEY not set"
