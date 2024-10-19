import os
from dotenv import load_dotenv

load_dotenv()

DISCOURSE_HOST = os.getenv('DISCOURSE_HOST', '').rstrip('/') or 'https://forum.flipdot.org'

DISCOURSE_CREDENTIALS = {
    'api_key': os.getenv('DISCOURSE_API_KEY'),
    'api_username': os.getenv('DISCOURSE_USERNAME') or 'flipbot',
    'host': DISCOURSE_HOST,
}

SENTRY_DSN = os.getenv('SENTRY_DSN')

DEBUG = 'test' in DISCOURSE_CREDENTIALS['api_username']

assert DISCOURSE_CREDENTIALS[
    'api_key'
], 'Environment variable DISCOURSE_API_KEY not set'
