# Aroma Mooresville — daily promo posters

Every day at ~10 AM ET a scheduled Claude task runs the `aroma-daily-promo` skill
(`.claude/skills/aroma-daily-promo/SKILL.md`):

1. `python3 daily.py prepare` — picks today's themed combo from the menu, renders a
   1080×1080 poster (`generator/`), commits it to `posters/`, prints the public image URL + caption.
2. Posts the poster to the Aroma Facebook Page via Zapier.
3. `python3 daily.py mark-posted ...` — logs the post in `posted.json` (prevents double posts).

Edit prices/items in `generator/menu.json`, themes and discounts in `generator/generate.py`
(`THEMES`), and the look in `generator/poster.html`.
Fonts in `generator/fonts` are SIL Open Font License (see OFL-*.txt).
