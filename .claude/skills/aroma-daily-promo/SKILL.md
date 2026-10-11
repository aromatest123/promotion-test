---
name: aroma-daily-promo
description: Create today's Aroma Mooresville promo poster from the menu, upload it to GitHub, and post it to the Aroma Facebook Page via Zapier. Use for the daily 10 AM promo run or when asked to post today's Aroma promo.
---

# Aroma Mooresville — daily promo poster

Builds one promo poster per day from the Aroma Indian Grill & Bar menu, saves it in
GitHub (`aromatest123/promotion-test`) so it has a public image URL, and posts it to the
Facebook Page through Zapier. Target post time: ~10:00 AM America/New_York.

## Validated fixed values
- GitHub repo: `aromatest123/promotion-test`, branch `main`, clone to `/home/claude/promotion-test`
- Zapier app (Facebook): selected_api `FacebookV2CLIAPI`, action `page_photo`,
  tool_name `facebook_pages_create_page_photo`
- Facebook Page: "Aroma posters", page id `1367259746471350`
- Zapier app (Instagram): selected_api `InstagramBusinessCLIAPI`, action `publish_media_v2`,
  tool_name `instagram_for_business_publish_photo_s` (only once an IG Business account is linked)

## How the promo is chosen (generator/generate.py)
Weekday themes, each slot drawing randomly from real menu items (prices in generator/menu.json):
Mon Biryani · Tue Chicken Lollipop · Wed Tandoori · Thu Special ($21.99 owner offer) ·
Fri Family Feast · Sat Game Day platter · Sun South Indian Brunch.
Promo price = regular menu total minus 15–30%, rounded to .99, shown as "ONLY $X.99!" with a
"SAVE $X" badge. The pick is seeded by date, so re-running the same date gives the same poster.

## Runtime instructions
1. Get the repo: if `/home/claude/promotion-test` is not a git clone, attach it with
   `add_repo(owner="aromatest123", repo="promotion-test", access="push")` and
   `git clone --depth 1 https://github.com/aromatest123/promotion-test /home/claude/promotion-test`
   (10-minute timeout). If it exists, `git -C /home/claude/promotion-test pull --rebase`.
2. Ensure deps: `python3 -c "import playwright, PIL"`; if missing,
   `pip install --break-system-packages playwright pillow` (do NOT run `playwright install`;
   Chromium is preinstalled).
3. Run `cd /home/claude/promotion-test && python3 daily.py prepare` (add `--date YYYY-MM-DD`
   only if asked for a specific day). It prints one JSON line.
   - `"status": "already_posted"` → stop; report that today's promo was already posted.
   - `"status": "ready"` → continue with its `image_url` and `caption`.
4. Look at the generated JPG under `posters/` (Read the image) and sanity-check it:
   correct weekday, price visible, no overlapping text. If it is broken, stop and report.
5. Wait ~20 seconds (GitHub raw CDN), then post to Facebook:
   `execute_zapier_write_action(selected_api="FacebookV2CLIAPI", action="page_photo",
   tool_name="facebook_pages_create_page_photo",
   params={"page": "1367259746471350", "source": [image_url], "message": caption})`
   If it fails because the image could not be fetched, wait 60 s and retry once.
6. On success, record it:
   `python3 daily.py mark-posted --date <date> --platform facebook --post-id <post_id>`
7. Instagram (optional): call `inspect_zapier_actions(tool_name="instagram_for_business_publish_photo_s",
   enum_property="instagramPageId")`. If it returns an account, post with
   `params={"instagramPageId": <value>, "media": [image_url], "caption": caption}` and run
   mark-posted with `--platform instagram`. If none is returned, skip and mention it.
8. Report in one short message: date, theme, price, Facebook post id (and Instagram status).

## Constraints
- Post at most once per platform per date — always trust posted.json / `already_posted`.
- Never ask for or use account passwords; Zapier and the GitHub connection handle auth.
- Do not change prices, themes or menu data during a scheduled run; only post what the
  generator produced. Menu/price changes are made by editing generator/menu.json and
  generator/generate.py in a normal session.
- If Zapier or GitHub auth is broken, stop and report the exact error instead of retrying
  in a loop.
