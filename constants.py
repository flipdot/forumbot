import os

DISCOURSE_CREDENTIALS = {
    'api_key': os.getenv('DISCOURSE_API_KEY'),
    'api_username': 'flipbot',
    'host': 'https://forum.flipdot.org'
}
