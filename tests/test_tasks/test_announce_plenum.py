import unittest
from datetime import datetime

from tasks import plenum


class TestTopicExists(unittest.TestCase):

    def setUp(self) -> None:
        self.topics = [
            "Wie funktioniert ein Plenum?",
            "2019-11-03 <strike>Plenum</strike> Vollversammlung",
            "2019-10-13 Plenum",
            "2019-09-08 Plenum",
            "2019-09-01 Plenum",
            "2019-08-04 Plenum",
            "2019-07-07 Plenum",
            "[POLL] [BIS 17.2.] Plenum 1x im Monat. Welcher Wochentag?",
            "2019-06-09 Plenum",
            "2019-05-05 - Plenum nach VV",
            "Ordentliche Vollversammlung 2019 am 5.5.2019 um 16:00",
            "2019-04-07 Plenum",
            "[2019-03-03] Plenum",
            "Themensammlung für Plenum 2018-03",
            "2019-02-10, 17:00 Plenum",
            "Festhalten Ergebnis Spontanplenum: Was gehört in unser Blog, was nicht?",
            "[erledigt] Wo ist der Accuschrauber aus der Werkstatt?",
            "2018-07-31 Plenum (Getränkepreise)",
            "[2018-05-29] Besprechung / Plenum HackWat!",
            "2018-05-08 Plenum",
            "Ordentliche Mitgliederversammlung Donnerstag 2018-04-12 um 20:00",
            "2018-02-20 Plenum (Neues Event)",
            "2017-11-14 Plenum",
            "2017-10-31 Plenum",
            "2017-10-24 Plenum [verschoben]",
            "2017-08-29 Plenum",
            "2017-08-01 Plenum",
            "Ordentliche Vollversammlung 2016 am 27.04.2017 um 20:00",
            "Vollversammlung 2.11.2016 18:00",
        ]

    def test_exact_match(self):
        self.assertTrue(plenum.topic_exists("2019-08-04 Plenum", self.topics))
        self.assertTrue(plenum.topic_exists("2019-09-08 Plenum", self.topics))
        # This is in the future, so it should not yet exist
        self.assertFalse(plenum.topic_exists("2019-12-01 Plenum", self.topics))

    def test_case_sensitivity(self):
        """
        Someone posted a plenum announcement, but fucked up the casing.
        :return:
        """
        self.assertTrue(plenum.topic_exists("2019-08-04 plenum", self.topics))
        self.assertTrue(plenum.topic_exists("2019-09-08 PLENUM", self.topics))
        self.assertTrue(plenum.topic_exists("2019-09-08 Plenum", ["2019-09-08 plenum"]))
        self.assertTrue(plenum.topic_exists("2019-09-08 Plenum", ["2019-09-08 PLENUM"]))
        self.assertTrue(plenum.topic_exists("2019-09-08 Plenum", ["2019-09-08 PlEnUm"]))

    def test_wrong_day(self):
        """
        A human posted the plenum on another day, but in the same month. Consider the topic as existent.
        :return:
        """
        self.assertTrue(plenum.topic_exists("2019-10-06 Plenum", self.topics))
        self.assertTrue(
            plenum.topic_exists(
                "2019-10-06 Plenum", ["2019-10-05 Plenum", "2019-10-27 Plenum"]
            )
        )
        self.assertFalse(
            plenum.topic_exists(
                "2019-11-01 Plenum", ["2019-10-01 Plenum", "2019-10-30 Plenum"]
            )
        )
        self.assertFalse(
            plenum.topic_exists(
                "2019-10-06 Plenum", ["2018-10-06 Plenum", "2020-10-06 Plenum"]
            )
        )

    def test_title_with_garbage(self):
        """
        The human did not comply to the usual formatting. Try to be smarter than the human.
        :return:
        """
        self.assertTrue(plenum.topic_exists("2019-11-03 Plenum", self.topics))
        self.assertTrue(
            plenum.topic_exists("2019-11-03 Plenum", ["2019-11-05 Gutes Plenum"])
        )


class TestAnnouncePlenum(unittest.TestCase):

    def test_get_next_plenum_date(self):
        plenum_date, delta = plenum.get_next_plenum_date(datetime(2019, 8, 1))
        self.assertEqual(datetime(2019, 8, 4), plenum_date)
        self.assertEqual(3, delta.days)

        plenum_date, delta = plenum.get_next_plenum_date(datetime(2019, 8, 3))
        self.assertEqual(datetime(2019, 8, 4), plenum_date)
        self.assertEqual(1, delta.days)

        plenum_date, delta = plenum.get_next_plenum_date(datetime(2019, 8, 4))
        self.assertEqual(datetime(2019, 8, 4), plenum_date)
        self.assertEqual(0, delta.days)

        plenum_date, delta = plenum.get_next_plenum_date(datetime(2019, 8, 5))
        self.assertEqual(datetime(2019, 9, 1), plenum_date)
        self.assertEqual(27, delta.days)

        plenum_date, delta = plenum.get_next_plenum_date(datetime(2019, 8, 6))
        self.assertEqual(datetime(2019, 9, 1), plenum_date)
        self.assertEqual(26, delta.days)

        plenum_date, delta = plenum.get_next_plenum_date(datetime(2019, 8, 7))
        self.assertEqual(datetime(2019, 9, 1), plenum_date)
        self.assertEqual(25, delta.days)

        plenum_date, delta = plenum.get_next_plenum_date(datetime(2019, 8, 25))
        self.assertEqual(datetime(2019, 9, 1), plenum_date)
        self.assertEqual(7, delta.days)

        plenum_date, delta = plenum.get_next_plenum_date(datetime(2019, 8, 31))
        self.assertEqual(datetime(2019, 9, 1), plenum_date)
        self.assertEqual(1, delta.days)

        plenum_date, delta = plenum.get_next_plenum_date(datetime(2019, 9, 1))
        self.assertEqual(datetime(2019, 9, 1), plenum_date)
        self.assertEqual(0, delta.days)

        plenum_date, delta = plenum.get_next_plenum_date(datetime(2019, 9, 2))
        self.assertEqual(datetime(2019, 10, 6), plenum_date)
        self.assertEqual(34, delta.days)

        plenum_date, delta = plenum.get_next_plenum_date(datetime(2019, 9, 3))
        self.assertEqual(datetime(2019, 10, 6), plenum_date)
        self.assertEqual(33, delta.days)

        plenum_date, delta = plenum.get_next_plenum_date(datetime(2019, 9, 4))
        self.assertEqual(datetime(2019, 10, 6), plenum_date)
        self.assertEqual(32, delta.days)

        plenum_date, delta = plenum.get_next_plenum_date(datetime(2019, 9, 5))
        self.assertEqual(datetime(2019, 10, 6), plenum_date)
        self.assertEqual(31, delta.days)

        plenum_date, delta = plenum.get_next_plenum_date(datetime(2019, 9, 6))
        self.assertEqual(datetime(2019, 10, 6), plenum_date)
        self.assertEqual(30, delta.days)
