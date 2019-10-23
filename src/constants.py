import os

DISCOURSE_CREDENTIALS = {
    'api_key': os.getenv('DISCOURSE_API_KEY'),
    'api_username': os.getenv('DISCOURSE_USERNAME') or 'flipbot',
    'host': os.getenv('DISCOURSE_HOST') or 'https://forum.flipdot.org',
}

assert DISCOURSE_CREDENTIALS[
    'api_key'
], 'Environment variable DISCOURSE_API_KEY not set'
