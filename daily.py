"""
Aroma Mooresville — daily promo runner.

  python3 daily.py prepare [--date YYYY-MM-DD]
      Builds today's poster (America/New_York date), saves it as
      posters/<date>_<Day>.jpg + .json, commits and pushes to GitHub, then prints
      one JSON line: {"status": "ready", "date", "image_url", "caption", ...}
      If that date is already in posted.json it prints {"status": "already_posted"}.

  python3 daily.py mark-posted --date YYYY-MM-DD --platform facebook --post-id ID
      Records a successful post in posted.json and pushes it.
"""
import argparse, datetime as dt, json, pathlib, shutil, subprocess, sys, time
from zoneinfo import ZoneInfo

REPO = pathlib.Path(__file__).resolve().parent
POSTERS = REPO / "posters"
LOG = REPO / "posted.json"
OWNER_REPO = "aromatest123/promotion-test"
BRANCH = "main"
sys.path.insert(0, str(REPO / "generator"))


def git(*args, check=True):
    r = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit(f"git {' '.join(args)} failed:\n{r.stdout}\n{r.stderr}")
    return r


def push(msg):
    git("add", "-A")
    if not git("status", "--porcelain").stdout.strip():
        return
    git("-c", "user.name=Aroma Promo Bot", "-c", "user.email=aromatest00@gmail.com", "commit", "-qm",
        msg + "\n\nCo-Authored-By: Claude <noreply@anthropic.com>")
    for attempt in range(3):
        git("fetch", "origin", BRANCH, check=False)
        git("rebase", f"origin/{BRANCH}", check=False)
        if git("push", "origin", f"HEAD:{BRANCH}", check=False).returncode == 0:
            return
        time.sleep(5 * (attempt + 1))
    raise SystemExit("push failed after 3 attempts")


def load_log():
    return json.loads(LOG.read_text()) if LOG.exists() else {}


def today_et():
    return dt.datetime.now(ZoneInfo("America/New_York")).date()


def prepare(day):
    log = load_log()
    if log.get(day.isoformat(), {}).get("facebook"):
        print(json.dumps({"status": "already_posted", "date": day.isoformat(), **log[day.isoformat()]}))
        return
    import generate  # generator/generate.py
    from PIL import Image
    o = generate.run([day])[0]
    POSTERS.mkdir(exist_ok=True)
    stem = f"{day.isoformat()}_{o['day']}"
    Image.open(generate.OUT / o["poster"]).convert("RGB").save(POSTERS / f"{stem}.jpg", quality=90, optimize=True)
    (POSTERS / f"{stem}.json").write_text(json.dumps(o, indent=2, ensure_ascii=False))
    shutil.rmtree(generate.OUT, ignore_errors=True)
    push(f"Promo poster for {day.isoformat()} ({o['day']})")
    sha = git("rev-parse", "HEAD").stdout.strip()
    print(json.dumps({
        "status": "ready", "date": day.isoformat(), "day": o["day"],
        "headline": o["headline"], "price": o["price"], "regular": o["regular"],
        # commit-pinned URL: immune to CDN caching of the branch URL
        "image_url": f"https://raw.githubusercontent.com/{OWNER_REPO}/{sha}/posters/{stem}.jpg",
        "caption": o["caption"],
    }, ensure_ascii=False))


def mark_posted(day, platform, post_id):
    log = load_log()
    log.setdefault(day, {})[platform] = {"post_id": post_id, "at": dt.datetime.now(ZoneInfo("America/New_York")).isoformat(timespec="seconds")}
    LOG.write_text(json.dumps(log, indent=2))
    push(f"Log {platform} post for {day}")
    print(json.dumps({"status": "logged", "date": day, "platform": platform, "post_id": post_id}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare"); p.add_argument("--date")
    m = sub.add_parser("mark-posted"); m.add_argument("--date", required=True)
    m.add_argument("--platform", required=True); m.add_argument("--post-id", required=True)
    a = ap.parse_args()
    if a.cmd == "prepare":
        prepare(dt.date.fromisoformat(a.date) if a.date else today_et())
    else:
        mark_posted(a.date, a.platform, a.post_id)
