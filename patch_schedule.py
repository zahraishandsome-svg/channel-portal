"""Show each channel's upload schedule in Pakistan time, with a live countdown.

Every channel publishes at fixed UTC times (slot_publish_times_utc), which sync.py now
carries into channels.enc. This renders them as PKT clock times and counts down to the
next one, so the schedule is readable without doing timezone maths.

Pakistan does not observe DST, so PKT is a constant UTC+5 — no timezone database needed.
"""
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
SRC = Path(r"C:\Users\Zahid\YT-Dashboard\dashboard.html")

CSS = """
/* upload schedule */
.sched{margin-top:12px;padding:9px 11px 10px;border-radius:11px;
  background:linear-gradient(180deg,var(--accent-soft),rgba(77,141,255,.02));
  border:1px solid var(--accent-line)}
.sched.idle{background:var(--raised2);border-color:var(--line2)}
.sched-h{display:flex;align-items:center;gap:7px;margin-bottom:8px}
.sched-k{font-size:10px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--faint);font-weight:600}
.sched-c{margin-left:auto;font-size:12.5px;font-weight:650;color:var(--accent);
  font-variant-numeric:tabular-nums;letter-spacing:-.1px}
.sched.idle .sched-c{color:var(--muted)}
.slots{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.slot{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;
  padding:3.5px 9px;border-radius:8px;background:var(--raised2);
  border:1px solid var(--line2);color:var(--muted);
  font-variant-numeric:tabular-nums;white-space:nowrap}
.slot .dot{width:5px;height:5px;border-radius:50%;background:var(--line3);flex-shrink:0}
.slot.next{background:rgba(77,141,255,.15);border-color:var(--accent-line);
  color:var(--fg);font-weight:600}
.slot.next .dot{background:var(--accent);box-shadow:0 0 0 0 rgba(77,141,255,.55);
  animation:slotPulse 2.2s ease-out infinite}
.slot.done{opacity:.45}
.slot.done .dot{background:var(--green)}
.slot-tz{margin-left:auto;font-size:9.5px;letter-spacing:.1em;color:var(--faint);
  font-weight:600}
@keyframes slotPulse{
  0%{box-shadow:0 0 0 0 rgba(77,141,255,.5)}
  70%{box-shadow:0 0 0 6px rgba(77,141,255,0)}
  100%{box-shadow:0 0 0 0 rgba(77,141,255,0)}}
@media(prefers-reduced-motion:reduce){.slot.next .dot{animation:none}}
"""

JS = r"""
/* ══ upload schedule ══
   Channels publish at fixed UTC times; Pakistan is a constant UTC+5 (no DST), so the
   clock face is a plain +5 and only the countdown needs real time. */
const PKT_OFFSET_MIN=5*60;

function slotToday(hhmm){
  /* Next occurrence of this UTC time-of-day, as epoch ms. */
  const [h,m]=hhmm.split(":").map(Number);
  const now=new Date();
  const d=Date.UTC(now.getUTCFullYear(),now.getUTCMonth(),now.getUTCDate(),h,m,0,0);
  return d>now.getTime()?d:d+864e5;
}
function pktClock(hhmm){
  const [h,m]=hhmm.split(":").map(Number);
  let t=(h*60+m+PKT_OFFSET_MIN)%1440;
  const H=Math.floor(t/60), M=t%60, ap=H<12?"AM":"PM";
  return `${(H%12)||12}:${String(M).padStart(2,"0")} ${ap}`;
}
function untilText(ms){
  if(ms<=0) return "any moment";
  const s=Math.floor(ms/1000), d=Math.floor(s/86400),
        h=Math.floor(s%86400/3600), m=Math.floor(s%3600/60);
  if(d>0) return `in ${d}d ${h}h`;
  if(h>0) return `in ${h}h ${m}m`;
  if(m>0) return `in ${m}m`;
  return "in under a minute";
}
function schedHTML(c){
  const slots=c.slots||[];
  if(!slots.length) return "";
  /* soonest first — that one carries the countdown */
  const withNext=slots.map(s=>({t:s,at:slotToday(s)})).sort((a,b)=>a.at-b.at);
  const next=withNext[0];
  const pills=slots.map(s=>{
    const isNext=s===next.t;
    return `<span class="slot ${isNext?"next":"done"}"><span class="dot"></span>${pktClock(s)}</span>`;
  }).join("");
  return `<div class="sched" data-next="${next.at}">
    <div class="sched-h"><span class="sched-k">Next upload</span>
      <span class="sched-c">${untilText(next.at-Date.now())}</span></div>
    <div class="slots">${pills}<span class="slot-tz">PKT</span></div></div>`;
}
function tickSchedules(){
  $$(".sched[data-next]").forEach(el=>{
    let at=+el.dataset.next;
    /* roll past a slot that just fired instead of sticking at "any moment" */
    while(at<=Date.now()-6e4){ at+=864e5; el.dataset.next=at; }
    const c=el.querySelector(".sched-c");
    if(c) c.textContent=untilText(at-Date.now());
    el.classList.toggle("idle", at-Date.now()>6*36e5);
  });
}
setInterval(tickSchedules,30000);
"""


def main():
    t = SRC.read_text(encoding="utf-8")
    assert "schedHTML" not in t, "already applied"

    # ── CSS: goes before the safe-area block, which must stay last ──────────
    anchor = "/* safe area — must stay last */"
    assert t.count(anchor) == 1
    t = t.replace(anchor, CSS.strip() + "\n" + anchor)

    # ── JS helpers: right before the channel-card renderer ──────────────────
    js_anchor = "function table(rows,prev,maxPD,best,showCh"
    assert t.count(js_anchor) == 1, "table() anchor not unique"
    t = t.replace(js_anchor, JS.strip() + "\n\n" + js_anchor)

    # ── card: schedule sits under the metrics, above the footer ─────────────
    card_anchor = """    </div>
    <div class="ch-foot"><span class="tiny">${linked(c.label)"""
    assert t.count(card_anchor) == 1, "card anchor not unique"
    t = t.replace(card_anchor, """    </div>
    ${schedHTML(c)}
    <div class="ch-foot"><span class="tiny">${linked(c.label)""")

    SRC.write_text(t, encoding="utf-8")
    print(f"patched dashboard.html: {len(t):,} chars")
    for k in ["schedHTML", "tickSchedules", "pktClock", ".sched{"]:
        print(f"  {k:<16}{t.count(k)}")


main()
