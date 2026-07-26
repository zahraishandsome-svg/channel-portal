"""Discover every automation channel, check whether it is still on YouTube, and
publish the results for the portal.

Nothing identifying is written in the clear:
  * channels.enc — AES-GCM ciphertext; the key lives only in the user's browser
  * status.json  — keyed by SHA-256 of the channel ID

Run by .github/workflows/sync.yml every 30 minutes.
"""
import base64
import hashlib
import json
import os
import re
import sqlite3
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

GH_TOKEN = os.environ["GH_TOKEN"]
YT_KEY = os.environ["YT_API_KEY"]
ENC_KEY = os.environ["PORTAL_ENC_KEY"] if "PORTAL_ENC_KEY" in os.environ else os.environ["ENC_KEY"]
OWNER = "zahraishandsome-svg"
REPO_RE = re.compile(r"^tiktok-yt-automation(-\d+)?$")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")


def gh(path, raw=False):
    req = urllib.request.Request("https://api.github.com" + path)
    req.add_header("Authorization", "token " + GH_TOKEN)
    req.add_header("Accept", "application/vnd.github.raw" if raw
                   else "application/vnd.github+json")
    with urllib.request.urlopen(req, timeout=40) as r:
        data = r.read()
    return data if raw else json.loads(data)


def yt(path, **params):
    params["key"] = YT_KEY
    url = f"https://www.googleapis.com/youtube/v3/{path}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=40) as r:
        return json.load(r)


# ── 1. every automation repo ───────────────────────────────────────────────
repos = []
page = 1
while True:
    batch = gh(f"/user/repos?per_page=100&page={page}&affiliation=owner")
    if not batch:
        break
    repos += [r["name"] for r in batch if REPO_RE.match(r["name"]) and not r.get("archived")]
    page += 1
repos.sort()
print("automation repos:", repos)


# ── 2. channels.yaml + newest upload from each repo's database ─────────────
found = {}          # label -> {"tiktok":…, "video":…}
for repo in repos:
    try:
        cfg = yaml.safe_load(gh(f"/repos/{OWNER}/{repo}/contents/channels.yaml", raw=True))
    except Exception as e:
        print(f"  {repo}: no channels.yaml ({e})")
        continue

    wanted = {}
    for ch in (cfg or {}).get("channels", []):
        if not ch.get("enabled", True):
            continue
        if not (ch.get("tiktok_username") or "").strip():
            continue          # an emptied slot waiting for a new channel
        wanted[ch["id"]] = "@" + ch["tiktok_username"]
    if not wanted:
        continue

    try:
        listing = gh(f"/repos/{OWNER}/{repo}/contents/data")
    except Exception:
        listing = []
    for f in listing:
        if not f["name"].endswith(".db"):
            continue
        try:
            blob = gh(f"/repos/{OWNER}/{repo}/contents/data/{f['name']}", raw=True)
        except Exception:
            continue
        tmp = Path(tempfile.gettempdir()) / f["name"]
        tmp.write_bytes(blob)
        try:
            con = sqlite3.connect(tmp)
            rows = con.execute(
                "SELECT channel_id, youtube_video_id FROM posted_videos "
                "WHERE status='uploaded' AND youtube_video_id IS NOT NULL "
                "ORDER BY posted_at DESC").fetchall()
            con.close()
        except Exception:
            continue
        for cid, vid in rows:
            if cid in wanted and cid not in found:
                found[cid] = {"tiktok": wanted[cid], "video": vid}

print("channels with an upload to identify them:", sorted(found))


# ── 3. resolve each to a YouTube channel ───────────────────────────────────
channels = []
vids = [v["video"] for v in found.values()]
snip = {}
for i in range(0, len(vids), 50):
    try:
        for it in yt("videos", part="snippet", id=",".join(vids[i:i + 50])).get("items", []):
            snip[it["id"]] = it["snippet"]
    except Exception as e:
        print("  videos.list failed:", e)

for label, info in sorted(found.items(), key=lambda kv: int(re.sub(r"\D", "", kv[0]) or 0)):
    s = snip.get(info["video"])
    if not s:
        print(f"  {label}: could not resolve (video {info['video']} unavailable)")
        continue
    channels.append({"label": label.replace("channel_", "ch"),
                     "id": s["channelId"],
                     "tiktok": info["tiktok"]})
print("resolved:", [c["label"] for c in channels])
if not channels:
    raise SystemExit("resolved no channels — refusing to publish an empty list")


# ── 4. is each one still on YouTube? ───────────────────────────────────────
def probe(cid):
    req = urllib.request.Request(f"https://www.youtube.com/channel/{cid}",
                                 headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return {"status": "missing"} if e.code == 404 else {"status": "unknown"}
    except Exception:
        return {"status": "unknown"}
    if "has been terminated" in html:
        return {"status": "terminated"}
    i, j = html.find("<title>"), html.find("</title>")
    title = html[i + 7:j].replace(" - YouTube", "").strip() if 0 <= i < j else ""
    if title and title.lower() != "youtube":
        return {"status": "indexing", "title": title}
    return {"status": "missing"}


status = {}
for c in channels:
    status[hashlib.sha256(c["id"].encode()).hexdigest()] = probe(c["id"])
    time.sleep(1.5)
status["_checked"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
print(json.dumps({k[:8] + "…": v for k, v in status.items() if k != "_checked"}, indent=1))


# ── 5. publish ─────────────────────────────────────────────────────────────
key = base64.urlsafe_b64decode(ENC_KEY + "=" * (-len(ENC_KEY) % 4))
nonce = os.urandom(12)
blob = AESGCM(key).encrypt(nonce, json.dumps({"channels": channels}).encode(), None)
Path("channels.enc").write_text(
    json.dumps({"v": 1,
                "nonce": base64.b64encode(nonce).decode(),
                "data": base64.b64encode(blob).decode(),
                "count": len(channels),
                "updated": status["_checked"]}, indent=1),
    encoding="utf-8")
Path("status.json").write_text(json.dumps(status, indent=1), encoding="utf-8")
print(f"published {len(channels)} channels")
