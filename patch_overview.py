"""Two changes to the overview.

1. Flag a channel whose uploads did not happen. sync.py publishes today's expected /
   uploaded counts and any run that ended in no_content or failed; the card compares
   that against how many slots are actually DUE (their time has passed today), so a
   slot that simply hasn't come round yet is never called a miss.

2. Default the headline numbers to the last 3 months instead of lifetime, with a
   toggle back to lifetime. Public data can only attribute views to the video that
   earned them, so "3 months" means videos PUBLISHED in the window — for channels this
   young that is nearly all of their views, but it is not the same as views received
   in the window, and subscriber counts stay lifetime because YouTube publishes no
   history for them.
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
SRC = Path(r"C:\Users\Zahid\YT-Dashboard\dashboard.html")

CSS = """
/* upload-miss flag + overview scope toggle */
.miss{display:flex;align-items:flex-start;gap:7px;margin-top:10px;padding:8px 10px;
  border-radius:10px;background:var(--amber-soft);border:1px solid rgba(242,181,68,.3);
  font-size:12px;line-height:1.45;color:var(--fg)}
.miss.bad{background:var(--red-soft);border-color:rgba(242,84,91,.32)}
.miss .ic{flex-shrink:0;width:15px;height:15px;margin-top:.5px}
.miss b{font-weight:650}
.miss .why{color:var(--muted)}
.scope{display:inline-flex;gap:3px;padding:3px;border-radius:11px;
  background:var(--raised);border:1px solid var(--line2)}
.scope button{border:0;background:transparent;color:var(--muted);cursor:pointer;
  font:inherit;font-size:12.5px;font-weight:550;padding:5px 13px;border-radius:8px;
  transition:background .14s,color .14s}
.scope button.on{background:var(--accent);color:#fff;font-weight:600}
.scope button:not(.on):hover{color:var(--fg);background:var(--raised2)}
.scope-row{display:flex;align-items:center;gap:11px;flex-wrap:wrap;margin-bottom:16px}
.scope-note{font-size:11.5px;color:var(--faint)}
"""

JS = r"""
/* ══ upload misses ══
   sync publishes {expected, uploaded, issues[]} per channel for the current UTC day.
   A slot only counts as missed once its scheduled time has actually passed. */
function slotsDueToday(slots){
  if(!slots||!slots.length) return 0;
  const n=new Date();
  const mins=n.getUTCHours()*60+n.getUTCMinutes();
  return slots.filter(s=>{const [h,m]=s.split(":").map(Number); return h*60+m<=mins;}).length;
}
function missHTML(c){
  const t=c.today; if(!t) return "";
  const due=Math.min(slotsDueToday(c.slots), t.expected||0);
  const missed=Math.max(0, due-(t.uploaded||0));
  const issues=t.issues||[];
  if(!missed && !issues.length) return "";
  const why=issues.length
    ? [...new Set(issues.map(i=>i.why))].join(" · ")
    : "the run did not report a reason";
  const n=missed||issues.length;
  const hard=issues.some(i=>i.why==="upload failed");
  return `<div class="miss ${hard?"bad":""}">
    <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1">
      <path d="M12 8v5M12 16.5v.5"/><circle cx="12" cy="12" r="9"/></svg>
    <div><b>${n} video${n>1?"s":""} missed today</b>
      <span class="why">&nbsp;— ${esc(why)}</span></div></div>`;
}

/* ══ overview scope ══
   Lifetime totals hide how a channel is doing now, so the default is the last 90
   days. Only views/videos/average can be scoped: subscriber counts have no public
   history, so they stay lifetime whichever scope is picked. */
const SCOPE_KEY="yt_dash_scope";
let SCOPE=localStorage.getItem(SCOPE_KEY)||"90";
const SCOPE_DAYS=90;
function inScope(v){ return SCOPE==="all" || ageD(v.published)<=SCOPE_DAYS; }
function scopeStats(c){
  if(SCOPE==="all") return {views:c.views, count:c.count, avg:c.avg, exact:true};
  const mine=(ST.window||[]).filter(v=>v.channel===c.label&&v.views!==null&&inScope(v));
  if(!mine.length) return {views:0,count:0,avg:null,exact:!!ST.windowReady};
  const sum=mine.reduce((a,v)=>a+v.views,0);
  return {views:sum, count:mine.length, avg:Math.round(sum/mine.length),
          exact:!!ST.windowReady};
}
function scopeRow(){
  return `<div class="scope-row">
    <div class="scope" id="scope">
      <button data-s="90" class="${SCOPE==="90"?"on":""}">Last 3 months</button>
      <button data-s="all" class="${SCOPE==="all"?"on":""}">Lifetime</button>
    </div>
    <span class="scope-note">${SCOPE==="90"
      ? "Views of videos published in the last 90 days"
      : "Everything since the channel started"}</span></div>`;
}
/* Pull enough uploads per channel to cover the window. The overview normally fetches
   only the newest handful, which is nowhere near 90 days at two videos a day. */
async function loadWindow(){
  if(ST.windowReady) return;
  const cut=Date.now()-SCOPE_DAYS*864e5;
  const live=ST.channels.filter(c=>!c.dead&&c.uploads);
  const per=await Promise.all(live.map(async c=>{
    const out=[]; let tok, pages=0;
    try{
      do{
        const r=await api("playlistItems",{part:"snippet",playlistId:c.uploads,
          maxResults:"50",...(tok?{pageToken:tok}:{})});
        for(const i of r.items||[]){
          out.push({channel:c.label,id:i.snippet.resourceId.videoId,
            title:i.snippet.title,published:i.snippet.publishedAt});
        }
        tok=r.nextPageToken;
        if(out.length&&new Date(out[out.length-1].published).getTime()<cut) break;
      }while(tok&&++pages<8);
    }catch{}
    return out;
  }));
  const all=per.flat().filter(v=>new Date(v.published).getTime()>=cut);
  let s={}; try{ s=await vidStats(all.map(v=>v.id)); }catch{}
  all.forEach(v=>deco(v,s));
  ST.window=all; ST.windowReady=true;
}
"""


def main():
    t = SRC.read_text(encoding="utf-8")
    assert "missHTML" not in t, "already applied"

    anchor = "/* safe area — must stay last */"
    assert t.count(anchor) == 1
    t = t.replace(anchor, CSS.strip() + "\n" + anchor)

    js_anchor = "function table(rows,prev,maxPD,best,showCh"
    assert t.count(js_anchor) == 1
    t = t.replace(js_anchor, JS.strip() + "\n\n" + js_anchor)

    # the miss flag sits above the schedule strip
    card = "    ${schedHTML(c)}\n"
    assert t.count(card) == 1
    t = t.replace(card, "    ${missHTML(c)}\n    ${schedHTML(c)}\n")

    SRC.write_text(t, encoding="utf-8")
    print(f"patched: {len(t):,} chars")
    for k in ["missHTML", "scopeRow", "loadWindow", "scopeStats", ".miss{", ".scope{"]:
        print(f"  {k:<14}{t.count(k)}")


main()
