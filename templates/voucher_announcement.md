Beep boop,

ich bin der Voucherbot für den Congress. Der Congress ist immer im Dezember zwischen den Jahren.

Wir haben bereits Oktober. Erfahrungsgemäß beginnt im Oktober die Verteilung der Voucher.

Ein Voucher ermöglicht euch, ein Ticket zu erwerben. In den letzten Jahren wurde es in der Regel so gehandhabt, dass ein Voucher nach Bezahlung einen weiteren Voucher generiert. So werden die Voucher von Person zu Person in Form einer Kette weitergegeben.

Ich helfe euch, effiziente Ketten zu bilden. Dazu muss ich wissen, wer von euch Interesse an einem Voucher hat!

{% if voucher_phase_start and voucher_phase_end %}
**Voucherphase**: {{ voucher_phase_start }} bis {{ voucher_phase_end }}
{% else %}
**Voucherphase**: Unbekannt. Schreibe mir eine PN mit dem Text **VOUCHER-PHASE: YYYY-MM-DD bis YYYY-MM-DD**
{% endif %}

# Status

{% if not vouchers %}

{% if not total_persons_reported %}

## Bedarfsermittlung

- **Schreib mir eine PN**
- Schreibe in deine Nachricht **VOUCHER-BEDARF: X**, wobei das X für die *Gesamtzahl* Personen steht, für die du ein Ticket kaufen willst.
  Wenn du also z.B. für dich und einen Freund je ein Ticket benötigst, schreibe "*VOUCHER-BEDARF: 2*"
- Ich setze dich auf die Interessentenliste und informiere dich, sobald ein Voucher für dich verfügbar ist

[details="Für Organisatoren: Bedarfsermittlung"]
- Wenn der Bedarf von flipdot feststeht, übermittle die Anzahl an die CCC Organisatoren
  - Bitte finde selber raus, wie das dieses Jahr funktioniert. Wahrscheinlich hat flipdot eine Mail mit Informationen bekommen
- Sobald du es erfolgreich getan hast, schicke mir eine PN mit dem Text **VOUCHER-GESAMT-BEDARF-GEMELDET: X**, wobei das X für die *Gesamtzahl* Personen steht, die du gemeldet hast
[/details]

Das ist die Liste der **insgesamt {{ total_persons_in_queue }}** Interessenten:

{% else %}

Wir haben an die CCC Organisatoren gemeldet, dass unser **Bedarf bei {{ total_persons_reported }} Personen** liegt.

Jetzt warten wir darauf, dass wir Voucher erhalten.

## Warteliste ({{ total_persons_in_queue }})

Die Bedarfsliste wurde **zufällig gemischt**, und daraus diese **Warteliste** erstellt.
Wenn du dich zur Bedarfsbestimmung nicht gemeldet hast, kannst du dich noch immer **ans Ende** der Liste setzen lassen.

{% endif %}

{% for item in queue %}
  - @{{ item.name }}{% if item.persons > 1 %} + {{ item.persons - 1 }}{% endif %}
{%- endfor %}
  - *Füge dich hier ein, indem du @{{ bot_name }} eine PN mit **VOUCHER-BEDARF: 1** schickst.*


[details="Ich habe eine Liste mit allen Vouchern"]
Ich, der Bot, übernehme die Verteilung! **Schick @{{ bot_name }} eine PN** mit dem Titel **VOUCHER-LISTE**.
Pack alle Voucher die du hast in eine einzige Nachricht!
Wenn ich deine Nachricht verstehen konnte, schreibe ich dir zurück und aktualisiere diesen Post.
[/details]

{% else %}
Wir haben {{ vouchers | length }} Voucher zur Verfügung! Hier sind sie:

| Voucher | Aktuell bei | erhalten | Für n Personen |
| ------- | ----------- |----------| -------------- |
{% for voucher in vouchers -%}
| #{{ loop.index }} | @{{ voucher.owner or bot_name }} | {{ voucher.received_at.strftime("%Y-%m-%d %H:%M") }} | {{ voucher.persons or '' }} |
{% endfor %}

Du bist oben in der Liste? Dann hast du eine PN von mir bekommen! **Bitte kaufe schnellstmöglich deine Tickets!** https://tickets.events.ccc.de/

{% if image_url %}
![gantt]({{ image_url }})
{% if not voucher_exhausted_at %}
Das Kontingent ist aufgebraucht? Schreibe mir eine PN mit dem Text `VOUCHER-EXHAUSTED-AT YYYY-MM-DD HH:MM`.
{% endif %}
{% elif not voucher_phase_start or not voucher_phase_end %}
**Hinweis:** Bitte schreibe mir eine PN mit dem Text
```
VOUCHER-PHASE: YYYY-MM-DD bis YYYY-MM-DD
```
Dann poste ich hier eine hübsche Grafik.
{% endif %}

## Warteliste

Die Bedarfsliste wurde **zufällig gemischt**, und daraus diese **Warteliste** erstellt.
Wenn du dich zur Bedarfsbestimmung nicht gemeldet hast, kannst du dich noch immer **ans Ende** der Liste setzen lassen.

Folgende Leute warten darauf, dass eine Person aus der obigen Tabelle einen Voucher weitergibt
{% for item in queue %}
  - @{{ item.name }}{% if item.persons > 1 %} + {{ item.persons - 1 }}{% endif %}
{%- endfor %}
  - *Füge dich hier ein, indem du @{{ bot_name }} eine PN mit **VOUCHER-BEDARF: 1** schickst.*
{% endif %}

# Wer kümmert sich?

Ich bin ein Hilfsbot – kein vollautomatischer Voucherbot! **Ein Mensch muss Verantwortung übernehmen**, und sich insbesondere um **die Kommunikation mit dem CCC** kümmern, um eine Voucherliste zu erhalten!

[color=#ff0000]Bitte **nutzt diesen Thread**, um euch darauf zu einigen, **wer das erledigt!**[/color] Von nix kommt nix.
