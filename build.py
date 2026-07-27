"""Build the published portal from the one source file.

    C:\\Users\\Zahid\\YT-Dashboard\\dashboard.html   <- the only file to edit
                     |
                     v  python build.py
              index.html   -> pushed to GitHub Pages
                              phone and desktop both load this, so one push
                              updates every device

What the build changes:
  * branding, PWA head tags, service worker, iPhone safe areas
  * a MODE flag (local / hosted / file) instead of "is it served"
  * termination probing and Google sign-in that need no local server
  * strips the API key and channel list — the published file must carry neither

Every edit asserts a unique anchor, so a drifted source fails the build instead of
silently producing a half-patched page.
"""
from pathlib import Path

SRC = Path(r"C:\Users\Zahid\YT-Dashboard\dashboard.html")
OUT = Path("index.html")
MODAL = Path("modal.js.txt")


def sub(t, old, new, what):
    assert old in t, f"anchor missing: {what}"
    assert t.count(old) == 1, f"anchor not unique ({t.count(old)}x): {what}"
    return t.replace(old, new, 1)


def cut(t, start, end):
    a = t.index(start)
    return t[a:t.index(end, a)]


t = SRC.read_text(encoding="utf-8")

# ── PWA head ──────────────────────────────────────────────────────────────
t = sub(t, "<title>Million Dollars App</title>",
"""<title>Million Dollars App</title>
<link rel="manifest" href="manifest.webmanifest">
<meta name="theme-color" content="#08090c">
<link rel="icon" href="favicon.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Million Dollars">
<script src="https://accounts.google.com/gsi/client" async defer></script>""", "head")

t = sub(t, ".tbar{position:sticky;top:0;z-index:40;",
           ".tbar{position:sticky;top:0;z-index:40;padding-top:max(12px,env(safe-area-inset-top));",
        "tbar safe-area")
t = sub(t, ".page{padding:22px 24px 80px;max-width:1400px;width:100%}",
           ".page{padding:22px 24px calc(80px + env(safe-area-inset-bottom));max-width:1400px;width:100%}",
        "page safe-area")

# ── run mode ──────────────────────────────────────────────────────────────
t = sub(t, 'const SERVED=location.protocol.startsWith("http");',
"""/* Three ways this page runs:
     local  — the desktop app on :8756 (has /status /link /analytics /probe)
     hosted — GitHub Pages; probes and signs in without any server of ours
     file   — opened straight off disk; public stats only */
const MODE = location.port==="8756" ? "local"
           : location.protocol.startsWith("http") ? "hosted" : "file";
const SERVED = MODE!=="file";""", "MODE")

# ── nothing identifying is published ──────────────────────────────────────
t = sub(t, 'const DEFAULT_KEY="AIzaSyDsr2ptOEQbGSvOnTJKN32rceEpS8ZnOIU";',
           'const DEFAULT_KEY="";', "default key")
a = t.index("const CHANNELS=[")
t = t[:a] + "let CHANNELS=[];" + t[t.index("];", a) + 2:]

# ── config from a setup link, channel list from the encrypted publish ─────
t = sub(t, "let CHANNELS=[];",
r'''let CHANNELS=[];
const CFG_KEY="yt_portal_config";

/** Config never ships inside this file. It arrives once per device through a setup
    link (#setup=<base64 json>) or the setup screen, then lives in this browser's
    localStorage only — a URL fragment is never sent to the server. */
function loadConfig(){
  const m=location.hash.match(/setup=([A-Za-z0-9+/=_-]+)/);
  if(m){
    try{
      const cfg=JSON.parse(decodeURIComponent(escape(
        atob(m[1].replace(/-/g,"+").replace(/_/g,"/")))));
      if(cfg.apiKey||Array.isArray(cfg.channels)){
        localStorage.setItem(CFG_KEY,JSON.stringify(cfg));
        if(cfg.apiKey) localStorage.setItem(KEY_STORE,cfg.apiKey);
        history.replaceState(null,"",location.pathname);
      }
    }catch(e){ console.warn("bad setup link",e); }
  }
  try{
    const cfg=JSON.parse(localStorage.getItem(CFG_KEY)||"null");
    if(cfg&&Array.isArray(cfg.channels)) CHANNELS=cfg.channels;
    return cfg;
  }catch{ return null; }
}

/** A scheduled workflow walks the automation repos and publishes the current channel
    list, AES-GCM encrypted. Decrypting it here means a channel added to the automation
    turns up on its own, and the published file still holds no identifiers. */
async function syncChannels(cfg){
  const b64=cfg?.encKey; if(!b64) return false;
  try{
    const r=await fetch("channels.enc?t="+Date.now());
    if(!r.ok) return false;
    const env=await r.json();
    const raw=s=>Uint8Array.from(atob(s),ch=>ch.charCodeAt(0));
    const key=await crypto.subtle.importKey("raw",
      raw(b64.replace(/-/g,"+").replace(/_/g,"/")),"AES-GCM",false,["decrypt"]);
    const plain=await crypto.subtle.decrypt({name:"AES-GCM",iv:raw(env.nonce)},key,raw(env.data));
    const list=JSON.parse(new TextDecoder().decode(plain)).channels;
    if(Array.isArray(list)&&list.length){
      const before=CHANNELS.map(c=>c.label).join(",");
      CHANNELS=list;
      const cur=JSON.parse(localStorage.getItem(CFG_KEY)||"{}");
      cur.channels=list; localStorage.setItem(CFG_KEY,JSON.stringify(cur));
      if(before && before!==list.map(c=>c.label).join(","))
        toast("Channel list updated from your automation","g");
      return true;
    }
  }catch(e){ console.warn("channel sync failed",e); }
  return false;
}''', "config + sync")

# ── first run ─────────────────────────────────────────────────────────────
t = sub(t, "async function load(){",
r'''function setupScreen(){
  $("#crumb").textContent="Setup";
  $("#sbScroll").innerHTML="";
  $("#page").innerHTML=`
    <div class="stats" style="grid-template-columns:1fr;max-width:620px">
      <div class="stat"><div class="lb">Welcome</div>
        <div class="vl" style="font-size:19px">Add your configuration</div>
        <div class="ft" style="white-space:normal">This portal ships empty on purpose &mdash; nothing about
          your channels is stored in the app itself.</div></div></div>
    <div class="alert i" style="max-width:620px">On iPhone a home-screen app keeps its own storage, separate
      from Safari &mdash; so a setup link you opened in Safari does not carry over. Paste it once here and this
      app remembers it for good.</div>
    <div class="tbl" style="max-width:620px;padding:18px">
      <div class="fld"><label>Paste your setup link</label>
        <textarea id="cfgIn" rows="5" placeholder="https://…/#setup=…&#10;&#10;(a plain {\"apiKey\":…} object works too)"
          style="width:100%;background:var(--surface);border:1px solid var(--line);border-radius:10px;
                 color:var(--fg);padding:10px 12px;font:12px ui-monospace,monospace;resize:vertical"></textarea></div>
      <div class="mrow"><button class="btn pri" id="cfgSave">Save and load</button>
        <button class="btn" id="cfgPaste">Paste from clipboard</button>
        <span id="cfgMsg" class="note" style="margin:0"></span></div></div>`;

  const apply=raw=>{
    raw=(raw||"").trim();
    if(!raw) throw new Error("nothing pasted");
    let cfg;
    // accept the whole setup link, just the #setup= payload, or raw JSON — on a
    // phone the link is the only one of the three that is easy to paste
    const m=raw.match(/setup=([A-Za-z0-9+/=_-]+)/);
    if(m){
      cfg=JSON.parse(decodeURIComponent(escape(
        atob(m[1].replace(/-/g,"+").replace(/_/g,"/")))));
    }else if(raw.startsWith("{")){
      cfg=JSON.parse(raw);
    }else{
      throw new Error("that doesn't look like a setup link");
    }
    if(!cfg.apiKey) throw new Error("this link has no API key in it");
    localStorage.setItem(CFG_KEY,JSON.stringify(cfg));
    localStorage.setItem(KEY_STORE,cfg.apiKey);
    if(Array.isArray(cfg.channels)) CHANNELS=cfg.channels;
    toast("Saved &mdash; loading your channels","g"); load();
  };
  $("#cfgSave").onclick=()=>{
    try{ apply($("#cfgIn").value); }
    catch(e){ $("#cfgMsg").innerHTML='<span class="warn">'+esc(e.message)+'</span>'; }
  };
  $("#cfgPaste").onclick=async()=>{
    try{ const txt=await navigator.clipboard.readText(); $("#cfgIn").value=txt; apply(txt); }
    catch(e){ $("#cfgMsg").innerHTML='<span class="warn">'+esc(e.message||"clipboard blocked — paste manually")+'</span>'; }
  };
}

async function load(){
  if(MODE!=="local"){
    const cfg=loadConfig();
    await syncChannels(cfg);
    if(!CHANNELS.length){ beat("err","setup needed"); setupScreen(); return; }
  }''', "setup screen")

# ── probing with no server of ours ────────────────────────────────────────
t = sub(t, cut(t, "async function probeDead(){", "async function loadDeep(l){"),
r'''async function probeDead(){
  const dead=ST.channels.filter(c=>c.dead&&!c.probe);
  if(!dead.length) return;
  await Promise.all(dead.map(async c=>{ c.probe=await probeOne(c); }));
  render();
  const gone=ST.channels.filter(c=>["terminated","gone"].includes(c.probe?.status));
  if(gone.length) toast(`<b>${gone.map(c=>c.label).join(", ")}</b> is no longer on YouTube`,"r");
}

/** The scheduled workflow publishes status.json keyed by SHA-256 of the channel ID,
    so the published file still reveals nothing. It is the only source that can say
    "terminated" with certainty. */
let STATUS_MAP=null;
async function loadStatusMap(){
  if(STATUS_MAP!==null) return STATUS_MAP;
  try{ const r=await fetch("status.json?t="+Date.now()); STATUS_MAP=r.ok?await r.json():{}; }
  catch{ STATUS_MAP={}; }
  return STATUS_MAP;
}
async function sha256hex(s){
  const b=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(s));
  return [...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,"0")).join("");
}

async function probeOne(c){
  try{
    const hit=(await loadStatusMap())[await sha256hex(c.id)];
    if(hit?.status && hit.status!=="unknown") return hit;
  }catch{}
  if(MODE==="local"){
    try{
      const r=await fetch("/probe?id="+encodeURIComponent(c.id));
      if(r.ok){const j=await r.json(); if(j.status&&j.status!=="unknown") return j;}
    }catch{}
  }
  return apiProbe(c);
}

/** Last resort, no extra service required. A channel's uploads playlist is "UU"+id:
    it 404s once the channel is gone but still works while the channel is merely
    too new for the Data API to have indexed. */
async function apiProbe(c){
  try{
    const r=await api("playlistItems",{part:"snippet",playlistId:"UU"+c.id.slice(2),maxResults:"1"});
    return {status:"indexing",title:(r.items||[])[0]?.snippet?.channelTitle||""};
  }catch(e){
    if(e.status===404||e.reason==="playlistNotFound") return {status:"gone",title:""};
    return {status:"unknown",title:""};
  }
}

''', "probe block")

t = sub(t,
    '      missing:["NOT FOUND","b-off","No channel exists at this ID any more — deleted, or the ID in the dashboard is wrong."],',
    '      missing:["NOT FOUND","b-off","No channel exists at this ID any more — deleted, or the ID in the dashboard is wrong."],\n'
    '      gone:["CHANNEL GONE","b-off","This channel is no longer on YouTube — terminated or deleted. Open it on YouTube to see which."],',
    "gone card")
t = sub(t,
    '  if(term.length) bits.push(`<b>${term.join(", ")} terminated by YouTube.</b> Uploads to ${term.length>1?"these channels":"this channel"} will fail until restored.`);',
    '  if(term.length) bits.push(`<b>${term.join(", ")} terminated by YouTube.</b> Uploads to ${term.length>1?"these channels":"this channel"} will fail until restored.`);\n'
    '  const gone=by("gone");\n'
    '  if(gone.length) bits.push(`<b>${gone.join(", ")} is no longer on YouTube</b> — terminated or deleted. Uploads will fail.`);',
    "gone alert")

# ── sign-in with no client secret ─────────────────────────────────────────
t = sub(t,
'''async function linkStatus(){ if(!SERVED){LINK={configured:false,linked:{},redirect_uri:""};return;}
  try{LINK=await(await fetch("/status")).json();}catch{LINK={configured:false,linked:{},redirect_uri:""};} }''',
'''const GIS_CID="yt_gis_client_id", GIS_TOK="yt_gis_tokens", GIS_LNK="yt_gis_linked";
const gisCid=()=>localStorage.getItem(GIS_CID)||"";
const gisTokens=()=>{try{return JSON.parse(sessionStorage.getItem(GIS_TOK))||{}}catch{return{}}};
const gisSave=o=>sessionStorage.setItem(GIS_TOK,JSON.stringify(o));
const gisLinked=()=>{try{return JSON.parse(localStorage.getItem(GIS_LNK))||{}}catch{return{}}};

async function linkStatus(){
  if(MODE==="local"){
    try{LINK=await(await fetch("/status")).json();}
    catch{LINK={configured:false,linked:{},redirect_uri:""};}
  }else if(MODE==="hosted"){
    LINK={configured:!!gisCid(),linked:gisLinked(),client_id:gisCid(),origin:location.origin};
  }else{
    LINK={configured:false,linked:{},redirect_uri:""};
  }
}

/** Browser sign-in via Google Identity Services. Google hands this tab a one-hour
    access token directly: no client secret exists and the token never leaves the
    device. */
function gisConnect(label){
  const cid=gisCid();
  if(!cid){toast("Add your OAuth Client ID first","r");return;}
  if(!window.google?.accounts?.oauth2){toast("Google sign-in hasn't loaded yet — try again","r");return;}
  google.accounts.oauth2.initTokenClient({
    client_id:cid,
    scope:"https://www.googleapis.com/auth/yt-analytics.readonly",
    prompt:"select_account",
    callback:resp=>{
      if(resp.error){toast("Sign-in failed: "+esc(resp.error),"r");return;}
      const tk=gisTokens();
      tk[label]={token:resp.access_token,exp:Date.now()+(resp.expires_in||3600)*1000};
      gisSave(tk);
      const lk=gisLinked();
      lk[label]={at:new Date().toISOString().slice(0,16).replace("T"," ")};
      localStorage.setItem(GIS_LNK,JSON.stringify(lk));
      closeModal();toast("Channel linked — loading analytics","g");
      linkStatus().then(()=>{ANA={};render();});
    }}).requestAccessToken();
}''', "linkStatus + GIS")

t = sub(t, cut(t, "async function loadAna(l,a,b2){", "function trendEl("),
'''async function loadAna(l,a,b2){
  const k=`${l}|${a}|${b2}`; if(ANA[k])return ANA[k];
  const metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,likes";
  let d;
  if(MODE==="local"){
    const q=new URLSearchParams({ch:l,start:a,end:b2,dimensions:"day",metrics});
    d=await(await fetch("/analytics?"+q)).json();
  }else{
    const tk=gisTokens()[l];
    if(!tk||tk.exp<Date.now()) throw new Error("SESSION_EXPIRED");
    const q=new URLSearchParams({ids:"channel==MINE",startDate:a,endDate:b2,dimensions:"day",metrics});
    const r=await fetch("https://youtubeanalytics.googleapis.com/v2/reports?"+q,
      {headers:{Authorization:"Bearer "+tk.token}});
    d=await r.json();
  }
  if(d.error) throw new Error(typeof d.error==="string"?d.error:(d.error.message||JSON.stringify(d.error)));
  const rows=(d.rows||[]).map(x=>({day:x[0],views:x[1],minutes:x[2],avgDur:x[3],avgPct:x[4],subs:x[5],likes:x[6]}));
  const tot=rows.reduce((z,r)=>({views:z.views+r.views,minutes:z.minutes+r.minutes,subs:z.subs+r.subs}),
    {views:0,minutes:0,subs:0});
  tot.avgDur=rows.length?rows.reduce((z,r)=>z+r.avgDur,0)/rows.length:null;
  tot.avgPct=rows.length?rows.reduce((z,r)=>z+r.avgPct,0)/rows.length:null;
  return ANA[k]={rows,tot};
}

''', "loadAna")

t = sub(t,
    '''      ${anaErr?`<div class="alert e"><b>Linked, but the Analytics request failed.</b><br>${esc(anaErr)}''',
    '''      ${anaErr==="SESSION_EXPIRED"?`<div class="alert i"><b>Analytics sign-in expired.</b>
        Browser sign-ins last an hour — tap <b>Link API</b> to sign in again. Public stats are unaffected.</div>`:""}
      ${anaErr&&anaErr!=="SESSION_EXPIRED"?`<div class="alert e"><b>Linked, but the Analytics request failed.</b><br>${esc(anaErr)}''',
    "expired notice")

# ── the setup modal, per mode ─────────────────────────────────────────────
t = sub(t, cut(t, "function openSetup(forCh){", "/* ══ palette ══ */"),
        MODAL.read_text(encoding="utf-8"), "openSetup")

# ── service worker ────────────────────────────────────────────────────────
t = sub(t, "load();\n</script>",
'''load();
if(MODE==="hosted"&&"serviceWorker" in navigator)
  addEventListener("load",()=>navigator.serviceWorker.register("sw.js").catch(()=>{}));
</script>''', "sw registration")

# ── guard rails ───────────────────────────────────────────────────────────
for tag, n in (("<body>", 1), ("</body>", 1), ("<style>", 1), ("</style>", 1), ("<script>", 1)):
    assert t.count(tag) == n, f"{tag} x{t.count(tag)}"
assert "AIzaSy" not in t, "an API key leaked into the published build"
assert "UCfK4nBw" not in t, "a channel id leaked into the published build"
assert "Million Dollars" in t, "branding missing"

OUT.write_text(t, encoding="utf-8", newline="\n")
print(f"built {OUT} — {len(t)} chars, no secrets embedded")
