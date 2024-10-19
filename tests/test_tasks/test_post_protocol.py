import unittest

from tasks.plenum.post_protocol import parse_protocol


class TestParseProtocol(unittest.TestCase):

    def setUp(self) -> None:
        pass

    def test_parse_protocol(self):
        markdown_1 = """
# flipdot Plenum 2020-03-01

## Meta

- Moderatorin / Rednerliste: @flipbot
- Zeitwächterin: @flipbot
- Anwesend:
  - 0 Mitglieder
  - Keine Gäste
- Beginn: 18:xx

## Tagesordnungspunkte

### Vorstellungsrunde und Mitgliedsanträge [von @vertrauensstufe_0] (10 min)


### Wichtige Dinge [von @jemandem] (15 min)

**Darüber möchte ich sprechen:**
- Dinge sind wichtig
- Sie sollten getan werden

**Darüber wurde während des Plenums gesprochen:**
- Okay, machen wir


### Weniger wichtige Dinge [von @unwichtig] (15 min)

**Darüber möchte ich sprechen:**
- Getane Dinge sind besser als ungetane Dinge

**Darüber wurde während des Plenums gesprochen:**
- Thema wurde nicht besprochen
"""
        markdown_2 = """
# flipdot Plenum 2020-03-01

## Meta

- Moderatorin / Rednerliste: @flipbot
- Zeitwächterin: @flipbot
- Anwesend:
  - 0 Mitglieder
  - Keine Gäste
- Beginn: 18:xx

## Tagesordnungspunkte

### Vorstellungsrunde und Mitgliedsanträge [von @vertrauensstufe_0] (10 min)


### Wichtige Dinge [von @jemandem] (15 min)

#### Darüber möchte ich sprechen
- Dinge sind wichtig
- Sie sollten getan werden

#### Darüber wurde während des Plenums gesprochen
- Okay, machen wir


### Weniger wichtige Dinge [von @unwichtig] (15 min)

#### Darüber möchte ich sprechen
- Getane Dinge sind besser als ungetane Dinge

#### Darüber wurde während des Plenums gesprochen
- Thema wurde nicht besprochen

## Pizza

"""
        markdown_3 = """
# flipdot Plenum 2020-03-01

## Meta

- Moderatorin / Rednerliste: @flipbot
- Zeitwächterin: @flipbot
- Anwesend:
  - 0 Mitglieder
  - Keine Gäste
- Beginn: 18:xx

## Tagesordnungspunkte

### Vorstellungsrunde und Mitgliedsanträge (10 min)


### Nächsten Monat ist etwas! [von @someone] (? min)

- Neue Teile
- Weitere Themen?


### Dingens Anfrage [@someone]

siehe Forum

### Postfach com@flipdot.org

#### Darüber möchte ich sprechen
- X
    - Y
    - Z
        - Blub
- Dinge

#### Darüber wurde während des Plenums gesprochen
- Thema wurde nicht besprochen
"""
        expected_1 = {
            "topics": [
                {
                    "title": "Wichtige Dinge",
                    "author": "jemandem",
                    "was_discussed": True,
                },
                {
                    "title": "Weniger wichtige Dinge",
                    "author": "unwichtig",
                    "was_discussed": False,
                },
            ]
        }
        expected_2 = expected_1
        expected_3 = {
            "topics": [
                {
                    "title": "Nächsten Monat ist etwas!",
                    "author": "someone",
                    "was_discussed": True,
                },
                {
                    "title": "Dingens Anfrage",
                    "author": "someone",
                    "was_discussed": True,
                },
                {
                    "title": "Postfach com@flipdot.org",
                    "author": None,
                    "was_discussed": False,
                },
            ]
        }
        self.assertEqual(parse_protocol(markdown_1), expected_1)
        self.assertEqual(parse_protocol(markdown_2), expected_2)
        self.assertEqual(parse_protocol(markdown_3), expected_3)
