"""Show which Google account owns each channel, with one tap to copy it.

The point is signing in on a phone: the handle alone does not tell you which of eight
Gmail accounts a channel lives under. The address is shown next to the handle and
copies to the clipboard when tapped, so it can be pasted straight into the sign-in box.
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
SRC = Path(r"C:\Users\Zahid\YT-Dashboard\dashboard.html")

CSS = """
/* owning Google account */
.mail{display:inline-flex;align-items:center;gap:5px;margin-top:5px;max-width:100%;
  padding:2.5px 8px 2.5px 6px;border-radius:7px;background:var(--raised2);
  border:1px solid var(--line2);font-size:11px;color:var(--muted);
  cursor:pointer;transition:border-color .14s,color .14s,background .14s}
.mail:hover{border-color:var(--accent-line);color:var(--fg);background:var(--accent-soft)}
.mail:active{transform:translateY(.5px)}
.mail .ic{width:12px;height:12px;flex-shrink:0;opacity:.75}
.mail .adr{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.mail.none{cursor:default;border-style:dashed;color:var(--faint)}
.mail.none:hover{border-color:var(--line2);color:var(--faint);background:var(--raised2)}
.mail.done{border-color:var(--green);color:var(--green)}
"""

JS = r"""
/* ══ owning account ══
   Which Gmail a channel lives under is not derivable from anything on screen, and it is
   what you need when signing in on a phone. Tap to copy. */
function mailHTML(c){
  const e=(c.email||"").trim();
  if(!e) return `<div class="mail none" title="Add owner_email to this channel's channels.yaml">
    <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <rect x="2" y="4" width="20" height="16" rx="2.5"/><path d="M2.5 7l9.5 6.5L21.5 7"/></svg>
    <span class="adr">email not recorded</span></div>`;
  return `<div class="mail" data-mail="${esc(e)}" title="Tap to copy">
    <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <rect x="2" y="4" width="20" height="16" rx="2.5"/><path d="M2.5 7l9.5 6.5L21.5 7"/></svg>
    <span class="adr">${esc(e)}</span></div>`;
}
function wireMail(){
  $$(".mail[data-mail]").forEach(el=>{
    el.onclick=async ev=>{
      ev.stopPropagation();                 /* the card itself is a link */
      const v=el.dataset.mail;
      try{ await navigator.clipboard.writeText(v); }
      catch{ const t=document.createElement("textarea"); t.value=v;
             document.body.appendChild(t); t.select();
             try{document.execCommand("copy");}catch{} t.remove(); }
      const s=el.querySelector(".adr"), was=s.textContent;
      el.classList.add("done"); s.textContent="Copied";
      setTimeout(()=>{ el.classList.remove("done"); s.textContent=was; },1200);
    };
  });
}
"""

t = SRC.read_text(encoding="utf-8")
assert "mailHTML" not in t, "already applied"

anchor = "/* safe area — must stay last */"
assert t.count(anchor) == 1
t = t.replace(anchor, CSS.strip() + "\n" + anchor)

js_anchor = "function table(rows,prev,maxPD,best,showCh"
assert t.count(js_anchor) == 1
t = t.replace(js_anchor, JS.strip() + "\n\n" + js_anchor)

# card: under the handle line
OLD_ID = ('      <div class="ch-id"><div class="ch-nm">${esc(c.title)}</div>\n'
          '        <div class="ch-hd">${c.label} · ${esc(c.tiktok)}</div></div>${badge}</div>')
NEW_ID = ('      <div class="ch-id"><div class="ch-nm">${esc(c.title)}</div>\n'
          '        <div class="ch-hd">${c.label} · ${esc(c.tiktok)}</div>\n'
          '        ${mailHTML(c)}</div>${badge}</div>')
assert t.count(OLD_ID) == 1, f"card anchor ({t.count(OLD_ID)})"
t = t.replace(OLD_ID, NEW_ID)

# channel page header
OLD_HD = ('''          <div style="font-size:12px;color:var(--faint)">${label} · ${esc(c.tiktok)} ·
            <a href="https://www.youtube.com/channel/${c.id}" target="_blank" rel="noopener"
               style="color:var(--accent)">YouTube ↗</a></div></div>''')
NEW_HD = ('''          <div style="font-size:12px;color:var(--faint)">${label} · ${esc(c.tiktok)} ·
            <a href="https://www.youtube.com/channel/${c.id}" target="_blank" rel="noopener"
               style="color:var(--accent)">YouTube ↗</a></div>
          ${mailHTML(c)}</div>''')
assert t.count(OLD_HD) == 1, "channel page anchor"
t = t.replace(OLD_HD, NEW_HD)

# both renderers must wire the click
for old, note in [('  wireCommon(overview);', "overview"),
                  ('    wireCommon(draw);', "channel page")]:
    assert t.count(old) == 1, f"wire anchor missing: {note}"
    t = t.replace(old, old + "\n" + (" " * (len(old) - len(old.lstrip()))) + "wireMail();")

SRC.write_text(t, encoding="utf-8")
print(f"patched: {len(t):,} chars")
for k in ["mailHTML", "wireMail()", ".mail{"]:
    print(f"  {k:<14}{t.count(k)}")
