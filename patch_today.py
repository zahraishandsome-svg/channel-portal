"""Publish, per channel, whether today's uploads actually happened.

The runs table already records the outcome of every slot — success, skipped (the day's
slot was already done), no_content (nothing left to post) or failed. Nothing surfaced
it, so a channel could quietly miss uploads for days: ch8 returned no_content every day
for a week and it only showed up by counting videos by hand.

Published into status.json, which is already keyed by SHA-256 of the channel ID, so
this adds no identifying data to the public repo.
"""
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
SRC = Path(r"C:\Users\Zahid\projects\channel-portal\scripts\sync.py")

# ── 1. collect videos_per_day alongside the schedule ───────────────────────
OLD_WANTED = '''        wanted[ch["id"]] = {"tiktok": "@" + ch["tiktok_username"], "slots": slots}'''
NEW_WANTED = '''        wanted[ch["id"]] = {"tiktok": "@" + ch["tiktok_username"], "slots": slots,
                            "per_day": int(ch.get("videos_per_day") or len(slots) or 1)}'''

# ── 2. read today's runs + uploads out of the same database ────────────────
OLD_QUERY = '''        try:
            con = sqlite3.connect(tmp)
            rows = con.execute(
                "SELECT channel_id, youtube_video_id, posted_at FROM posted_videos "
                "WHERE status='uploaded' AND youtube_video_id IS NOT NULL "
                "ORDER BY posted_at DESC").fetchall()
            con.close()
        except Exception:
            continue'''
NEW_QUERY = '''        try:
            con = sqlite3.connect(tmp)
            rows = con.execute(
                "SELECT channel_id, youtube_video_id, posted_at FROM posted_videos "
                "WHERE status='uploaded' AND youtube_video_id IS NOT NULL "
                "ORDER BY posted_at DESC").fetchall()
            try:
                for cid, slot, st in con.execute(
                        "SELECT channel_id, slot, status FROM runs WHERE run_date=?",
                        (TODAY,)):
                    if cid in wanted:
                        today_runs.setdefault(cid, []).append((slot, st))
                for cid, cnt in con.execute(
                        "SELECT channel_id, COUNT(*) FROM posted_videos "
                        "WHERE status='uploaded' AND youtube_video_id IS NOT NULL "
                        "AND youtube_video_id != 'already_on_yt' AND posted_at LIKE ? "
                        "GROUP BY channel_id", (TODAY + "%",)):
                    if cid in wanted:
                        today_up[cid] = max(today_up.get(cid, 0), cnt)
            except Exception as e:
                print(f"    {f['name']}: no runs/today data ({e})")
            con.close()
        except Exception:
            continue'''

# ── 3. fold it into what gets published ────────────────────────────────────
OLD_FOUND = '''                found[cid] = {"tiktok": wanted[cid]["tiktok"],
                              "slots": wanted[cid]["slots"],
                              "video": vid, "at": at or ""}'''
NEW_FOUND = '''                found[cid] = {"tiktok": wanted[cid]["tiktok"],
                              "slots": wanted[cid]["slots"],
                              "per_day": wanted[cid]["per_day"],
                              "video": vid, "at": at or ""}'''

OLD_APPEND = '''    channels.append({"label": short, "id": cid, "tiktok": info["tiktok"],
                     "slots": info.get("slots") or []})'''
NEW_APPEND = '''    channels.append({"label": short, "id": cid, "tiktok": info["tiktok"],
                     "slots": info.get("slots") or []})
    today_by_id[cid] = _today_report(label, info)'''

HELPERS = '''
TODAY = time.strftime("%Y-%m-%d", time.gmtime())
today_runs = {}     # channel_id -> [(slot, status), …] for today
today_up = {}       # channel_id -> uploads recorded today


def _today_report(label, info):
    """What happened to today's uploads for one channel.

    'skipped' is not a miss — it is the per-day guard firing after a slot already
    succeeded, which is exactly what the retry jobs are supposed to hit."""
    expected = int(info.get("per_day") or 1)
    uploaded = today_up.get(label, 0)
    issues = []
    for slot, st in sorted(today_runs.get(label, [])):
        if st == "no_content":
            issues.append({"slot": slot, "why": "no new video to post"})
        elif st == "failed":
            issues.append({"slot": slot, "why": "upload failed"})
    # a slot that never ran at all is only a miss once its time has passed; the
    # portal knows the schedule, so just report the raw numbers and let it decide
    return {"expected": expected, "uploaded": uploaded, "issues": issues}

'''


def main():
    t = SRC.read_text(encoding="utf-8")
    assert "_today_report" not in t, "already applied"

    for old, new, what in [(OLD_WANTED, NEW_WANTED, "per_day"),
                           (OLD_QUERY, NEW_QUERY, "today query"),
                           (OLD_FOUND, NEW_FOUND, "found"),
                           (OLD_APPEND, NEW_APPEND, "append")]:
        assert t.count(old) == 1, f"anchor not unique: {what} ({t.count(old)})"
        t = t.replace(old, new)

    anchor = "# ── 1. every automation repo ───"
    assert t.count(anchor) == 1
    t = t.replace(anchor, HELPERS.strip() + "\n\n\n" + anchor)

    # today_by_id must exist before the resolve loop fills it
    a2 = "# ── 3. resolve each to a YouTube channel ───"
    assert t.count(a2) == 1
    t = t.replace(a2, "today_by_id = {}\n\n" + a2)

    # merge into the per-channel status entries
    old_status = '''status = {}
for c in channels:
    status[hashlib.sha256(c["id"].encode()).hexdigest()] = probe(c["id"])
    time.sleep(1.5)'''
    new_status = '''status = {}
for c in channels:
    entry = probe(c["id"])
    rep = today_by_id.get(c["id"])
    if rep:
        entry["today"] = rep
    status[hashlib.sha256(c["id"].encode()).hexdigest()] = entry
    time.sleep(1.5)'''
    assert t.count(old_status) == 1, "status loop anchor"
    t = t.replace(old_status, new_status)

    import ast
    ast.parse(t)
    SRC.write_text(t, encoding="utf-8")
    print(f"sync.py patched: {len(t):,} chars, syntax OK")


main()
