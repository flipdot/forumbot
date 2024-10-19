Beep boop,

ich bin der Voucherbot für den Congress. Der Congress ist immer im Dezember zwischen den Jahren.

Wir haben bereits Oktober. Erfahrungsgemäß beginnt im Oktober die Verteilung der Voucher.

Ein Voucher ermöglicht euch, ein Ticket zu erwerben. In den letzten Jahre wurde es in der Regel so gehandhabt, dass ein Voucher nach Bezahlung einen weiteren Voucher generiert. So werden die Voucher von Person zu Person in Form einer Kette weitergegeben.

Ich helfe euch, effiziente Ketten zu bilden. Dazu muss ich wissen, wer von euch Interesse an einem Voucher hat!

# Status

{% if not vouchers %}

## Bedarfsermittlung

- **Schreib mir eine PN**
- Schreibe in deine Nachricht **VOUCHER-BEDARF: X**, wobei das X für die *Gesamtzahl* Personen steht, für die du ein Ticket kaufen willst.
  Wenn du also z.B. für dich und einen Freund je ein Ticket benötigst, schreibe "*VOUCHER-BEDARF: 2*"
- Ich setze dich auf die Interessentenliste und informiere dich, sobald ein Voucher für dich verfügbar ist

Das ist die Liste der **insgesamt {{ total_persons_in_queue }}** Interessenten:

{% for item in queue %}
  - @{{ item.name }}{% if item.persons > 1 %} + {{ item.persons - 1 }}{% endif %}
{%- endfor %}

## Du hast eine Liste mit allen Vouchern?

Ich übernehme die Verteilung! **Schick mir eine PN** mit dem Titel **VOUCHER-LISTE**.
Pack alle Voucher die du hast in eine einzige Nachricht!
Wenn ich deine Nachricht verstehen konnte, schreibe ich dir zurück und aktualisiere diesen Post.

{% else %}
Wir haben {{ vouchers | length }} Voucher bekommen! Hier sind sie:

| Voucher | Aktuell bei | seit | Für n Personen |
| ------- | ----------- | ---- | -------------- |
{% for voucher in vouchers -%}
| #{{ loop.index }} | {{ voucher.owner or '' }} | {{ voucher.received.strftime('%c') if voucher.received else '' }} | {{ voucher.persons or '' }} |
{% endfor %}

Du bist oben in der Liste? Dann hast du eine PN von mir bekommen! **Bitte kaufe schnellstmöglich deine Tickets!** https://tickets.events.ccc.de/

## Warteliste

Ich habe die Bedarfsliste **zufällig** gemischt, und daraus diese Warteliste gebaut.
Wenn du dich zur Bedarfsbestimmung nicht gemeldet hast, kannst du dich noch immer ans Ende der Liste setzen lassen.

Folgende Leute warten darauf, dass eine Person aus der obigen Tabelle einen Voucher weitergibt
{% for item in queue %}
  - @{{ item.name }}{% if item.persons > 1 %} + {{ item.persons - 1 }}{% endif %}
{%- endfor %}
{% endif %}
