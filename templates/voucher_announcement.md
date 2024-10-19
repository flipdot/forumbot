Beep boop,

ich bin der Voucherbot für den Congress. Der Congress ist immer im Dezember zwischen den Jahren.

Wir haben bereits Oktober. Erfahrungsgemäß beginnt im Oktober die Verteilung der Voucher.

Ein Voucher ermöglicht euch, ein Ticket zu erwerben. In den letzten Jahre wurde es in der Regel so gehandhabt,
dass ein Voucher nach Bezahlung einen weiteren Voucher generiert. So werden die Voucher von Person zu Person
in Form einer Kette weitergegeben.

Ich helfe euch, effiziente Ketten zu bilden. Dazu muss ich wissen, wer von euch Interesse an einem Voucher habt!

# Bedarfsermittlung

- **Schreib mir eine PN** mit dem Titel **VOUCHER-BEDARF**
- Schreibe in deine Nachricht **Personen: X**, wobei das X für die *Gesamtzahl* Personen steht, für die du ein Ticket kaufen willst.
  Wenn du also z.B. für dich und einen Freund je ein Ticket benötigst, schreibe *Personen: 2*


# Status

{% if waiting_for_vouchers %}
Ich habe noch keine Voucherliste erhalten. Hoffentlich hat der Verkauf noch nicht begonnen.

## Du hast eine Liste mit allen Vouchern?

Ich übernehme die Verteilung! **Schick mir eine PN** mit dem Titel **VOUCHER-LISTE**.
Pack alle Voucher die du hast in eine einzige Nachricht!
Wenn ich deine Nachricht verstehen konnte, schreibe ich dir zurück und aktualisiere diesen Post.

{% elif sale_started %}
Der Verkauf ist im Gange! Wir haben folgende Voucher:

| Voucher | Aktuell bei | seit | Für n Personen |
| ------- | ----------- | ---- | -------------- |
{% for voucher in vouchers -%}
| #{{ loop.index }} | {{ voucher.owner or '' }} | {{ voucher.received.strftime('%c') if voucher.received else '' }} | {{ voucher.persons or '' }} |
{% endfor -%}

## Warteliste

Folgende Leute warten darauf, dass eine Person aus der obigen Tabelle einen Voucher weitergibt
{% for name in queue %}
  - {{ name }}
{%- endfor %}
{% elif sale_over %}
Der Voucher-Verkauf ist vorbei. Vielleicht gibt es noch einen öffentlichen Verkauf, ohne Voucher.

Ich drück dir die Daumen! Ansonsten wünsche ich allen Beteiligten viel Spaß und ich melde mich nächstes Jahr wieder :)
{% endif %}
