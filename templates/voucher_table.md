Hi,

wie die letzten Jahre starten wir den Vorverkauf für den diesjährigen Chaos Communication Congress (36C3) mit einer Vocherphase vor dem öffentlichen Verkauf.

Als chaosnahe Gruppe bzw Ansprechpartner für eine solche (Kassel) bekommt ihr eine Liste von Voucher-Codes. Damit könnt ihr unter https://tickets.events.ccc.de ab **dem 21. Oktober um 18 Uhr MEZ** Tickets kaufen.

Die Voucher replizieren sich, das heißt: Im Bestellvorgang könnt ihr eine Mailadresse nennen, an die wir einen weiteren Voucher senden sollen. 1-2 Tage nachdem wir den Zahlungseingang verbuchen, werden wir an diese Adresse einen weiteren (wieder replizierenden) Voucher versenden, falls die Voucherphase noch nicht beendet ist. Die Voucherphase endet am **7. November, oder früher, wenn das Kontingent aufgebraucht ist** vorbei.

**Bitte verteilt die Voucher in eurem Umfeld!** Das heißt innerhalb der Gruppe, aber bitte auch in eurem sozialen und geographischen Umfeld, das nicht anders angebunden ist. Diese Voucher sind explizit **nicht nur für eure Mitglieder** gedacht!


| Voucher | Aktuell bei | seit | Für n Personen |
| ------- | ----------- | ---- | -------------- |
{% for voucher in vouchers -%}
| #{{ loop.index }} | {{ voucher.owner or '' }} | {{ voucher.received.strftime('%c') if voucher.received else '' }} | {{ voucher.persons or '' }} |
{% endfor -%}