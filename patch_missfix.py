"""Stop calling a slot missed before anyone could know that it was.

The flag compared "has this slot's clock time passed?" against upload counts that come
from the last sync. Two ways that goes wrong:

  * the counts are up to 30 minutes stale, so a slot that fired five minutes ago is
    counted as due while its upload is not yet in the published report — every US
    channel showed "1 video missed" right after the 3 AM PKT slot succeeded;
  * a failed slot still has its +90 minute retry to come, so calling it missed
    immediately is wrong even when the data is fresh.

A slot is now only judged once BOTH the retry window has elapsed and the published
report was generated after that point.
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
DASH = Path(r"C:\Users\Zahid\YT-Dashboard\dashboard.html")
BUILD = Path(r"C:\Users\Zahid\projects\channel-portal\build.py")

OLD_JS = '''function slotsDueToday(slots){
  if(!slots||!slots.length) return 0;
  const n=new Date();
  const mins=n.getUTCHours()*60+n.getUTCMinutes();
  return slots.filter(s=>{const [h,m]=s.split(":").map(Number); return h*60+m<=mins;}).length;
}
function missHTML(c){
  const t=c.today; if(!t) return "";
  const due=Math.min(slotsDueToday(c.slots), t.expected||0);
  const missed=Math.max(0, due-(t.uploaded||0));
  const issues=t.issues||[];'''

NEW_JS = '''/* A slot is only judged once its retry has also had time to run AND the published
   report is new enough to have seen the outcome. DATA_AS_OF is when sync last ran;
   without it (desktop build) fall back to the clock alone. */
const RETRY_GRACE_MIN=100;      /* slot + 90m retry + a few minutes to upload */
function slotInstantUTC(hhmm){
  const [h,m]=hhmm.split(":").map(Number), n=new Date();
  return Date.UTC(n.getUTCFullYear(),n.getUTCMonth(),n.getUTCDate(),h,m,0,0);
}
function slotSettled(hhmm){
  const cut=slotInstantUTC(hhmm)+RETRY_GRACE_MIN*6e4;
  const asOf=DATA_AS_OF||Date.now();
  return Date.now()>=cut && asOf>=cut;
}
function slotsDueToday(slots){
  if(!slots||!slots.length) return 0;
  return slots.filter(slotSettled).length;
}
function missHTML(c){
  const t=c.today; if(!t) return "";
  const slots=c.slots||[];
  const due=Math.min(slotsDueToday(slots), t.expected||0);
  const missed=Math.max(0, due-(t.uploaded||0));
  /* an issue on a slot whose retry is still pending is not a miss yet */
  const issues=(t.issues||[]).filter(i=>{
    const s=slots[(i.slot||1)-1];
    return s?slotSettled(s):true;
  });'''

t = DASH.read_text(encoding="utf-8")
assert t.count(OLD_JS) == 1, f"js anchor ({t.count(OLD_JS)})"
t = t.replace(OLD_JS, NEW_JS)

# the global sync fills this in; the desktop build simply leaves it null
OLD_DECL = "const SCOPE_KEY=\"yt_dash_scope\";"
assert t.count(OLD_DECL) == 1
t = t.replace(OLD_DECL, "let DATA_AS_OF=null;    /* when sync last published, ms */\n" + OLD_DECL)

DASH.write_text(t, encoding="utf-8")
print(f"dashboard.html: {len(t):,} chars")

# ── record when the published data was generated ───────────────────────────
b = BUILD.read_text(encoding="utf-8")
OLD_B = "    const list=JSON.parse(new TextDecoder().decode(plain)).channels;"
NEW_B = ("    const list=JSON.parse(new TextDecoder().decode(plain)).channels;\n"
         "    if(env.updated) DATA_AS_OF=Date.parse(env.updated)||null;")
assert b.count(OLD_B) == 1, f"build anchor ({b.count(OLD_B)})"
b = b.replace(OLD_B, NEW_B)
BUILD.write_text(b, encoding="utf-8")
print("build.py: DATA_AS_OF wired from channels.enc")
