"""Make a deploy actually reach the running app.

The service worker already fetches network-first, so a new index.html is downloaded —
but the JavaScript already running in the page keeps running. An installed PWA on iOS
resumes from a frozen state rather than reloading, and a Chrome app window left open
never reloads either, so the fix I ship and the code the user is looking at can be days
apart. That is exactly what happened with the missed-upload flag: the fix was live and
correct, and the app kept showing the old result.

Each build now stamps an id into the page and publishes the same id in version.json.
The page compares them whenever it comes back to the foreground and reloads itself once
if they differ.
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
DASH = Path(r"C:\Users\Zahid\YT-Dashboard\dashboard.html")
BUILD = Path(r"C:\Users\Zahid\projects\channel-portal\build.py")

JS = r'''
/* ══ self-update ══
   A deployed fix is worthless if the page never re-runs. The build stamps its id here
   and publishes the same id in version.json; when the app returns to the foreground it
   compares the two and reloads once if the deploy moved on. */
const BUILD_ID="__BUILD__";
let updateChecking=false;
async function checkForUpdate(){
  if(!SERVED||BUILD_ID==="__BUILD__"||updateChecking) return;
  updateChecking=true;
  try{
    const r=await fetch("version.json?t="+Date.now(),{cache:"no-store"});
    if(r.ok){
      const {build}=await r.json();
      if(build&&build!==BUILD_ID&&sessionStorage.getItem("mda_reloaded")!==build){
        sessionStorage.setItem("mda_reloaded",build);   /* never loop on a bad deploy */
        location.reload();
        return;
      }
    }
  }catch{}
  updateChecking=false;
}
document.addEventListener("visibilitychange",()=>{ if(!document.hidden) checkForUpdate(); });
addEventListener("focus",checkForUpdate);
setInterval(checkForUpdate,6e5);
'''

t = DASH.read_text(encoding="utf-8")
assert "BUILD_ID" not in t, "already applied"
anchor = "let DATA_AS_OF=null;"
assert t.count(anchor) == 1
t = t.replace(anchor, JS.strip() + "\n\n" + anchor)
DASH.write_text(t, encoding="utf-8")
print(f"dashboard.html: {len(t):,} chars")

# ── stamp the id at build time and publish version.json ────────────────────
b = BUILD.read_text(encoding="utf-8")
OLD = '''OUT.write_text(t, encoding="utf-8", newline="\\n")
print(f"built {OUT} — {len(t)} chars, no secrets embedded")'''
NEW = '''# ── stamp the build so a running page can notice it is out of date ────────
import hashlib

build_id = hashlib.sha1(t.encode("utf-8")).hexdigest()[:12]
t = t.replace('"__BUILD__"', f'"{build_id}"')
assert "__BUILD__" not in t, "build id placeholder survived"

OUT.write_text(t, encoding="utf-8", newline="\\n")
(OUT.parent / "version.json").write_text(
    json.dumps({"build": build_id}) + "\\n", encoding="utf-8", newline="\\n")
print(f"built {OUT} — {len(t)} chars, no secrets embedded, build {build_id}")'''
assert b.count(OLD) == 1, f"build tail anchor ({b.count(OLD)})"
b = b.replace(OLD, NEW)
if "\nimport json" not in b and "import json" not in b.split("\n\n")[0]:
    b = b.replace("import re", "import json\nimport re", 1)
BUILD.write_text(b, encoding="utf-8")
import ast
ast.parse(b)
print("build.py: stamps BUILD_ID and writes version.json")
