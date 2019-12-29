import os

DISCOURSE_HOST = os.getenv('DISCOURSE_HOST').rstrip("/") or 'https://forum.flipdot.org'

DISCOURSE_CREDENTIALS = {
    'api_key': os.getenv('DISCOURSE_API_KEY'),
    'api_username': os.getenv('DISCOURSE_USERNAME') or 'flipbot',
    'host': DISCOURSE_HOST,
}

assert DISCOURSE_CREDENTIALS[
    'api_key'
], 'Environment variable DISCOURSE_API_KEY not set'
