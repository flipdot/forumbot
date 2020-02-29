# flipdot Plenum {{ plenum_date.strftime('%Y-%m-%d') }}

## Meta

- Moderatorin / Rednerliste: @flipbot
- Zeitwächterin: @flipbot
- Anwesend:
  - 0 Mitglieder
  - Keine Gäste
- Beginn: 18:xx

## Tagesordnungspunkte

### Vorstellungsrunde und Mitgliedsanträge [von @vertrauensstufe_0] (10 min)

{% for topic in topics %}
### {{ topic.title }} [von @{{ topic.author or 'flipbot' }}] (15 min)

#### Darüber möchte ich sprechen
- Lorem
- Ipsum

#### Darüber wurde während des Plenums gesprochen
- Thema wurde nicht besprochen

{% endfor %}