"""Wire the 3-month / lifetime toggle into the overview and the channel cards."""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
SRC = Path(r"C:\Users\Zahid\YT-Dashboard\dashboard.html")

t = SRC.read_text(encoding="utf-8")
assert "scopeRow()}" not in t, "already wired"

# ── 1. scoped headline totals ──────────────────────────────────────────────
OLD = ("  const tSubs=live.reduce((a,c)=>a+c.subs,0), "
       "tViews=live.reduce((a,c)=>a+c.views,0);")
NEW = ("  const tSubs=live.reduce((a,c)=>a+c.subs,0);\n"
       "  /* views follow the scope; subscribers cannot — YouTube publishes no history */\n"
       "  const tViews=live.reduce((a,c)=>a+scopeStats(c).views,0);")
assert t.count(OLD) == 1
t = t.replace(OLD, NEW)

# the 24h comparison only makes sense against lifetime totals
OLD_P = ("  const pViews=prev?live.reduce((a,c)=>a+(prev.channels?.[c.label]?.views??c.views),0):null;")
NEW_P = ("  const pViews=(prev&&SCOPE===\"all\")\n"
         "    ?live.reduce((a,c)=>a+(prev.channels?.[c.label]?.views??c.views),0):null;")
assert t.count(OLD_P) == 1
t = t.replace(OLD_P, NEW_P)

# ── 2. label + subline on the views card ───────────────────────────────────
OLD_CARD = ('''      ${statCard("Total views",kf(tViews),trendEl(tViews,pViews)+(prev?` vs ${prev.key}`:" tracking starts today"),
                 totSeries.length>1?spark(totSeries,240,38):"",.04)}''')
NEW_CARD = ('''      ${statCard(SCOPE==="all"?"Total views":"Views · 3 months",kf(tViews),
                 SCOPE==="all"
                   ?trendEl(tViews,pViews)+(prev?` vs ${prev.key}`:" tracking starts today")
                   :(ST.windowReady?"from videos posted in the last 90 days":"counting…"),
                 totSeries.length>1&&SCOPE==="all"?spark(totSeries,240,38):"",.04)}''')
assert t.count(OLD_CARD) == 1
t = t.replace(OLD_CARD, NEW_CARD)

# ── 3. put the toggle above the stat cards ─────────────────────────────────
OLD_STATS = '''    <div class="stats">
      ${statCard("Total subscribers"'''
NEW_STATS = '''    ${scopeRow()}
    <div class="stats">
      ${statCard("Total subscribers"'''
assert t.count(OLD_STATS) == 1
t = t.replace(OLD_STATS, NEW_STATS)

# ── 4. channel card metrics follow the scope ───────────────────────────────
OLD_METS = '''    <div class="mets">
      <div class="met"><div class="k">Subscribers</div>
        <div class="v">${kf(c.subs)}${p?trendEl(c.subs,p.subs):""}</div></div>
      <div class="met"><div class="k">Total views</div>
        <div class="v">${kf(c.views)}${p?trendEl(c.views,p.views):""}</div></div>
      <div class="met"><div class="k">Videos</div><div class="v">${nf(c.count)}</div></div>
      <div class="met"><div class="k">Avg · last ${c.rc}</div><div class="v">${c.avg===null?"—":kf(c.avg)}</div></div>
    </div>'''
NEW_METS = '''    <div class="mets">
      <div class="met"><div class="k">Subscribers</div>
        <div class="v">${kf(c.subs)}${p?trendEl(c.subs,p.subs):""}</div></div>
      <div class="met"><div class="k">${SCOPE==="all"?"Total views":"Views · 3mo"}</div>
        <div class="v">${kf(sc.views)}${SCOPE==="all"&&p?trendEl(c.views,p.views):""}</div></div>
      <div class="met"><div class="k">${SCOPE==="all"?"Videos":"Videos · 3mo"}</div>
        <div class="v">${nf(sc.count)}</div></div>
      <div class="met"><div class="k">${SCOPE==="all"?`Avg · last ${c.rc}`:"Avg per video"}</div>
        <div class="v">${sc.avg===null?"—":kf(sc.avg)}</div></div>
    </div>'''
assert t.count(OLD_METS) == 1
t = t.replace(OLD_METS, NEW_METS)

# sc must exist before the template uses it
OLD_SER = ("  const ser=Object.keys(hist.days).sort()"
           ".map(k=>hist.days[k].channels?.[c.label]?.views).filter(v=>v!==undefined);")
NEW_SER = OLD_SER + "\n  const sc=scopeStats(c);"
assert t.count(OLD_SER) == 1
t = t.replace(OLD_SER, NEW_SER)

# ── 5. ranking should follow what is on screen ─────────────────────────────
OLD_RANK = ("  const ranked=[...channels].sort((a,b)=>a.dead!==b.dead?(a.dead?1:-1)"
            ":(b.avg??-1)-(a.avg??-1));")
NEW_RANK = ("  const rankVal=c=>SCOPE===\"all\"?(c.avg??-1):(scopeStats(c).avg??-1);\n"
            "  const ranked=[...channels].sort((a,b)=>a.dead!==b.dead?(a.dead?1:-1)"
            ":rankVal(b)-rankVal(a));")
assert t.count(OLD_RANK) == 1
t = t.replace(OLD_RANK, NEW_RANK)

# ── 6. hook the buttons up ─────────────────────────────────────────────────
OLD_WIRE = ('  $("#chseg").querySelectorAll("button").forEach('
            'b=>b.onclick=()=>{FILTER=b.dataset.ch||null;overview();});')
NEW_WIRE = OLD_WIRE + '''
  $("#scope")?.querySelectorAll("button").forEach(b=>b.onclick=async()=>{
    if(SCOPE===b.dataset.s) return;
    SCOPE=b.dataset.s; localStorage.setItem(SCOPE_KEY,SCOPE);
    overview();                       /* paint the switch immediately */
    if(SCOPE==="90"&&!ST.windowReady){ await loadWindow(); overview(); }
  });'''
assert t.count(OLD_WIRE) == 1
t = t.replace(OLD_WIRE, NEW_WIRE)

# ── 7. fetch the window on first load when 3 months is the active scope ────
OLD_LOAD = "  writeHist(ST);render();\n  probeDead();"
NEW_LOAD = ('  writeHist(ST);render();\n  probeDead();\n'
            '  if(SCOPE==="90"){ loadWindow().then(()=>{ if(!location.hash) overview(); }); }')
assert t.count(OLD_LOAD) == 1
t = t.replace(OLD_LOAD, NEW_LOAD)

SRC.write_text(t, encoding="utf-8")
print(f"wired: {len(t):,} chars")
for k in ["scopeRow()", "scopeStats(c)", "loadWindow()", "SCOPE_KEY"]:
    print(f"  {k:<16}{t.count(k)}")
