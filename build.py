"""Build the public portal from the desktop dashboard.

The published file must contain no channel IDs and no API key: configuration is
seeded once per device by a setup link and kept in localStorage, and the live
channel list is fetched encrypted from channels.enc.

Every edit asserts its anchor so a mismatch fails loudly instead of corrupting
the output.
"""
from pathlib import Path

SRC = Path(r"C:\Users\Zahid\projects\yt-portal\public\index.html")
OUT = Path("index.html")


def sub(t, old, new, what):
    assert old in t, f"anchor missing: {what}"
    assert t.count(old) == 1, f"anchor not unique ({t.count(old)}x): {what}"
    return t.replace(old, new, 1)


t = SRC.read_text(encoding="utf-8")

# ── nothing identifying is baked in ───────────────────────────────────────
t = sub(t, 'const DEFAULT_KEY="AIzaSyDsr2ptOEQbGSvOnTJKN32rceEpS8ZnOIU";',
           'const DEFAULT_KEY="";', "default key")

a = t.index("const CHANNELS=[")
b = t.index("];", a) + 2
t = t[:a] + "let CHANNELS=[];" + t[b:]

# ── config: setup link -> localStorage ────────────────────────────────────
t = sub(t, "let CHANNELS=[];",
r'''let CHANNELS=[];
const CFG_KEY="yt_portal_config";

/** Config never ships inside this file. It arrives once per device through a setup
    link (#setup=<base64 json>) or the setup screen, and then lives in this browser's
    localStorage only — the URL fragment is never sent to the server. */
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

/** The scheduled workflow walks the automation repos and publishes the current
    channel list, AES-GCM encrypted. Decrypting it here means a channel added to the
    automation shows up on its own — and the public file still holds no IDs. */
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
    <div class="alert i" style="max-width:620px">Open the <b>setup link</b> you were given and this fills in
      automatically. Or paste the configuration below &mdash; it stays in this browser only.</div>
    <div class="tbl" style="max-width:620px;padding:18px">
      <div class="fld"><label>Configuration</label>
        <textarea id="cfgIn" rows="7" placeholder='{"apiKey":"AIza…","encKey":"…","channels":[]}'
          style="width:100%;background:var(--surface);border:1px solid var(--line);border-radius:10px;
                 color:var(--fg);padding:10px 12px;font:12px ui-monospace,monospace;resize:vertical"></textarea></div>
      <div class="mrow"><button class="btn pri" id="cfgSave">Save and load</button>
        <span id="cfgMsg" class="note" style="margin:0"></span></div></div>`;
  $("#cfgSave").onclick=()=>{
    try{
      const cfg=JSON.parse($("#cfgIn").value.trim());
      if(!cfg.apiKey) throw new Error("apiKey is required");
      localStorage.setItem(CFG_KEY,JSON.stringify(cfg));
      localStorage.setItem(KEY_STORE,cfg.apiKey);
      if(Array.isArray(cfg.channels)) CHANNELS=cfg.channels;
      toast("Saved &mdash; loading your channels","g"); load();
    }catch(e){ $("#cfgMsg").innerHTML='<span class="warn">'+esc(e.message)+'</span>'; }
  };
}

async function load(){
  const cfg=loadConfig();
  await syncChannels(cfg);
  if(!CHANNELS.length){ beat("err","setup needed"); setupScreen(); return; }''',
        "setup screen")

# ── published status wins over any live guess ─────────────────────────────
t = sub(t, "async function probeOne(c){",
r'''/** The scheduled workflow publishes status.json keyed by SHA-256 of the channel ID,
    so this public file still reveals nothing. It is the only source that can say
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
  }catch{}''', "status map")

# ── relative paths: GitHub Pages serves from /<repo>/ ─────────────────────
for a_, b_ in [('href="/manifest.webmanifest"', 'href="manifest.webmanifest"'),
               ('href="/favicon.png"', 'href="favicon.png"'),
               ('href="/apple-touch-icon.png"', 'href="apple-touch-icon.png"'),
               ('navigator.serviceWorker.register("/sw.js")',
                'navigator.serviceWorker.register("sw.js")')]:
    t = sub(t, a_, b_, a_)

for tag, n in (("<body>", 1), ("</body>", 1), ("<style>", 1), ("</style>", 1), ("<script>", 1)):
    assert t.count(tag) == n, f"{tag} x{t.count(tag)}"
assert "AIzaSy" not in t, "an API key leaked into the public build"
assert "UCfK4nBw" not in t, "a channel id leaked into the public build"

OUT.write_text(t, encoding="utf-8", newline="\n")
print(f"built {OUT} — {len(t)} chars, no secrets embedded")
