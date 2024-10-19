Danke für die Teilnahme am Plenum! Das Protokoll ist jetzt im Eingangspost verfügbar, scroll doch einmal nach ganz oben :)

Diese Themen wurden besprochen:

{%- for topic in discussed_topics %}
- {{ topic['title'] }} [von @{{ topic['author'] or 'flipbot' }}]
{%- endfor %}
{% if undiscussed_topics %}
Diese Themen wurden nicht mehr besprochen:

{%- for topic in undiscussed_topics %}
- {{ topic['title'] }} [von @{{ topic['author'] or 'flipbot' }}]
{%- endfor %}

Die Titel der unbesprochenen Themen werde ich zum Pad für das nächste Plenum hinzufügen.
{% else %}
Unbesprochene Themen gab's keine, nice!
{% endif %}
