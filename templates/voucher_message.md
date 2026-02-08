Hi,

unter https://tickets.events.ccc.de kannst du dir dein Ticket kaufen. Nutze dafür diesen Voucher:

{{ voucher.voucher }}

- Bei der Bestellung wirst du gefragt, an wen du deinen **replizierten Voucher** geben möchtest.
  - Gib **diese E-Mail-Adresse** an: **{{ voucher_ingress_email }}**
- **Bezahle** dein Ticket **sofort** nach Bestellung

Solltest du nicht ASAP bestellen und bezahlen können, schicke den Voucher bitte an mich zurück.
Andernfalls warten andere vergeblich auf ihre Chance, sich ein Ticket kaufen zu können. Das wäre schade.

{% if voucher.old_owner %}
Falls es Probleme mit dem Voucher gibt, wende dich bitte an @{{ voucher.old_owner }}. Von dieser Person stammt der Voucher.
{% endif %}
Danke und viel Spaß beim Congress!
