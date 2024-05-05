import os
import re
from datetime import datetime, timedelta
from itertools import count
from typing import Tuple, List
from constants import DEBUG

PAD_BASE_URL = os.getenv('PAD_BASE_URL', '').rstrip('/') or 'https://pad.flipdot.org'
PROTOCOL_PLACEHOLDER = 'PROTOCOL_PLACEHOLDER'

# Category 23 == 'orga/plena'. But we must use the id in client.create_post. D'oh!
# Category 24 == 'test'
DISCOURSE_CATEGORY_ID = 24 if DEBUG else 23
DISCOURSE_CATEGORY_NAME = 'test' if DEBUG else 'orga/plena'


def get_next_plenum_date(now: datetime) -> Tuple[datetime, timedelta]:
    next_days = (now + timedelta(days=i) for i in count())
    first_tuesdays = (x for x in next_days if x.weekday() == 1 and x.day <= 7)
    plenum_date = next(first_tuesdays)
    delta = plenum_date - now
    return plenum_date, delta


def topic_exists(title: str, topics: List[str]):
    # Use the first 8 chars from the title, e.g: 2019-10-
    # Then, there need to come any two digits (\d{2} - the formatting is a bit fucked up since we use formatstrings),
    # followed by anything, as long as "plenum" appears anywhere
    pattern = re.compile(fr'^{title[:8]}\d{{2}} .*plenum.*$', re.IGNORECASE)
    matches = [pattern.search(t) for t in topics]
    return any(matches)
