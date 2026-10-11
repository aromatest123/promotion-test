"""
Aroma Mooresville — daily promo poster generator.

Each weekday has a theme (chosen for Mooresville / Lake Norman diners: slow-Monday
traffic builders, wings-style lollipops, family weekends, game-day groups, Sunday
South-Indian brunch). Every slot in a theme has several menu options; the engine
picks one at random each run, totals the regular menu prices, and sets a promo
price ~18-25% below regular, rounded to .99.

Usage:
  python generate.py --week 2026-10-12            # Mon..Sun samples
  python generate.py --date 2026-10-15            # a single day
  python generate.py --date 2026-10-15 --seed 7   # reproducible pick
"""
import argparse, base64, datetime as dt, json, math, random, pathlib, html

ROOT = pathlib.Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
FONTS = ROOT / "fonts"
OUT = ROOT / "out"
MENU = json.loads((ROOT / "menu.json").read_text())["items"]

# ---------------------------------------------------------------- themes
# slot option = (column text, [(item_key, qty), ...], image_key or None)
THEMES = {
    0: dict(  # Monday
        script="Monday", headline="BIRYANI",
        hook="Start the week the Hyderabadi way",
        discount=(0.15, 0.2),
        slots=[
            [("Hyderabadi\nChicken Dum Biryani", [("chk_dum_biryani", 1)], "biryani"),
             ("Hyderabadi\nGoat Dum Biryani", [("goat_dum_biryani", 1)], "biryani"),
             ("Chicken 65\nDum Biryani", [("c65_biryani", 1)], "biryani"),
             ("Vijayawada\nChicken Biryani", [("vjw_biryani", 1)], "biryani"),
             ("Paneer or Veg\nDum Biryani", [("paneer_biryani", 1)], "biryani")],
            [("Mirchi ka Salan\n& Raita", [], None)],
            [("1 Mango\nLassi", [("mango_lassi", 1)], "mango_lassi")],
        ],
        layout=[("biryani", 230, 45, 300), ("mango_lassi", 730, 55, 290)],
    ),
    1: dict(  # Tuesday
        script="Tuesday", headline="LOLLIPOP",
        hook="Our answer to wings",
        discount=(0.2, 0.25),
        slots=[
            [("Guntur Chicken\nLollipop  🌶", [("lolli_guntur", 1)], "lollipop"),
             ("Tandoori Chicken\nLollipop", [("lolli_tandoori", 1)], "lollipop"),
             ("Mughalai Chicken\nLollipop", [("lolli_mughalai", 1)], "lollipop"),
             ("Vijayawada Chicken\nLollipop  🌶", [("lolli_vjw", 1)], "lollipop"),
             ("Chilli Chicken\nLollipop", [("lolli_chilli", 1)], "lollipop")],
            [("Peri-Peri\nFries", [("peri_fries", 1)], None)],
            [("1 Soft\nDrink", [("soft_drink", 1)], "coke")],
        ],
        layout=[("lollipop", 200, 45, 300), ("coke", 720, 50, 290)],
    ),
    2: dict(  # Wednesday
        script="Wednesday", headline="TANDOORI",
        hook="Fresh from our clay oven",
        discount=(0.18, 0.22),
        slots=[
            [("Tandoori\nChicken", [("tandoori_chicken", 1)], "tandoori_chicken"),
             ("Chicken\nTikka Kabab", [("chicken_tikka", 1)], "tandoori_chicken"),
             ("Malai Chicken\nKabab", [("malai_kabab", 1)], "tandoori_chicken"),
             ("Paneer\nTikka", [("paneer_tikka", 1)], "paneer_tikka")],
            [("1 Butter or\nGarlic Naan", [("garlic_naan", 1)], "naan")],
            [("1 Mango\nLassi", [("mango_lassi", 1)], "mango_lassi")],
        ],
        layout=[("@0", 40, 50, 250), ("naan", 560, 60, 260), ("mango_lassi", 900, 60, 260)],
    ),
    3: dict(  # Thursday (owner's existing offer, fixed price)
        script="Thursday", headline="SPECIAL",
        hook=None, fixed_price=21.99,
        slots=[
            [("Choose 1\nChicken or\nPaneer Entrée", [("entree_choice", 1)], "curry_rice")],
            [("1 × 8 oz\nAppetizer", [("appetizer_8oz", 1)], "chicken65")],
            [("1 Butter\nNaan", [("butter_naan", 1)], "naan")],
        ],
        layout=[("kadai_curry", 20, 40, 290), ("naan", 580, 110, 240), ("chicken65", 560, 40, 200)],
    ),
    4: dict(  # Friday
        script="Family Friday", headline="FEAST",
        hook="Feeds 4 · Perfect for the whole family",
        discount=(0.17, 0.2),
        slots=[
            [("2 Entrées\nChicken, Paneer\nor Veg", [("entree_choice", 2)], "kadai_curry")],
            [("1 Hyderabadi\nChicken Dum\nBiryani", [("chk_dum_biryani", 1)], "biryani"),
             ("1 Hyderabadi\nGoat Dum\nBiryani", [("goat_dum_biryani", 1)], "biryani")],
            [("Bread Basket\n+ Gulab Jamun", [("bread_basket", 1), ("gulab_jamun", 1)], "gulab_jamun")],
        ],
        layout=[("biryani", 0, 50, 260), ("naan", 700, 120, 200), ("kadai_curry", 340, 40, 230), ("gulab_jamun", 800, 35, 190, "round")],
    ),
    5: dict(  # Saturday
        script="Saturday", headline="GAME DAY",
        hook="Bring the crew — platter for 4",
        discount=(0.22, 0.25),
        slots=[
            [("Any 3\nAppetizers", [("appetizer_any", 3)], "chicken65")],
            [("Mix & Match\nVeg or Non-Veg", [], None)],
            [("4 Soft\nDrinks", [("soft_drink", 4)], "coke")],
        ],
        layout=[("tandoori_chicken", 700, 120, 160), ("lollipop", 10, 50, 260), ("chicken65", 380, 40, 200), ("coke", 900, 40, 230)],
    ),
    6: dict(  # Sunday
        script="Sunday", headline="BRUNCH",
        hook="South Indian tiffin, all day",
        discount=(0.25, 0.3),
        slots=[
            [("Any Dosa\nMasala or Onion", [("dosa", 1)], "cone_dosa")],
            [("2 Idly with\nSambar & Chutney", [("idly", 1)], None)],
            [("Masala Chai\nor Coffee", [("masala_chai", 1)], "chai")],
        ],
        layout=[("cone_dosa", 200, 45, 320), ("chai", 590, 55, 230)],
    ),
}


def promo_price(regular, lo, hi, rnd):
    target = regular * (1 - rnd.uniform(lo, hi))
    return max(math.floor(target) - 0.01, 0.99)


def build_offer(day: dt.date, rnd: random.Random):
    t = THEMES[day.weekday()]
    cols, regular, picks = [], 0.0, {}
    for i, slot in enumerate(t["slots"]):
        text, items, img = rnd.choice(slot)
        cols.append(text)
        if img:
            picks[f"@{i}"] = img
        for key, qty in items:
            regular += MENU[key]["price"] * qty
    price = t.get("fixed_price") or promo_price(regular, *t["discount"], rnd)
    return dict(date=day.isoformat(), day=day.strftime("%A"), script=t["script"],
                headline=t["headline"], hook=t["hook"], columns=cols,
                regular=round(regular, 2), price=price, layout=t["layout"], picks=picks)


def b64(name):
    return "data:image/png;base64," + base64.b64encode((ASSETS / f"{name}.png").read_bytes()).decode()


def render_html(o):
    imgs = []
    for spec in o["layout"]:
        key, left, bottom, h = spec[:4]
        bottom += 32; h = round(h * 0.93)
        key = o["picks"].get(key, key)
        if len(spec) > 4 and spec[4] == "round":
            style = f"width:{h}px;height:{h}px;object-fit:cover;border-radius:50%;border:5px solid #c99a4a;"
        else:
            style = f"height:{h}px;"
        imgs.append(f'<img class="dish" src="{b64(key)}" style="left:{left}px;bottom:{bottom}px;{style}">')
    cols = "".join(f'<div class="col">{html.escape(c).replace(chr(10), "<br>")}</div>' for c in o["columns"])
    save = o["regular"] - o["price"]
    badge = f'<div class="save">SAVE<br><b>${save:.0f}</b></div>' if save >= 3 else ""
    hook = f'<div class="hook">{html.escape(o["hook"])}</div>' if o["hook"] else ""
    d = dt.date.fromisoformat(o["date"])
    fine = f'Valid {d.strftime("%a %b")} {d.day} only · Not valid with other offers · Tax extra'
    return TEMPLATE.format(logo=b64("logo"), script=html.escape(o["script"]), headline=html.escape(o["headline"]),
                           cols=cols, price=f'{o["price"]:.2f}', badge=badge, hook=hook,
                           dishes="".join(imgs), fine=fine).replace("<style>", "<style>" + FONT_CSS, 1)


TEMPLATE = (ROOT / "poster.html").read_text()

FONT_FACES = [("Great Vibes", "GreatVibes-Regular.ttf", "400", "normal"),
              ("Poppins", "Poppins-Medium.ttf", "500", "normal"), ("Poppins", "Poppins-SemiBold.ttf", "600", "normal"),
              ("Poppins", "Poppins-Bold.ttf", "700", "normal"), ("Poppins", "Poppins-ExtraBold.ttf", "800", "normal"),
              ("Poppins", "Poppins-Black.ttf", "900", "normal"),
              ("Playfair Display", "PlayfairDisplay.ttf", "400 900", "normal"),
              ("Playfair Display", "PlayfairDisplay-Italic.ttf", "400 900", "italic")]
FONT_CSS = "".join(f"@font-face{{font-family:'{f}';src:url('{(FONTS / p).as_uri()}');font-weight:{w};font-style:{st}}}"
                   for f, p, w, st in FONT_FACES)


def caption(o):
    items = " + ".join(c.replace("\n", " ") for c in o["columns"])
    extra = ["#Biryani #HyderabadiBiryani", "#ChickenLollipop #WingNight", "#Tandoori #TandooriChicken",
             "#ThursdaySpecial #ButterChicken", "#FamilyDinner #FridayFeast", "#GameDay #GameDayEats",
             "#Dosa #SundayBrunch"][dt.date.fromisoformat(o["date"]).weekday()]
    tags = f"#AromaMooresville #MooresvilleNC #LakeNorman #LKNEats #CharlotteFoodie #IndianFood {extra}"
    return (f'{o["day"]} {o["headline"].title()} at Aroma Indian Grill & Bar! 🔥\n'
            f'{items} — only ${o["price"]:.2f}.\n'
            f'Dine-in · Takeout · Delivery\n📍 128 Argus Lane, Mooresville NC · 📞 (704) 632-5045\n'
            f'Order: www.aromamooresville.com\n\n{tags}')


def run(days, seed=None):
    from playwright.sync_api import sync_playwright
    OUT.mkdir(exist_ok=True)
    results = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1080})
        for d in days:
            rnd = random.Random(seed if seed is not None else d.toordinal())
            o = build_offer(d, rnd)
            hp = OUT / f"{d.isoformat()}_{o['day']}.html"
            hp.write_text(render_html(o))
            pg.goto(hp.as_uri()); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(400)
            png = hp.with_suffix(".png"); pg.screenshot(path=str(png))
            o["caption"] = caption(o); o["poster"] = png.name
            o.pop("layout"); o.pop("picks")
            results.append(o); print(png.name, o["price"], "(reg", o["regular"], ")")
        b.close()
    (OUT / "posts.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--week"); ap.add_argument("--date"); ap.add_argument("--seed", type=int)
    a = ap.parse_args()
    if a.week:
        s = dt.date.fromisoformat(a.week)
        days = [s + dt.timedelta(i) for i in range(7)]
    else:
        days = [dt.date.fromisoformat(a.date) if a.date else dt.date.today()]
    run(days, a.seed)
