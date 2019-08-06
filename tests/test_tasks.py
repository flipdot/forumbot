import unittest
from datetime import datetime
import tasks


class TestAnnouncePlenum(unittest.TestCase):

    def test_get_next_plenum_date(self):
        plenum_date, delta = tasks.get_next_plenum_date(datetime(2019, 8, 1))
        self.assertEqual(datetime(2019, 8, 4), plenum_date)
        self.assertEqual(3, delta.days)

        plenum_date, delta = tasks.get_next_plenum_date(datetime(2019, 8, 3))
        self.assertEqual(datetime(2019, 8, 4), plenum_date)
        self.assertEqual(1, delta.days)

        plenum_date, delta = tasks.get_next_plenum_date(datetime(2019, 8, 4))
        self.assertEqual(datetime(2019, 8, 4), plenum_date)
        self.assertEqual(0, delta.days)

        plenum_date, delta = tasks.get_next_plenum_date(datetime(2019, 8, 5))
        self.assertEqual(datetime(2019, 9, 1), plenum_date)
        self.assertEqual(27, delta.days)

        plenum_date, delta = tasks.get_next_plenum_date(datetime(2019, 8, 25))
        self.assertEqual(datetime(2019, 9, 1), plenum_date)
        self.assertEqual(7, delta.days)

        plenum_date, delta = tasks.get_next_plenum_date(datetime(2019, 8, 31))
        self.assertEqual(datetime(2019, 9, 1), plenum_date)
        self.assertEqual(1, delta.days)

        plenum_date, delta = tasks.get_next_plenum_date(datetime(2019, 9, 1))
        self.assertEqual(datetime(2019, 9, 1), plenum_date)
        self.assertEqual(0, delta.days)

        plenum_date, delta = tasks.get_next_plenum_date(datetime(2019, 9, 2))
        self.assertEqual(datetime(2019, 10, 6), plenum_date)
        self.assertEqual(34, delta.days)
