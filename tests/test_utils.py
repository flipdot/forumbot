import unittest
import utils


class TestTopicExists(unittest.TestCase):

    def setUp(self) -> None:
        self.topics = ['Wie funktioniert ein Plenum?', '2019-11-03 <strike>Plenum</strike> Vollversammlung',
                       '2019-10-13 Plenum', '2019-10-06 Plenum', '2019-09-08 Plenum', '2019-09-01 Plenum',
                       '2019-08-04 Plenum', '2019-07-07 Plenum',
                       '[POLL] [BIS 17.2.] Plenum 1x im Monat. Welcher Wochentag?', '2019-06-09 Plenum',
                       '2019-05-05 - Plenum nach VV', 'Ordentliche Vollversammlung 2019 am 5.5.2019 um 16:00',
                       '2019-04-07 Plenum', '[2019-03-03] Plenum', 'Themensammlung für Plenum 2018-03',
                       '2019-02-10, 17:00 Plenum',
                       'Festhalten Ergebnis Spontanplenum: Was gehört in unser Blog, was nicht?',
                       '[erledigt] Wo ist der Accuschrauber aus der Werkstatt?', '2018-07-31 Plenum (Getränkepreise)',
                       '[2018-05-29] Besprechung / Plenum HackWat!', '2018-05-08 Plenum',
                       'Ordentliche Mitgliederversammlung Donnerstag 2018-04-12 um 20:00',
                       '2018-02-20 Plenum (Neues Event)', '2017-11-14 Plenum', '2017-10-31 Plenum',
                       '2017-10-24 Plenum [verschoben]', '2017-08-29 Plenum', '2017-08-01 Plenum',
                       'Ordentliche Vollversammlung 2016 am 27.04.2017 um 20:00', 'Vollversammlung 2.11.2016 18:00']

    def test_exact_match(self):
        self.assertTrue(utils.topic_exists('2019-08-04 Plenum', self.topics))
        self.assertTrue(utils.topic_exists('2019-09-08 Plenum', self.topics))
        self.assertTrue(utils.topic_exists('2019-10-13 Plenum', self.topics))
        # This is in the future, so it should not yet exist
        self.assertFalse(utils.topic_exists('2019-11-03 Plenum', self.topics))
